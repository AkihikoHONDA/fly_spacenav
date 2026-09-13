"""Audit numerical records independently of plots and reported success."""
import json
from pathlib import Path
import numpy as np
from flyrendezvous.phase2_runtime import load_config,checked_trial
from flyrendezvous.hcw import Teacher
from flyrendezvous.camera import Camera
from flyrendezvous.features import history_matrix
from flyrendezvous.readout import Readout
from flyrendezvous.recording import sha256,write_json

OUT=Path("outputs/phase2")
def main():
    cfg=load_config();teacher=Teacher(cfg);camera=Camera(cfg["camera"])
    contract=json.loads((OUT/"contract.json").read_text());lock=json.loads((OUT/"model_lock.json").read_text())
    assert sha256("configs/phase2.json")==contract["config_sha256"]==lock["config_sha256"]
    assert sha256(OUT/"splits.json")==contract["splits_sha256"]==lock["splits_sha256"]
    assert sha256(OUT/"lqr.json")==contract["lqr_sha256"]
    assert sha256(OUT/"pooling.npz")==lock["pooling_sha256"]
    assert sha256(OUT/"readout.npz")==lock["readout_sha256"]
    splits=json.loads((OUT/"splits.json").read_text())
    initial={c["id"]:c for cases in splits.values() for c in cases}
    assert len({tuple(c["initial_state"]) for c in initial.values()})==42
    data=json.loads((OUT/"data.json").read_text())["episodes"]
    evaluation=json.loads((OUT/"evaluation.json").read_text())
    replays=json.loads((OUT/"replays.json").read_text())
    finalmodel=Readout.load(OUT/"readout.npz")
    candidates=[]
    for directory in ["round0","round1"]:
        path=OUT/directory/"candidates.json"
        if path.exists():candidates+=json.loads(path.read_text())
    assert len(candidates)<=12
    jobs=[(m,None) for m in data+evaluation["teacher"]+evaluation["zero"]]
    jobs +=[(m,finalmodel) for m in evaluation["learner"]+replays]
    for c in candidates:
        assert sha256(c["model"])==c["sha256"]
        model=Readout.load(c["model"]);jobs +=[(m,model) for m in c["closed_loop"]]
    augmentation=json.loads((OUT/"augmentation.json").read_text())
    assert augmentation["rounds"]<=1 and len(augmentation["episodes"])<=8
    if augmentation["episodes"]:
        previous=json.loads((OUT/"round0/selected.json").read_text())
        model=Readout.load(previous["model"])
        jobs +=[(m,model) for m in augmentation["episodes"]]
    max_dynamics=0.;max_policy=0.;frames=0;full_checks=0
    for m,model in jobs:
        d=checked_trial(m);N=m["samples"];frames+=N
        np.testing.assert_array_equal(d["states"][0],initial[m["id"]]["initial_state"])
        np.testing.assert_array_equal(d["sample_id"],np.arange(N))
        np.testing.assert_allclose(d["observation_time"],np.arange(N)*cfg["dt_phys"],atol=1e-12)
        np.testing.assert_allclose(d["neural_response_time"],(np.arange(N)+1)*cfg["dt_neural"],atol=1e-12)
        np.testing.assert_allclose(d["acceleration_interval"],np.column_stack([np.arange(N)*.5,(np.arange(N)+1)*.5]))
        expected=d["states"][:-1]@teacher.Ad.T+d["u_applied"]@teacher.Bd.T
        error=float(np.max(np.abs(expected-d["states"][1:])))
        max_dynamics=max(max_dynamics,error);assert error<1e-11
        np.testing.assert_array_equal(d["u_applied"][:20],0)
        np.testing.assert_array_equal(d["control_mask"],np.arange(N)>=20)
        labels=np.array([teacher.command(s)[1] for s in d["states"][:-1]])
        np.testing.assert_allclose(labels,d["u_teacher"],atol=1e-14)
        if m["controller"]=="teacher":
            np.testing.assert_allclose(d["u_applied"][20:],labels[20:],atol=1e-14)
        elif m["controller"]=="zero":np.testing.assert_array_equal(d["u_applied"],0)
        else:
            x=history_matrix(d["phi"],model.lag)
            predicted=cfg["a_max"]*model.predict(x[20:])
            e=float(np.max(np.abs(predicted-d["u_raw"][20:])))
            max_policy=max(max_policy,e);assert e<1e-10
            np.testing.assert_allclose(d["u_applied"][20:],np.clip(predicted,-cfg["a_max"],cfg["a_max"]),atol=1e-10)
        # Every image is from state[k], not state[k+1].
        for k,s in enumerate(d["states"][:-1]):np.testing.assert_array_equal(d["images"][k],camera.render(s))
        err=np.linalg.norm(d["states"][:,:2]-[cfg["x_goal"],0],axis=1)
        speed=np.linalg.norm(d["states"][:,2:],axis=1)
        good=(err<cfg["success_position_m"]) & (speed<cfg["success_speed_m_s"])
        run=0;maximum=0
        for k in range(N):
            run=run+1 if k>=20 and good[k] and good[k+1] else 0
            maximum=max(maximum,run)
        assert (maximum*.5>=10)==m["success"]
        np.testing.assert_allclose(m["final_position_error_m"],err[-1],atol=1e-12)
        np.testing.assert_allclose(m["final_speed_m_s"],speed[-1],atol=1e-12)
        if "activity" in d:
            with np.load(OUT/"pooling.npz",allow_pickle=False) as p:
                used=p["used_indices"];assignment=p["used_cell_feature_index"];counts=p["feature_counts"]
                for k in range(N):
                    delta=d["activity"][k].astype(float)-d["baseline"]
                    reference=np.array([delta[used[assignment==i]].mean() if counts[i] else 0 for i in range(len(counts))])
                    np.testing.assert_allclose(d["phi"][k],reference,atol=1e-12)
                types=d["all_types"]
                for j,name in enumerate(types):
                    delta=d["activity"][:,d["cell_type"]==name].astype(float)-d["baseline"][d["cell_type"]==name]
                    np.testing.assert_allclose(d["type_mean"][:,j],delta.mean(1),atol=1e-12)
                    np.testing.assert_allclose(d["type_rms"][:,j],np.sqrt(np.mean(delta*delta,axis=1)),atol=1e-12)
            full_checks+=1
    # Recompute the selected standardization using ONLY its training episodes.
    train=[m for m in data if m["split"]=="train"]+augmentation["episodes"]
    matrices=[]
    for m in train:
        d=checked_trial(m);x=history_matrix(d["phi"],finalmodel.lag);matrices.append(x[d["control_mask"]])
    x=np.concatenate(matrices)
    np.testing.assert_allclose(finalmodel.mean,x.mean(0),atol=1e-14)
    np.testing.assert_allclose(finalmodel.std,x.std(0),atol=1e-14)
    for path,digest in json.loads((OUT/"prior_hashes.json").read_text()).items():assert sha256(path)==digest,path
    size=sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    assert size<cfg["disk_budget_gib"]*1024**3
    result=dict(status="passed",episodes_checked=len(jobs),frames_checked=frames,full_response_episodes_checked=full_checks,
        max_dynamics_error=max_dynamics,max_saved_policy_error=max_policy,train_only_normalization_verified=True,
        success_recomputed=True,images_from_current_state_verified=True,old_files_unchanged=True,
        bytes=size,readout_sha256=sha256(OUT/"readout.npz"))
    write_json(Path("outputs/phase2e/phase2_numerical_audit.json"),result);print(json.dumps(result,indent=2))
if __name__=="__main__":main()
