"""Audit actual RRD joystick geometry and labels against all saved applied commands."""
import hashlib,json
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.pilot_phase4a import load_asset,BASE,LENGTH,TRAVEL,A_REF
OUT=Path('outputs/phase4a')
def verify(mode):
 asset,meta=load_asset();manifest=json.loads((OUT/f'viewer_{mode}.json').read_text())
 expected={}
 for trial in manifest['episodes']:
  assert sha256(trial['record'])==trial['record_sha256']
  with np.load(trial['record']) as d:
   for k,t in enumerate(d['observation_time']):
    a=d['u_applied'][k].astype(float);xy=np.array([-a[1],a[0]]);u=np.clip(xy/A_REF,-1,1)
    tip=BASE+np.r_[TRAVEL*u,np.sqrt(LENGTH**2-np.sum((TRAVEL*u)**2))]
    expected[round((trial['offset']+float(t))*1e9)]=(a,xy,tip)
 counts={p:set() for p in ['/pilot/joystick/shaft','/pilot/joystick/grip','/pilot/command','/pilot_values']};static_asset=False
 for chunk in RrdReader(OUT/f'{mode}.rrd').stream():
  p=chunk.entity_path;b=chunk.to_record_batch()
  if p=='/pilot/fly':
   assert chunk.is_static
   blob=b.column('Asset3D:blob')[0].as_py()
   # Arrow binary columns may expose a singleton list of byte buffers.
   if isinstance(blob,list) and len(blob)==1 and isinstance(blob[0],(bytes,list)):blob=blob[0]
   assert hashlib.sha256(bytes(blob)).hexdigest()==sha256(asset)
   static_asset=True
  if p not in counts or chunk.is_static:continue
  key={'/pilot/joystick/shaft':'LineStrips3D:strips','/pilot/joystick/grip':'Points3D:positions','/pilot/command':'Arrows3D:vectors','/pilot_values':'TextDocument:text'}[p]
  if key not in b.schema.names:continue
  for ns,value in zip(b.column('physical_display_s').cast('int64').to_pylist(),b.column(key).to_pylist()):
   if value is None:continue
   a,xy,tip=expected[ns]
   if p.endswith('shaft'):np.testing.assert_allclose(value,[[BASE,tip]],atol=1e-7)
   elif p.endswith('grip'):np.testing.assert_allclose(value,[tip],atol=1e-7)
   elif p.endswith('command'):np.testing.assert_allclose(value,[[*(tip[:2]-BASE[:2]),0]],atol=1e-7)
   else:
    assert f"a_disp X {xy[0]:+.5f} · Y {xy[1]:+.5f} m/s²" in value[0]
    assert 'not biological motor output' in value[0]
   counts[p].add(ns)
 assert static_asset and all(s==set(expected) for s in counts.values())
 return dict(samples=len(expected),component_samples={p:len(v) for p,v in counts.items()},static_asset_sha256=sha256(asset),rrd_sha256=sha256(OUT/f'{mode}.rrd'),status='passed')
if __name__=='__main__':
 r={m:verify(m) for m in ['demo','analysis']}
 write_json(OUT/'pilot_verification.json',r);print(json.dumps(r,indent=2))
