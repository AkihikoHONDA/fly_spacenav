"""Analyze completed rounds only; held-out test is never invoked here."""
import csv,json,runpy
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flyrendezvous.recording import write_json
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.features import history_matrix
from flyrendezvous.readout import Readout
from flyrendezvous.diagnostics_phase5br import terminal,learner_state_error
O=Path('outputs/phase5br');E=Path('docs/evidence_phase5br')
def save(fig,name):
    fig.tight_layout();fig.savefig(E/name,dpi=160,bbox_inches='tight');plt.close(fig)
def main():
    ns=runpy.run_path('scripts/run_phase5br.py');cfg=ns['cfg']()
    rounds=json.loads((O/'validation_by_round.json').read_text())['rounds']
    coverage=[];terms=[];errors=[]
    for selected in rounds:
        r=selected['round'];lag=selected['lag'];model=Readout.load(selected['model'])
        tx,_,_=ns['dataset'](0,lag);cx,_,_=ns['dataset'](r,lag)
        low,high=tx.min(0),tx.max(0);clo,chi=cx.min(0),cx.max(0)
        np.testing.assert_allclose(model.mean,cx.mean(0),atol=0,rtol=0)
        np.testing.assert_allclose(model.std,cx.std(0),atol=0,rtol=0)
        for m in selected['closed_loop']:
            d=checked_trial(m);x=history_matrix(d['phi'],lag);mask=d['control_mask']&np.isfinite(x).all(1);x=x[mask]
            z=(x[:,model.keep]-model.mean[model.keep])/model.std[model.keep]
            coverage.append(dict(round=r,trial=m['id'],lag=lag,feature_dimension=x.shape[1],z_score_retained_features=int(model.keep.sum()),
                control_samples=len(x),teacher_bound_exceedance=float(np.mean((x<low)|(x>high))),
                current_train_exceedance=float(np.mean((x<clo)|(x>chi))),
                z_gt_3=float(np.mean(abs(z)>3)),z_gt_5=float(np.mean(abs(z)>5))))
            terms.append(dict(round=r,**terminal(d,m,cfg)))
        # Round selected learner's own train trajectories: next aggregation or final diagnostic.
        paths=[O/f'aggregation_round{r+1}.json',O/f'round{r}_train_diagnostic.json']
        source=next((p for p in paths if p.exists()),None)
        if source:
            data=json.loads(source.read_text())
            assert data['source_model_sha256']==selected['sha256']
            for m in data['episodes']:
                errors.append(dict(round=r,trial=m['id'],diagnostic_only=data['diagnostic_only'],**learner_state_error(checked_trial(m),cfg)))
    write_json(O/'feature_coverage.json',dict(records=coverage,
        definition='Mean over control samples and actual readout-input features; lag5 has current plus lagged 1824 features; z-score excludes constant features',
        causal_claim=False))
    write_json(O/'terminal_stabilization.json',dict(records=terms))
    write_json(O/'learner_state_error.json',dict(records=errors,teacher_trajectory_mse_separate=True,
        command='applied learner vs saturated local teacher; observation excluded'))
    colors=['#367bbd','#d78a28','#6c9f47'];plt.rcParams.update({'axes.grid':True,'grid.alpha':.2,'font.size':10})
    fig,ax=plt.subplots(figsize=(9,4))
    for selected in rounds:
        r=selected['round'];cands=json.loads((O/f'round{r}/candidates.json').read_text())
        ax.scatter(np.arange(6)+(r-.8)*.15,[c['success'] for c in cands],color=colors[r],label=f'Round {r}',s=40)
        k=next(i for i,c in enumerate(cands) if c['candidate']==selected['candidate'])
        ax.scatter(k+(r-.8)*.15,selected['success'],marker='*',s=180,facecolors='none',edgecolors=colors[r])
    ax.set(xticks=np.arange(6),xticklabels=[c['candidate'] for c in cands],ylim=(-.5,12.8),ylabel='Validation success / 12')
    ax.tick_params(axis='x',rotation=20);ax.axhline(10,ls=':',c='gray');ax.legend();save(fig,'validation_by_round.png')
    fig,ax=plt.subplots(figsize=(8,4));labels=['success','timeout','field_of_view_exit','range_exit','collision']
    bottoms=np.zeros(len(rounds))
    for reason in labels:
        counts=[sum(m['termination_reason']==reason for m in s['closed_loop']) for s in rounds]
        ax.bar(np.arange(len(rounds)),counts,bottom=bottoms,label=reason);bottoms+=counts
    ax.set(xticks=np.arange(len(rounds)),xticklabels=[f'Round {s["round"]}' for s in rounds],ylabel='Selected validation trial count');ax.legend(fontsize=8)
    save(fig,'failure_modes_by_round.png')
    fig,axes=plt.subplots(1,4,figsize=(14,4))
    for ax,field in zip(axes,['teacher_bound_exceedance','current_train_exceedance','z_gt_3','z_gt_5']):
        for s in rounds:
            r=s['round'];vals=[c[field]*100 for c in coverage if c['round']==r]
            ax.scatter([r]*len(vals),vals,color=colors[r],s=20)
        ax.set(title=field,ylabel='Feature-sample fraction [%]',xticks=[s['round'] for s in rounds],xlabel='Round')
    save(fig,'feature_coverage.png')
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,field,label in zip(axes,['command_rmse_m_s2','mean_command_angle_error_deg','axis_saturation_disagreement_fraction'],['Applied command RMSE [m/s²]','Mean command angle error [deg]','Axis saturation disagreement']):
        for s in rounds:
            r=s['round'];vals=[c[field] for c in errors if c['round']==r and c[field] is not None]
            ax.scatter([r]*len(vals),vals,color=colors[r],s=12)
        ax.set(ylabel=label,xlabel='Source selected round',xticks=[s['round'] for s in rounds])
    save(fig,'learner_state_error.png')
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
    for s in rounds:
        r=s['round'];m=next(m for m in s['closed_loop'] if m['id']=='validation_00');d=checked_trial(m)
        state=d['states'];t=np.arange(len(state))*.5;goal=np.array(cfg['goal_direction'])*5
        axes[0].plot(t,np.linalg.norm(state[:,:2]-goal,axis=1),color=colors[r],label=f'Round{r}')
        axes[1].plot(t,np.linalg.norm(state[:,2:],axis=1),color=colors[r])
        axes[2].plot(d['observation_time'],d['u_applied'][:,0],color=colors[r]);axes[2].plot(d['observation_time'],d['u_applied'][:,1],ls='--',color=colors[r])
    axes[0].axhline(.25,c='gray',ls=':');axes[1].axhline(.01,c='gray',ls=':')
    axes[0].set_ylabel('Goal error [m]');axes[1].set_ylabel('Speed [m/s]');axes[2].set_ylabel('ax solid / ay dashed [m/s²]')
    axes[2].set_xlabel('Physical time [s]');axes[0].legend();save(fig,'terminal_stabilization_val00.png')
    p=O/'fresh_test.json'
    if p.exists():
        test=json.loads(p.read_text());rows=[terminal(checked_trial(m),m,cfg) for m in test['results']]
        with (O/'fresh_test.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        fig,axes=plt.subplots(1,2,figsize=(10,4));x=np.arange(8)
        axes[0].bar(x,[int(m['success']) for m in test['results']]);axes[0].set(ylim=(0,1.2),ylabel='Success',xticks=x)
        axes[1].bar(x,[m['final_position_error_m'] for m in test['results']]);axes[1].set(ylabel='Final goal error [m]',xticks=x)
        fig.suptitle('Fresh test (different samples from historical Phase 5B)');save(fig,'fresh_test_summary.png')
    else:
        fig,ax=plt.subplots(figsize=(8,3));ax.axis('off');ax.text(.5,.5,'Fresh test NOT RUN\nValidation gate not met; held-out remains unopened',ha='center',va='center',fontsize=15)
        save(fig,'fresh_test_summary.png')
    print('Analyzed rounds',[r['round'] for r in rounds],len(coverage),'validation trajectories',len(errors),'train diagnostic trajectories')
if __name__=='__main__':main()
