"""Two static comparison figures, using common scales and original test_00."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

def main():
    out=Path("outputs/phase2e");dest=Path("docs/evidence_phase2e");dest.mkdir(parents=True,exist_ok=True)
    selection=json.loads((out/"candidate_selection.json").read_text())
    names=[r["cell_type"] for r in selection["candidates"]]
    report=json.loads((out/"cell_type_screening.json").read_text())
    rows={r["cell_type"]:r for r in report["metrics"]}
    with np.load(out/"cell_type_metrics.npz",allow_pickle=False) as z:
        chosen=z["episode"]=="test_00";t=z["physical_time"][chosen];stage=z["stage"][chosen]
        columns=[z["all_types"].tolist().index(n) for n in names]
        rms=z["type_rms"][chosen][:,columns];mean=z["type_mean"][chosen][:,columns]
    palette={"observation":"#dddddd","approach":"#bbdafa","braking":"#ffe0ae","near_hold":"#bde7c5","other":"#eeeeee"}
    starts=np.r_[0,np.flatnonzero(stage[1:]!=stage[:-1])+1];ends=np.r_[starts[1:],len(t)]
    fig,axes=plt.subplots(4,2,figsize=(12,10),sharex=True,sharey=True,layout="constrained")
    for j,ax in enumerate(axes.flat):
        for lo,hi in zip(starts,ends):ax.axvspan(t[lo],t[hi-1]+.5,color=palette[stage[lo]],alpha=.5,lw=0)
        ax.plot(t,rms[:,j],c="#174e89",lw=1.5)
        ax.plot(t,mean[:,j],c="#a13b31",lw=1,ls="--")
        ax.set_title(names[j],fontsize=11);ax.grid(alpha=.15);ax.axhline(0,c="#888888",lw=.5)
        ax.set_ylim(-.09,.6);ax.set_xlim(t[0],t[-1]+.5)

        if j>=6:ax.set_xlabel("Physical time [s]")
    fig.supylabel("Activity relative to baseline [model units]")
    handles=[Line2D([],[],c="#174e89",label="Type RMS"),Line2D([],[],c="#a13b31",ls="--",label="Signed mean")]
    handles += [Patch(color=palette[k],alpha=.5,label=k) for k in ["observation","approach","braking","near_hold"]]
    fig.legend(handles=handles,loc="outside lower center",ncols=6,fontsize=9)
    fig.suptitle("Original learned test_00: all candidates use the same time and activity scales\nStages from saved LVLH states / applied commands; no new inference",fontsize=12)
    fig.savefig(dest/"candidate_traces.png",dpi=170);fig.savefig(dest/"candidate_traces.pdf");plt.close(fig)

    fig,axes=plt.subplots(1,3,figsize=(12,5),sharey=True,layout="constrained")
    y=np.arange(len(names))
    for ax,key,title in [(axes[0],"rms_dynamic_range","Response p95 - p05"),(axes[1],"phase_contrast","Phase contrast (matched 9 trials)")]:
        ax.barh(y,[rows[n][key] for n in names],color="#5683ac")
        ax.set_xlim(0,.2);ax.set_xlabel("Baseline-relative RMS [model units]");ax.set_title(title,fontsize=11)
    axes[2].barh(y-.17,[rows[n]["contribution_ax_rms"]*1000 for n in names],height=.32,color="#d99645",label="LVLH ax")
    axes[2].barh(y+.17,[rows[n]["contribution_ay_rms"]*1000 for n in names],height=.32,color="#5683ac",label="LVLH ay")
    axes[2].set_xlim(0,.85);axes[2].set_xlabel("Contribution RMS [10^-3 m/s²]");axes[2].set_title("Pre-clipping additive components",fontsize=11)
    axes[2].legend(fontsize=9);axes[0].set_yticks(y,names);axes[0].invert_yaxis()
    for ax in axes:ax.grid(axis="x",alpha=.2)
    fig.suptitle("Frozen original test logs: equal weight per trial, control periods only\nReadout components are numerical contributions, not causal importance",fontsize=12)
    fig.savefig(dest/"candidate_metrics.png",dpi=170);fig.savefig(dest/"candidate_metrics.pdf");plt.close(fig)
if __name__=="__main__":main()
