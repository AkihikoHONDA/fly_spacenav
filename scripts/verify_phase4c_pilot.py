"""Independent FK of recorded joint transforms against original u_applied."""
import hashlib,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
OUT=Path('outputs/phase4c');ASSETS=Path('assets/fly_pilot_phase4c')
P=json.loads((ASSETS/'design_params.json').read_text())
def rows(path):
 result=defaultdict(dict)
 for c in RrdReader(path).stream():
  if not c.entity_path.startswith('/pilot'):continue
  b=c.to_record_batch();times=[None]*b.num_rows if c.is_static else b.column('physical_display_s').cast('int64').to_pylist()
  for name in b.schema.names:
   if ':' not in name:continue
   for t,v in zip(times,b.column(name).to_pylist()):
    if v is not None:result[(c.entity_path,name)][t]=v
 return result
def verify(mode):
 path=OUT/(mode+'.rrd');data=rows(path);old=rows(Path('outputs/phase4b')/(mode+'.rrd'))
 unchanged=['/pilot/pedestal','/pilot/joystick/base','/pilot/joystick/shaft','/pilot/joystick/grip','/pilot/command','/pilot/command_range']
 for key,values in old.items():
  if not key[1].startswith('Asset3D:'):assert data[key]==values,key
 assert set(data)==set(old), 'Pilot component set changed'
 m=json.loads((OUT/f'viewer_{mode}.json').read_text());manifest=json.loads((ASSETS/'manifest.json').read_text())
 asset_paths={'/pilot/fly':manifest['body_default']}
 for side in ['left','right']:
  root='/pilot/forelegs/'+side
  for name,end in [('upper','/upper/mesh'),('lower','/upper/lower/mesh'),('foot','/upper/lower/foot/mesh')]:
   asset_paths[root+end]=manifest['segment_assets'][side+'_'+name]
 for entity,asset in asset_paths.items():
  blob=data[(entity,'Asset3D:blob')][None]
  if isinstance(blob,list) and len(blob)==1 and isinstance(blob[0],(bytes,list)):blob=blob[0]
  assert hashlib.sha256(bytes(blob)).hexdigest()==asset['sha256']==sha256(ASSETS/asset['file'])
 maximum=0.;counts=0;directions=[];previous={};minimum_dot=1.
 for trial in m['episodes']:
  previous={}
  with np.load(trial['record']) as d:
   assert sha256(trial['record'])==trial['record_sha256']
   for k,t in enumerate(d['observation_time']):
    ns=round((trial['offset']+float(t))*1e9);a=d['u_applied'][k]
    u=np.clip(np.array([-a[1],a[0]])/.005,-1,1)
    base=np.array([.65,.25,.18]);tip=base+np.r_[.55*u,np.sqrt(1.2**2-np.sum((.55*u)**2))]
    np.testing.assert_allclose(data[('/pilot/joystick/grip','Points3D:positions')][ns],[tip],atol=1e-7)
    np.testing.assert_allclose(data[('/pilot_guide/command','Arrows2D:vectors')][ns],[u*[1,-1]],atol=1e-7)
    assert f"X {-a[1]:+.5f} · Y {a[0]:+.5f} m/s²" in data[('/pilot_values','TextDocument:text')][ns][0]
    shaft=(tip-base)/1.2;side_direction=np.array([0.,1,0])-shaft*shaft[1];side_direction/=np.linalg.norm(side_direction)
    for side,sign in [('left',1),('right',-1)]:
     root='/pilot/forelegs/'+side;upper=root+'/upper';lower=upper+'/lower'
     shoulder=np.array(data[(root,'Transform3D:translation')][None][0])
     r1=np.array(data[(upper,'Transform3D:mat3x3')][ns][0]).reshape(3,3,order='F')
     r2=np.array(data[(lower,'Transform3D:mat3x3')][ns][0]).reshape(3,3,order='F')
     t1=np.array(data[(upper,'Transform3D:translation')][ns][0])
     t2=np.array(data[(lower,'Transform3D:translation')][ns][0])
     foot=np.array(data[(lower+'/foot','Transform3D:translation')][None][0])
     np.testing.assert_allclose(t2,[0,0,P['rig']['lengths'][0]],atol=1e-7)
     np.testing.assert_allclose(foot,[0,0,P['rig']['lengths'][1]],atol=1e-7)
     np.testing.assert_allclose(r1.T@r1,np.eye(3),atol=1e-7)
     np.testing.assert_allclose(r2.T@r2,np.eye(3),atol=1e-7)
     elbow=shoulder+t1+r1@t2;end=elbow+r1@r2@foot
     target=tip+sign*.11*side_direction
     error=float(np.linalg.norm(end-target));maximum=max(maximum,error)
     assert error<4e-7
     np.testing.assert_allclose(np.linalg.norm(elbow-shoulder),P['rig']['lengths'][0],atol=2e-7)
     np.testing.assert_allclose(np.linalg.norm(end-elbow),P['rig']['lengths'][1],atol=2e-7)
     axis=target-shoulder;axis/=np.linalg.norm(axis);bend=elbow-shoulder-axis*np.dot(elbow-shoulder,axis);bend/=np.linalg.norm(bend)
     assert bend[2]<0
     if side in previous:minimum_dot=min(minimum_dot,float(bend@previous[side]))
     previous[side]=bend
    counts+=1
 assert minimum_dot>0
 for side in ['left','right']:
  assert len(data[('/pilot/forelegs/'+side+'/upper','Transform3D:mat3x3')])==counts
 result=dict(status='passed',samples=counts,feet_verified=counts*2,max_fk_contact_error=maximum,minimum_adjacent_bend_dot=minimum_dot,static_assets_verified=len(asset_paths),non_asset_pilot_components_identical_to_phase4b=True,rrd_sha256=sha256(path))
 return result
if __name__=='__main__':
 result={mode:verify(mode) for mode in ['demo','analysis']}
 write_json(OUT/'pilot_verification.json',result);print(json.dumps(result,indent=2))
