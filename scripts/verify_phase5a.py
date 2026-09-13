"""Independent saved-data audit, existing 4C regression with output redirected to 5A."""
import csv,json,math,runpy,hashlib
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
OUT=Path('outputs/phase5a')
def main():
    manifest=json.loads((OUT/'analysis_manifest.json').read_text())
    for p,h in {**manifest['input_sources'],**manifest['code_version']}.items():assert sha256(p)==h,p
    saved=json.loads((OUT/'trial_summary.json').read_text())
    with (OUT/'trial_summary.csv').open() as f:csv_data=list(csv.DictReader(f))
    assert len(saved)==len(csv_data)==12
    cfg=json.loads(Path('configs/phase3.json').read_text());goal=np.array(cfg['goal_direction'])*cfg['standoff_radius_m']
    samples=0
    for row,record in zip(saved,csv_data):
        for key,val in row.items():
            if val is None:assert record[key]==''
            elif isinstance(val,(int,float)):assert float(record[key])==val
            else:assert record[key]==val
        with np.load(f"outputs/phase3/test_learner/{row['trial_id']}.npz") as d:
            u=d['u_applied'];interval=d['acceleration_interval'];state=d['states']
            amounts=[math.hypot(*a)*(b-a0) for a,(a0,b) in zip(u,interval)]
            total=math.fsum(amounts);np.testing.assert_allclose(total,row['total_dv_mps'],rtol=1e-13)
            braking=0.;perp=0.;previous=None;changes45=0;changes90=0
            for a,s,(a0,b),amount in zip(u,state[:-1],interval,amounts):
                speed=math.hypot(*s[2:]);norm=math.hypot(*a);dot=sum(a*s[2:])
                if speed>1e-4:
                    if dot<0:braking+=amount
                    # Independent 2D cross-product formula, rather than projection subtraction.
                    perp+=abs(a[0]*s[3]-a[1]*s[2])/speed*(b-a0)
                if a0>=10 and norm>=.05*np.sqrt(2)*.005:
                    angle=math.atan2(a[1],a[0])
                    if previous is not None:
                        turn=abs(math.atan2(math.sin(angle-previous),math.cos(angle-previous)))*180/math.pi
                        changes45+=turn>=45;changes90+=turn>=90
                    previous=angle
                else:previous=None
            np.testing.assert_allclose(braking/total,row['braking_dv_fraction'],rtol=1e-12)
            np.testing.assert_allclose(perp/total,row['perpendicular_dv_fraction'],rtol=1e-12)
            assert (changes45,changes90)==(row['direction_changes_45deg'],row['direction_changes_90deg'])
            metric=json.loads((OUT/'trials'/(row['trial_id']+'_metrics.json')).read_text())
            for basis,windows in metric['time_windows'].items():
                for window in windows.values():
                    value=math.fsum(math.hypot(*a)*max(0,min(b,window['end_s'])-max(a0,window['start_s'])) for a,(a0,b) in zip(u,interval))
                    np.testing.assert_allclose(value,window['dv_mps'],atol=1e-14)
            for bins in metric['command_distribution'].values():
                for field in ['sample_fraction','time_fraction','dv_fraction']:
                    np.testing.assert_allclose(sum(r[field] for r in bins),1,atol=1e-12)
            for q,t in metric['dv_reach_times_s'].items():
                value=math.fsum(math.hypot(*a)*max(0,min(b,t)-a0) for a,(a0,b) in zip(u,interval) if a0<t)
                np.testing.assert_allclose(value,float(q)*total,atol=1e-13)
            # Scan endpoint conditions independently and require the same saved success time.
            good=(np.linalg.norm(state[:,:2]-goal,axis=1)<.25)&(np.linalg.norm(state[:,2:],axis=1)<.01)
            run=0.;first_complete=None
            for k,(a0,b) in enumerate(interval):
                run=run+b-a0 if a0>=10 and good[k] and good[k+1] else 0.
                if run>=10 and first_complete is None:first_complete=float(b)
            assert first_complete==row['success_time_s']
            samples+=len(u)
    # Verify CSV interval alignment, final N+1 state semantics and Pilot scale using original mapping.
    with (OUT/'test00_timeseries.csv').open() as f:rows=list(csv.DictReader(f))
    with np.load('outputs/phase3/test_learner/test_00.npz') as d:
        assert len(rows)==439
        from flyrendezvous.pilot_phase4a import command_state,BASE,LENGTH
        for k,r in enumerate(rows):
            assert float(r['time_s'])==d['observation_time'][k]
            np.testing.assert_array_equal([float(r['ax_mps2']),float(r['ay_mps2'])],d['u_applied'][k])
            tip=command_state(d['u_applied'][k])['tip']
            tilt=math.degrees(math.acos(np.clip((tip-BASE)[2]/LENGTH,-1,1)))
            np.testing.assert_allclose(float(r['joystick_tilt_deg']),tilt,atol=2e-11)
    # Independent geometric projection only; never render an image or advance a state.
    from flyrendezvous.geometry_phase3 import Camera
    camera=Camera(cfg['camera']);er=np.asarray(cfg['goal_direction']);et=np.array([-er[1],er[0]])
    geometry=json.loads((OUT/'phase5b_geometry_candidates.json').read_text())
    for c in geometry['candidates']:
        pos=c['radial_depth_m']*er+c['cross_offset_abs_m']*et
        projected,visible=camera.project(pos)
        assert visible==c['entire_silhouette_in_fov']
        np.testing.assert_allclose(2*projected[2],c['diameter_px'],atol=1e-12)
        np.testing.assert_allclose(np.linalg.norm(pos-goal),c['goal_error_m'],atol=1e-12)
    pooled=json.loads((OUT/'pooled_command_distribution.json').read_text())['bins']
    for bins in pooled.values():
        for key in ['sample_fraction','time_fraction','dv_fraction']:
            np.testing.assert_allclose(sum(b[key] for b in bins),1,atol=1e-12)
    assert sum(b['samples'] for b in pooled['full'])==samples
    assert sum(b['samples'] for b in pooled['post_observe'])==samples-12*20
    np.testing.assert_allclose(sum(b['dv_mps'] for b in pooled['full']),sum(r['total_dv_mps'] for r in saved),atol=1e-12)
    # Reuse old verifier functions, but redirect every result write away from existing artifacts.
    old=runpy.run_path('scripts/verify_phase4c_regression.py')
    old['main'].__globals__['write_json']=lambda path,data:write_json(OUT/'phase4c_regression.json',data)
    old['main']()
    pilot=runpy.run_path('scripts/verify_phase4c_pilot.py')
    write_json(OUT/'phase4c_pilot_verification.json',{mode:pilot['verify'](mode) for mode in ['demo','analysis']})
    prior=json.loads((OUT/'prior_hashes.json').read_text())
    changed=[p for p,h in prior.items() if not Path(p).is_file() or sha256(p)!=h]
    assert not changed,changed
    result=dict(status='passed',trials=len(saved),samples=samples,old_files_unchanged=len(prior),
        csv_json_exact=True,independent_dv_braking_cross_product_and_angle_audit=True,
        phase4c_regression='passed; result redirected to outputs/phase5a',
        new_inference=0,new_training=0,new_simulation=0)
    write_json(OUT/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
