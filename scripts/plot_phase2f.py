"""Original test_00 time series, fixed scales and state-derived phase shading."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from flyrendezvous.activity_display import TYPES
from flyrendezvous.viewer_phase2f import TYPE_COLORS

def main():
    out=Path("outputs/phase2f");evidence=Path("docs/evidence_phase2f");evidence.mkdir(exist_ok=True)
    with np.load(out/"type_activity.npz",allow_pickle=False) as z:
        sel=z["episode"]=="test_00";t=z["physical_time"][sel];raw=z["raw_rms"][sel];q=z["q"][sel];stage=z["stage"][sel]
    fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True,layout="constrained")
    phase_colors={"observation":"#dedede","approach":"#d3e6f9","braking":"#fde8c9","near_hold":"#d6efd8","other":"#efefef"}
    starts=np.r_[0,np.flatnonzero(stage[1:]!=stage[:-1])+1];ends=np.r_[starts[1:],len(t)]
    for ax in axes:
        for lo,hi in zip(starts,ends):ax.axvspan(t[lo],t[hi-1]+.5,color=phase_colors[stage[lo]],lw=0)
        ax.grid(alpha=.15);ax.set_xlim(0,t[-1]+.5)
    for j,name in enumerate(TYPES):
        color=np.array(TYPE_COLORS[j])/255
        axes[0].plot(t,raw[:,j],color=color,label=name,lw=2)
        axes[1].plot(t,q[:,j],color=color,label=name,lw=2)
    axes[0].set(ylabel="Raw RMS [model units]",ylim=(0,.6));axes[0].legend(ncols=5)
    axes[1].set(ylabel="Within-type q",ylim=(-.03,1.03))
    axes[2].plot(t,np.clip(raw[:,2]/.22,0,1),color="#2877a7",label="A: absolute color fraction RMS / 0.22",lw=2)
    axes[2].plot(t,q[:,2],color="#bb721e",label="B: fixed relative color fraction",lw=2)
    axes[2].set(ylabel="T4a palette fraction",xlabel="Physical time [s]",ylim=(-.03,1.03));axes[2].legend()
    fig.legend(handles=[Patch(color=phase_colors[k],label=k) for k in ["observation","approach","braking","near_hold"]],loc="outside lower center",ncols=4)
    fig.suptitle("Frozen original learned test_00 — one fixed calibration per type\nRelative levels do not compare absolute activity between types")
    fig.savefig(evidence/"raw_relative_timeseries.png",dpi=170);fig.savefig(evidence/"raw_relative_timeseries.pdf");plt.close(fig)
if __name__=="__main__":main()
