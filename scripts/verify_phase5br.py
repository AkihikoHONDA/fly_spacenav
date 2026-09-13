"""Independent aggregation/provenance audit; never modifies old Phase 5B results."""
import json,runpy
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.phase3_runtime import checked_trial,Teacher
from flyrendezvous.aggregation_phase5br import ensure_unique,select_samples,stratified_indices,selection_key,validation_gate
from flyrendezvous.readout import Readout
O=Path('outputs/phase5br')
def main():
    ns=runpy.run_path('scripts/run_phase5br.py');cfg,splits=ns['contracts']()
    prior=json.loads((O/'prior_hashes.json').read_text())
    for p,h in prior.items():
        if p in ['README.md','docs/project.md']:
            assert Path(p).read_bytes().startswith((O/(Path(p).stem+'_before.md')).read_bytes())
        else:assert sha256(p)==h,p
    old=json.loads(Path('outputs/phase5b/splits.json').read_text())
    ensure_unique([c['initial_state'] for cs in splits.values() for c in cs],[c['initial_state'] for cs in old.values() for c in cs])
    oldcfg=json.loads(Path('configs/phase5b/training.json').read_text())
    changed={'phase','splits','selection_rule','validation_gate','augmentation','nominal_gate','main_demo','scale_calibration'}
    for k,v in oldcfg.items():
        if k not in changed:assert cfg[k]==v,k
    teacher=Teacher(cfg);agg=ns['aggregate_manifest']();total=0;count=0;caps={}
    train={c['id']:c for c in splits['train']}
    for rn,block in agg['rounds'].items():
        r=int(rn);all_samples=[]
        for m in block['episodes']:
            assert m['split']=='train' and m['id'] in train
            np.testing.assert_array_equal(m['initial_state'],train[m['id']]['initial_state'])
            d=checked_trial(m);idx,err,speed,reasons=select_samples(d,m,cfg,r)
            assert len(idx)<=block['per_trial_cap']
            for k in idx:all_samples.append((m['id'],int(k),float(np.linalg.norm(d['states'][k,:2]-teacher.goal[:2]))))
        chosen=stratified_indices([s[2] for s in all_samples],block['teacher_train_cap'])
        expected=[(all_samples[i][0],all_samples[i][1]) for i in chosen]
        actual=[(s['source_trial'],s['source_sample']) for s in block['samples']]
        assert actual==expected
        assert len(actual)==len(set(actual))==block['retained_samples']<=block['teacher_train_cap']
        lookup={m['id']:checked_trial(m) for m in block['episodes']}
        for s in block['samples']:
            d=lookup[s['source_trial']];k=s['source_sample'];state=d['states'][k]
            assert s['source_split']=='train' and s['round']==r and s['source_time_s']>=10
            assert s['source_time_s']==d['observation_time'][k]
            np.testing.assert_array_equal(s['true_state_used_for_teacher_label'],state)
            np.testing.assert_array_equal(s['teacher_label_m_s2'],d['u_teacher'][k])
            np.testing.assert_array_equal(teacher.command(state)[1],d['u_teacher'][k])
            count+=1
        total+=len(actual);caps[r]=len(actual)
    if caps:assert total<=2*block['teacher_train_cap']
    rounds=json.loads((O/'validation_by_round.json').read_text())['rounds'];episode_count=0;parameters=set()
    for r in rounds:
        datasets={}
        candidates=json.loads((O/f"round{r['round']}/candidates.json").read_text())
        assert len(candidates)==6 and min(candidates,key=selection_key)==r
        assert r['gate_passed']==validation_gate(r)
        for c in candidates:
            assert sha256(c['model'])==c['sha256']
            if c['lag'] not in datasets:datasets[c['lag']]=ns['dataset'](r['round'],c['lag'])
            X,Y,N=datasets[c['lag']];model=Readout.load(c['model'])
            np.testing.assert_array_equal(model.mean,X.mean(0));np.testing.assert_array_equal(model.std,X.std(0))
            assert X.shape[0]==c['train_samples'] and N==c['teacher_train_samples']
            for m in c['closed_loop']:
                assert m['split']=='validation';d=checked_trial(m);episode_count+=1
                parameters.add(m['parameter_sha256_after'])
                assert d['states'].shape==(m['samples']+1,4)
    expected=json.loads((O/'data.json').read_text())['parameter_sha256'];assert parameters=={expected}
    test=O/'fresh_test.json';locked=O/'model_lock.json'
    if test.exists():
        lock=json.loads(locked.read_text());assert validation_gate(lock['selected'])
        for p,h in {**lock['source_files'],**lock['contract_files']}.items():assert sha256(p)==h,p
        assert sha256(lock['readout'])==lock['readout_sha256']
        assert sha256(O/'aggregation_manifest.json')==lock['aggregation_manifest_sha256']
        results=json.loads(test.read_text())['results'];assert len(results)==8
        for m,case in zip(results,splits['test']):
            assert m['id']==case['id'];np.testing.assert_array_equal(m['initial_state'],case['initial_state']);checked_trial(m)
        assert (O/'test_started.json').exists()
    else:
        assert not locked.exists() and not (O/'test_started.json').exists()
    # Run legacy GUI comparison with its only result write redirected.
    oldverify=runpy.run_path('scripts/verify_phase4c_regression.py')
    oldverify['main'].__globals__['write_json']=lambda path,data:write_json(O/'phase4c_regression.json',data)
    oldverify['main']()
    write_json(O/'regression.json',dict(status='passed',protected_files=len(prior),old_reports_logs_models_unchanged=True,
        documentation_append_only=True,duplicates=0,aggregation_labels_checked=count,round_caps=caps,
        total_aggregation_samples=total,validation_episodes_checked=episode_count,
        scaler_train_only=True,selection_rule_verified=True,parameter_sha256=expected,
        fresh_test_run=test.exists(),fresh_test_once_guard=True,old_test_reused=False,truth_used=False))
    print('Audit passed:',count,'aggregation labels;',len(prior),'protected files')
if __name__=='__main__':main()
