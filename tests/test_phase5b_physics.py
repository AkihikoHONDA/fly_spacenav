import copy,json
from pathlib import Path
import numpy as np
from flyrendezvous.physics_phase5b import *
C=json.loads(Path('configs/phase5b/truth_model.json').read_text())
M={c['name']:c for c in json.loads(Path('configs/phase5b/evaluation_matrix.json').read_text())['conditions']}
def test_round_trip_rotating_velocity():
    rng=np.random.default_rng(5100)
    for _ in range(50):
        angle=rng.uniform(-np.pi,np.pi);r=C['chief_radius_m']*np.array([np.cos(angle),np.sin(angle)])
        v=C['n']*quarter(r)+rng.normal(0,1,2)
        s=rng.uniform([-35,-35,-.1,-.1],[35,35,.1,.1])
        np.testing.assert_allclose(to_relative(to_inertial(s,np.r_[r,v])),s,atol=2e-9,rtol=0)
def test_zero_separation_identical_properties():
    c=copy.deepcopy(C);c['chaser']=c['target'].copy();y=to_inertial(np.zeros(4),chief_initial(c))
    for k in range(40):y=advance(k*.5,y,np.zeros(2),M['E0'],c)
    np.testing.assert_array_equal(to_relative(y),np.zeros(4))
def test_control_follows_current_basis_chaser_only():
    chief=chief_initial(C);angle=.8;B=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    chief=np.r_[B@chief[:2],B@chief[2:]];y=to_inertial(np.array([25,1,0,0]),chief)
    for i in range(2):
        u=np.eye(2)[i]*.005;f=forces(0,y,u,M['T0'],C)
        np.testing.assert_allclose(f['chaser']['control'],B@u,atol=1e-18)
        np.testing.assert_array_equal(f['target']['control'],[0,0])
def test_j2_equator_and_zero_limit():
    r=np.array([C['chief_radius_m'],1234.]);rr=np.linalg.norm(r)
    expected=-1.5*C['J2']*C['mu_E']*C['R_E']**2/rr**5*r
    np.testing.assert_allclose(j2(r,C),expected,rtol=1e-15)
    c={**C,'J2':0};y=to_inertial(np.array([25,1,0,0]),chief_initial(c))
    np.testing.assert_array_equal(rhs(0,y,[0,0],M['T1'],c),rhs(0,y,[0,0],M['T0'],c))
def test_srp_magnitude_direction_shadow_and_common_mode():
    sun=np.array(C['sun_direction_ECI']);r=C['chief_radius_m']*sun;p=C['target']
    a=srp(r,p,C)
    np.testing.assert_allclose(np.linalg.norm(a),C['P_srp']*p['C_R']*p['A_srp']/p['mass'],rtol=1e-15)
    assert a@sun<0 and not shadow(r,C) and shadow(-r,C)
    np.testing.assert_array_equal(srp(-r,p,C),[0,0])
    np.testing.assert_array_equal(srp(r,p,C)-srp(r+np.array([1,0]),p,C),[0,0])
    assert not shadow(C['chief_radius_m']*quarter(sun),C)
def test_drag_opposes_relative_atmosphere_and_zero():
    chief=chief_initial(C);r=chief[:2];v=chief[2:];p=C['target']
    rel=v-C['omega_E']*quarter(r);a=drag(r,v,p,1e-12,C)
    assert a@rel<0
    np.testing.assert_array_equal(drag(r,v,p,0,C),[0,0])
    np.testing.assert_array_equal(drag(r,v,p,1e-12,C)-drag(r,v,p,1e-12,C),[0,0])
def test_residual_exact_boundaries_and_target_exclusion():
    c=M['RM3']
    for t,mag in [(0,0),(119.999,0),(120,3e-5),(179.999,3e-5),(180,0),(600,0)]:
        np.testing.assert_array_equal(residual(t,c,C),[0,mag])
    y=to_inertial(np.array([30,1,0,0]),chief_initial(C))
    f=forces(130,y,[0,0],c,C)
    np.testing.assert_array_equal(f['target']['residual'],[0,0])
    np.testing.assert_array_equal(f['chaser']['residual'],[0,3e-5])
def test_residual_rk4_has_no_boundary_leak():
    # Isolate acceleration in an inertial zero-gravity test system; exact impulse.
    c={**C,'mu_E':0.,'omega_E':0.}
    cond={**M['RM3'],'j2':False,'srp':False,'density_kg_m3':0}
    y=np.array([7e6,0,0,0,7e6+30,0,0,0],float)
    original=y.copy()
    for t in [119.5]:y=advance(t,y,[0,0],cond,c)
    np.testing.assert_array_equal(y,original)
    for k in range(120):y=advance(120+k*.5,y,[0,0],cond,c)
    np.testing.assert_allclose(y[7],60*3e-5,atol=2e-17)
    v=y[7];y=advance(180,y,[0,0],cond,c)
    assert y[7]==v
