import json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.pilot_phase4a import command_state,BASE,LENGTH,TRAVEL,A_REF,load_asset
from flyrendezvous.recording import sha256
@pytest.mark.parametrize("a,screen",[
 ([0,0],[0,0]),([0,.005],[-1,0]),([0,-.005],[1,0]),([-.005,0],[0,1]),([.005,0],[0,-1]),
 ([.01,-.02],[1,-1])])
def test_applied_direction_clip_and_neutral(a,screen):
 s=command_state(a)
 np.testing.assert_allclose((s['tip'][:2]-BASE[:2])*[1,-1]/TRAVEL,screen,atol=1e-14)
 np.testing.assert_allclose(np.linalg.norm(s['tip']-BASE),LENGTH)
 assert s['clipped']==(max(np.abs(a))>A_REF)
def test_every_saved_command_matches_orbit_projection():
 m=json.loads(Path('outputs/phase3w/viewer_multi.json').read_text())
 for trial in m['episodes']:
  with np.load(trial['record']) as d:
   a=d['u_applied'];s=command_state(a)
   assert not s['clipped'].any()
   np.testing.assert_allclose((s['tip'][:,:2]-BASE[:2])*[1,-1],np.column_stack([-a[:,1],-a[:,0]])/A_REF*TRAVEL,atol=1e-14)
   np.testing.assert_allclose(np.linalg.norm(s['tip']-BASE,axis=1),LENGTH)
def test_asset_provenance_and_converted_hash():
 p,m=load_asset()
 assert m['model_uid']=='2baa84955f704a4091a274ef4acec24a'
 assert m['author']=='Glowbox 3D' and m['license']=='CC BY 4.0'
 assert m['armature_count']==0
 for f in m['source_files']:assert sha256(f['path'])==f['sha256']
 assert p.suffix=='.glb'

def test_perspective_projection_has_no_neutral_parallax():
 from flyrendezvous.pilot_phase4a import PILOT_EYE,PILOT_LOOK
 np.testing.assert_array_equal(PILOT_EYE[:2],BASE[:2])
 np.testing.assert_array_equal(PILOT_LOOK[:2],BASE[:2])
 a=np.array([[0,0],[.005,0],[-.005,0],[0,.005],[0,-.005],[.001,-.002]])
 tip=command_state(a)['tip']
 projected=(tip[:,:2]-PILOT_EYE[:2])/(PILOT_EYE[2]-tip[:,2,None])*[1,-1]
 direction=np.column_stack([-a[:,1],-a[:,0]])
 np.testing.assert_allclose(projected[0],[0,0],atol=1e-14)
 np.testing.assert_allclose(projected[:,0]*direction[:,1]-projected[:,1]*direction[:,0],0,atol=1e-14)
 assert np.all(np.sum(projected[1:]*direction[1:],axis=1)>0)
