"""Offline control audit. Pure saved-array reductions; no policy or dynamics calls."""
import numpy as np

VELOCITY_THRESHOLD=1e-4
ACTIVE_THRESHOLDS=(.02,.05,.10)
BINS=np.array([0,.01,.05,.10,.25,.50,1.,np.inf])

def ratio(a,b):
    return float(a/b) if b>0 else None

def overlap(intervals,start,end):
    return np.maximum(0,np.minimum(intervals[:,1],end)-np.maximum(intervals[:,0],start))

def integrate(intervals,signal,start=None,end=None):
    weights=np.diff(intervals,axis=1).ravel() if start is None else overlap(intervals,start,end)
    return float(np.sum(np.asarray(signal)*weights))

def reach_time(intervals,rates,fraction):
    amounts=np.asarray(rates)*np.diff(intervals,axis=1).ravel()
    total=amounts.sum()
    if total<=0:return None
    target=total*fraction
    k=int(np.searchsorted(np.cumsum(amounts),target,side="left"))
    before=amounts[:k].sum()
    return float(intervals[k,0]+(target-before)/rates[k])

def decomposition(u,v,velocity_threshold=VELOCITY_THRESHOLD):
    speed=np.linalg.norm(v,axis=1);valid=speed>velocity_threshold
    dot=np.einsum('ij,ij->i',u,v)
    signed=np.full(len(u),np.nan);parallel=np.full_like(u,np.nan,dtype=float)
    signed[valid]=dot[valid]/speed[valid]
    parallel[valid]=signed[valid,None]*v[valid]/speed[valid,None]
    perpendicular=u-parallel
    return dict(speed=speed,dot=dot,valid=valid,braking=valid&(dot<0),
                signed=signed,parallel=parallel,perpendicular=perpendicular,
                parallel_norm=np.linalg.norm(parallel,axis=1),
                perp_norm=np.linalg.norm(perpendicular,axis=1))

def events(intervals,u,reference,threshold,start=None):
    norm=np.linalg.norm(u,axis=1)
    eligible=np.ones(len(u),dtype=bool) if start is None else intervals[:,0]>=start
    active=eligible&(norm>=threshold*reference)&(norm>0)
    starts=np.flatnonzero(active&~np.r_[False,active[:-1]])
    ends=np.flatnonzero(active&~np.r_[active[1:],False])
    changes=[]
    for k in np.flatnonzero(active[1:]&active[:-1])+1:
        angle=float(np.degrees(np.arccos(np.clip(np.dot(u[k],u[k-1])/(norm[k]*norm[k-1]),-1,1))))
        if angle>=45:changes.append(dict(time_s=float(intervals[k,0]),angle_deg=angle))
    dt=np.diff(intervals,axis=1).ravel()
    return dict(threshold=float(threshold),active_samples=int(active.sum()),
                active_sample_fraction=ratio(active.sum(),eligible.sum()),
                active_duty_ratio=ratio(dt[active].sum(),dt[eligible].sum()),
                intervals=[dict(start_s=float(intervals[a,0]),end_s=float(intervals[b,1])) for a,b in zip(starts,ends)],
                number_of_active_intervals=len(starts),direction_changes_45deg=len(changes),
                direction_changes_90deg=sum(c['angle_deg']>=90 for c in changes),major_changes=changes)

def distribution(intervals,u_norm,reference,start,end):
    w=overlap(intervals,start,end);eligible=w>0;frac=u_norm/reference
    total=np.dot(w,u_norm);result=[]
    for i,(lo,hi) in enumerate(zip(BINS[:-1],BINS[1:])):
        # 100% is physically allowed and included in the 50–100% bin.
        mask=(frac>=lo)&(frac<hi)
        if hi==1:mask=(frac>=lo)&(frac<=hi)
        if lo==1:mask=frac>1
        mask &= eligible
        result.append(dict(lower_fraction=float(lo),upper_fraction=None if not np.isfinite(hi) else float(hi),
            samples=int(mask.sum()),sample_fraction=ratio(mask.sum(),eligible.sum()),
            time_s=float(w[mask].sum()),time_fraction=ratio(w[mask].sum(),w.sum()),
            dv_mps=float(np.dot(w[mask],u_norm[mask])),dv_fraction=ratio(np.dot(w[mask],u_norm[mask]),total)))
    return result

def condition_times(state_times,states,intervals,control,cfg,goal):
    error=np.linalg.norm(states[:,:2]-goal,axis=1);speed=np.linalg.norm(states[:,2:],axis=1)
    position=error<cfg['success_position_m'];slow=speed<cfg['success_speed_m_s'];good=position&slow
    def first(mask):
        return float(state_times[np.flatnonzero(mask)[0]]) if mask.any() else None
    start=None;longest=0.;reached=None;success_start=None;holds=[]
    for k,(a,b) in enumerate(intervals):
        if control[k] and good[k] and good[k+1]:
            if start is None:start=float(a)
            length=float(b-start);longest=max(longest,length)
            if reached is None and length>=cfg['success_hold_seconds']:
                reached=float(b);success_start=start
        elif start is not None:
            holds.append([start,float(a)]);start=None
    if start is not None:holds.append([start,float(intervals[-1,1])])
    return dict(first_goal_position_condition_s=first(position),first_goal_speed_condition_s=first(slow),
                first_joint_condition_s=first(good),success_hold_start_s=success_start,
                criteria_hold_completed_s=reached,longest_hold_s=longest,good_interval_runs=holds)

def analyze(d,m,cfg):
    intervals=np.asarray(d['acceleration_interval'],float);u=np.asarray(d['u_applied'],float)
    states=np.asarray(d['states'],float);t=np.asarray(d['observation_time'],float)
    n=len(u);dt=np.diff(intervals,axis=1).ravel()
    if n==0:raise ValueError("Empty trajectory")
    if states.shape!=(n+1,4) or u.shape!=(n,2) or intervals.shape!=(n,2):raise ValueError("Misaligned saved arrays")
    if not all(np.isfinite(a).all() for a in [intervals,u,states,t]) or not np.all(dt>0):raise ValueError("Invalid saved numeric data")
    np.testing.assert_allclose(intervals[:,0],t,rtol=0,atol=1e-12)
    np.testing.assert_allclose(intervals[:-1,1],intervals[1:,0],rtol=0,atol=1e-12)
    np.testing.assert_allclose(np.diff(t),dt[:-1],rtol=0,atol=1e-12)
    np.testing.assert_allclose(dt,cfg['dt_phys'],rtol=0,atol=1e-12)
    np.testing.assert_array_equal(d['sample_id'],np.arange(n))
    control=np.asarray(d['control_mask'],bool)
    np.testing.assert_array_equal(control,t>=cfg['observe_seconds'])
    assert np.all(u[~control]==0) and np.max(np.abs(u))<=cfg['a_max']+1e-12
    goal=cfg['standoff_radius_m']*np.asarray(cfg['goal_direction'])
    state_times=np.r_[t,intervals[-1,1]]
    error=np.linalg.norm(states[:,:2]-goal,axis=1)
    dec=decomposition(u,states[:-1,2:])
    norm=np.linalg.norm(u,axis=1);ref=np.sqrt(2)*cfg['a_max'];dv=norm*dt;total=float(dv.sum())
    start=float(t[0]);end=float(intervals[-1,1]);post=float(t[control][0]) if control.any() else end
    times=condition_times(state_times,states,intervals,control,cfg,goal)
    whole={};dist={};sensitivity={}
    for name,a in [('full',start),('post_observe',post)]:
        length=end-a;windows={}
        for part in ['first','last']:
            for frac in [.1,.25,.5]:
                lo,hi=(a,a+length*frac) if part=='first' else (end-length*frac,end)
                value=integrate(intervals,norm,lo,hi)
                windows[part+str(round(frac*100))]=dict(start_s=lo,end_s=hi,dv_mps=value,dv_fraction=ratio(value,total))
        whole[name]=windows
        dist[name]=distribution(intervals,norm,ref,a,end)
        sensitivity[name]={str(th):events(intervals,u,ref,th,a) for th in ACTIVE_THRESHOLDS}
    brake=dec['braking'];valid=dec['valid'];parallel=np.nan_to_num(dec['parallel_norm']);perp=np.nan_to_num(dec['perp_norm'])
    brake_info=dict(velocity_threshold_mps=VELOCITY_THRESHOLD,samples=int(brake.sum()),
        sample_fraction_all=ratio(brake.sum(),n),sample_fraction_valid=ratio(brake.sum(),valid.sum()),
        sample_fraction_post_observe=ratio(brake[control].sum(),control.sum()),
        time_s=float(dt[brake].sum()),dv_mps=float(dv[brake].sum()),dv_fraction=ratio(dv[brake].sum(),total),
        negative_parallel_dv_mps=integrate(intervals,np.maximum(0,-np.nan_to_num(dec['signed']))),
        first_time_s=float(t[np.flatnonzero(brake)[0]]) if brake.any() else None,
        largest_event_time_s=float(t[np.argmin(np.where(brake,dec['dot'],np.inf))]) if brake.any() else None,
        largest_event_definition="minimum u_applied dot v at interval start",excluded_low_speed_samples=int((~valid).sum()),
        excluded_low_speed_time_s=float(dt[~valid].sum()),excluded_low_speed_dv_mps=float(dv[~valid].sum()))
    aidx=np.flatnonzero(brake&~np.r_[False,brake[:-1]])
    bidx=np.flatnonzero(brake&~np.r_[brake[1:],False])
    brake_info['contiguous_intervals']=[dict(start_s=float(t[a]),end_s=float(intervals[b,1])) for a,b in zip(aidx,bidx)]
    brake_info['speed_peak_time_s']=float(state_times[np.argmax(np.linalg.norm(states[:,2:],axis=1))])
    brake_info['speed_peak_mps']=float(np.linalg.norm(states[:,2:],axis=1).max())
    phases={}
    cuts=[('early_quarter',post,post+(end-post)*.25),('middle_half',post+(end-post)*.25,post+(end-post)*.75),
          ('terminal_quarter',post+(end-post)*.75,end)]
    if times['success_hold_start_s'] is not None:cuts.append(('success_hold',times['success_hold_start_s'],end))
    for name,a,b in cuts:
        w=overlap(intervals,a,b);mask=w>0;amount=float(np.dot(w,norm))
        phases[name]=dict(start_s=a,end_s=b,dv_mps=amount,dv_fraction=ratio(amount,total),
            braking_dv_mps=float(np.dot(w,norm*brake)),braking_dv_fraction_total=ratio(np.dot(w,norm*brake),total),
            parallel_dv_mps=float(np.dot(w,parallel)),perpendicular_dv_mps=float(np.dot(w,perp)),
            max_command_mps2=float(norm[mask].max()),mean_command_mps2=ratio(amount,w.sum()),
            median_command_mps2=float(np.median(norm[mask])),max_norm_fraction=float((norm[mask]/ref).max()),
            median_norm_fraction=float(np.median(norm[mask]/ref)),
            median_joystick_tilt_deg=float(np.median(np.degrees(np.arcsin(.55*norm[mask]/cfg['a_max']/1.2)))))
    er=np.asarray(cfg['goal_direction']);et=np.array([-er[1],er[0]])
    summary=dict(trial_id=m['id'],group=m['category'],result=m['termination_reason'],
        failure_reason=None if m['success'] else m['termination_reason'],samples=n,duration_s=end-start,
        post_observe_duration_s=end-post,start_goal_error_m=float(error[0]),start_center_distance_m=float(np.linalg.norm(states[0,:2])),
        start_radial_m=float(states[0,:2]@er),start_cross_offset_m=float(states[0,:2]@et),
        start_speed_mps=float(np.linalg.norm(states[0,2:])),min_goal_error_m=float(error.min()),
        final_goal_error_m=float(error[-1]),final_speed_mps=float(np.linalg.norm(states[-1,2:])),
        max_u_norm_mps2=float(norm.max()),mean_u_norm_mps2=ratio(total,end-start),total_dv_mps=total,
        dv_first25_fraction=whole['post_observe']['first25']['dv_fraction'],
        dv_first50_fraction=whole['post_observe']['first50']['dv_fraction'],
        dv_last25_fraction=whole['post_observe']['last25']['dv_fraction'],
        braking_dv_fraction=brake_info['dv_fraction'],perpendicular_dv_fraction=ratio(integrate(intervals,perp),total),
        active_duty_5pct=sensitivity['post_observe']['0.05']['active_duty_ratio'],
        direction_changes_45deg=sensitivity['post_observe']['0.05']['direction_changes_45deg'],
        direction_changes_90deg=sensitivity['post_observe']['0.05']['direction_changes_90deg'],
        first_goal_position_condition_s=times['first_goal_position_condition_s'],
        first_goal_speed_condition_s=times['first_goal_speed_condition_s'],first_joint_condition_s=times['first_joint_condition_s'],
        success_time_s=end if m['success'] else None,success_hold_start_s=times['success_hold_start_s'])
    metrics=dict(summary=summary,goal=goal.tolist(),dt_min_s=float(dt.min()),dt_max_s=float(dt.max()),
        norm_reference_mps2=ref,time_windows=whole,command_distribution=dist,direction_sensitivity=sensitivity,
        braking=brake_info,conditions=times,phases=phases,
        dv_reach_times_s={str(p):reach_time(intervals,norm,p) for p in [.5,.8,.9]},
        decomposition=dict(parallel_dv_mps=integrate(intervals,parallel),perpendicular_dv_mps=integrate(intervals,perp),
            perpendicular_dv_fraction=summary['perpendicular_dv_fraction'],
            note="Velocity-relative magnitudes; integrals are not additive and are not radial/along-track components. Invalid low-speed components excluded, CSV null."),
        optional_saved_fields=[k for k in ['u_raw','u_teacher','projection'] if k in d])
    series=dict(sample_id=np.arange(n),time_s=t,interval_end_s=intervals[:,1],dt_s=dt,
        x_m=states[:-1,0],y_m=states[:-1,1],vx_mps=states[:-1,2],vy_mps=states[:-1,3],
        goal_error_m=error[:-1],relative_speed_mps=dec['speed'],ax_mps2=u[:,0],ay_mps2=u[:,1],
        u_norm_mps2=norm,ax_fraction=np.abs(u[:,0])/cfg['a_max'],ay_fraction=np.abs(u[:,1])/cfg['a_max'],
        u_norm_fraction=norm/ref,dv_mps=dv,dv_cumulative_start_mps=np.r_[0,np.cumsum(dv)[:-1]],
        dv_cumulative_end_mps=np.cumsum(dv),u_dot_v=dec['dot'],velocity_valid=valid,braking=brake,
        parallel_signed_mps2=dec['signed'],parallel_norm_mps2=dec['parallel_norm'],perpendicular_norm_mps2=dec['perp_norm'],
        joystick_tilt_deg=np.degrees(np.arcsin(.55*norm/cfg['a_max']/1.2)),post_observe=control)
    if 'u_raw' in d:
        series['raw_ax_mps2']=d['u_raw'][:,0];series['raw_ay_mps2']=d['u_raw'][:,1]
    return summary,metrics,series
