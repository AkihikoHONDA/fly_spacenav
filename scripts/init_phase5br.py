"""Pre-register Phase 5B-R. No prior logs are training data."""
import json,shutil
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.aggregation_phase5br import ensure_unique
O=Path('outputs/phase5br')
if (O/'contract.json').exists():raise RuntimeError('Already preregistered')
O.mkdir(parents=True,exist_ok=True)
for p in ['configs/phase5br','models/phase5br','docs/evidence_phase5br']:Path(p).mkdir(parents=True,exist_ok=True)
prior=set(json.loads(Path('outputs/phase5b/prior_hashes.json').read_text()))
prior.update(json.loads(Path('outputs/phase5b/manifest.json').read_text())['artifacts'])
prior.add('outputs/phase5b/manifest.json')
for root in ['src','scripts','tests','configs','models','docs']:
    prior.update(str(p) for p in Path(root).rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'phase5br' not in str(p))
write_json(O/'prior_hashes.json',{p:sha256(p) for p in sorted(prior)})
for p in ['README.md','docs/project.md']:shutil.copyfile(p,O/(Path(p).stem+'_before.md'))
cfg=json.loads(Path('configs/phase5b/training.json').read_text())
cfg.update(phase='5B-R',splits={s:dict(count=n,near=0,seed=seed) for s,n,seed in [('train',36,5201),('validation',12,5202),('test',8,5203)]},
    selection_rule=['max success','min catastrophic exits','min median final goal error','min median final speed',
        'min median total dv','min teacher-forced validation MSE','lag0 before lag5','smaller lambda'],
    validation_gate=dict(success_min=10,catastrophic_max=1,median_error_max_m=.50,median_speed_max_m_s=.015),
    augmentation=dict(max_rounds=2,round1_mandatory=True,round2_if_round1_gate_fails=True,weights=1.,
        round1_primary_stride=4,round1_primary_cap=300,round1_total_cap=450,
        round2_total_cap=600,round_cap='N_teacher_train',total_cap='2*N_teacher_train',
        subsampling='equal goal-stratum quota with deterministic midpoint-spaced chronological selection; redistribute unused quotas',
        critical='goal_error<2 OR speed<.03 OR final 10 seconds before catastrophic safety failure',
        final_model_train_diagnostics='36 fresh train rollouts; diagnostic only, no additional dataset or training round'),
    nominal_gate=dict(minimum_success=6,total=8),main_demo='test_00',
    scale_calibration='fresh teacher train+validation control periods; fixed before any test')
write_json('configs/phase5br/training.json',cfg)
splits={};er=np.array(cfg['goal_direction']);ec=np.array([-er[1],er[0]])
for name,spec in cfg['splits'].items():
    rng=np.random.default_rng(spec['seed']);n=spec['count']
    q=np.column_stack([(rng.permutation(n)+rng.random(n))/n for _ in range(4)])
    x=np.array([25,-4,-.02,-.02])+q*np.array([10,8,.04,.04])
    splits[name]=[dict(id=f'{name}_{i:02d}',split=name,seed=spec['seed'],category='approach',
        depth_m=float(v[0]),cross_m=float(v[1]),initial_state=np.r_[v[0]*er+v[1]*ec,v[2:]].tolist()) for i,v in enumerate(x)]
old=json.loads(Path('outputs/phase5b/splits.json').read_text())
fresh=[c['initial_state'] for cs in splits.values() for c in cs]
oldstates=[c['initial_state'] for cs in old.values() for c in cs]
ensure_unique(fresh,oldstates)
write_json(O/'splits.json',splits)
write_json(O/'duplicate_audit.json',dict(fresh=56,old=56,duplicates=0,absolute_all_components_tolerance=1e-12,
    old_split_sha256=sha256('outputs/phase5b/splits.json')))
write_json(O/'contract.json',dict(files={p:sha256(p) for p in ['configs/phase5br/training.json',str(O/'splits.json')]},
    before_trials=True,old_test_reuse=False,main_demo='test_00',truth_evaluation=False))
print('Protected',len(prior),'files; new 36/12/8 split registered')
