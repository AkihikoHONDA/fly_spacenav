"""Offline paired analysis of once-only Phase 5B evaluations."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flyrendezvous.analysis_phase5a import analyze,decomposition,overlap
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.recording import sha256,write_json
O=Path('outputs/phase5b');E=Path('docs/evidence_phase5b')
def csv_write(path,columns):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(columns)
        w.writerows(zip(*columns.values()))
def clean(obj):
    if isinstance(obj,dict):return {k:clean(v) for k,v in obj.items()}
    if isinstance(obj,list):return [clean(v) for v in obj]
    if isinstance(obj,float) and not np.isfinite(obj):return None
    return obj
def save_fig(fig,name):
    fig.tight_layout();fig.savefig(E/name,dpi=170,bbox_inches='tight');plt.close(fig)
def main():
    cfg=json.loads(Path('configs/phase5b/training.json').read_text())
    stages=[p for p in [O/'h0_evaluation.json',O/'physical_evaluation.json',O/'residual_evaluation.json'] if p.exists()]
    episodes=[m for p in stages for m in json.loads(p.read_text())['results']]
    if not episodes:raise RuntimeError('No completed evaluation')
    O.joinpath('analysis').mkdir(exist_ok=True)
    records={};summary=[];metrics={};series={}
    for m in episodes:
        key=(m['condition'],m['controller'],m['id']);d=checked_trial(m)
        s,x,z=analyze(d,m,cfg)
        s.update(condition=key[0],controller=key[1],success=m['success'],
            max_range_m=float(np.linalg.norm(d['states'][:,:2],axis=1).max()),
            min_clearance_m=m['min_surface_clearance_m'],FOV_exit=m['fov_loss'],
            post_first25_dv_fraction=1-s['dv_first25_fraction'],
            middle_half_dv_fraction=x['phases']['middle_half']['dv_fraction'],
            eclipse_samples=int(d['eclipse'].any(axis=1).sum()) if 'eclipse' in d else None,
            record=m['record'],record_sha256=m['record_sha256'])
        if m['success']:
            assert x['conditions']['first_completed_hold_end_s']==m['final_time_s'] if 'first_completed_hold_end_s' in x['conditions'] else True
        records[key]=d;metrics[key]=x;series[key]=z;summary.append(s)
        write_json(O/'analysis'/('_'.join(key)+'_metrics.json'),clean(x))
        if key[2]=='test_00':
            z.update(image_center_x_px=d['projection'][:,0],image_center_y_px=d['projection'][:,1],image_radius_px=d['projection'][:,2])
            if 'forces_ECI_m_s2' in d:
                f=d['forces_ECI_m_s2'].reshape(-1,2,6,2)
                for j,term in enumerate(d['force_terms']):
                    z[str(term)+'_differential_m_s2']=np.linalg.norm(f[:,1,j]-f[:,0,j],axis=1)
            csv_write(O/(f'test00_timeseries_{key[0]}_{key[1]}.csv'),z)
            # Full N+1 state, including success endpoint, saved separately.
            csv_write(O/(f'test00_states_{key[0]}_{key[1]}.csv'),dict(time_s=np.arange(len(d['states']))*.5,
                x_m=d['states'][:,0],y_m=d['states'][:,1],vx_m_s=d['states'][:,2],vy_m_s=d['states'][:,3]))
    csv_write(O/'evaluation.csv',{k:[s[k] for s in summary] for k in summary[0]})
    conditions=list(dict.fromkeys(s['condition'] for s in summary))
    aggregates=[]
    for c in conditions:
        for mode in ['learner','teacher']:
            rows=[s for s in summary if s['condition']==c and s['controller']==mode]
            aggregates.append(dict(condition=c,controller=mode,success=sum(s['success'] for s in rows),total=len(rows),
                failures=[dict(id=s['trial_id'],reason=s['failure_reason']) for s in rows if not s['success']],
                mean_total_dv_m_s=float(np.mean([s['total_dv_mps'] for s in rows])),
                mean_perpendicular_fraction=float(np.mean([s['perpendicular_dv_fraction'] for s in rows])),
                mean_direction_changes_45=float(np.mean([s['direction_changes_45deg'] for s in rows])),
                mean_active_duty_5pct=float(np.mean([s['active_duty_5pct'] for s in rows]))))
    pair_summaries=[]
    pairs=list(dict.fromkeys([(c,'H0') for c in conditions if c!='H0']+
        [(c,'E0') for c in ['Elo','Ehi','R1','R3','R5','RM3'] if c in conditions]+
        [('E0','T0')] if 'T0' in conditions else []))
    for a,b in pairs:
        for mode in ['learner','teacher']:
            for i in range(8):
                trial=f'test_{i:02d}';da,db=records[(a,mode,trial)],records[(b,mode,trial)]
                np.testing.assert_allclose(da['states'][0],db['states'][0],atol=0,rtol=0)
                n=min(len(da['sample_id']),len(db['sample_id']))
                delta=da['states'][:n+1]-db['states'][:n+1]
                p=da['projection'][:n]-db['projection'][:n];u=da['u_applied'][:n]-db['u_applied'][:n]
                columns=dict(time_s=da['observation_time'][:n],dx_m=delta[:n,0],dy_m=delta[:n,1],
                    dvx_m_s=delta[:n,2],dvy_m_s=delta[:n,3],dux_m_s2=u[:,0],duy_m_s2=u[:,1],
                    image_center_dx_px=p[:,0],image_center_dy_px=p[:,1],image_radius_diff_px=p[:,2])
                csv_write(O/'differences'/f'{trial}_{mode}_{a}_minus_{b}.csv',columns)
                pair_summaries.append(dict(trial=trial,controller=mode,pair=a+'-'+b,
                    common_end_s=n*.5,position_samples_including_endpoint=n+1,
                    max_position_difference_m=float(np.linalg.norm(delta[:,:2],axis=1).max()),
                    max_velocity_difference_m_s=float(np.linalg.norm(delta[:,2:],axis=1).max()),
                    max_command_difference_m_s2=float(np.linalg.norm(u,axis=1).max()),
                    max_center_difference_px=float(np.linalg.norm(p[:,:2],axis=1).max()),
                    max_radius_difference_px=float(abs(p[:,2]).max())))
    windows=[]
    if 'RM3' in conditions:
        for mode in ['learner','teacher']:
            for i in range(8):
                trial=f'test_{i:02d}'
                for c in ['E0','RM3']:
                    d=records[(c,mode,trial)];z=series[(c,mode,trial)]
                    for name,lo,hi in [('pre',90,120),('post',120,150),('late',150,180)]:
                        w=overlap(d['acceleration_interval'],lo,hi);duration=float(w.sum())
                        if not duration:continue
                        mean=np.average(d['u_applied'],axis=0,weights=w)
                        n=min(len(d['sample_id']),len(records[('E0',mode,trial)]['sample_id']))
                        wp=w[:n];de=d['projection'][:n,:2]-records[('E0',mode,trial)]['projection'][:n,:2]
                        windows.append(dict(condition=c,controller=mode,trial=trial,window=name,start_s=lo,end_s=hi,
                            observed_duration_s=duration,complete=bool(duration==hi-lo),
                            mean_command_m_s2=float(np.average(z['u_norm_mps2'],weights=w)),
                            mean_perpendicular_m_s2=float(np.average(np.nan_to_num(z['perpendicular_norm_mps2']),weights=w)),
                            mean_ax_m_s2=float(mean[0]),mean_ay_m_s2=float(mean[1]),
                            mean_vector_direction_deg=float(np.degrees(np.arctan2(mean[1],mean[0]))),
                            mean_image_center_error_px=float(np.average(np.linalg.norm(d['projection'][:,:2]-31.5,axis=1),weights=w)),
                            mean_paired_E0_center_difference_px=float(np.average(np.linalg.norm(de,axis=1),weights=wp)) if wp.sum()>0 else None))
        csv_write(O/'midcourse_windows.csv',{k:[r[k] for r in windows] for k in windows[0]})
    write_json(O/'evaluation.json',dict(trials=summary,condition_summary=aggregates,
        difference_summary=pair_summaries,midcourse_windows=windows,analysis='Phase 5A definitions; saved records only',
        units=dict(position='m',velocity='m/s',acceleration='m/s^2',dv='m/s',time='physical s',image='pixels'),
        comparison='paired common interval; full state comparisons include final endpoint; no padding after termination'))
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.25,'figure.facecolor':'white'})
    colors={'H0':'#367bbd','E0':'#e38b24','RM3':'#a84b9e'}
    if 'T0' in conditions:
        fig,axes=plt.subplots(1,2,figsize=(12,4))
        for ax,mode in zip(axes,['learner','teacher']):
            for i in range(8):
                a=records[('T0',mode,f'test_{i:02d}')]['states'];b=records[('H0',mode,f'test_{i:02d}')]['states'];n=min(len(a),len(b))
                ax.plot(np.arange(n)*.5,np.linalg.norm((a[:n]-b[:n])[:,:2],axis=1),label=f'{i:02d}')
            ax.set(title=mode+' | T0 - H0',xlabel='Physical time [s]',ylabel='Relative position difference [m]');ax.legend(ncol=4)
        save_fig(fig,'hcw_vs_twobody.png')
    sanity=json.loads((O/'perturbation_sanity.json').read_text())
    fig,ax=plt.subplots(figsize=(8,4));names=['J2','SRP','drag','R1','R3 / RM3','R5']
    vals=[sanity['accelerations'][t]['differential_m_s2'] for t in ['j2','srp','drag']]+[1e-5,3e-5,5e-5]
    ax.bar(names,vals,color=['#367bbd']*3+['#a84b9e']*3);ax.set(yscale='log',ylabel='Differential acceleration [m/s²]',title='Physical terms (blue) / prescribed residual stress (purple)')
    save_fig(fig,'perturbation_magnitudes.png')
    fig,ax=plt.subplots(figsize=(11,4));x=np.arange(len(conditions))
    for mode,off,col in [('learner',-.18,'#367bbd'),('teacher',.18,'#999999')]:
        yy=[next(r['success'] for r in aggregates if r['condition']==c and r['controller']==mode) for c in conditions]
        ax.bar(x+off,yy,width=.35,label=mode+' / 8',color=col)
    ax.set(xticks=x,xticklabels=conditions,ylim=(0,9),ylabel='Success count',title='Same eight held-out initial states');ax.legend()
    save_fig(fig,'condition_success.png')
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    for ax,field,label in zip(axes,['total_dv_mps','direction_changes_45deg','perpendicular_dv_fraction'],['Total Δv [m/s]','Direction changes ≥45°','Perpendicular fraction']):
        for mode,off,col in [('learner',-.15,'#367bbd'),('teacher',.15,'#999999')]:
            for j,c in enumerate(conditions):
                values=[s[field] for s in summary if s['condition']==c and s['controller']==mode]
                ax.scatter(np.full(8,j+off),values,s=12,color=col,alpha=.6)
        ax.set(xticks=x,xticklabels=conditions,ylabel=label);ax.tick_params(axis='x',rotation=45)
    save_fig(fig,'control_activity_comparison.png')
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for c in ['H0','E0','RM3']:
        if c not in conditions:continue
        d=records[(c,'learner','test_00')];z=series[(c,'learner','test_00')];t=z['time_s'];col=colors[c]
        axes[0,0].plot(-d['states'][:,1],-d['states'][:,0],color=col,label=c)
        axes[0,1].plot(t,z['goal_error_m'],color=col,label=c)
        axes[1,0].plot(t,z['ax_mps2'],color=col,label=c+' ax');axes[1,0].plot(t,z['ay_mps2'],'--',color=col,label=c+' ay')
        axes[1,1].plot(t,z['joystick_tilt_deg'],color=col,label=c)
    goal=np.array(cfg['goal_direction'])*5
    axes[0,0].scatter([-goal[1]],[-goal[0]],marker='*',c='green',s=100)
    axes[0,0].set(xlabel='-along-track [m]',ylabel='-radial [m]',title='test_00 saved trajectory');axes[0,0].invert_yaxis();axes[0,0].axis('equal')
    axes[0,1].set(xlabel='Physical time [s]',ylabel='Goal error [m]')
    axes[1,0].set(xlabel='Physical time [s]',ylabel='Command [m/s²]')
    axes[1,1].set(xlabel='Physical time [s]',ylabel='Unchanged Pilot tilt [deg]')
    for ax in axes.flat:ax.legend()
    save_fig(fig,'test00_condition_comparison.png')
    if 'RM3' in conditions:
        fig,axes=plt.subplots(2,2,figsize=(12,7))
        for c in ['E0','RM3']:
            z=series[(c,'learner','test_00')];t=z['time_s'];d=records[(c,'learner','test_00')]
            for ax,value in zip(axes.flat,[z['u_norm_mps2'],z['perpendicular_norm_mps2'],np.degrees(np.unwrap(np.arctan2(z['ay_mps2'],z['ax_mps2']))),d['projection'][:,0]-31.5]):
                ax.plot(t,value,label=c,color=colors[c]);ax.axvspan(120,180,color='#a84b9e',alpha=.1)
                ax.set_xlim(90,210);ax.set_xlabel('Physical time [s]');ax.legend()
        for ax,label in zip(axes.flat,['Command norm [m/s²]','Perpendicular command [m/s²]','Unwrapped command direction [deg]','Image center minus boresight [px]']):ax.set_ylabel(label)
        save_fig(fig,'test00_midcourse_correction.png')
    print(json.dumps(aggregates,indent=2))
if __name__=='__main__':main()
