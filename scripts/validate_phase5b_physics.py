"""Gate 2: preregistered numerical validation before any policy trial."""
import json,time
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
from flyrendezvous.physics_phase5b import *
from flyrendezvous.geometry_phase3 import Teacher
from flyrendezvous.recording import write_json,sha256
O=Path('outputs/phase5b')
cfg=json.loads(Path('configs/phase5b/training.json').read_text())
C=json.loads(Path('configs/phase5b/truth_model.json').read_text())
M={c['name']:c for c in json.loads(Path('configs/phase5b/evaluation_matrix.json').read_text())['conditions']}
assert (O/'gate1.json').exists()
assert json.loads((O/'gate1.json').read_text())['passed']
contract=json.loads((O/'contract.json').read_text())
for p,h in contract['files'].items():assert sha256(p)==h
small=np.array([.1,-.1,.0001,-.0002]);y=to_inertial(small,chief_initial(C));s=small.copy();teacher=Teacher(cfg)
for k in range(120):
    y=advance(k*.5,y,np.zeros(2),M['T0'],C);s=teacher.advance(s,np.zeros(2))
delta=to_relative(y)-s
small_result=dict(position_error_m=float(np.linalg.norm(delta[:2])),velocity_error_m_s=float(np.linalg.norm(delta[2:])),
    duration_s=60,relative_initial=small.tolist(),command=[0,0])
print('small separation',small_result,flush=True)
acc=C['accuracy_gate']
assert small_result['position_error_m']<acc['small_separation_position_error_m']
assert small_result['velocity_error_m_s']<acc['small_separation_velocity_error_m_s']
results=[]
for name,u in [('T0',[.001,-.002]),('E0',[0,0]),('RM3',[-.002,.001])]:
    y0=to_inertial(np.array([-22.,21.,-.02,.02]),chief_initial(C));y=y0.copy()
    ref=y0.copy()
    # Fixed commands, no learned controller; high accuracy reference segmented at residual edges.
    times=[0.,120.,180.,600.]
    for lo,hi in zip(times[:-1],times[1:]):
        res=residual((lo+hi)/2,M[name],C)
        sol=solve_ivp(lambda t,z:rhs(t,z,u,M[name],C,res),(lo,hi),ref,method='DOP853',
            rtol=2.3e-14,atol=1e-10,max_step=2.)
        assert sol.success
        ref=sol.y[:,-1]
    for k in range(1200):y=advance(k*.5,y,u,M[name],C)
    d=(y-ref).reshape(4,2)
    result=dict(condition=name,command_LVLH_m_s2=u,duration_s=600,
        absolute_position_error_m=float(max(np.linalg.norm(d[0]),np.linalg.norm(d[2]))),
        absolute_velocity_error_m_s=float(max(np.linalg.norm(d[1]),np.linalg.norm(d[3]))),
        relative_position_error_m=float(np.linalg.norm((to_relative(y)-to_relative(ref))[:2])),
        relative_velocity_error_m_s=float(np.linalg.norm((to_relative(y)-to_relative(ref))[2:])))
    print('reference',result,flush=True);results.append(result)
    assert result['absolute_position_error_m']<acc['absolute_position_error_m']
    assert result['absolute_velocity_error_m_s']<acc['absolute_velocity_error_m_s']
# Force magnitudes at preregistered representative state, before any teacher/learned trial.
representative=np.array([-30/np.sqrt(2),30/np.sqrt(2),0,0])
y=to_inertial(representative,chief_initial(C))
f=forces(0,y,[0,0],M['E0'],C);magnitudes={}
for term in ['two_body','j2','srp','drag']:
    magnitudes[term]=dict(target_m_s2=float(np.linalg.norm(f['target'][term])),
        chaser_m_s2=float(np.linalg.norm(f['chaser'][term])),
        differential_m_s2=float(np.linalg.norm(f['chaser'][term]-f['target'][term])))
ratios={s:dict(CR_A_over_m_m2_kg=C[s]['C_R']*C[s]['A_srp']/C[s]['mass'],
    CD_A_over_m_m2_kg=C[s]['C_D']*C[s]['A_drag']/C[s]['mass']) for s in ['target','chaser']}
# Physical chief orbit sunlit check for all density levels; no controller involved.
eclipse={}
for name in ['E0','Elo','Ehi']:
    yy=y.copy();dark=0
    for k in range(1200):
        dark+=int(shadow(yy[:2],C) or shadow(yy[4:6],C))
        yy=advance(k*.5,yy,[0,0],M[name],C)
    eclipse[name]=dark
assert not any(eclipse.values())
write_json(O/'perturbation_sanity.json',dict(before_trials=True,initial_relative=representative.tolist(),
    units='m/s^2 unless labeled otherwise',accelerations=magnitudes,property_ratios=ratios,
    chief_radius_m=C['chief_radius_m'],chief_altitude_m=C['chief_radius_m']-C['R_E'],
    sunlit_600_s_no_control_check=eclipse,residual_stress_m_s2=[1e-5,3e-5,5e-5]))
write_json(O/'physics_validation.json',dict(passed=True,small_separation=small_result,integrator=results,
    thresholds=acc,integrator_method='fixed RK4 4 x 0.125 s; DOP853 rtol 2.3e-14 atol 1e-10 max_step 2 s',
    code_sha256=sha256('src/flyrendezvous/physics_phase5b.py')))
print('Gate 2 passed',flush=True)
