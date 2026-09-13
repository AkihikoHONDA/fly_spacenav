"""Nominal failure diagnostics from saved logs only."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.recording import write_json
O=Path('outputs/phase5b')
def main():
    ev=json.loads((O/'evaluation.json').read_text())
    selected=json.loads((O/'readout_selection.json').read_text())['selected']
    cfg=json.loads(Path('configs/phase5b/training.json').read_text());goal=np.array(cfg['goal_direction'])*5
    m=json.loads((O/'evaluation/H0/learner/test_00.json').read_text());d=checked_trial(m)
    tm=json.loads((O/'evaluation/H0/teacher/test_00.json').read_text());teacher=checked_trial(tm)
    t=d['observation_time'];u=d['u_applied'];n=min(len(u),len(teacher['u_applied']))
    posdiff=np.linalg.norm(d['states'][:n+1,:2]-teacher['states'][:n+1,:2],axis=1)
    uerror=np.linalg.norm(u-d['u_teacher'],axis=1)
    error=np.linalg.norm(d['states'][:,:2]-goal,axis=1)
    from flyrendezvous.readout import Readout
    model=Readout.load('models/phase5b/readout.npz')
    episodes=json.loads((O/'data.json').read_text())['episodes']
    training=np.concatenate([checked_trial(ep)['phi'][checked_trial(ep)['control_mask']] for ep in episodes if ep['split']=='train'])
    lo,hi=training.min(0),training.max(0)
    outside=((d['phi']<lo)|(d['phi']>hi)).mean(1)
    result=dict(saved_only=True,teacher_forced_normalized_RMSE=float(np.sqrt(selected['validation_mse'])),
        teacher_forced_acceleration_RMSE_m_s2=float(np.sqrt(selected['validation_mse'])*cfg['a_max']),
        selected_validation_success=[selected['success'],selected['total']],
        training_control_samples=len(training),data_samples=sum(m['samples'] for m in episodes),
        test00_first_position_difference_from_teacher_over_1m_s=float(np.flatnonzero(posdiff>1)[0]*.5) if np.any(posdiff>1) else None,
        test00_min_goal_error_m=float(error.min()),test00_min_goal_error_time_s=float(np.argmin(error)*.5),
        test00_control_period_RMSE_against_local_LQR_m_s2=m['acceleration_rmse_m_s2'],
        test00_control_period_saturation_fraction=m['saturation_fraction'],
        test00_max_fraction_of_features_outside_train_marginal_range=float(outside.max()),
        test00_initial_projection=d['projection'][0].tolist(),
        test00_first_active_applied_u_m_s2=u[20].tolist(),test00_first_active_local_LQR_m_s2=d['u_teacher'][20].tolist(),
        interpretation='Small teacher-forced error did not imply stable learned feedback. Marginal feature extrapolation and divergent local labels are descriptive diagnostics, not established causes.',
        no_post_test_training=True,no_truth_rollout=True)
    write_json(O/'nominal_failure_diagnosis.json',result)
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    axes[0,0].plot(np.arange(len(error))*.5,error,label='H0 learner')
    te=np.linalg.norm(teacher['states'][:,:2]-goal,axis=1)
    axes[0,0].plot(np.arange(len(te))*.5,te,label='H0 state LQR')
    axes[0,0].axhline(.25,color='green',ls=':');axes[0,0].set_ylabel('Goal error [m]');axes[0,0].legend()
    axes[0,1].plot(t,u[:,0],label='applied ax');axes[0,1].plot(t,d['u_teacher'][:,0],label='LQR label at learner state',alpha=.7)
    axes[0,1].set_ylabel('Acceleration [m/s²]');axes[0,1].legend()
    axes[1,0].plot(t,d['projection'][:,0]);axes[1,0].fill_between(t,d['projection'][:,0]-d['projection'][:,2],d['projection'][:,0]+d['projection'][:,2],alpha=.2)
    axes[1,0].axhline(-.5,c='red',ls=':');axes[1,0].axhline(63.5,c='red',ls=':');axes[1,0].set_ylabel('Image horizontal center / silhouette [px]')
    axes[1,1].plot(t,outside*100);axes[1,1].set_ylabel('Features outside train marginal range [%]')
    for ax in axes.flat:ax.set_xlabel('Physical time [s]');ax.grid(alpha=.25)
    fig.suptitle('test_00: nominal H0 failure, not a truth-disturbance correction')
    fig.tight_layout();fig.savefig('docs/evidence_phase5b/nominal_failure_diagnosis.png',dpi=160);plt.close(fig)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
