"""No inference: calibrate type bars on 12 original tests, maps on 2 full replays."""
import csv,json
from pathlib import Path
import numpy as np
from flyrendezvous.activity_display import TYPES,MIN_RANGE,select_types,trial_equal_quantile,relative_activity,check_timing,map_metrics
from flyrendezvous.phase2_runtime import checked_trial
from flyrendezvous.screening import classify_stages
from flyrendezvous.recording import sha256,write_json
OUT=Path("outputs/phase2f")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    ev=json.loads(Path("outputs/phase2/evaluation.json").read_text())
    records=ev["learner"];data=[checked_trial(m) for m in records]
    for d in data:check_timing(d)
    columns=[int(x[0]) for x in select_types(data[0]["all_types"])]
    for d in data:np.testing.assert_array_equal(d["all_types"],data[0]["all_types"])
    bounds=np.array([trial_equal_quantile([d["type_rms"][d["control_mask"],j] for d in data],[.05,.95]) for j in columns])
    replays=json.loads(Path("outputs/phase2/replays.json").read_text())
    full=[checked_trial(m) for m in replays]
    deltas=[]
    for d in full:
        check_timing(d)
        groups=select_types(d["cell_type"])
        delta=np.stack([d["activity"][:,idx].astype(float)-d["baseline"][idx] for idx in groups],axis=1)
        np.testing.assert_allclose(np.sqrt(np.mean(delta**2,axis=2)),d["type_rms"][:,columns],atol=1e-12,rtol=0)
        deltas.append(delta)
    limits=np.array([trial_equal_quantile([np.abs(a[d["control_mask"],j]) for a,d in zip(deltas,full)],[.99])[0] for j in range(len(TYPES))])
    assert np.all(limits>MIN_RANGE)
    scales=dict(types=list(TYPES),p05=bounds[:,0].tolist(),p95=bounds[:,1].tolist(),
        dynamic_range=np.diff(bounds,axis=1)[:,0].tolist(),relative_valid=(np.diff(bounds,axis=1)[:,0]>MIN_RANGE).tolist(),
        min_range=MIN_RANGE,signed_map_limit=limits.tolist(),absolute_rms_upper=.22,
        rms_calibration="inverse empirical mixture CDF, each original held-out test trial equal mass, control periods only",
        map_calibration="p99(abs(cell delta)), each of 2 full-response replay trials equal mass, control periods only; full activity absent from original 12 test logs",
        quantile_rule="sort values; inverse CDF at requested cumulative probability, no per-frame normalization",
        records=[dict(record=m["record"],sha256=m["record_sha256"],control_samples=int(d["control_mask"].sum())) for m,d in zip(records,data)],
        map_records=[dict(record=m["record"],sha256=m["record_sha256"],control_samples=int(d["control_mask"].sum())) for m,d in zip(replays,full)],
        readout_sha256=sha256("outputs/phase2/readout.npz"))
    write_json(OUT/"display_scales.json",scales)
    series={k:[] for k in ["episode","physical_time","neural_input_time","neural_response_time","sample_id","control_mask","stage","raw_rms","q"]}
    trial_rows=[]
    for m,d in zip(records,data):
        raw=d["type_rms"][:,columns];q=relative_activity(raw,bounds[:,0],bounds[:,1])
        stage=classify_stages(d["states"][:-1],d["u_applied"],d["control_mask"])
        active=d["control_mask"];pairs=active[:-1]&active[1:];rates=np.abs(np.diff(q,axis=0))/.5
        for j,name in enumerate(TYPES):
            row=dict(id=m["id"],cell_type=name,q_std=float(q[active,j].std()),
                q_rate_median=float(np.median(rates[pairs,j])),q_rate_p95=float(np.quantile(rates[pairs,j],.95)),
                clipped_low=float(np.mean(raw[active,j]<bounds[j,0])),clipped_high=float(np.mean(raw[active,j]>bounds[j,1])))
            for phase in ["approach","braking","near_hold"]:
                values=q[stage==phase,j];row[phase+"_count"]=len(values)
                row[phase+"_median_q"]=float(np.median(values)) if len(values) else None
            trial_rows.append(row)
        values=dict(episode=np.repeat(m["id"],len(raw)),raw_rms=raw,q=q,stage=stage,
            **{key:d[key] for key in ["neural_input_time","neural_response_time","sample_id","control_mask"]},physical_time=d["observation_time"])
        for k,v in values.items():series[k].append(v)
    np.savez_compressed(OUT/"type_activity.npz",**{k:np.concatenate(v) for k,v in series.items()},types=np.array(TYPES),p05=bounds[:,0],p95=bounds[:,1],signed_map_limit=limits)
    map_rows=[];replay_checks=[]
    for m,d,delta in zip(replays,full,deltas):
        stage=classify_stages(d["states"][:-1],d["u_applied"],d["control_mask"])
        raw=np.sqrt(np.mean(delta**2,axis=2));q=relative_activity(raw,bounds[:,0],bounds[:,1])
        groups=select_types(d["cell_type"])
        np.savez_compressed(OUT/(m["id"]+"_display.npz"),types=np.array(TYPES),delta=delta,raw_rms=raw,q=q,
            stage=stage,control_mask=d["control_mask"],sample_id=d["sample_id"],physical_time=d["observation_time"],
            neural_input_time=d["neural_input_time"],neural_response_time=d["neural_response_time"],
            cell_index=np.array([d["cell_index"][g] for g in groups]),u=np.array([d["u"][g] for g in groups]),v=np.array([d["v"][g] for g in groups]))
        for j,name in enumerate(TYPES):
            row=dict(id=m["id"],cell_type=name,**map_metrics(delta[:,j],limits[j],d["control_mask"]))
            map_rows.append(row)
        replay_checks.append(dict(id=m["id"],frames=len(raw),raw_rms_max_error=float(np.max(np.abs(raw-d["type_rms"][:,columns]))),
            record=m["record"],sha256=m["record_sha256"]))
    rows=[]
    comparable=[m["id"] for m in records if all(next(r for r in trial_rows if r["id"]==m["id"] and r["cell_type"]==TYPES[0])[p+"_count"]>=5 for p in ["approach","braking","near_hold"])]
    for j,name in enumerate(TYPES):
        trials=[r for r in trial_rows if r["cell_type"]==name];maps=[r for r in map_rows if r["cell_type"]==name]
        row=dict(cell_type=name,p05=float(bounds[j,0]),p95=float(bounds[j,1]),dynamic_range=float(bounds[j,1]-bounds[j,0]),map_limit=float(limits[j]))
        for k in ["q_std","q_rate_median","q_rate_p95","clipped_low","clipped_high"]:row[k]=float(np.median([r[k] for r in trials]))
        for phase in ["approach","braking","near_hold"]:
            row[phase+"_median_q"]=float(np.median([r[phase+"_median_q"] for r in trials if r["id"] in comparable]))
        for k in maps[0]:
            if k not in ["id","cell_type"]:row[k]=float(np.median([r[k] for r in maps]))
        rows.append(row)
    with (OUT/"motion_metrics.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    write_json(OUT/"motion_metrics.json",dict(status="passed",metrics=rows,trial_metrics=trial_rows,map_metrics=map_rows,
        replay_checks=replay_checks,phase_comparable_episodes=comparable,
        aggregation="median of per-trial control-period metrics; phase medians use the same >=5-sample three-phase trials",
        map_motion_definition="per-frame spatial std; RMS across cells of successive differences / .5 physical seconds, also spatial-mean-subtracted and clipped display-normalized versions",
        new_inference=False,original_test_results=ev["learner_groups"],scales_sha256=sha256(OUT/"display_scales.json")))
    print(json.dumps(rows,indent=2))
if __name__=="__main__":main()
