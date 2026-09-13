"""Phase 5A entry point: only reads saved trials; writes new audit artifacts."""
import csv,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flyrendezvous.analysis_phase5a import analyze,VELOCITY_THRESHOLD,ACTIVE_THRESHOLDS,overlap,events
from flyrendezvous.recording import sha256

OUT=Path('outputs/phase5a');FIG=Path('docs/evidence_phase5a')
FIELDS=['states','observation_time','acceleration_interval','sample_id','u_applied','control_mask']
OPTIONAL=['u_raw','u_teacher','projection']
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    return x
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean(data),indent=2,allow_nan=False,ensure_ascii=False)+'\n')
def csv_rows(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(clean(rows))
def save(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=160,bbox_inches='tight')
    fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
def main():
    OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
    cfg=json.loads(Path('configs/phase3.json').read_text())
    evaluation=json.loads(Path('outputs/phase3/evaluation.json').read_text())['learner']
    split=json.loads(Path('outputs/phase3/splits.json').read_text())['test']
    assert len(evaluation)==len(split)==12
    inputs=['configs/phase3.json','outputs/phase3/evaluation.json','outputs/phase3/splits.json',
            'outputs/phase4c/viewer_demo.json','outputs/phase4c/video_manifest_demo.json',
            'src/flyrendezvous/phase3_runtime.py','src/flyrendezvous/geometry_phase3.py','src/flyrendezvous/camera.py',
            'src/flyrendezvous/hcw.py','src/flyrendezvous/readout.py','src/flyrendezvous/viewer_phase4c.py',
            'src/flyrendezvous/pilot_phase4a.py','assets/fly_pilot_phase4c/design_params.json']
    summaries=[];all_metrics={};datasets={};series_by_trial={};missing=[]
    for case in split:
        m=next(m for m in evaluation if m['id']==case['id'])
        path=Path(m['record']);meta=path.with_suffix('.json')
        if not path.exists() or not meta.exists():
            missing.append(dict(trial=case['id'],reason='missing raw NPZ or metadata'));continue
        assert sha256(path)==m['record_sha256']
        assert json.loads(meta.read_text())==m
        with np.load(path,allow_pickle=False) as z:
            absent=[k for k in FIELDS if k not in z.files]
            if absent:missing.append(dict(trial=case['id'],reason='missing fields',fields=absent));continue
            d={k:z[k] for k in FIELDS+OPTIONAL if k in z.files}
        np.testing.assert_array_equal(d['states'][0],case['initial_state'])
        summary,metrics,series=analyze(d,m,cfg)
        np.testing.assert_allclose(summary['total_dv_mps'],m['integrated_acceleration_m_s'],rtol=1e-12,atol=1e-14)
        np.testing.assert_allclose(summary['final_goal_error_m'],m['final_position_error_m'],rtol=1e-12)
        np.testing.assert_allclose(summary['final_speed_mps'],m['final_speed_m_s'],rtol=1e-12)
        assert metrics['conditions']['success_hold_start_s']==m['first_hold_time_s']
        assert metrics['conditions']['longest_hold_s']==m['longest_hold_s']
        assert summary['duration_s']==m['final_time_s']
        assert (metrics['conditions']['criteria_hold_completed_s'] is not None)==m['success']
        inputs += [str(path),str(meta)]
        summaries.append(summary);all_metrics[m['id']]=metrics;datasets[m['id']]=d;series_by_trial[m['id']]=series
        write(OUT/'trials'/(m['id']+'_metrics.json'),metrics)
    write(OUT/'trial_summary.json',summaries);csv_rows(OUT/'trial_summary.csv',summaries)
    write(OUT/'all_trial_metrics.json',all_metrics)
    pooled={}
    for basis in ['full','post_observe']:
        bins=[]
        sample_total=sum(r['samples']-(20 if basis=='post_observe' else 0) for r in summaries)
        duration_total=sum(r['post_observe_duration_s' if basis=='post_observe' else 'duration_s'] for r in summaries)
        dv_total=sum(r['total_dv_mps'] for r in summaries)
        for j in range(7):
            selected=[m['command_distribution'][basis][j] for m in all_metrics.values()]
            count=sum(x['samples'] for x in selected);duration=sum(x['time_s'] for x in selected);amount=sum(x['dv_mps'] for x in selected)
            bins.append(dict(lower_fraction=selected[0]['lower_fraction'],upper_fraction=selected[0]['upper_fraction'],
                samples=count,sample_fraction=count/sample_total,time_s=duration,time_fraction=duration/duration_total,
                dv_mps=amount,dv_fraction=amount/dv_total))
        pooled[basis]=bins
    write(OUT/'pooled_command_distribution.json',dict(weighting='Pooled samples/time/effort, not equal-trial means; unequal durations and failure censoring retained',bins=pooled))
    if 'test_00' not in datasets:raise RuntimeError('test_00 required detail log missing')
    s=series_by_trial['test_00'];d=datasets['test_00'];m=all_metrics['test_00']
    write(OUT/'test00_metrics.json',m)
    csv_rows(OUT/'test00_timeseries.csv',[{k:v[i] for k,v in s.items()} for i in range(len(s['time_s']))])
    video=json.loads(Path('outputs/phase4c/video_manifest_demo.json').read_text())
    viewer=json.loads(Path('outputs/phase4c/viewer_demo.json').read_text())
    assert video['source_record']==evaluation[0]['record'] and video['source_sha256']==sha256(video['source_record'])
    assert viewer['episodes'][0]['record_sha256']==video['source_sha256']
    capture=np.array([f['sample'] for f in video['frames']],int)
    np.testing.assert_allclose([f['physical_time'] for f in video['frames']],s['time_s'][capture])
    held=capture[np.searchsorted(capture,np.arange(len(s['time_s'])),side='right')-1]
    u=d['u_applied'];norm=s['u_norm_mps2'];ref=m['norm_reference_mps2'];dt=s['dt_s']
    impact={}
    for name,start,end in [('post_observe',10.,float(d['acceleration_interval'][-1,1])),
                           ('terminal_quarter',m['phases']['terminal_quarter']['start_s'],float(d['acceleration_interval'][-1,1]))]:
        w=overlap(d['acceleration_interval'],start,end)
        impact[name]=dict(command_vector_rms_error_mps2=float(np.sqrt(np.dot(w,np.sum((u-u[held])**2,axis=1))/w.sum())),
            max_command_vector_error_fraction=float((np.linalg.norm(u-u[held],axis=1)/ref)[w>0].max()),
            apparent_held_command_integral_mps=float(np.dot(w,norm[held])),
            true_command_integral_mps=float(np.dot(w,norm)),
            held_active_duty_5pct=float(np.dot(w,norm[held]>=.05*ref)/w.sum()),
            true_time_below_5pct=float(np.dot(w,norm<.05*ref)/w.sum()),
            true_time_below_10pct=float(np.dot(w,norm<.10*ref)/w.sum()))
    impact.update(source_record=video['source_record'],source_sha256=video['source_sha256'],source_samples=len(u),
        capture_frames=len(capture),physical_sampling_s=3.,playback_speed=15.,display_update_s=.2,
        last_state_display_time_s=float(s['time_s'][-1]),actual_success_time_s=m['summary']['success_time_s'],
        max_captured_to_actual_command_ratio=float(norm[capture].max()/norm.max()),
        current_joystick_reference_per_axis_mps2=.005,
        tilt_reference_deg={str(q):float(np.degrees(np.arcsin(.55*np.sqrt(2)*q/1.2))) for q in [.01,.05,.1,.25,.5,1]},
        note='Analysis of existing sample-and-hold video schedule, not a new video or changed GUI. Apparent integral is display distortion, not physical delta-v.')
    write(OUT/'pilot_sampling_audit.json',impact)

    # Geometry-only proposed starts; no image rendering, inference or propagation.
    er=np.asarray(cfg['goal_direction']);et=np.array([-er[1],er[0]])
    f=(cfg['camera']['width']-1)/2/np.tan(np.deg2rad(cfg['camera']['hfov_degrees']/2));R=cfg['camera']['target_radius_m']
    candidates=[]
    for depth in [25.,30.,35.]:
        for cross in [0.,2.,4.,6.]:
            distance=np.hypot(depth,cross);lateral=cross
            center=31.5+f*lateral*depth/(depth**2-R**2)
            radius=f*R*np.sqrt(distance**2-R**2)/(depth**2-R**2)
            candidates.append(dict(radial_depth_m=depth,cross_offset_abs_m=cross,center_distance_m=distance,
                goal_error_m=float(np.hypot(depth-5,cross)),diameter_px=2*radius,
                bearing_plus_angular_radius_deg=float(np.degrees(np.arctan2(abs(cross),depth)+np.arcsin(R/distance))),
                min_image_edge_margin_px=float(min(center-radius+.5,63.5-center-radius,32-radius)),
                entire_silhouette_in_fov=bool(center-radius>=-.5 and center+radius<=63.5 and radius<=32),
                within_existing_range_gate=bool(distance<cfg['max_range_m'])))
    write(OUT/'phase5b_geometry_candidates.json',dict(candidates=candidates,
        interpretation='25–35 m denotes radial depth from target center, NOT goal error. Signed offsets are symmetric.',
        goal_error_alternative='25–35 m goal error on axis means 30–40 m center distance; 40 m hits existing >=40 range exit.',
        projection='Same conservative sphere circle formula as geometry_phase3.Camera; geometry only; not evidence of learned visual robustness.'))
    plot(s,d,m,summaries)
    code=['src/flyrendezvous/analysis_phase5a.py','scripts/analyze_phase5a.py']
    write(OUT/'analysis_manifest.json',dict(input_sources={p:sha256(p) for p in sorted(set(inputs))},
        code_version={p:sha256(p) for p in code},commit=None,commit_reason='Workspace has no .git directory; code SHA-256 is version identifier',
        analyzed_trials=[r['trial_id'] for r in summaries],missing_trials=missing,
        dt_s=cfg['dt_phys'],dt_source='NPZ acceleration_interval endpoints checked against observation_time and terminal metadata',
        command_reference=dict(axis_max=cfg['a_max'],norm_max=float(np.sqrt(2)*cfg['a_max']),definition='sqrt(2) * per-axis saturation, L2 norm'),
        velocity_threshold=VELOCITY_THRESHOLD,active_thresholds=ACTIVE_THRESHOLDS,
        direction_rule='>=45 and >=90 degrees between adjacent original samples in same contiguous active interval; no bridging gaps',
        summary_window_basis='dv fractions and active duty use post-observe duration; mean_u uses full duration. Full alternatives in per-trial metrics',
        braking_rule='u dot pre-interval velocity < 0 and speed > 1e-4; no orbital energy interpretation',
        success_condition_source=['configs/phase3.json','src/flyrendezvous/phase3_runtime.py:rollout'],
        success=dict(position_strict_lt=cfg['success_position_m'],speed_strict_lt=cfg['success_speed_m_s'],hold_s=cfg['success_hold_seconds'],interval_endpoints=True,post_observe_only=True),
        no_new_inference=True,no_training=True,no_simulation=True,analysis_only=True,
        missing_values='JSON null / empty CSV for unavailable values; undefined low-speed decomposition never treated as a measured zero',
        end_state='states has N+1 rows; command CSV has N interval-start rows; final state metrics include last state after last applied command'))
    print(json.dumps(clean(dict(summary=m['summary'],windows=m['time_windows'],braking=m['braking'],times=m['dv_reach_times_s'],phases=m['phases'],conditions=m['conditions'])),indent=2))

def plot(s,d,m,summary):
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22,'figure.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
    t=s['time_s'];end=float(s['interval_end_s'][-1]);st=np.r_[t,end]
    states=d['states'];goal=np.array(m['goal']);cond=m['conditions']
    def annotate(ax):
        ax.axvspan(0,10,color='gray',alpha=.16)
        for a,b in d['acceleration_interval'][s['braking']]:ax.axvspan(a,b,color='#368eb8',alpha=.12,lw=0)
        if cond['success_hold_start_s'] is not None:ax.axvspan(cond['success_hold_start_s'],end,color='#56ad62',alpha=.18)
        ax.set_xlim(0,end)
    fig,axs=plt.subplots(5,1,figsize=(12,12),sharex=True)
    fig.suptitle('test_00 | original saved image-only closed loop\nGray: observe; blue: u dot v < 0; green: successful 10 s hold',fontsize=14)
    axs[0].plot(st,np.linalg.norm(states[:,:2]-goal,axis=1));axs[0].axhline(.25,color='red',ls='--',label='position < 0.25');axs[0].set_ylabel('Goal error [m]');axs[0].legend()
    axs[1].plot(st,np.linalg.norm(states[:,2:],axis=1));axs[1].axhline(.01,color='red',ls='--',label='speed < 0.01');axs[1].set_ylabel('Speed [m/s]');axs[1].legend()
    axs[2].step(t,s['ax_mps2'],where='post',label='ax');axs[2].step(t,s['ay_mps2'],where='post',label='ay');axs[2].set_ylabel('Applied [m/s²]');axs[2].legend()
    axs[3].step(t,s['u_norm_mps2'],where='post');axs[3].set_ylabel('L2 command [m/s²]')
    axs[4].plot(st,np.r_[0,s['dv_cumulative_end_mps']]);axs[4].set_ylabel('Cumulative Δv [m/s]');axs[4].set_xlabel('Physical time [s]')
    for ax in axs:annotate(ax)
    fig.tight_layout(rect=(0,0,1,.95));save(fig,'test00_overview')
    fig,axs=plt.subplots(3,1,figsize=(12,8),sharex=True)
    axs[0].plot(t,s['u_dot_v']);axs[0].axhline(0,color='black',lw=.7);axs[0].set_ylabel('u dot v [m²/s³]')
    axs[1].plot(t,s['parallel_norm_mps2'],label='|parallel|');axs[1].plot(t,np.maximum(-s['parallel_signed_mps2'],0),ls='--',label='negative parallel');axs[1].legend();axs[1].set_ylabel('[m/s²]')
    axs[2].plot(t,s['perpendicular_norm_mps2'],color='#bd6337',label='|perpendicular|');axs[2].legend();axs[2].set_ylabel('[m/s²]');axs[2].set_xlabel('Physical time [s]')
    for ax in axs:annotate(ax)
    fig.suptitle('test_00 | velocity-relative control decomposition (not orbital radial/along-track)\nBlue: braking, valid speed > 1e-4 m/s; magnitudes do not add as scalar Δv')
    fig.tight_layout(rect=(0,0,1,.92));save(fig,'test00_control_decomposition')
    fig,axs=plt.subplots(2,1,figsize=(12,7),sharex=True)
    axs[0].step(t,100*s['u_norm_fraction'],where='post',color='#6340a1')
    for q in [5,10,25,50]:axs[0].axhline(q,color='gray',ls='--',lw=.7);axs[0].text(end+1,q,str(q)+'%',va='center')
    axs[0].set_ylabel('Command / L2 maximum [%]');axs[0].set_ylim(0,105)
    axs[1].plot(t,s['joystick_tilt_deg']);axs[1].set_ylabel('Current joystick tilt [deg]');axs[1].set_xlabel('Physical time [s]')
    for ax in axs:annotate(ax)
    fig.suptitle('test_00 | unchanged full-scale Pilot mapping\nL2 reference = sqrt(2) × 0.005 m/s²; no display exaggeration')
    fig.tight_layout(rect=(0,0,1,.92));save(fig,'test00_command_scale')
    fig,ax=plt.subplots(figsize=(12,5))
    ax.plot(st,np.r_[0,s['dv_cumulative_end_mps']],lw=2)
    for q,when in m['dv_reach_times_s'].items():
        value=float(q)*m['summary']['total_dv_mps'];ax.plot(when,value,'o');ax.axvline(when,ls='--',lw=.7)
        ax.annotate(f'{float(q):.0%}: {when:.2f} s',(when,value),xytext=(7,-18 if q=='0.9' else 10),textcoords='offset points')
    annotate(ax);ax.set(xlabel='Physical time [s]',ylabel='Integral of |u_applied| [m/s]',title='test_00 | cumulative control effort; exact piecewise-constant integration')
    fig.tight_layout();save(fig,'test00_cumulative_dv')
    fig,axs=plt.subplots(3,1,figsize=(11,8),sharex=True)
    axs[0].plot(st,np.linalg.norm(states[:,:2]-goal,axis=1));axs[0].axhline(.25,color='red',ls='--');axs[0].set_ylim(.1,1.1);axs[0].set_ylabel('Goal error [m]')
    axs[1].plot(st,np.linalg.norm(states[:,2:],axis=1));axs[1].axhline(.01,color='red',ls='--');axs[1].set_ylim(0,.03);axs[1].set_ylabel('Speed [m/s]')
    axs[2].plot(t,1000*s['u_norm_mps2']);axs[2].set_ylim(0,.7);axs[2].set_ylabel('Command [10^-3 m/s²]');axs[2].set_xlabel('Physical time [s]')
    for ax in axs:
        annotate(ax);ax.set_xlim(160,end)
        for when,color in [(cond['first_goal_speed_condition_s'],'#be603c'),(cond['success_hold_start_s'],'#288842')]:ax.axvline(when,color=color,ls=':')
    fig.suptitle('test_00 | terminal detail from saved states only\nSpeed < 0.01 at 203 s; position < 0.25 and hold start 209.5 s; success 219.5 s')
    fig.tight_layout(rect=(0,0,1,.92));save(fig,'test00_terminal_detail')
    features=[('total_dv_mps','Total Δv [m/s]'),('max_u_norm_mps2','Max command [m/s²]'),('braking_dv_fraction','Braking Δv / total'),('perpendicular_dv_fraction','Perpendicular integral / total'),('active_duty_5pct','Active duty (5%, post-observe)'),('direction_changes_45deg','Major changes ≥45° (5%)'),('min_goal_error_m','Min goal error [m]'),('final_speed_mps','Final speed [m/s]')]
    groups=['approach success','near success','near failure'];colors=['#3984b9','#41a370','#bc5149']
    fig,axs=plt.subplots(4,2,figsize=(12,13))
    for ax,(key,label) in zip(axs.ravel(),features):
        for i,g in enumerate(groups):
            selected=[r for r in summary if (r['group']+' '+('success' if r['result']=='success' else 'failure'))==g]
            for j,r in enumerate(selected):
                x=i+(j-(len(selected)-1)/2)*.055
                ax.scatter(x,r[key],color=colors[i],marker='x' if r['result']=='timeout' else 'o',s=45)
                if g=='near failure':ax.annotate(r['trial_id'][-2:],(x,r[key]),xytext=(5,3),textcoords='offset points',fontsize=8)
        ax.set_xticks(range(3),['Approach\nsuccess (8)','Near\nsuccess (2)','Near\nfailure (2)']);ax.set_ylabel(label)
    fig.suptitle('All 12 saved held-out trials | descriptive comparison, no significance claim\nNear failure 09: FOV exit (circle); 11: timeout (cross)')
    fig.tight_layout(rect=(0,0,1,.94));save(fig,'trial_comparison')
    fig,axs=plt.subplots(1,3,figsize=(14,4))
    for ax,(key,label) in zip(axs,[features[0],('duration_s','Duration [s]'),features[5]]):
        for r in summary:
            color=colors[0] if r['group']=='approach' else (colors[1] if r['result']=='success' else colors[2])
            ax.scatter(r['start_goal_error_m'],r[key],color=color,marker='x' if r['result']=='timeout' else 'o')
        ax.set(xlabel='Initial goal error [m]',ylabel=label)
    fig.suptitle('Existing start-distance range only | no regression or 25–35 m extrapolation')
    fig.tight_layout();save(fig,'start_distance_relationship')
if __name__=='__main__':main()
