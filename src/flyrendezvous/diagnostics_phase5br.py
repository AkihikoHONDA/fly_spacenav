"""Saved-state diagnostics; no training or physics propagation."""
import numpy as np
from .analysis_phase5a import analyze,overlap,decomposition
def terminal(d,m,cfg):
    summary,metrics,series=analyze(d,m,cfg)
    goal=np.array(cfg['goal_direction'])*5;states=d['states'];t=np.arange(len(states))*.5
    error=np.linalg.norm(states[:,:2]-goal,axis=1);speed=np.linalg.norm(states[:,2:],axis=1)
    first=lambda mask:float(t[np.flatnonzero(mask)[0]]) if mask.any() else None
    near=first((error<2)&(t>=10));half=first((error<.5)&(t>=10))
    speed_near=(error<2)&(speed<.01)&(t>=10);slowed=first(speed_near)
    departed=bool(near is not None and np.any((t>near)&(error>=2)))
    weights=np.zeros(len(series['u_norm_mps2'])) if near is None else overlap(d['acceleration_interval'],near,t[-1])
    dv=float(weights@series['u_norm_mps2']);brake=float(weights@(series['u_norm_mps2']*series['braking']))
    status='success' if m['success'] else 'did_not_enter_2m' if near is None else (
        'entered_2m_did_not_slow' if slowed is None else 'slowed_then_redeparted' if departed else 'slowed_but_not_stabilized')
    return dict(**summary,first_error_lt_2m_s=near,first_error_lt_0_5m_s=half,
        longest_continuous_joint_hold_s=m['longest_hold_s'],post_near_goal_dv_m_s=dv,
        braking_fraction_after_entering_2m=brake/dv if dv else None,
        exit_after_entering_2m=bool(near is not None and m['termination_reason'] in ['range_exit','field_of_view_exit']),
        slowed_within_2m_time_s=slowed,redeparted_2m=departed,terminal_failure_mode=status)
def learner_state_error(d,cfg):
    mask=d['control_mask'];u=d['u_applied'][mask];label=d['u_teacher'][mask]
    norms=np.linalg.norm(u,axis=1);ln=np.linalg.norm(label,axis=1);valid=(norms>1e-8)&(ln>1e-8)
    angles=np.degrees(np.arccos(np.clip(np.sum(u[valid]*label[valid],axis=1)/(norms[valid]*ln[valid]),-1,1)))
    sat=np.abs(u)>=cfg['a_max']-1e-12;tsat=np.abs(label)>=cfg['a_max']-1e-12
    return dict(samples=len(u),command_rmse_m_s2=float(np.sqrt(np.mean((u-label)**2))),
        mean_command_angle_error_deg=float(np.mean(angles)) if len(angles) else None,
        median_command_angle_error_deg=float(np.median(angles)) if len(angles) else None,
        angle_samples=int(valid.sum()),angle_zero_norm_threshold_m_s2=1e-8,
        axis_saturation_disagreement_fraction=float(np.mean(sat!=tsat)),
        any_axis_saturation_disagreement_fraction=float(np.mean(np.any(sat!=tsat,axis=1))))
