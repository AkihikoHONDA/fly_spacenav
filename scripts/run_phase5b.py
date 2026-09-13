"""Phase 5B sequential gated data/training/evaluation, no truth-based tuning."""
import argparse,json,runpy,shutil,time
from pathlib import Path
import numpy as np
from flyrendezvous.phase3_runtime import adapter_config,rollout,save_trial,checked_trial,write_json,sha256,groups
from flyrendezvous.features import Pooling
from flyrendezvous.readout import Readout,ImagePolicy
O=Path('outputs/phase5b')
def config():return json.loads(Path('configs/phase5b/training.json').read_text())
def contracts():
    c=json.loads((O/'contract.json').read_text())
    for p,h in c['files'].items():
        if sha256(p)!=h:raise ValueError('Preregistered file changed: '+p)
    return config(),json.loads((O/'splits.json').read_text())
def neural_setup():
    from flyrendezvous.adapter import FlyvisAdapter
    a=FlyvisAdapter(adapter_config());return a,Pooling(a.nodes,config()['pool_bins'])
def old_training():
    ns=runpy.run_path('scripts/run_phase3.py')
    g=ns['stage_b'].__globals__
    g.update(OUT=O,load_config=config,contracts=contracts,neural_setup=neural_setup)
    return ns
def data():
    assert json.loads((O/'teacher_gate.json').read_text())['passed']
    ns=old_training();ns['stage_b']()
    # Existing non-test calibration, Phase 5B outputs and provenance only.
    source=Path('scripts/calibrate_phase3.py').read_text().replace('outputs/phase3','outputs/phase5b').replace('configs/phase3.json','configs/phase5b/training.json').replace('30 train+validation','48 train+validation')
    exec(compile(source,'phase5b_calibration','exec'),{'__name__':'__main__'})
def train():
    cfg,splits=contracts()
    assert json.loads((O/'data.json').read_text())['status']=='passed'
    if (O/'model_lock.json').exists() or (O/'test_started.json').exists():raise RuntimeError('Already locked')
    a,p=neural_setup();episodes=json.loads((O/'data.json').read_text())['episodes']
    selected=old_training()['candidates'](cfg,splits,a,p,
        [m for m in episodes if m['split']=='train'],[m for m in episodes if m['split']=='validation'],'readout_candidates')
    dest=Path('models/phase5b/readout.npz');shutil.copyfile(selected['model'],dest)
    write_json(O/'readout_selection.json',dict(selected=selected,
        candidates=json.loads((O/'readout_candidates/candidates.json').read_text()),
        nominal_validation_only=True,augmentation_rounds=0))
    source_paths=['src/flyrendezvous/adapter.py','src/flyrendezvous/features.py','src/flyrendezvous/readout.py',
        'src/flyrendezvous/phase3_runtime.py','src/flyrendezvous/phase5b_runtime.py',
        'src/flyrendezvous/physics_phase5b.py','scripts/run_phase5b.py']
    write_json(O/'model_lock.json',dict(readout=str(dest),readout_sha256=sha256(dest),
        pooling_sha256=sha256(O/'pooling.npz'),parameter_sha256=a.parameter_hash(),
        config_files=json.loads((O/'contract.json').read_text())['files'],
        source_files={p:sha256(p) for p in source_paths},
        display_scales_sha256=sha256(O/'display_scales.json'),before_held_out=True))
def check_model():
    cfg,splits=contracts();lock=json.loads((O/'model_lock.json').read_text())
    assert sha256(lock['readout'])==lock['readout_sha256']
    assert sha256(O/'display_scales.json')==lock['display_scales_sha256']
    assert sha256(O/'pooling.npz')==lock['pooling_sha256']
    for p,h in lock['source_files'].items():assert sha256(p)==h,p
    return cfg,splits,lock
def evaluate(stage):
    cfg,splits,lock=check_model()
    matrix=json.loads(Path('configs/phase5b/evaluation_matrix.json').read_text())['conditions']
    names={'h0':['H0'],'physical':['T0','T1','E0','Elo','Ehi'],'residual':['R1','R3','R5','RM3']}[stage]
    if stage!='h0':assert json.loads((O/'h0_evaluation.json').read_text())['passed']
    if stage=='residual':assert (O/'physical_evaluation.json').exists()
    marker=O/(stage+'_started.json')
    if marker.exists():raise RuntimeError('Stage already started; do not repeat or tune')
    write_json(marker,dict(readout_sha256=lock['readout_sha256'],conditions=names,main_demo='test_00'))
    if stage=='h0':write_json(O/'test_started.json',dict(readout_sha256=lock['readout_sha256']))
    a,p=neural_setup();assert a.parameter_hash()==lock['parameter_sha256']
    policy=ImagePolicy(a,p,Readout.load(lock['readout']),cfg['a_max'])
    from flyrendezvous.phase5b_runtime import rollout as truth_rollout
    results=[]
    for name in names:
        condition=next(c for c in matrix if c['name']==name)
        for case in splits['test']:
            for mode in ['teacher','learner']:
                if name=='H0':
                    arrays,m=rollout(cfg,case,mode,a if mode=='learner' else None,p if mode=='learner' else None,
                        policy if mode=='learner' else None)
                else:
                    arrays,m=truth_rollout(cfg,case,mode,a if mode=='learner' else None,p if mode=='learner' else None,
                        policy if mode=='learner' else None,condition=condition)
                m.update(condition=name,truth_category=condition['category'],
                    controller_label='image-only Flyvis readout' if mode=='learner' else 'perfect-state nominal HCW LQR sanity reference')
                m=save_trial(O/'evaluation'/name/mode,arrays,m);results.append(m)
                write_json(O/(stage+'_progress.json'),dict(results=results))
                print(name,case['id'],mode,m['termination_reason'],round(m['final_position_error_m'],6),flush=True)
    passes=True
    if stage=='h0':passes=sum(m['success'] for m in results if m['controller']=='learner')>=cfg['nominal_gate']['minimum_success']
    write_json(O/(stage+'_evaluation.json'),dict(passed=passes,results=results,readout_sha256=lock['readout_sha256']))
    if not passes:raise SystemExit('STOP: nominal H0 gate failed; truth evaluation prohibited')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['data','train','h0','physical','residual'])
    stage=parser.parse_args().stage
    if stage=='data':data()
    elif stage=='train':train()
    else:evaluate(stage)
