import json,subprocess
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.ik_phase4b import solve_ik,pose,settings,project
from flyrendezvous.pilot_phase4a import command_state,BASE,A_REF
from flyrendezvous.pilot_phase4b import load_asset
from flyrendezvous.recording import sha256
P=settings()
@pytest.mark.parametrize('target',[[0,0,0],[10,2,1],[.5,.2,.3],[.048,0,0],[0,1,0]])
def test_ik_lengths_clamp_and_finite(target):
 v=solve_ik([0,0,0],target,*P['rig']['lengths'],[0,1,-.22])
 a,b=P['rig']['lengths']
 np.testing.assert_allclose(np.linalg.norm(v['elbow']),a,atol=1e-12)
 np.testing.assert_allclose(np.linalg.norm(v['end']-v['elbow']),b,atol=1e-12)
 assert np.isfinite(v['end']).all()
 d=np.linalg.norm(target);assert v['clamped']==(d<abs(a-b)+1e-7 or d>a+b-1e-7)
@pytest.mark.parametrize('side',['left','right'])
def test_all_saved_grasps_reachable_constant_length_and_bend(side):
 m=json.loads(Path('outputs/phase4a/viewer_demo.json').read_text())
 for trial in m['episodes']:
  with np.load(trial['record']) as d:
   previous=None
   for a in d['u_applied']:
    s,legs=pose(a,P);v=legs[side];l1,l2=P['rig']['lengths']
    assert not v['clamped'];assert v['error']<1e-12
    np.testing.assert_allclose(v['end'],v['target'],atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(v['elbow']-v['shoulder']),l1,atol=1e-12)
    np.testing.assert_allclose(np.linalg.norm(v['end']-v['elbow']),l2,atol=1e-12)
    np.testing.assert_allclose(v['upper_rotation'].T@v['upper_rotation'],np.eye(3),atol=1e-12)
    assert np.linalg.det(v['lower_local_rotation'])>0.999999
    if previous is not None:assert v['bend']@previous>0 # no branch inversion on recorded transitions
    previous=v['bend']
    np.testing.assert_array_equal(s['tip'],command_state(a)['tip'])
    np.testing.assert_allclose(np.linalg.norm(v['target']-s['tip']),.11,atol=1e-12)
def test_neutral_and_dense_command_grid_no_bend_branch_flip():
 _,neutral=pose([0,0],P)
 assert np.linalg.norm(neutral['left']['end']-neutral['right']['end'])==pytest.approx(.22)
 for x in np.linspace(-.005,.005,21):
  for y in np.linspace(-.005,.005,21):
   s,legs=pose([x,y],P)
   for side,v in legs.items():
    sign=1 if side=='left' else -1
    axis=(v['end']-v['shoulder']);axis/=np.linalg.norm(axis)
    bend_component=v['elbow']-v['shoulder']-axis*np.dot(v['elbow']-v['shoulder'],axis)
    assert bend_component@np.array([0,0,-1])>=-1e-12
@pytest.mark.parametrize('a,axis,sign',[
 ([0,-.005],0,1),([0,.005],0,-1),([.005,0],1,-1),([-.005,0],1,1)])
def test_oblique_projected_axis_sign_and_exact_planar_guide(a,axis,sign):
 zero=command_state([0,0])['tip'];tip=command_state(a)['tip']
 screen=project(tip,P)-project(zero,P)
 assert screen[axis]*sign>0
 guide=command_state(a)['normalized']*[1,-1]
 np.testing.assert_array_equal(guide,np.array([-a[1],-a[0]])/A_REF)
def test_procedural_assets_and_default():
 p,m=load_asset();assert p.name=='stylized_fly_body.glb'
 assert sha256(p)==m['variants']['B']['sha256']
 assert set(m['variants'])==set('ABC')
 assert len({v['sha256'] for v in m['variants'].values()})==3
 assert len(m['segment_assets'])==6
 assert P['variants']['B']['head']/P['variants']['A']['head']==pytest.approx(1.25)
 for k in 'ABC':
  assert Path(f'docs/evidence_phase4b/design_{k}.png').is_file()
def test_generator_reproducible_without_external_assets(tmp_path):
 command=['blender','--background','--disable-autoexec','--python-exit-code','1','--python','assets/fly_pilot_phase4b/generate_stylized_fly.py','--','--output',str(tmp_path),'--no-render']
 r=subprocess.run(command,capture_output=True,text=True,timeout=60)
 assert r.returncode==0,r.stdout[-1500:]+r.stderr[-1500:]
 m=json.loads(Path('assets/fly_pilot_phase4b/manifest.json').read_text())
 for v in [*m['variants'].values(),m['body_default'],*m['segment_assets'].values()]:
  assert sha256(tmp_path/v['file'])==v['sha256']
