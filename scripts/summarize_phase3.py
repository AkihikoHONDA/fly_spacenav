"""Figures and descriptive metrics from frozen records; no tuning."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flyrendezvous.phase3_runtime import checked_trial,load_config
from flyrendezvous.geometry_phase3 import Teacher,Camera
from flyrendezvous.display_coordinates import display_coordinates
from flyrendezvous.viewer_phase3 import display_data
from flyrendezvous.activity_display import TYPES,map_metrics
from flyrendezvous.projection import rms_colors
from flyrendezvous.recording import write_json,sha256
OUT=Path("outputs/phase3");E=Path("docs/evidence_phase3")
def main():
    E.mkdir(exist_ok=True);cfg=load_config();goal=Teacher(cfg).goal[:2]
    evaluation=json.loads((OUT/"evaluation.json").read_text());zero=json.loads((OUT/"zero_shot.json").read_text())
    scales=json.loads((OUT/"display_scales.json").read_text())
    theta=np.linspace(0,2*np.pi,200);circle=np.c_[np.cos(theta),np.sin(theta)]
    def geometry(ax,title):
        ax.fill(circle[:,0],circle[:,1],color=".5",label="sphere R=1 m")
        ax.plot(5*circle[:,0],5*circle[:,1],color="seagreen",ls="--",label="5 m standoff")
        xy=display_coordinates(goal);ax.scatter(*xy,c="green",marker="*",s=95,label="selected goal")
        ax.set(xlabel="Display X = -y [m] (left: along-track)",ylabel="Display Y = x [m] (down: central body)",title=title,xlim=(-19,7),ylim=(-19,7))
        ax.set_aspect("equal");ax.grid(alpha=.15)
    fig,axes=plt.subplots(1,3,figsize=(15,5))
    for ax,key,title in zip(axes,["teacher","learner","zero"],["Teacher: held-out 12/12","New readout: approach 8/8, near 2/4","Old readout: zero-shot 0/4 (train cases)"]):
        geometry(ax,title);records=zero["results"] if key=="zero" else evaluation[key]
        for m in records:
            d=checked_trial(m);xy=display_coordinates(d["states"][:,:2])
            ax.plot(*xy.T,color="steelblue" if m["success"] else "firebrick",alpha=.7,lw=1)
            ax.scatter(*xy[0],s=8,c="black")
            if not m["success"]:ax.scatter(*xy[-1],marker="x",color="firebrick",s=35)
    axes[0].legend(fontsize=7,loc="upper left");fig.tight_layout();fig.savefig(E/"trajectories.png",dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(13,7))
    for col,ident in enumerate(["test_00","test_09","test_11"]):
        for key,color in [("teacher","seagreen"),("learner","steelblue")]:
            m=next(m for m in evaluation[key] if m["id"]==ident);d=checked_trial(m);t=np.arange(len(d["states"]))*cfg["dt_phys"]
            error=np.linalg.norm(d["states"][:,:2]-goal,axis=1);speed=np.linalg.norm(d["states"][:,2:],axis=1)
            axes[0,col].plot(t,error,label=key,color=color);axes[1,col].plot(t,speed,label=key,color=color)
        axes[0,col].axhline(.25,c=".5",ls="--");axes[1,col].axhline(.01,c=".5",ls="--")
        axes[0,col].set(title=ident,ylabel="Goal error [m]");axes[1,col].set(xlabel="Physical seconds",ylabel="Speed [m/s]")
        for ax in axes[:,col]:ax.grid(alpha=.2);ax.legend()
    fig.tight_layout();fig.savefig(E/"teacher_vs_learner.png",dpi=160);plt.close(fig)
    initial=json.loads((OUT/"phase3a_initial.json").read_text())["results"][0]
    final=json.loads((OUT/"phase3a.json").read_text())["results"][0]
    camera=Camera(cfg["camera"]);fig,axes=plt.subplots(1,2,figsize=(11,5));geometry(axes[0],"Teacher gate_00: initial and rotated Q")
    for m,label in [(initial,"Initial LVLH Q: FOV exit"),(final,"Approach-frame Q: success")]:
        d=checked_trial(m);xy=display_coordinates(d["states"][:,:2]);axes[0].plot(*xy.T,label=label)
        rel=-d["states"][:,:2];distance=np.linalg.norm(rel,axis=1)
        extent=np.abs(np.arctan2(rel@camera.right,rel@camera.bore))+np.arcsin(1/distance)
        axes[1].plot(np.arange(len(rel))*.5,np.rad2deg(extent),label=label)
    axes[0].legend(fontsize=7);axes[1].axhline(20,color="red",ls="--",label="nominal FOV half-angle")
    axes[1].set(xlabel="Physical seconds",ylabel="abs(bearing) + sphere angular radius [deg]",title="Independent angular FOV diagnostic")
    axes[1].legend(fontsize=8);fig.tight_layout();fig.savefig(E/"teacher_gate_diagnostic.png",dpi=160);plt.close(fig)
    activity=[];palette=[]
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for col,ident in enumerate(["test_00","test_09"]):
        m=next(m for m in evaluation["learner"] if m["id"]==ident);d=checked_trial(m);delta,raw,q=display_data(d,scales);active=d["control_mask"]
        for j,name in enumerate(TYPES):
            axes[0,col].plot(d["observation_time"],raw[:,j],label=name)
            axes[1,col].plot(d["observation_time"],q[:,j],label=name)
        axes[0,col].set(title=ident+" / "+m["termination_reason"],ylabel="Raw RMS [model units]")
        axes[1,col].set(xlabel="Physical seconds",ylabel="Fixed within-type relative q")
        for ax in axes[:,col]:ax.legend(ncol=5,fontsize=8);ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(E/"activity_summary.png",dpi=160);plt.close(fig)
    for m in evaluation["learner"]:
        d=checked_trial(m);delta,raw,q=display_data(d,scales);active=d["control_mask"];pairs=active[1:]&active[:-1]
        for j,name in enumerate(TYPES):
            activity.append(dict(id=m["id"],type=name,q_std=float(q[active,j].std()),
                low_clip=float(np.mean(raw[active,j]<scales["p05"][j])),high_clip=float(np.mean(raw[active,j]>scales["p95"][j])),
                map=map_metrics(delta[:,j],scales["signed_map_limit"][j],active)))
        for mode,rgb in [("absolute",rms_colors(raw[:,2],.22)),("relative",rms_colors(q[:,2],1))]:
            palette.append(dict(id=m["id"],mode=mode,rgb_range=np.ptp(rgb[active].astype(float),axis=0).tolist(),
                changed_fraction=float(np.mean(np.any(np.diff(rgb.astype(float),axis=0)[pairs]!=0,axis=1)))))
    write_json(OUT/"activity_summary.json",dict(metrics=activity,palette=palette))
    stats={}
    for key,records in [("teacher",evaluation["teacher"]),("learner",evaluation["learner"]),("zero_shot",zero["results"])]:
        stats[key]={}
        for category in ["approach","near","all"]:
            a=[m for m in records if category=="all" or m["category"]==category]
            stats[key][category]=dict(success=sum(m["success"] for m in a),total=len(a),
                fov_loss=sum(m["fov_loss"] for m in a),collision=sum(m["collision"] for m in a),
                min_center_m=min(m["min_target_distance_m"] for m in a),min_clearance_m=min(m["min_surface_clearance_m"] for m in a),
                final_error_mean_m=float(np.mean([m["final_position_error_m"] for m in a])),
                final_speed_mean_m_s=float(np.mean([m["final_speed_m_s"] for m in a])),
                success_time_range_s=[min(m["final_time_s"] for m in a if m["success"]),max(m["final_time_s"] for m in a if m["success"])] if any(m["success"] for m in a) else None,
                max_saturation_fraction=max(m["saturation_fraction"] for m in a),
                mean_integrated_acceleration_m_s=float(np.mean([m["integrated_acceleration_m_s"] for m in a])))
    stats["failed_learner"]=[]
    for m in evaluation["learner"]:
        if m["success"]:continue
        d=checked_trial(m);last=d["states"][-1];radial=np.array(cfg["goal_direction"]);tangent=np.array([-radial[1],radial[0]])
        stats["failed_learner"].append(dict(id=m["id"],reason=m["termination_reason"],initial=m["initial_state"],
            final=last.tolist(),radial_error=float((last[:2]-goal)@radial),tangential_error=float((last[:2]-goal)@tangent),
            last_applied=d["u_applied"][-1].tolist(),last_teacher_label=d["u_teacher"][-1].tolist(),
            final_time=m["final_time_s"],longest_hold=m["longest_hold_s"]))
    write_json(OUT/"summary.json",stats);print(json.dumps(stats,indent=2))
if __name__=="__main__":main()
