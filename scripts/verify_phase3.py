"""Independent saved-record audit. No Flyvis inference or new trajectories."""
import json,inspect
from pathlib import Path
import numpy as np
from flyrendezvous.phase3_runtime import load_config,checked_trial
from flyrendezvous.geometry_phase3 import Camera,Teacher
from flyrendezvous.features import history_matrix
from flyrendezvous.readout import Readout,ImagePolicy
from flyrendezvous.activity_display import TYPES,check_timing,trial_equal_quantile
from flyrendezvous.recording import sha256,write_json
OUT=Path("outputs/phase3")
def main():
    cfg=load_config();teacher=Teacher(cfg);camera=Camera(cfg["camera"])
    contract=json.loads((OUT/"contract.json").read_text());lock=json.loads((OUT/"model_lock.json").read_text())
    assert sha256("configs/phase3.json")==contract["config_sha256"]==lock["config_sha256"]
    assert sha256(OUT/"splits.json")==contract["splits_sha256"]==lock["splits_sha256"]
    assert sha256(OUT/"readout.npz")==lock["readout_sha256"]
    assert list(inspect.signature(ImagePolicy.step).parameters)==["self","image"]
    assert not lock["selection_uses_test"]
    scales=json.loads((OUT/"display_scales.json").read_text())
    testlock=json.loads((OUT/"test_started.json").read_text())
    assert sha256(OUT/"display_scales.json")==testlock["display_scales_sha256"] and not scales["test_used"]
    reference_parameter=json.loads(Path("outputs/phase2/model_lock.json").read_text())["parameter_sha256"]
    records=[]
    for path in sorted(OUT.rglob("*.json")):
        m=json.loads(path.read_text())
        if isinstance(m,dict) and "record" in m and "controller" in m:records.append(m)
    count=0;neural=0;full=0;maximum_dynamics_error=0.
    for m in records:
        d=checked_trial(m);check_timing(d);n=m["samples"];assert n==len(d["images"])
        initial="/teacher_preflight/" in m["record"]
        t=Teacher(json.loads((OUT/"config_initial.json").read_text())) if initial else teacher
        reconstructed=d["states"][:-1]@t.Ad.T+d["u_applied"]@t.Bd.T
        maximum_dynamics_error=max(maximum_dynamics_error,float(np.max(np.abs(reconstructed-d["states"][1:]))))
        np.testing.assert_allclose(reconstructed,d["states"][1:],atol=1e-12,rtol=1e-13)
        raw=t.u_eq-(d["states"][:-1]-t.goal)@t.K.T
        np.testing.assert_allclose(raw,d["u_teacher_raw"],atol=1e-14)
        np.testing.assert_allclose(np.clip(raw,-.005,.005),d["u_teacher"],atol=1e-14)
        np.testing.assert_array_equal(d["u_applied"][:20],0)
        for k,s in enumerate(d["states"][:-1]):
            np.testing.assert_array_equal(camera.render(s),d["images"][k])
            np.testing.assert_allclose(camera.project(s)[0],d["projection"][k],atol=1e-12)
        if m["controller"]=="teacher":
            np.testing.assert_allclose(d["u_applied"][20:],d["u_teacher"][20:],atol=1e-14)
        elif m["controller"]=="zero":np.testing.assert_array_equal(d["u_applied"],0)
        else:
            parent=Path(m["record"]).parent
            if parent.name=="zero_shot":model=Readout.load("outputs/phase2/readout.npz")
            elif parent.name=="test_learner":model=Readout.load(OUT/"readout.npz")
            elif parent.name=="augmentation":model=Readout.load(OUT/"round0"/(json.loads((OUT/"round0/selected.json").read_text())["candidate"]+".npz"))
            else:model=Readout.load(parent.parent/(parent.name+".npz"))
            X=history_matrix(d["phi"],model.lag);valid=np.isfinite(X).all(1)&d["control_mask"]
            prediction=np.zeros((n,2));prediction[valid]=.005*model.predict(X[valid])
            np.testing.assert_allclose(prediction,d["u_raw"],atol=2e-14,rtol=1e-10)
            np.testing.assert_allclose(np.clip(prediction,-.005,.005),d["u_applied"],atol=2e-14)
        distance=np.linalg.norm(d["states"][:,:2],axis=1)
        np.testing.assert_allclose(distance.min(),m["min_target_distance_m"],atol=1e-12)
        np.testing.assert_allclose(distance.min()-1,m["min_surface_clearance_m"],atol=1e-12)
        np.testing.assert_allclose(np.linalg.norm(d["u_applied"],axis=1).sum()*.5,m["integrated_acceleration_m_s"],atol=1e-12)
        good=(np.linalg.norm(d["states"][:,:2]-t.goal[:2],axis=1)<.25)&(np.linalg.norm(d["states"][:,2:],axis=1)<.01)
        longest=0;run=0
        for k in range(n):
            run=run+1 if k>=20 and good[k] and good[k+1] else 0;longest=max(run,longest)
        assert longest*.5==m["longest_hold_s"]
        assert (longest>=20)==m["success"]
        if "phi" in d:
            assert m["parameter_sha256_before"]==m["parameter_sha256_after"]==reference_parameter
            assert d["phi"].shape==(n,912)
            delta=d["display_activity"].astype(float)-d["baseline"][d["display_indices"]]
            for j,name in enumerate(TYPES):
                np.testing.assert_allclose(np.sqrt((delta[:,j]**2).mean(1)),d["type_rms"][:,np.flatnonzero(d["all_types"]==name).item()],atol=1e-12)
            neural+=n
        if "activity" in d:
            with np.load(OUT/"pooling.npz") as p:
                for k in range(n):
                    dv=d["activity"][k].astype(float)-d["baseline"]
                    sums=np.bincount(p["used_cell_feature_index"],weights=dv[p["used_indices"]],minlength=912)
                    values=np.divide(sums,p["feature_counts"],out=np.zeros(912),where=p["feature_counts"]>0)
                    np.testing.assert_allclose(values,d["phi"][k],atol=1e-12)
            full+=n
        count+=n
    data=json.loads((OUT/"data.json").read_text())["episodes"]
    train=[m for m in data if m["split"]=="train"];validation=[m for m in data if m["split"]=="validation"]
    assert len(train)==24 and len(validation)==6
    augmentation=json.loads((OUT/"augmentation.json").read_text())
    assert augmentation["rounds"]<=1 and len(augmentation["episodes"])<=8
    model=Readout.load(OUT/"readout.npz")
    if augmentation["rounds"]:train+=augmentation["episodes"]
    X=[]
    for m in train:
        assert m["split"]=="train";d=checked_trial(m);x=history_matrix(d["phi"],model.lag)
        X.append(x[d["control_mask"]&np.isfinite(x).all(1)])
    X=np.concatenate(X)
    np.testing.assert_array_equal(model.mean,X.mean(0));np.testing.assert_array_equal(model.std,X.std(0))
    np.testing.assert_array_equal(model.keep,X.std(0)>1e-8)
    candidates=json.loads((OUT/("round1" if augmentation["rounds"] else "round0")/"candidates.json").read_text())
    assert len(candidates)==6
    expected=min(candidates,key=lambda r:(-r["success"],r["mean_final_position_error"],r["validation_mse"],r["lag"],r["regularization"]))
    assert expected["sha256"]==sha256(OUT/"readout.npz")
    raw=[[] for _ in TYPES];delta=[[] for _ in TYPES]
    for source in scales["sources"]:
        assert source["split"] in ("train","validation")
        m=next(m for m in data if m["id"]==source["id"]);assert m["record_sha256"]==source["record_sha256"]
        d=checked_trial(m);mask=d["control_mask"]
        for j,name in enumerate(TYPES):
            raw[j].append(d["type_rms"][mask,np.flatnonzero(d["all_types"]==name).item()])
            delta[j].append(np.abs(d["display_activity"][mask,j].astype(float)-d["baseline"][d["display_indices"][j]]))
    bounds=np.array([trial_equal_quantile(a,[.05,.95]) for a in raw])
    np.testing.assert_array_equal(bounds[:,0],scales["p05"]);np.testing.assert_array_equal(bounds[:,1],scales["p95"])
    np.testing.assert_array_equal([trial_equal_quantile(a,[.99])[0] for a in delta],scales["signed_map_limit"])
    prior=json.loads((OUT/"prior_hashes.json").read_text())
    changed=[p for p,h in prior.items() if not Path(p).exists() or sha256(p)!=h]
    assert not changed,changed
    result=dict(status="passed",episodes=len(records),samples=count,neural_samples=neural,
        full_population_pooling_samples=full,max_dynamics_error=maximum_dynamics_error,
        prior_files_unchanged=len(prior),train_only_standardization=True,non_test_display_scales=True,
        selected_by_predeclared_validation_rule=True,parameter_sha256=reference_parameter,
        readout_sha256=sha256(OUT/"readout.npz"),test_inference_repeated=False)
    write_json(OUT/"audit.json",result);print(json.dumps(result,indent=2))
if __name__=="__main__":main()
