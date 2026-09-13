"""Standalone scientific figures and flat results from immutable test records."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flyrendezvous.phase2_runtime import checked_trial
from flyrendezvous.recording import write_json
OUT=Path("outputs/phase2");EVIDENCE=Path("docs/evidence_phase2")
def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    ev=json.loads((OUT/"evaluation.json").read_text())
    fields=["id","category","controller","success","termination_reason","final_time_s","first_hold_time_s","longest_hold_s",
        "final_position_error_m","final_speed_m_s","min_target_distance_m","saturation_fraction","acceleration_rmse_m_s2","integrated_acceleration_m_s","wall_seconds"]
    with (OUT/"results.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");writer.writeheader()
        writer.writerows(ev["teacher"]+ev["learner"]+ev["zero"])
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for records,color,style,label in [(ev["teacher"],"#777777","--","LQR teacher"),(ev["learner"],"#1666a5","-","Image-only learned policy")]:
        for i,m in enumerate(records):
            d=checked_trial(m);s=d["states"];t=np.arange(len(s))*.5
            axes[0,0].plot(s[:,0],s[:,1],style,color=color,alpha=.55,label=label if i==0 else None)
            axes[0,1].plot(t,np.linalg.norm(s[:,:2]-[10,0],axis=1),style,color=color,alpha=.5)
            axes[1,0].plot(t,np.linalg.norm(s[:,2:],axis=1),style,color=color,alpha=.5)
    axes[0,0].scatter([10],[0],c="green",marker="x",s=60,label="Goal");axes[0,0].legend(fontsize=8)
    axes[0,0].set(xlabel="x radial outward [m]",ylabel="y along-track [m]",title="All 12 held-out initial conditions")
    axes[0,1].axhline(.25,c="green",ls=":");axes[0,1].set(xlabel="Physical time [s]",ylabel="Position error [m]")
    axes[1,0].axhline(.01,c="green",ls=":");axes[1,0].set(xlabel="Physical time [s]",ylabel="Speed [m/s]")
    for controller,color in [("teacher","#777777"),("learner","#1666a5")]:
        d=checked_trial(ev[controller][0]);t=d["observation_time"]
        axes[1,1].plot(t,d["u_applied"][:,0],color=color,label=controller+" ax")
        axes[1,1].plot(t,d["u_applied"][:,1],color=color,ls="--",label=controller+" ay")
    axes[1,1].set(xlabel="Physical time [s]",ylabel="Applied acceleration [m/s²]",title="test_00 actual applied commands")
    axes[1,1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle("FlyRendezvous Phase 2 — original test evaluation (replays excluded)")
    fig.savefig(EVIDENCE/"evaluation.png",dpi=180);fig.savefig(EVIDENCE/"evaluation.pdf")
    plt.close(fig)
    replay_info=[]
    for m in json.loads((OUT/"replays.json").read_text()):
        new=checked_trial(m)
        with np.load(m["original_record"],allow_pickle=False) as z:old={k:z[k] for k in z.files}
        n=min(len(old["sample_id"]),len(new["sample_id"]))
        image_diff=np.any(new["images"][:n]!=old["images"][:n],axis=(1,2))
        replay_info.append(dict(id=m["id"],outcome_matches=m["replay_outcome_matches"],
            numerical_match=m["replay_numerically_matches"],time_difference_s=m["replay_time_difference_s"],
            max_position_component_difference_m=float(np.abs(new["states"][:n+1,:2]-old["states"][:n+1,:2]).max()),
            max_velocity_component_difference_m_s=float(np.abs(new["states"][:n+1,2:]-old["states"][:n+1,2:]).max()),
            max_acceleration_difference_m_s2=m["replay_max_acceleration_difference"],
            baseline_max_difference=float(np.abs(new["baseline"]-old["baseline"]).max()),
            first_different_image_sample=int(np.flatnonzero(image_diff)[0]) if image_diff.any() else None))
    write_json(OUT/"replay_comparison.json",replay_info)
    # Receptor visibility relative to an actual uniform image through the same BoxEye:
    # gray image is included in the smoke only indirectly, so report central contrast
    # and actual stimulus response range without equating border padding to target.
    smoke=json.loads((OUT/"smoke.json").read_text())
    camera_info=[]
    for m in smoke:
        d=checked_trial(m);central=(d["receptor_u"]==0)&(d["receptor_v"]==0)
        camera_info.append(dict(id=m["id"],radius_px_min=float(d["projection"][:,2].min()),
            radius_px_max=float(d["projection"][:,2].max()),central_receptor_min=float(d["receptor_input"][:,central].min()),
            central_receptor_max=float(d["receptor_input"][:,central].max()),
            image_levels=len(np.unique(d["images"]))))
    write_json(OUT/"camera_diagnostic.json",camera_info)
    print("Saved results.csv, evaluation PNG/PDF, camera and replay diagnostics")
if __name__=="__main__":main()
