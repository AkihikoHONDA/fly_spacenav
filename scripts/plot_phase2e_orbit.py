"""Display-only plot of the original immutable test results."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from flyrendezvous.phase2_runtime import checked_trial
from flyrendezvous.display_coordinates import display_coordinates
DEST=Path("outputs/phase2e")
def main():
    DEST.mkdir(parents=True,exist_ok=True)
    ev=json.loads(Path("outputs/phase2/evaluation.json").read_text())
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for records,color,style,label in [(ev["teacher"],"#777777","--","LQR teacher"),(ev["learner"],"#1666a5","-","Image-only learned policy")]:
        for i,m in enumerate(records):
            d=checked_trial(m);s=d["states"];t=np.arange(len(s))*.5
            xy=display_coordinates(s[:,:2])
            axes[0,0].plot(xy[:,0],xy[:,1],style,color=color,alpha=.55,label=label if i==0 else None)
            axes[0,1].plot(t,np.linalg.norm(s[:,:2]-[10,0],axis=1),style,color=color,alpha=.5)
            axes[1,0].plot(t,np.linalg.norm(s[:,2:],axis=1),style,color=color,alpha=.5)
    axes[0,0].scatter([0],[10],c="green",marker="x",s=60,label="Goal");axes[0,0].legend(fontsize=8)
    axes[0,0].set(xlabel="X = -y [m] (left: along-track)",ylabel="Y = x [m] (down: central body)",title="All 12 held-out initial conditions")
    axes[0,0].scatter([0],[0],c="black",s=25,label="Target")
    axes[0,0].legend(fontsize=8)
    axes[0,0].set_aspect("equal",adjustable="datalim")
    axes[0,1].axhline(.25,c="green",ls=":");axes[0,1].set(xlabel="Physical time [s]",ylabel="Position error [m]")
    axes[1,0].axhline(.01,c="green",ls=":");axes[1,0].set(xlabel="Physical time [s]",ylabel="Speed [m/s]")
    for controller,color in [("teacher","#777777"),("learner","#1666a5")]:
        d=checked_trial(ev[controller][0]);t=d["observation_time"]
        axes[1,1].plot(t,d["u_applied"][:,0],color=color,label=controller+" ax")
        axes[1,1].plot(t,d["u_applied"][:,1],color=color,ls="--",label=controller+" ay")
    axes[1,1].set(xlabel="Physical time [s]",ylabel="Applied acceleration [m/s²]",title="test_00 actual applied commands")
    axes[1,1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.2)
    fig.suptitle("FlyRendezvous Phase 2E — original test evaluation (replays excluded)")
    fig.savefig(DEST/"evaluation_display_coordinates.png",dpi=180);fig.savefig(DEST/"evaluation_display_coordinates.pdf")
    plt.close(fig)
if __name__=="__main__":main()
