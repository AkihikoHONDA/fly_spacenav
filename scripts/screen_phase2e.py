"""Analyze all original learned test logs; replays are checked separately."""
import csv,json
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.phase2_runtime import checked_trial
from flyrendezvous.readout import Readout
from flyrendezvous.screening import *

SRC=Path("outputs/phase2");OUT=Path("outputs/phase2e")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(Path("configs/phase2.json").read_text())
    lock=json.loads((SRC/"model_lock.json").read_text())
    assert sha256(SRC/"readout.npz")==lock["readout_sha256"]
    assert sha256(SRC/"pooling.npz")==lock["pooling_sha256"]
    with np.load(SRC/"pooling.npz",allow_pickle=False) as z:pool={k:z[k] for k in z.files}
    labels=feature_types(pool);types=pool["all_types"];groups=type_groups(pool["cell_type"])
    model=Readout.load(SRC/"readout.npz")
    evaluation=json.loads((SRC/"evaluation.json").read_text())
    records=evaluation["learner"];episodes=[]
    arrays={k:[] for k in ["episode","sample_id","physical_time","stage","control_mask","type_mean","type_rms","contribution"]}
    dr=[];mean_dr=[];rate=[];mean_rate=[];crms=[];cdr=[];correlations=[];phase_medians=[];mean_phase_medians=[];phase_counts=[]
    max_error=0
    for m in records:
        d=checked_trial(m);assert np.array_equal(d["all_types"],types)
        stage=classify_stages(d["states"][:-1],d["u_applied"],d["control_mask"],cfg["x_goal"],cfg["success_position_m"],cfg["success_speed_m_s"])
        c,bias=contributions(d["phi"],model,labels,types,cfg["a_max"])
        active=d["control_mask"];N=len(active)
        err=float(np.max(np.abs((c.sum(1)+bias)[active]-d["u_raw"][active])))
        assert err<1e-10;max_error=max(err,max_error)
        x=d["type_rms"][active];y=d["type_mean"][active]
        dr.append(robust_range(x));mean_dr.append(robust_range(y))
        rate.append(np.mean(np.abs(np.diff(x,axis=0)),axis=0)/cfg["dt_phys"])
        mean_rate.append(np.mean(np.abs(np.diff(y,axis=0)),axis=0)/cfg["dt_phys"])
        crms.append(np.sqrt(np.mean(c[active]**2,axis=0)));cdr.append(robust_range(c[active]))
        correlations.append(np.corrcoef(x.T))
        phase_counts.append([int((stage==name).sum()) for name in ["approach","braking","near_hold"]])
        phase_medians.append([np.median(d["type_rms"][stage==name],axis=0) if (stage==name).sum()>=5 else np.full(len(types),np.nan) for name in ["approach","braking","near_hold"]])
        mean_phase_medians.append([np.median(d["type_mean"][stage==name],axis=0) if (stage==name).sum()>=5 else np.full(len(types),np.nan) for name in ["approach","braking","near_hold"]])
        values=dict(episode=np.repeat(m["id"],N),sample_id=d["sample_id"],physical_time=d["observation_time"],
            stage=stage,control_mask=active,type_mean=d["type_mean"],type_rms=d["type_rms"],contribution=c)
        for k,v in values.items():arrays[k].append(v)
        episodes.append(dict(id=m["id"],category=m["category"],record=m["record"],sha256=m["record_sha256"],
            samples=N,control_samples=int(active.sum()),stage_counts=dict(zip(["approach","braking","near_hold"],phase_counts[-1]))))
    joined={k:np.concatenate(v) for k,v in arrays.items()}
    phase_counts=np.array(phase_counts);phase_medians=np.array(phase_medians);mean_phase_medians=np.array(mean_phase_medians)
    comparable=np.all(phase_counts>=5,axis=1)
    phase=np.median(phase_medians[comparable],axis=0);mean_phase=np.median(mean_phase_medians[comparable],axis=0)
    phase_contrast=np.ptp(phase,axis=0)
    corr=np.median(np.array(correlations),axis=0)
    # Availability is exact matching in the already cached table; no downloads.
    annotations={str(t):dict(status="not found",count=0,example_root_id=None,side=None) for t in types}
    annotation_path=Path("assets/phase1b/sources/annotations.tsv")
    with annotation_path.open() as f:
        for row in csv.DictReader(f,delimiter="\t"):
            name=row["cell_type"]
            if name in annotations:
                a=annotations[name];a["count"]+=1;a["status"]="available in cached annotations"
                if a["example_root_id"] is None:a.update(example_root_id=row["root_id"],side=row["side"])
    rows=[]
    active=joined["control_mask"]
    for j,name in enumerate(types):
        indices=groups[str(name)];roles=sorted(set(pool["role"][indices]))
        rms=joined["type_rms"][active,j];means=joined["type_mean"][active,j]
        row=dict(cell_type=str(name),model_cells=len(indices),role=";".join(roles),
            readout_used=bool(np.any(labels==name)),pool_bins=int((labels==name).sum()),
            rms_min=float(rms.min()),rms_max=float(rms.max()),
            mean_min=float(means.min()),mean_max=float(means.max()),
            rms_dynamic_range=float(np.median(np.array(dr)[:,j])),
            mean_dynamic_range=float(np.median(np.array(mean_dr)[:,j])),
            rms_mean_abs_rate_per_phys_s=float(np.median(np.array(rate)[:,j])),
            mean_abs_rate_per_phys_s=float(np.median(np.array(mean_rate)[:,j])),
            phase_contrast=float(phase_contrast[j]),phase_comparable_episodes=int(comparable.sum()),
            phase_rms_approach=float(phase[0,j]),phase_rms_braking=float(phase[1,j]),phase_rms_near_hold=float(phase[2,j]),
            contribution_ax_rms=float(np.median(np.array(crms)[:,j,0])),
            contribution_ay_rms=float(np.median(np.array(crms)[:,j,1])),
            contribution_ax_dynamic_range=float(np.median(np.array(cdr)[:,j,0])),
            contribution_ay_dynamic_range=float(np.median(np.array(cdr)[:,j,1])),
            rms_correlation_T4a=float(corr[j,np.flatnonzero(types=="T4a")[0]]),
            annotation_status=annotations[str(name)]["status"],annotation_count=annotations[str(name)]["count"],
            annotation_example_root_id=annotations[str(name)]["example_root_id"])
        rows.append(row)
    # Full neural responses are available for 2 replays, not the original test run.
    replay_checks=[]
    for m in json.loads((SRC/"replays.json").read_text()):
        d=checked_trial(m);names,mean,rms=type_response(d["activity"],d["baseline"],d["cell_type"])
        assert np.array_equal(names,types)
        np.testing.assert_allclose(mean,d["type_mean"],atol=1e-12)
        np.testing.assert_allclose(rms,d["type_rms"],atol=1e-12)
        c,bias=contributions(d["phi"],model,labels,types,cfg["a_max"])
        error=float(np.max(np.abs((c.sum(1)+bias)[d["control_mask"]]-d["u_raw"][d["control_mask"]])))
        assert error<1e-10
        replay_checks.append(dict(id=m["id"],record=m["record"],sha256=m["record_sha256"],
            frames=len(rms),max_mean_error=float(np.max(np.abs(mean-d["type_mean"]))),
            max_rms_error=float(np.max(np.abs(rms-d["type_rms"]))),max_readout_error=error))
    np.savez_compressed(OUT/"cell_type_metrics.npz",**joined,all_types=types,feature_types=labels,
        bias_acceleration=bias,episode_ids=np.array([m["id"] for m in episodes]),
        episode_rms_dynamic_range=dr,episode_mean_dynamic_range=mean_dr,episode_contribution_rms=crms,
        episode_contribution_dynamic_range=cdr,episode_rms_abs_rate=rate,episode_mean_abs_rate=mean_rate,
        phase_counts=phase_counts,episode_phase_rms_medians=phase_medians,episode_phase_mean_medians=mean_phase_medians,
        comparable_phase_episodes=comparable,rms_correlation=corr)
    with (OUT/"cell_type_screening.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=dict(status="passed",all_types_evaluated=len(types),readout_types=len(set(labels)),
        episodes=episodes,metrics=rows,annotations=annotations,replay_checks=replay_checks,
        phase_comparable_episode_ids=[episodes[i]["id"] for i in np.flatnonzero(comparable)],
        aggregation="control-only metrics; median of per-episode p95-p05/rate/contribution RMS (equal episode weight); global extrema; phase medians across the same complete episodes",
        stage_rule="observation overrides all; near: error<.25 and speed<.01; braking: x>goal,vx<0,applied ax>0; approach: x>goal+.25,vx<0 excluding braking; else other",
        phase_contrast="max-min of three phase RMS medians over common episodes, >=5 samples each",
        contribution="pre-clipping a_max W_j z_j; bias separate; numerical additive components, not biological or causal importance",
        redundancy="median across episodes of within-episode Pearson RMS correlations; no correlation across reset boundaries",
        max_readout_reconstruction_error=max_error,bias_acceleration=bias.tolist(),
        original_test_success=evaluation["learner_groups"],
        readout_sha256=sha256(SRC/"readout.npz"),annotation_sha256=sha256(annotation_path),
        metrics_sha256=sha256(OUT/"cell_type_metrics.npz"),new_neural_inference=False,new_morphologies=0)
    write_json(OUT/"cell_type_screening.json",summary)
    for key in ["rms_dynamic_range","phase_contrast","contribution_ax_rms","contribution_ay_rms"]:
        print(key,[(r["cell_type"],round(r[key],6)) for r in sorted(rows,key=lambda r:-r[key])[:12]])
    print("Requested types",[(r["cell_type"],round(r["rms_dynamic_range"],4),round(r["phase_contrast"],4),round(r["contribution_ax_rms"],6),round(r["rms_correlation_T4a"],3)) for r in rows if r["cell_type"] in ["Mi1","Tm3"] or r["cell_type"].startswith(("T4","T5"))])
    print("Complete phase episodes",summary["phase_comparable_episode_ids"],"max reconstruction error",max_error)
if __name__=="__main__":main()
