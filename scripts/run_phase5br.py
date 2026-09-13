"""Bounded train-only aggregation, nominal HCW only. Fresh test behind fixed gate."""
import argparse,json,runpy,shutil,time
from pathlib import Path
import numpy as np
from flyrendezvous.phase3_runtime import rollout,save_trial,checked_trial,adapter_config,Teacher
from flyrendezvous.recording import write_json,sha256
from flyrendezvous.features import Pooling,history_matrix
from flyrendezvous.readout import Readout,ImagePolicy
from flyrendezvous.aggregation_phase5br import *
O=Path('outputs/phase5br')
def cfg():return json.loads(Path('configs/phase5br/training.json').read_text())
def contracts():
    for p,h in json.loads((O/'contract.json').read_text())['files'].items():
        if sha256(p)!=h:raise ValueError('Fixed config/split changed: '+p)
    return cfg(),json.loads((O/'splits.json').read_text())
def setup():
    from flyrendezvous.adapter import FlyvisAdapter
    a=FlyvisAdapter(adapter_config())
    expected=json.loads((O/'gpu_reproducibility.json').read_text())['parameter_hashes'][0]['before']
    if a.parameter_hash()!=expected:raise ValueError('Flyvis parameters changed')
    return a,Pooling(a.nodes,cfg()['pool_bins'])
def start(name):
    p=O/(name+'_started.json')
    if p.exists():raise RuntimeError('Already started: '+name)
    write_json(p,dict(stage=name,once_only=True))
def teacher():
    config,splits=contracts()
    if not json.loads((O/'gpu_reproducibility.json').read_text())['safe_to_continue']:raise RuntimeError('GPU gate')
    start('teacher');results=[]
    for cases in splits.values():
        for case in cases:
            d,m=rollout(config,case,'teacher');results.append(save_trial(O/'teacher_gate',d,m))
            print(case['id'],m['termination_reason'],flush=True)
    write_json(O/'teacher_gate.json',dict(passed=all(m['success'] for m in results),success=sum(m['success'] for m in results),total=56,results=results))
    if not all(m['success'] for m in results):raise SystemExit('STOP: fresh teacher gate failed')
def data():
    assert json.loads((O/'teacher_gate.json').read_text())['passed'];start('data')
    old=runpy.run_path('scripts/run_phase3.py');old['stage_b'].__globals__.update(OUT=O,load_config=cfg,contracts=contracts,neural_setup=setup)
    old['stage_b']()
    source=Path('scripts/calibrate_phase3.py').read_text().replace('outputs/phase3','outputs/phase5br').replace('configs/phase3.json','configs/phase5br/training.json').replace('30 train+validation','48 train+validation')
    exec(compile(source,'phase5br_calibration','exec'),{'__name__':'__main__'})
def teacher_episodes():
    return json.loads((O/'data.json').read_text())['episodes']
def aggregate_manifest():
    p=O/'aggregation_manifest.json'
    return json.loads(p.read_text()) if p.exists() else dict(rounds={},old_data_used=False,weights=1.)
def dataset(round_number,lag):
    X=[];Y=[];config=cfg()
    for m in teacher_episodes():
        if m['split']!='train':continue
        d=checked_trial(m);x=history_matrix(d['phi'],lag);idx=np.flatnonzero(d['control_mask']&np.isfinite(x).all(1))
        X.append(x[idx]);Y.append(d['u_teacher'][idx]/config['a_max'])
    N_teacher=sum(map(len,X))
    agg=aggregate_manifest()
    for r in range(1,round_number+1):
        block=agg['rounds'][str(r)]
        assert block['retained_samples']<=N_teacher
        groups={}
        for item in block['samples']:groups.setdefault(item['source_trial'],[]).append(item['source_sample'])
        lookup={m['id']:m for m in block['episodes']}
        for trial,indices in groups.items():
            m=lookup[trial]
            if m['split']!='train':raise ValueError('Nontrain aggregation')
            d=checked_trial(m);x=history_matrix(d['phi'],lag);idx=np.array(indices,int)
            if not np.isfinite(x[idx]).all():raise ValueError('Invalid causal history')
            X.append(x[idx]);Y.append(d['u_teacher'][idx]/config['a_max'])
    assert sum(map(len,X))<=N_teacher*(1+round_number)
    return np.concatenate(X),np.concatenate(Y),N_teacher
def val_data(lag):
    X=[];Y=[]
    for m in teacher_episodes():
        if m['split']!='validation':continue
        d=checked_trial(m);x=history_matrix(d['phi'],lag);idx=d['control_mask']&np.isfinite(x).all(1)
        X.append(x[idx]);Y.append(d['u_teacher'][idx]/cfg()['a_max'])
    return np.concatenate(X),np.concatenate(Y)
def train(round_number):
    config,splits=contracts()
    if round_number not in [0,1,2]:raise ValueError('Round3 forbidden')
    if (O/'model_lock.json').exists() or (O/'test_started.json').exists():raise RuntimeError('No post-lock training')
    if round_number and str(round_number) not in aggregate_manifest()['rounds']:raise RuntimeError('Aggregation missing')
    if round_number==2 and json.loads((O/'round1/selected.json').read_text())['gate_passed']:raise RuntimeError('Round2 not allowed after pass')
    start(f'round{round_number}_train');a,p=setup();directory=O/f'round{round_number}';directory.mkdir(exist_ok=True)
    results=[]
    for lag in config['history_lags']:
        X,Y,N=dataset(round_number,lag);VX,VY=val_data(lag)
        for lam in config['ridge_lambdas']:
            name=f'lag{lag}_lambda{lam:g}';model=Readout.fit(X,Y,lag,lam,config['constant_std_threshold'])
            path=Path('models/phase5br')/f'round{round_number}_{name}.npz';model.save(path)
            reloaded=Readout.load(path);np.testing.assert_array_equal(model.predict(VX),reloaded.predict(VX))
            policy=ImagePolicy(a,p,reloaded,config['a_max']);closed=[]
            for case in splits['validation']:
                d,m=rollout(config,case,'learner',a,p,policy);closed.append(save_trial(directory/name,d,m))
            r=dict(round=round_number,candidate=name,lag=lag,regularization=lam,model=str(path),sha256=sha256(path),
                train_samples=len(X),teacher_train_samples=N,retained_features=int(model.keep.sum()),
                train_mse=float(np.mean((model.predict(X)-Y)**2)),validation_mse=float(np.mean((model.predict(VX)-VY)**2)),
                success=sum(m['success'] for m in closed),total=12,
                catastrophic_exits=sum(m['termination_reason'] in CATASTROPHIC for m in closed),
                median_final_goal_error=float(np.median([m['final_position_error_m'] for m in closed])),
                median_final_speed=float(np.median([m['final_speed_m_s'] for m in closed])),
                median_total_dv=float(np.median([m['integrated_acceleration_m_s'] for m in closed])),closed_loop=closed)
            r['gate_passed']=validation_gate(r);results.append(r);write_json(directory/'candidates.json',results)
            print(f'Round{round_number}',name,r['success'],'/12 catastrophic',r['catastrophic_exits'],'median error',r['median_final_goal_error'],flush=True)
    chosen=min(results,key=selection_key);write_json(directory/'selected.json',chosen)
    index=[json.loads((O/f'round{r}/selected.json').read_text()) for r in range(round_number+1)]
    write_json(O/'validation_by_round.json',dict(rounds=index,selection_rule=config['selection_rule']))
    print('Selected',chosen['candidate'],'gate',chosen['gate_passed'],flush=True)
def collect(source_round,diagnostic=False):
    config,splits=contracts();selected=json.loads((O/f'round{source_round}/selected.json').read_text())
    target_round=source_round+1
    if not diagnostic and target_round not in [1,2]:raise ValueError('No Round3')
    if not diagnostic and target_round==2 and selected['gate_passed']:raise RuntimeError('Round2 gate already passed')
    if (O/'test_started.json').exists():raise RuntimeError('No train collection after test')
    name=f'round{source_round}_train_diagnostic' if diagnostic else f'aggregation_round{target_round}'
    start(name);a,p=setup();model=Readout.load(selected['model'])
    assert sha256(selected['model'])==selected['sha256'];policy=ImagePolicy(a,p,model,config['a_max'])
    episodes=[];samples=[]
    for case in splits['train']:
        d,m=rollout(config,case,'learner',a,p,policy);m=save_trial(O/name,d,m);episodes.append(m)
        if not diagnostic:
            idx,errors,speeds,reasons=select_samples(d,m,config,target_round)
            for k,e,v,why in zip(idx,errors,speeds,reasons):
                samples.append(dict(source_trial=m['id'],source_split='train',source_record=m['record'],
                    source_record_sha256=m['record_sha256'],source_sample=int(k),source_time_s=float(d['observation_time'][k]),
                    true_state_used_for_teacher_label=d['states'][k].tolist(),teacher_label_m_s2=d['u_teacher'][k].tolist(),
                    goal_error_m=float(e),relative_speed_m_s=float(v),sampling_reason=why,round=target_round))
        print(name,case['id'],m['termination_reason'],flush=True)
    write_json(O/(name+'.json'),dict(source_model=selected['model'],source_model_sha256=selected['sha256'],
        source_round=source_round,episodes=episodes,diagnostic_only=diagnostic))
    if diagnostic:return
    _,_,N=dataset(0,0);before=len(samples);idx=stratified_indices([s['goal_error_m'] for s in samples],N)
    samples=[samples[i] for i in idx];agg=aggregate_manifest()
    agg['rounds'][str(target_round)]=dict(source_round=source_round,source_model=selected['model'],
        source_model_sha256=selected['sha256'],episodes=episodes,samples=samples,
        before_global_cap=before,retained_samples=len(samples),teacher_train_cap=N,
        per_trial_cap=450 if target_round==1 else 600)
    assert sum(b['retained_samples'] for b in agg['rounds'].values())<=2*N
    write_json(O/'aggregation_manifest.json',agg)
def final_round():
    rounds=json.loads((O/'validation_by_round.json').read_text())['rounds']
    return rounds[-1]
def lock_model():
    config,splits=contracts();r=final_round()
    if r['round']==0:raise RuntimeError('Round1 required')
    if not validation_gate(r):raise RuntimeError('Validation gate failed; do not open test')
    if (O/'model_lock.json').exists():raise RuntimeError('Already locked')
    path=Path('models/phase5br/readout.npz');shutil.copyfile(r['model'],path)
    sources=['scripts/run_phase5br.py','src/flyrendezvous/aggregation_phase5br.py',
        'src/flyrendezvous/phase3_runtime.py','src/flyrendezvous/adapter.py','src/flyrendezvous/features.py','src/flyrendezvous/readout.py']
    write_json(O/'model_lock.json',dict(selected=r,readout=str(path),readout_sha256=sha256(path),
        parameter_sha256=json.loads((O/'data.json').read_text())['parameter_sha256'],
        source_files={s:sha256(s) for s in sources},contract_files=json.loads((O/'contract.json').read_text())['files'],
        display_scales_sha256=sha256(O/'display_scales.json'),aggregation_manifest_sha256=sha256(O/'aggregation_manifest.json'),
        pooling_sha256=sha256(O/'pooling.npz'),test_used=False,
        locked_data_files={str(p):sha256(p) for p in [
            O/'data.json',O/'validation_by_round.json',O/f"round{r['round']}/selected.json",
            O/'aggregation_manifest.json',O/'display_scales.json',O/'pooling.npz',path]}))
def test():
    config,splits=contracts();r=final_round()
    require_test_allowed(r,(O/'model_lock.json').exists(),(O/'test_started.json').exists())
    lock=json.loads((O/'model_lock.json').read_text())
    check_locked_files(lock['locked_data_files'])
    if lock['selected']!=r:raise RuntimeError('Selected round differs from model lock')
    for path,h in {**lock['source_files'],**lock['contract_files']}.items():assert sha256(path)==h,path
    assert sha256(lock['readout'])==lock['readout_sha256']
    assert sha256(O/'aggregation_manifest.json')==lock['aggregation_manifest_sha256']
    assert sha256(O/'display_scales.json')==lock['display_scales_sha256']
    start('test');a,p=setup();policy=ImagePolicy(a,p,Readout.load(lock['readout']),config['a_max']);results=[]
    for case in splits['test']:
        d,m=rollout(config,case,'learner',a,p,policy);m.update(condition='H0')
        results.append(save_trial(O/'evaluation/H0/learner',d,m))
        write_json(O/'test_progress.json',dict(results=results))
        print('fresh test',case['id'],m['termination_reason'],flush=True)
    write_json(O/'fresh_test.json',dict(results=results,success=sum(m['success'] for m in results),total=8,
        recovery_passed=sum(m['success'] for m in results)>=6,
        catastrophic_exits=sum(m['termination_reason'] in CATASTROPHIC for m in results),
        median_final_goal_error=float(np.median([m['final_position_error_m'] for m in results])),
        median_final_speed=float(np.median([m['final_speed_m_s'] for m in results])),
        readout_sha256=lock['readout_sha256'],old_test_reused=False,truth_evaluation=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['teacher','data','train','collect','diagnostic','lock','test']);p.add_argument('--round',type=int,default=0)
    args=p.parse_args()
    if args.stage=='train':train(args.round)
    elif args.stage in ['collect','diagnostic']:collect(args.round,args.stage=='diagnostic')
    elif args.stage=='lock':lock_model()
    else:globals()[args.stage]()
