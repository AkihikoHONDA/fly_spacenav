"""Phase 4C asset and strict presentation-only regression contracts."""
import json,struct,subprocess
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous import pilot_phase4c
from flyrendezvous.ik_phase4b import pose,settings
from flyrendezvous.recording import sha256

ASSETS=Path('assets/fly_pilot_phase4c')
P=json.loads((ASSETS/'design_params.json').read_text())
OLD=settings()

def glb(path):
 data=Path(path).read_bytes()
 length,kind=struct.unpack_from('<II',data,12)
 assert kind==0x4e4f534a
 return json.loads(data[20:20+length]),data

def test_unchanged_rig_camera_layout_and_original_ik():
 assert P['rig']==OLD['rig']
 assert P['camera']==OLD['camera']
 assert P['design_camera']==OLD['design_camera']
 assert pilot_phase4c.pose is pose
 old=Path('src/flyrendezvous/viewer_phase4b.py').read_text()
 new=Path('src/flyrendezvous/viewer_phase4c.py').read_text()
 assert new==old.replace('phase4b','phase4c').replace('Phase4B','Phase4C')
 old=Path('src/flyrendezvous/pilot_phase4b.py').read_text()
 new=Path('src/flyrendezvous/pilot_phase4c.py').read_text()
 # Everything that logs live frames and clears between trials is byte-identical code.
 assert new[new.index('def log_sample'):]==old[old.index('def log_sample'):]

def test_every_saved_pose_exactly_equal_to_4b():
 count=0
 for entry in json.loads(Path('outputs/phase4b/viewer_demo.json').read_text())['episodes']:
  with np.load(entry['record']) as data:
   assert sha256(entry['record'])==entry['record_sha256']
   for applied in data['u_applied']:
    old_s,old_legs=pose(applied,OLD);s,legs=pose(applied,P)
    for key in old_s:np.testing.assert_array_equal(s[key],old_s[key])
    for side in old_legs:
     for key in old_legs[side]:np.testing.assert_array_equal(legs[side][key],old_legs[side][key])
     assert not legs[side]['clamped']
    count+=1
 assert count==777

def test_c2_contract_and_no_textures():
 _,manifest=pilot_phase4c.load_asset()
 assert manifest['default']=='C2'
 assert set(manifest['variants'])=={'C1','C2','C3'}
 assert manifest['body_default']['sha256']==manifest['variants']['C2']['sha256']
 d=P['variants']['C2']
 assert d['head']/OLD['variants']['B']['head']==pytest.approx(.85)
 assert d['head_xyz'][0]<d['head_xyz'][1]
 assert d['eye_xyz'][2]>max(d['eye_xyz'][:2])
 assert .78<=d['leg_distal']/.06<=d['leg_radius']/.06<=.85
 assert P['variants']['C3']['head']/d['head']==pytest.approx(1.06)
 for variant in manifest['variants'].values():
  model,_=glb(ASSETS/variant['file'])
  assert not model.get('textures') and not model.get('images')
  assert len(model['nodes'])==variant['objects']
  wing=next(m for m in model['materials'] if m['name']=='wings')
  assert wing['alphaMode']=='BLEND'
  assert wing['pbrMetallicRoughness']['baseColorFactor'][3]<.35
  assert all('emissiveFactor' not in m for m in model['materials'])
 model,_=glb(ASSETS/'stylized_fly_body.glb')
 names=[n['name'] for n in model['nodes']]
 assert all('Antenna_'+side in names for side in ['left','right'])

@pytest.mark.parametrize('side',['left','right'])
def test_limb_glb_geometry_is_tapered_with_fixed_kinematic_length(side):
 for segment in ['upper','lower']:
  model,data=glb(ASSETS/f'stylized_front_leg_{side}_{segment}.glb')
  mesh=next(m for m in model['meshes'] if m['name']==side+'_'+segment)
  accessor=model['accessors'][mesh['primitives'][0]['attributes']['POSITION']]
  view=model['bufferViews'][accessor['bufferView']]
  json_length=struct.unpack_from('<I',data,12)[0]
  start=20+json_length+8+view.get('byteOffset',0)+accessor.get('byteOffset',0)
  xyz=np.frombuffer(data,dtype='<f4',count=accessor['count']*3,offset=start).reshape(-1,3)
  assert xyz[:,2].min()==pytest.approx(0,abs=1e-7)
  assert xyz[:,2].max()==pytest.approx(.62,abs=1e-7)
  radii=np.linalg.norm(xyz[:,:2],axis=1)
  assert max(radii[np.isclose(xyz[:,2],0)])==pytest.approx(P['variants']['C2']['leg_radius'],abs=1e-7)
  assert max(radii[np.isclose(xyz[:,2],.62)])==pytest.approx(P['variants']['C2']['leg_distal'],abs=1e-7)

def test_deterministic_regeneration_all_variants_and_limbs(tmp_path):
 cmd=['blender','--background','--disable-autoexec','--python-exit-code','1','--python',str(ASSETS/'generate_fly_phase4c.py'),'--','--output',str(tmp_path),'--no-render']
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
 assert r.returncode==0,r.stdout[-1500:]+r.stderr[-1500:]
 manifest=json.loads((ASSETS/'manifest.json').read_text())
 for item in [*manifest['variants'].values(),manifest['body_default'],*manifest['segment_assets'].values()]:
  assert sha256(tmp_path/item['file'])==item['sha256']
 assert sha256(tmp_path/'manifest.json')==sha256(ASSETS/'manifest.json')
