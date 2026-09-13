"""Compare each saved Rerun sample with its fresh held-out source."""
import json
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.display_coordinates import rerun_coordinates
from flyrendezvous.pilot_phase4a import command_state,BASE
from flyrendezvous.representatives_phase3v import intensity_color
from flyrendezvous.activity_display import relative_activity,TYPES
O=Path('outputs/phase5br')
def main():
    m=json.loads((O/'fresh_test.json').read_text())['results'][0];d=checked_trial(m);N=m['samples']
    scales=json.loads((O/'display_scales.json').read_text())
    delta=d['display_activity'].astype(float)-d['baseline'][d['display_indices']]
    raw=np.sqrt(np.mean(delta**2,axis=2));q=relative_activity(raw,scales['p05'],scales['p95'])
    paths={'/orbit/craft':'Points2D:positions','/pilot/joystick/shaft':'LineStrips3D:strips',
        '/input/image':'Image:buffer','/series/acceleration/test_00/ax':'Scalars:scalars',
        '/series/acceleration/test_00/ay':'Scalars:scalars'}
    for name in ['T2','T4a','T5d']:paths['/brain/multi/'+name+'/arbors']='LineStrips3D:colors'
    values={p:{} for p in paths}
    for c in RrdReader(O/'demo/H0/demo.rrd').stream():
        p=c.entity_path
        if c.is_static or p not in paths:continue
        b=c.to_record_batch();col=paths[p]
        if col not in b.schema.names:continue
        times=b.column('physical_display_s').cast('int64').to_pylist()
        for ns,v in zip(times,b.column(col).to_pylist()):
            assert ns%500000000==0
            k=ns//500000000;assert k not in values[p];values[p][k]=v
    visual=json.loads(Path('configs/phase3w.json').read_text())
    override=Path('outputs/phase3w/display_override.json')
    if override.exists():visual.update(json.loads(override.read_text()))
    for p,rows in values.items():assert sorted(rows)==list(range(N)),p
    for k in range(N):
        for i,axis in enumerate(['ax','ay']):
            np.testing.assert_allclose(values['/series/acceleration/test_00/'+axis][k],[d['u_applied'][k,i]],rtol=0,atol=1e-9)
        np.testing.assert_allclose(values['/orbit/craft'][k],[rerun_coordinates(d['states'][k,:2])],rtol=0,atol=2e-6)
        np.testing.assert_allclose(values['/pilot/joystick/shaft'][k],[np.array([BASE,command_state(d['u_applied'][k])['tip']])],rtol=0,atol=2e-7)
        buffer=values['/input/image'][k][0]
        actual=np.frombuffer(buffer,dtype=np.uint8) if isinstance(buffer,bytes) else np.array(buffer,dtype=np.uint8)
        np.testing.assert_array_equal(actual.reshape(64,64),np.rint(d['images'][k]*255).astype(np.uint8))
        for name in ['T2','T4a','T5d']:
            rgba=[*intensity_color(name,q[k,TYPES.index(name)]),visual['morphology_alpha']]
            expected=int.from_bytes(bytes(rgba),'big')
            assert values['/brain/multi/'+name+'/arbors'][k]==[expected],(name,k)
    a=Path('src/flyrendezvous/viewer_phase5b.py').read_text();b=Path('src/flyrendezvous/viewer_phase5br.py').read_text()
    section=lambda s:s[s.index('    brain_eye='):s.index('    rr.init(')]
    assert section(a)==section(b)
    cap=json.loads(Path('docs/evidence_phase5br/H0/screenshots_demo.json').read_text())
    for s in cap['screenshots']+[cap['terminal_frame']]:assert sha256(s['file'])==s['sha256']
    video=json.loads((O/'mp4/H0_verification.json').read_text())
    assert sha256(video['file'])==video['sha256'] and video['source_record_sha256']==m['record_sha256']
    write_json(O/'viewer_verification.json',dict(status='passed',samples=N,component_streams=len(paths),
        exact_source_record_sha256=m['record_sha256'],rrd_sha256=sha256(O/'demo/H0/demo.rrd'),
        images_exact_uint8=True,within_type_q_colors_exact=True,applied_commands=True,
        orbit_positions=True,pilot_shaft_follows_original_scale=True,blueprint_unchanged_from_phase5b=True,
        coordinate_float32_tolerance_m=2e-6,pilot_float32_tolerance=2e-7,
        command_tolerance_m_s2=1e-9,mp4_frames=video['frames'],new_inference=False))
    print('RRD verified',N,'samples across',len(paths),'streams')
if __name__=='__main__':main()
