"""Semi-stylized C2 and illustrative foreleg IK; the Phase 4A command stays exact."""
import json
from pathlib import Path
import numpy as np
from .recording import sha256
from .pilot_phase4a import command_state,BASE,LENGTH,TRAVEL,A_REF
from .ik_phase4b import settings,pose
ASSETS=Path('assets/fly_pilot_phase4c')
PARAMS=json.loads((ASSETS/"design_params.json").read_text())
PILOT_EYE=PARAMS['camera']['position']
PILOT_LOOK=PARAMS['camera']['look_target']
PILOT_UP=PARAMS['camera']['eye_up']
def load_asset():
 m=json.loads((ASSETS/'manifest.json').read_text())
 assert m['default']=='C2' and not m['external_assets']
 assert sha256(ASSETS/'design_params.json')==m['params_sha256']
 for item in [m['body_default'],*m['segment_assets'].values()]:
  if sha256(ASSETS/item['file'])!=item['sha256']:raise ValueError('Procedural asset hash mismatch')
 return ASSETS/m['body_default']['file'],m
def log_static(allow_missing=False):
 import rerun as rr
 import trimesh
 asset,m=load_asset()
 def mesh(path,obj,color):
  rr.log(path,rr.Mesh3D(vertex_positions=obj.vertices,triangle_indices=obj.faces,vertex_normals=obj.vertex_normals,albedo_factor=color),static=True)
 pedestal=trimesh.creation.box(extents=[4.3,3.5,.15]);pedestal.apply_translation([0,-.2,-.12])
 mesh('/pilot/pedestal',pedestal,[95,108,125])
 base=trimesh.creation.cylinder(radius=.42,height=.16,sections=32);base.apply_translation(BASE-[0,0,.08])
 mesh('/pilot/joystick/base',base,[120,132,150])
 ring=BASE+np.array([[-TRAVEL,-TRAVEL,0],[TRAVEL,-TRAVEL,0],[TRAVEL,TRAVEL,0],[-TRAVEL,TRAVEL,0],[-TRAVEL,-TRAVEL,0]])
 rr.log('/pilot/command_range',rr.LineStrips3D(ring,colors=[100,115,135],radii=.01),static=True)
 rr.log('/pilot/fly',rr.Asset3D(path=asset),static=True)
 rr.log('/pilot/neutral',rr.LineStrips3D([BASE,BASE+[0,0,LENGTH]],colors=[190,190,190,90],radii=.012),static=True)
 for side in ['left','right']:
  root='/pilot/forelegs/'+side
  rr.log(root,rr.Transform3D(translation=PARAMS['rig']['shoulders'][side]),static=True)
  for segment,path in [('upper',root+'/upper/mesh'),('lower',root+'/upper/lower/mesh'),('foot',root+'/upper/lower/foot/mesh')]:
   rr.log(path,rr.Asset3D(path=ASSETS/m['segment_assets'][side+'_'+segment]['file']),static=True)
  rr.log(root+'/upper/lower/foot',rr.Transform3D(translation=[0,0,PARAMS['rig']['lengths'][1]]),static=True)
 rr.log('/pilot_guide/bounds',rr.LineStrips2D([[-1.15,-1.15],[1.15,-1.15],[1.15,1.15],[-1.15,1.15],[-1.15,-1.15]],colors=[90,100,115]),static=True)
 rr.log('/pilot_guide/axes',rr.LineStrips2D([[[-1,0],[1,0]],[[0,-1],[0,1]]],colors=[85,95,110]),static=True)
 rr.log('/pilot_guide/zero',rr.Points2D([[0,0]],radii=.055,colors=[130,140,150]),static=True)
def log_sample(applied):
 import rerun as rr
 s,legs=pose(applied,PARAMS);tip=s['tip']
 # Same geometry, color, source signal, and timestamp as Phase 4A.
 rr.log('/pilot/joystick/shaft',rr.LineStrips3D([BASE,tip],colors=[185,195,205],radii=.055))
 rr.log('/pilot/joystick/grip',rr.Points3D([tip],radii=.13,colors=[80,215,225]))
 rr.log('/pilot/command',rr.Arrows3D(origins=[[BASE[0],BASE[1],BASE[2]+.01]],vectors=[[*(tip[:2]-BASE[:2]),0]],colors=[255,170,70],radii=.025))
 rr.log('/pilot/forelegs',rr.Transform3D(scale=1.))
 for side,v in legs.items():
  root='/pilot/forelegs/'+side+'/upper'
  rr.log(root,rr.Transform3D(translation=[0,0,0],mat3x3=v['upper_rotation']))
  rr.log(root+'/lower',rr.Transform3D(translation=[0,0,PARAMS['rig']['lengths'][0]],mat3x3=v['lower_local_rotation']))
 guide=s['normalized']*[1,-1]
 rr.log('/pilot_guide/command',rr.Arrows2D(origins=[[0,0]],vectors=[guide],colors=[255,170,70]))
 rr.log('/pilot_guide/tip',rr.Points2D([guide],radii=.075,colors=[80,215,225]))
 rr.log('/pilot_values',rr.TextDocument(
  'Joystick: learned 2D command.\nForelegs: illustrative IK, not biological motor output.\n'
  f"X {s['display'][0]:+.5f} · Y {s['display'][1]:+.5f} m/s²\n"
  'Guide: left = along-track; down = central body.',media_type='text/plain'))
 return s
def reset():
 import rerun as rr
 rr.log('/pilot/forelegs',rr.Transform3D(scale=0.))
 for path in ['/pilot_guide/command','/pilot_guide/tip']:rr.log(path,rr.Clear(recursive=True))
