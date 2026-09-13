"""Causal simulator and auditable episodes. Learned policy cannot access state."""
import json,time
from pathlib import Path
import numpy as np
from .geometry_phase3 import Camera,Teacher
from .recording import write_json,sha256

def load_config():return json.loads(Path("configs/phase3.json").read_text())
def adapter_config():
    cfg=json.loads(Path("configs/phase1.json").read_text())
    assert cfg["dt"]==load_config()["dt_neural"]
    return cfg

def make_splits(cfg):
    splits={}
    er=np.asarray(cfg["goal_direction"]);et=np.array([-er[1],er[0]])
    for split,spec in {**cfg["splits"],"gate":cfg["teacher_gate"]}.items():
        rng=np.random.default_rng(spec["seed"]);cases=[]
        for i in range(spec["count"]):
            category="near" if i>=spec["count"]-spec["near"] else "approach"
            if category=="approach":
                radial=rng.uniform(*cfg["approach_radial_m"]);cross=rng.uniform(*cfg["cross_offset_m"])
                velocity=rng.uniform(*cfg["approach_velocity_m_s"],size=2)
            else:
                radial=cfg["standoff_radius_m"]+rng.uniform(*cfg["near_position_offset_m"])
                cross=rng.uniform(*cfg["near_position_offset_m"])
                velocity=rng.uniform(*cfg["near_velocity_m_s"],size=2)
            state=np.r_[radial*er+cross*et,velocity]
            cases.append(dict(id=f"{split}_{i:02d}",split=split,seed=spec["seed"],category=category,initial_state=state.tolist()))
        splits[split]=cases
    keys=[tuple(c["initial_state"]) for cases in splits.values() for c in cases]
    assert len(keys)==len(set(keys))
    return splits

def safety(state,camera,cfg):
    if not np.isfinite(state).all():return "nonfinite"
    distance=np.linalg.norm(state[:2])
    if distance<=cfg["camera"]["target_radius_m"]+cfg["collision_margin_m"]:return "collision"
    if distance>=cfg["max_range_m"]:return "range_exit"
    if not camera.project(state)[1]:return "field_of_view_exit"
    return None

def rollout(cfg,case,mode,adapter=None,pooling=None,policy=None,full=False,max_steps=None):
    teacher=Teacher(cfg);camera=Camera(cfg["camera"]);s=np.array(case["initial_state"],dtype=float)
    if mode=="learner" and policy is None:raise ValueError("Learned policy required")
    if policy is not None:
        if policy.adapter is not adapter:raise ValueError("Inconsistent neural adapter")
        policy.reset();baseline=policy.baseline
    elif adapter is not None:baseline=adapter.reset()
    else:baseline=None
    data={k:[] for k in ["images","projection","u_raw","u_applied","u_teacher_raw","u_teacher",
                         "control_mask","phi","type_mean","type_rms","receptor_input","activity","display_activity","wall_seconds"]}
    display_indices=None
    if adapter is not None:
        display_indices=np.array([np.flatnonzero(pooling.cell_type==name) for name in ["T2","Tm3","T4a","T5d","L2"]])
    states=[s.copy()];reason="timeout";hold_start=None;longest_hold=0.;arrival=None
    dt=cfg["dt_phys"];observe=round(cfg["observe_seconds"]/dt)
    steps=round(cfg["max_phys_seconds"]/dt) if max_steps is None else max_steps
    start=time.perf_counter()
    if adapter is not None:adapter.torch.cuda.reset_peak_memory_stats(adapter.device)
    for k in range(steps):
        failure=safety(s,camera,cfg)
        if failure:reason=failure;break
        image=camera.render(s);projection,_=camera.project(s)
        active=k>=observe
        label_raw,label=teacher.command(s)
        if mode=="learner":
            raw,applied,neural=policy.step(image)
        elif adapter is not None:
            activity,receptor=adapter.chunk(image[None])
            neural=dict(activity=activity[0],receptors=receptor[0],
                        phi=pooling.extract(activity[0],baseline))
            raw,applied=(label_raw,label) if mode=="teacher" else (np.zeros(2),np.zeros(2))
        else:
            neural=None;raw,applied=(label_raw,label) if mode=="teacher" else (np.zeros(2),np.zeros(2))
        if not active:raw=np.zeros(2);applied=np.zeros(2)
        if not np.isfinite(raw).all() or not np.isfinite(applied).all():reason="nonfinite";break
        next_s=teacher.advance(s,applied)
        for key,value in dict(images=image,projection=projection,u_raw=raw,u_applied=applied,
            u_teacher_raw=label_raw,u_teacher=label,control_mask=active).items():data[key].append(value)
        if neural is not None:
            mean,rms=pooling.summaries(neural["activity"],baseline)
            data["phi"].append(neural["phi"]);data["type_mean"].append(mean);data["type_rms"].append(rms)
            data["display_activity"].append(neural["activity"][display_indices])
            if full:
                data["receptor_input"].append(neural["receptors"]);data["activity"].append(neural["activity"])
        data["wall_seconds"].append(time.perf_counter()-start)
        states.append(next_s.copy())
        good=lambda v:np.linalg.norm(v[:2]-teacher.goal[:2])<cfg["success_position_m"] and np.linalg.norm(v[2:])<cfg["success_speed_m_s"]
        if active and good(s) and good(next_s):
            if hold_start is None:hold_start=k*dt
            longest_hold=max(longest_hold,(k+1)*dt-hold_start)
        else:hold_start=None
        s=next_s
        failure=safety(s,camera,cfg)
        if failure:reason=failure;break
        if longest_hold>=cfg["success_hold_seconds"]:
            reason="success";arrival=hold_start;break
    if max_steps is not None and reason=="timeout":reason="smoke_complete"
    arrays={k:np.asarray(v) for k,v in data.items() if len(v)}
    arrays["states"]=np.asarray(states);N=len(states)-1
    arrays["sample_id"]=np.arange(N,dtype=np.int64)
    arrays["observation_time"]=np.arange(N)*dt
    arrays["neural_input_time"]=np.arange(N)*cfg["dt_neural"]
    arrays["neural_response_time"]=arrays["neural_input_time"]+cfg["dt_neural"]
    arrays["acceleration_interval"]=np.column_stack([np.arange(N)*dt,(np.arange(N)+1)*dt])
    if baseline is not None:arrays["baseline"]=baseline
    if adapter is not None:
        adapter.assert_frozen()
        arrays["all_types"]=pooling.types
        arrays["display_indices"]=display_indices
        arrays["display_types"]=np.array(["T2","Tm3","T4a","T5d","L2"])
        arrays["display_u"]=adapter.nodes["u"].to_numpy()[display_indices]
        arrays["display_v"]=adapter.nodes["v"].to_numpy()[display_indices]
        if full:
            nodes=adapter.nodes
            arrays.update(cell_index=pooling.cell_index,cell_type=pooling.cell_type,
                u=nodes["u"].to_numpy(),v=nodes["v"].to_numpy(),
                receptor_u=np.asarray(adapter.receptor_u),receptor_v=np.asarray(adapter.receptor_v))
    for key,value in arrays.items():
        if value.dtype.kind in "fc" and not np.isfinite(value).all():raise ValueError("Nonfinite saved "+key)
    control=arrays.get("control_mask",np.zeros(0,dtype=bool))
    applied=arrays.get("u_applied",np.empty((0,2)))
    label=arrays.get("u_teacher",np.empty((0,2)))
    metrics=dict(**case,controller=mode,success=reason=="success",termination_reason=reason,
        samples=N,final_time_s=N*dt,first_hold_time_s=arrival,longest_hold_s=longest_hold,
        final_position_error_m=float(np.linalg.norm(s[:2]-teacher.goal[:2])),
        final_speed_m_s=float(np.linalg.norm(s[2:])),min_target_distance_m=float(np.linalg.norm(arrays["states"][:,:2],axis=1).min()),
        min_surface_clearance_m=float(np.linalg.norm(arrays["states"][:,:2],axis=1).min()-cfg["camera"]["target_radius_m"]),
        fov_loss=reason=="field_of_view_exit",collision=reason=="collision",
        saturation_fraction=float(np.mean(np.any(np.abs(applied[control])>=cfg["a_max"]-1e-12,axis=1))) if control.any() else 0.,
        acceleration_rmse_m_s2=float(np.sqrt(np.mean((applied[control]-label[control])**2))) if control.any() else None,
        integrated_acceleration_m_s=float(np.linalg.norm(applied,axis=1).sum()*dt),
        wall_seconds=time.perf_counter()-start,
        peak_cuda_allocated_bytes=adapter.torch.cuda.max_memory_allocated(adapter.device) if adapter is not None else None,
        parameter_sha256_before=adapter.initial_parameter_hash if adapter is not None else None,
        parameter_sha256_after=adapter.parameter_hash() if adapter is not None else None)
    return arrays,metrics

def save_trial(directory,arrays,metrics):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    path=directory/(metrics["id"]+".npz");np.savez_compressed(path,**arrays)
    metrics={**metrics,"record":path.as_posix(),"record_sha256":sha256(path)}
    write_json(directory/(metrics["id"]+".json"),metrics)
    return metrics

def checked_trial(metrics):
    if sha256(metrics["record"])!=metrics["record_sha256"]:raise ValueError("Modified episode")
    if metrics["parameter_sha256_before"]!=metrics["parameter_sha256_after"]:raise ValueError("Weights changed")
    with np.load(metrics["record"],allow_pickle=False) as z:return {k:z[k] for k in z.files}

def groups(results):
    return {category:dict(success=sum(r["success"] for r in results if r["category"]==category),
        total=sum(r["category"]==category for r in results),
        reasons={reason:sum(r["termination_reason"]==reason and r["category"]==category for r in results)
                 for reason in sorted(set(r["termination_reason"] for r in results))})
        for category in ["approach","near"]}
