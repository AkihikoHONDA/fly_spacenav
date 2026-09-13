"""Read-only checks of saved Phase 5B logs, old artifacts and source semantics."""
import ast,json,runpy
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.readout import Readout
O=Path('outputs/phase5b')
def main():
    contract=json.loads((O/'contract.json').read_text());lock=json.loads((O/'model_lock.json').read_text())
    for p,h in {**contract['files'],**lock['source_files']}.items():assert sha256(p)==h,p
    assert sha256(lock['readout'])==lock['readout_sha256']
    prior=json.loads((O/'prior_hashes.json').read_text())
    changed=[]
    for p,h in prior.items():
        if p in ['README.md','docs/project.md']:
            before=(O/(Path(p).stem+'_before.md')).read_bytes()
            assert Path(p).read_bytes().startswith(before),p
        elif not Path(p).is_file() or sha256(p)!=h:changed.append(p)
    assert not changed,changed
    cfg=json.loads(Path('configs/phase5b/training.json').read_text())
    old=json.loads(Path('configs/phase3.json').read_text())
    for field in ['n','a_max','dt_phys','dt_neural','observe_seconds','success_position_m','success_speed_m_s',
        'success_hold_seconds','Q_diag','R_diag','camera','pool_bins','history_lags','ridge_lambdas',
        'constant_std_threshold','display','goal_direction','standoff_radius_m','collision_margin_m',
        'max_range_m','approach_velocity_m_s','teacher_cost_frame']:assert cfg[field]==old[field],field
    splits=json.loads((O/'splits.json').read_text());states=[c['initial_state'] for cases in splits.values() for c in cases]
    assert len(states)==len(set(map(tuple,states)))==56
    for name,cases in splits.items():
        N=len(cases);sample=np.array([[c['depth_m'],c['cross_m'],*c['initial_state'][2:]] for c in cases])
        q=(sample-np.array([25,-4,-.02,-.02]))/np.array([10,8,.04,.04])
        assert np.all((q>=0)&(q<1))
        for j in range(4):np.testing.assert_array_equal(np.sort((q[:,j]*N).astype(int)),np.arange(N))
    sources=[]
    for path in [O/'teacher_gate.json',O/'data.json',O/'h0_evaluation.json']:
        j=json.loads(path.read_text());sources.extend(j.get('episodes',j.get('results',[])))
    candidates=json.loads((O/'readout_candidates/candidates.json').read_text())
    for c in candidates:sources.extend(c['closed_loop'])
    assert len(candidates)==6
    count=0;neural_samples=0;param=set()
    for m in sources:
        d=checked_trial(m);n=len(d['sample_id']);count+=1
        assert n==m['samples'] and d['states'].shape==(n+1,4)
        np.testing.assert_array_equal(d['states'][0],m['initial_state'])
        np.testing.assert_array_equal(d['sample_id'],np.arange(n))
        np.testing.assert_array_equal(d['acceleration_interval'],np.c_[np.arange(n)*.5,(np.arange(n)+1)*.5])
        assert np.all(d['u_applied'][d['observation_time']<10]==0)
        assert np.max(abs(d['u_applied']))<=cfg['a_max']
        if 'phi' in d:
            assert d['phi'].shape==(n,912)
            param.add(m['parameter_sha256_after']);neural_samples+=n
        # Independent original endpoint hold semantics and safety first.
        goal=np.array(cfg['goal_direction'])*5
        good=(np.linalg.norm(d['states'][:,:2]-goal,axis=1)<.25)&(np.linalg.norm(d['states'][:,2:],axis=1)<.01)
        hold=0;completion=None
        for k in range(n):
            hold=hold+.5 if k>=20 and good[k] and good[k+1] else 0
            if hold>=10 and completion is None:completion=(k+1)*.5
        if m['success']:assert completion==m['final_time_s']
    assert param=={lock['parameter_sha256']}
    learner=next(node for node in ast.walk(ast.parse(Path('src/flyrendezvous/readout.py').read_text())) if isinstance(node,ast.ClassDef) and node.name=='ImagePolicy')
    step=next(node for node in learner.body if isinstance(node,ast.FunctionDef) and node.name=='step')
    assert [a.arg for a in step.args.args]==['self','image']
    # Every learner call in both rollouts receives only image.
    for p in ['src/flyrendezvous/phase3_runtime.py','src/flyrendezvous/phase5b_runtime.py']:
        tree=ast.parse(Path(p).read_text())
        calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and isinstance(node.func.value,ast.Name) and node.func.value.id=='policy' and node.func.attr=='step']
        assert len(calls)==1 and len(calls[0].args)==1 and ast.unparse(calls[0].args[0])=='image'
    # The existing GUI verifier's only write is redirected to the new phase.
    oldcheck=runpy.run_path('scripts/verify_phase4c_regression.py')
    oldcheck['main'].__globals__['write_json']=lambda p,d:write_json(O/'phase4c_regression.json',d)
    oldcheck['main']()
    # Check presentation blueprint, Pilot and Brain imports against unchanged Phase 4C.
    v4=Path('src/flyrendezvous/viewer_phase4c.py').read_text();v5=Path('src/flyrendezvous/viewer_phase5b.py').read_text()
    get=lambda s:s[s.index('    brain_eye='):s.index('    rr.init(')]
    assert get(v4)==get(v5)
    for p in ['src/flyrendezvous/pilot_phase4c.py','src/flyrendezvous/ik_phase4b.py','configs/phase3w.json']:
        assert sha256(p)==prior[p]
    h0=json.loads((O/'h0_evaluation.json').read_text())
    assert not h0['passed']
    for stage in ['physical','residual']:assert not (O/(stage+'_started.json')).exists()
    assert not (O/'evaluation/T0').exists()
    write_json(O/'regression.json',dict(status='passed',old_files_unchanged=len(prior)-2,
        documentation_append_only=2,total_protected=len(prior),saved_episodes_checked=count,
        neural_samples_checked=neural_samples,parameter_sha256=next(iter(param)),
        original_phase3_result={'approach':[8,8],'near':[2,4]},
        phase4c_GUI_component_regression=True,phase4c_blueprint_and_pilot_unchanged=True,
        image_only_interface=True,truth_stages_not_started=True,
        note='Saved data/source audit; GPU numerical-prefix test results are separately reported, not covered by this pass'))
    print('Saved audit passed',count,'episodes;',len(prior),'protected files',flush=True)
if __name__=='__main__':main()
