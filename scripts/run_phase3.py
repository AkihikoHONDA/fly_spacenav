"""Bounded Phase 2 stages; immutable split/config contracts, no test tuning."""
import argparse,json,time,shutil
from pathlib import Path
import numpy as np
from flyrendezvous.phase3_runtime import *
from flyrendezvous.features import Pooling,history_matrix
from flyrendezvous.readout import Readout,ImagePolicy

OUT=Path("outputs/phase3")
def contracts():
    cfg=load_config()
    if sha256("configs/phase3.json")!=json.loads((OUT/"contract.json").read_text())["config_sha256"]:raise ValueError("Frozen config changed")
    c=json.loads((OUT/"contract.json").read_text())
    if sha256(OUT/"splits.json")!=c["splits_sha256"]:raise ValueError("Frozen splits changed")
    return cfg,json.loads((OUT/"splits.json").read_text())
def stage_a():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"contract.json").exists():raise RuntimeError("Already initialized; preserve the frozen run")
    cfg=load_config();splits=make_splits(cfg);write_json(OUT/"splits.json",splits)
    write_json(OUT/"config.json",cfg);write_json(OUT/"lqr.json",Teacher(cfg).metadata())
    results=[]
    for case in splits["gate"]:
        arrays,m=rollout(cfg,case,"teacher");m=save_trial(OUT/("teacher_preflight_"+cfg.get("teacher_gate_attempt","initial")),arrays,m);results.append(m)
    write_json(OUT/"phase3a.json",dict(status="passed" if all(r["success"] for r in results) else "failed",
        results=results,groups=groups(results),changes_from_initial_proposal=["Q rotated from LVLH axes into approach radial/tangential axes; same eigenvalues and R; geometry unchanged"]))
    print("Teacher preflight",groups(results),flush=True)
    if not all(r["success"] for r in results):raise RuntimeError("Teacher gate failed; inspect before making data")
    write_json(OUT/"contract.json",dict(config_sha256=sha256("configs/phase3.json"),
        splits_sha256=sha256(OUT/"splits.json"),lqr_sha256=sha256(OUT/"lqr.json"),
        note="Locked before neural data, learning or test evaluation; geometry unchanged; teacher cost axes rotated after documented initial FOV failures"))
def neural_setup():
    from flyrendezvous.adapter import FlyvisAdapter
    adapter=FlyvisAdapter(adapter_config());pooling=Pooling(adapter.nodes,load_config()["pool_bins"])
    return adapter,pooling
def stage_b():
    if (OUT/"data.json").exists():raise RuntimeError("Data already generated; use a new output directory")
    cfg,splits=contracts();adapter,pooling=neural_setup();pooling.save(OUT/"pooling.npz")
    write_json(OUT/"features.json",dict(n_model_cells=len(pooling.cell_index),excluded_role="input",
        excluded_types=sorted(set(pooling.cell_type[pooling.excluded])),used_types=pooling.used_types.tolist(),
        used_cells=len(pooling.used),dimension=pooling.dimension,empty_bins=int((pooling.counts==0).sum()),
        bounds="shared retinal lattice x=1.5v, screen y=sqrt(3)*(u+v/2); 4 equal intervals each axis",
        bin_assignment="left-closed internal bins; last includes maximum; empty bins zero",
        pooling_sha256=sha256(OUT/"pooling.npz"),checkpoint_sha256=sha256(adapter.checkpoint),
        connectome_sha256=sha256(adapter.connectome_file),flyvis=adapter.flyvis_version))
    results=[]
    for case in splits["train"]+splits["validation"]:
        a,m=rollout(cfg,case,"teacher",adapter,pooling,full=case["id"]=="train_00")
        if not m["success"]:raise RuntimeError("Neural teacher data gate failed: "+str(m))
        m=save_trial(OUT/"teacher_data",a,m);results.append(m)
        print("data",case["id"],m["samples"],round(m["wall_seconds"],2),flush=True)
    write_json(OUT/"data.json",dict(status="passed",episodes=results,
        pooling_sha256=sha256(OUT/"pooling.npz"),
        parameter_sha256=adapter.parameter_hash(),test_neural_data_generated=False))

def regression_data(episodes,lag,cfg):
    X=[];Y=[]
    for m in episodes:
        d=checked_trial(m);x=history_matrix(d["phi"],lag);mask=d["control_mask"] & np.isfinite(x).all(1)
        X.append(x[mask]);Y.append(d["u_teacher"][mask]/cfg["a_max"])
    return np.concatenate(X),np.concatenate(Y)
def candidates(cfg,splits,adapter,pooling,training,validation,round_name):
    directory=OUT/round_name;directory.mkdir(parents=True,exist_ok=True);results=[]
    for lag in cfg["history_lags"]:
        X,Y=regression_data(training,lag,cfg);VX,VY=regression_data(validation,lag,cfg)
        for lam in cfg["ridge_lambdas"]:
            name=f"lag{lag}_lambda{lam:g}";path=directory/(name+".npz")
            start=time.perf_counter()
            model=Readout.fit(X,Y,lag,lam,cfg["constant_std_threshold"]);model.save(path)
            reloaded=Readout.load(path)
            np.testing.assert_allclose(reloaded.predict(VX),model.predict(VX),atol=0,rtol=0)
            train_mse=float(np.mean((model.predict(X)-Y)**2));val_mse=float(np.mean((model.predict(VX)-VY)**2))
            policy=ImagePolicy(adapter,pooling,reloaded,cfg["a_max"]);closed=[]
            for case in splits["validation"]:
                a,m=rollout(cfg,case,"learner",adapter,pooling,policy)
                closed.append(save_trial(directory/name,a,m))
            result=dict(candidate=name,lag=lag,regularization=lam,model=path.as_posix(),sha256=sha256(path),
                training_samples=len(X),retained_features=int(model.keep.sum()),train_mse=train_mse,validation_mse=val_mse,
                success=sum(m["success"] for m in closed),total=len(closed),
                mean_final_position_error=float(np.mean([m["final_position_error_m"] for m in closed])),
                groups=groups(closed),closed_loop=closed,wall_seconds=time.perf_counter()-start)
            results.append(result);write_json(directory/"candidates.json",results)
            print(round_name,name,"MSE",val_mse,"closed",result["success"],"/",len(closed),flush=True)
    selected=min(results,key=lambda r:(-r["success"],r["mean_final_position_error"],r["validation_mse"],r["lag"],r["regularization"]))
    write_json(directory/"selected.json",selected)
    return selected
def stage_c():
    cfg,splits=contracts()
    if (OUT/"model_lock.json").exists():raise RuntimeError("Model already locked; no retuning")
    adapter,pooling=neural_setup()
    data=json.loads((OUT/"data.json").read_text())["episodes"]
    training=[m for m in data if m["split"]=="train"];validation=[m for m in data if m["split"]=="validation"]
    selected=candidates(cfg,splits,adapter,pooling,training,validation,"round0")
    augmented=[];trigger=(np.sqrt(selected["validation_mse"])<.25 and selected["success"]<len(splits["validation"]))
    if trigger:
        model=Readout.load(selected["model"]);policy=ImagePolicy(adapter,pooling,model,cfg["a_max"])
        # Predeclared first 6 approach + first 2 near training initial conditions.
        cases=[c for c in splits["train"] if c["category"]=="approach"][:6]+[c for c in splits["train"] if c["category"]=="near"][:2]
        for case in cases:
            a,m=rollout(cfg,case,"learner",adapter,pooling,policy)
            augmented.append(save_trial(OUT/"augmentation",a,m))
            print("augmentation",case["id"],m["termination_reason"],flush=True)
        write_json(OUT/"augmentation.json",dict(rounds=1,episodes=augmented,
            reason="teacher-forced normalized RMSE < 0.25 but validation closed-loop failures",
            dynamics="learner only; LQR only labels; training initial conditions only"))
        selected=candidates(cfg,splits,adapter,pooling,training+augmented,validation,"round1")
    else:write_json(OUT/"augmentation.json",dict(rounds=0,episodes=[],reason="predeclared trigger not met"))
    shutil.copyfile(selected["model"],OUT/"readout.npz")
    lock=dict(selected=selected,readout_sha256=sha256(OUT/"readout.npz"),pooling_sha256=sha256(OUT/"pooling.npz"),
        config_sha256=sha256("configs/phase3.json"),splits_sha256=sha256(OUT/"splits.json"),
        parameter_sha256=adapter.parameter_hash(),augmentation_rounds=int(trigger),selection_uses_test=False)
    write_json(OUT/"model_lock.json",lock)
def stage_d():
    cfg,splits=contracts();lock=json.loads((OUT/"model_lock.json").read_text())
    if sha256(OUT/"readout.npz")!=lock["readout_sha256"]:raise ValueError("Locked model changed")
    if (OUT/"evaluation.json").exists():raise RuntimeError("Final test already evaluated; do not tune")
    assert (OUT/"display_scales.json").exists(),"Freeze non-test display scales before test"
    if (OUT/"test_started.json").exists():raise RuntimeError("Test was already started; do not repeat")
    write_json(OUT/"test_started.json",dict(readout_sha256=lock["readout_sha256"],display_scales_sha256=sha256(OUT/"display_scales.json")))
    adapter,pooling=neural_setup();model=Readout.load(OUT/"readout.npz")
    policy=ImagePolicy(adapter,pooling,model,cfg["a_max"]);teacher_results=[];learner_results=[]
    for case in splits["test"]:
        a,m=rollout(cfg,case,"teacher")
        teacher_results.append(save_trial(OUT/"test_teacher",a,m))
        a,m=rollout(cfg,case,"learner",adapter,pooling,policy)
        learner_results.append(save_trial(OUT/"test_learner",a,m))
        write_json(OUT/"test_progress.json",dict(teacher=teacher_results,learner=learner_results))
        print("test",case["id"],"teacher",teacher_results[-1]["termination_reason"],"learner",m["termination_reason"],m["final_position_error_m"],flush=True)
    a,m=rollout(cfg,splits["test"][0],"zero")
    zero=save_trial(OUT/"zero",a,m)
    result=dict(teacher=teacher_results,learner=learner_results,zero=[zero],teacher_groups=groups(teacher_results),
        learner_groups=groups(learner_results),readout_sha256=lock["readout_sha256"],
        initial_demo_criterion=sum(r["success"] and r["category"]=="approach" for r in learner_results)>=3)
    write_json(OUT/"evaluation.json",result)
    print("Final",result["learner_groups"],"criterion",result["initial_demo_criterion"],flush=True)


def stage_zero():
    cfg,splits=contracts()
    if (OUT/"zero_shot.json").exists():raise RuntimeError("Zero-shot already evaluated")
    adapter,pooling=neural_setup()
    original=Path("outputs/phase2/readout.npz");before=sha256(original)
    policy=ImagePolicy(adapter,pooling,Readout.load(original),cfg["a_max"])
    cases=splits["train"][:2]+[c for c in splits["train"] if c["category"]=="near"][:2]
    results=[]
    for case in cases:
        a,m=rollout(cfg,case,"learner",adapter,pooling,policy)
        results.append(save_trial(OUT/"zero_shot",a,m))
        print("zero-shot",case["id"],m["termination_reason"],flush=True)
    assert sha256(original)==before
    write_json(OUT/"zero_shot.json",dict(results=results,groups=groups(results),readout_sha256=before,
        diagnostic_only=True,output_axes_unchanged=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("stage",choices=["a","zero","b","c","d"])
    args=p.parse_args()
    {"a":stage_a,"zero":stage_zero,"b":stage_b,"c":stage_c,"d":stage_d}[args.stage]()
