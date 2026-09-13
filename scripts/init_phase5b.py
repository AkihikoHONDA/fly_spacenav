"""Pre-register Phase 5B before any new trial."""
import json, shutil
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
O=Path('outputs/phase5b')
if (O/'contract.json').exists():raise RuntimeError('Already preregistered')
O.mkdir(parents=True,exist_ok=True)
for d in ['configs/phase5b','models/phase5b','docs/evidence_phase5b']:Path(d).mkdir(parents=True,exist_ok=True)
prior=json.loads(Path('outputs/phase5a/prior_hashes.json').read_text())
paths=set(prior)
for root in ['outputs/phase5a','docs/evidence_phase5a']:
    paths.update(str(p) for p in Path(root).rglob('*') if p.is_file())
for root in ['src','scripts','tests','configs','models','docs']:
    paths.update(str(p) for p in Path(root).rglob('*') if p.is_file() and 'phase5b' not in str(p).lower() and '__pycache__' not in str(p))
write_json(O/'prior_hashes.json',{p:sha256(p) for p in sorted(paths)})
for p in ['README.md','docs/project.md']:
    shutil.copyfile(p,O/(Path(p).stem+'_before.md'))
cfg=json.loads(Path('configs/phase3.json').read_text())
cfg.update(max_phys_seconds=600,approach_radial_m=[25.,35.],cross_offset_m=[-4.,4.],
    splits={s:dict(count=n,near=0,seed=seed) for s,n,seed in [('train',36,5101),('validation',12,5102),('test',8,5103)]},
    augmentation=dict(max_rounds=0,reason='Six original candidates only; no additional training round'),
    teacher_gate=dict(required_success=56,total=56,resampling=False),
    nominal_gate=dict(minimum_success=6,total=8,rule='Stop before truth when H0 successes < 6/8'),
    phase='5B',sampling='independent randomized Latin hypercube per split, four dimensions',
    units=dict(position='m',velocity='m/s',acceleration='m/s^2',time='s',n='rad/s'))
write_json('configs/phase5b/training.json',cfg)
truth=dict(mu_E=3.986004418e14,R_E=6378137.,J2=1.08262668e-3,omega_E=7.2921150e-5,n=cfg['n'],
    chief_radius_m=(3.986004418e14/cfg['n']**2)**(1/3),P_srp=4.57e-6,
    sun_direction_ECI=[float(1/np.sqrt(2))]*2,
    target=dict(mass=500.,A_srp=4.,C_R=1.3,A_drag=4.,C_D=2.2),
    chaser=dict(mass=100.,A_srp=5.,C_R=1.5,A_drag=5.,C_D=2.2),
    residual_direction_ECI=[0.,1.],residual_on_s=120.,residual_off_s=180.,
    substeps=4,dt_phys=.5,cylindrical_shadow=True,
    accuracy_gate=dict(duration_s=600.,absolute_position_error_m=1e-4,absolute_velocity_error_m_s=1e-7,
       small_separation_duration_s=60.,small_separation_position_error_m=1e-5,small_separation_velocity_error_m_s=1e-7),
    units=dict(mu_E='m^3/s^2',R_E='m',omega_E='rad/s',J2='dimensionless',P_srp='N/m^2',
       density='kg/m^3',mass='kg',area='m^2',state='ECI m, m/s',residual='m/s^2'),
    sources=dict(earth='https://earth-info.nga.mil/?action=wgs84&dir=wgs84',
        J2='https://kelvins.esa.int/gtoc9-kessler-run/constants/',
        SRP='https://ntrs.nasa.gov/api/citations/20240004259/downloads/GEONSMS_R3_0_NASA-TP-20240004259.pdf',
        density='https://ccmc.gsfc.nasa.gov/models/NRLMSIS~00/'))
write_json('configs/phase5b/truth_model.json',truth)
matrix=[]
for name,j2,srp,rho,res,mid in [
    ('H0',False,False,0,0,False),('T0',False,False,0,0,False),('T1',True,False,0,0,False),
    ('E0',True,True,1e-12,0,False),('Elo',True,True,3e-13,0,False),('Ehi',True,True,3e-12,0,False),
    ('R1',True,True,1e-12,1e-5,False),('R3',True,True,1e-12,3e-5,False),
    ('R5',True,True,1e-12,5e-5,False),('RM3',True,True,1e-12,3e-5,True)]:
    matrix.append(dict(name=name,dynamics='HCW' if name=='H0' else 'nonlinear_equatorial_ECI',
       j2=j2,srp=srp,density_kg_m3=rho,residual_m_s2=res,midcourse=mid,
       category='nominal' if name=='H0' else 'residual_stress' if res else 'nonlinear_only' if name=='T0' else 'physical'))
write_json('configs/phase5b/evaluation_matrix.json',dict(conditions=matrix,main_demo='test_00',
    demo_conditions=['H0','E0','RM3'],playback_speed=15,controller_input='image only',
    state_baseline='nominal HCW LQR; perfect current relative state; no truth feedforward'))
splits={};er=np.asarray(cfg['goal_direction']);et=np.array([-er[1],er[0]])
for name,spec in cfg['splits'].items():
    rng=np.random.default_rng(spec['seed']);N=spec['count']
    q=np.column_stack([(rng.permutation(N)+rng.random(N))/N for _ in range(4)])
    x=np.array([25,-4,-.02,-.02])+q*np.array([10,8,.04,.04])
    splits[name]=[dict(id=f'{name}_{i:02d}',split=name,seed=spec['seed'],category='approach',
        depth_m=float(v[0]),cross_m=float(v[1]),initial_state=np.r_[v[0]*er+v[1]*et,v[2:]].tolist()) for i,v in enumerate(x)]
assert len({tuple(c['initial_state']) for cs in splits.values() for c in cs})==56
write_json(O/'splits.json',splits)
locked=['configs/phase5b/training.json','configs/phase5b/truth_model.json','configs/phase5b/evaluation_matrix.json',str(O/'splits.json')]
write_json(O/'contract.json',dict(files={p:sha256(p) for p in locked},before_all_trials=True,
    main_demo='test_00',nominal_min_success=6,truth_retuning=False))
print('Preregistered 36/12/8 Latin hypercube; protected',len(paths),'old files',flush=True)
