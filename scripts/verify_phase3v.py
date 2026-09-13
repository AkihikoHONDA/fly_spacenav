"""Audit fixed control assets, non-test calibration, morphology and visibility metrics."""
import json,csv
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.activity_display import TYPES,trial_equal_quantile
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.viewer_phase3 import display_data
from flyrendezvous.representatives_phase3v import TYPES3,PALETTE,intensity_color,load_representatives
OUT=Path("outputs/phase3v");SOURCE=Path("outputs/phase3")
def main():
    prior=json.loads((OUT/"prior_hashes.json").read_text())
    changed=[p for p,h in prior.items() if not Path(p).is_file() or sha256(p)!=h]
    assert not changed,changed
    m=json.loads(Path("docs/anatomy_mapping_phase3v.json").read_text())
    for p,meta in m["files"].items():assert sha256(p)==meta["sha256"]
    with Path(m["annotation"]["cache"]).open() as f:rows={r["root_id"]:r for r in csv.DictReader(f,delimiter="\t")}
    for name in TYPES3:
        a=m["morphologies"][name]
        assert rows[a["root_id"]]==a["annotation_row"] and rows[a["root_id"]]["cell_type"]==name
    geometry=load_representatives()
    scales=json.loads((SOURCE/"display_scales.json").read_text())
    testlock=json.loads((SOURCE/"test_started.json").read_text())
    assert sha256(SOURCE/"display_scales.json")==testlock["display_scales_sha256"]
    assert sha256(SOURCE/"readout.npz")==testlock["readout_sha256"]
    trials=json.loads((SOURCE/"data.json").read_text())["episodes"];calibration=[[] for _ in TYPES]
    for item in trials:
        assert item["split"] in ["train","validation"]
        d=checked_trial(item)
        for j,name in enumerate(TYPES):
            calibration[j].append(d["type_rms"][d["control_mask"],np.flatnonzero(d["all_types"]==name).item()])
    bounds=np.array([trial_equal_quantile(x,[.05,.95]) for x in calibration])
    np.testing.assert_array_equal(bounds[:,0],scales["p05"]);np.testing.assert_array_equal(bounds[:,1],scales["p95"])
    evaluation=json.loads((SOURCE/"evaluation.json").read_text())
    assert evaluation["learner_groups"]["approach"]["success"]==8 and evaluation["learner_groups"]["near"]["success"]==2
    chosen=next(m for m in evaluation["learner"] if m["id"]=="test_00")
    d=checked_trial(chosen);delta,raw,q=display_data(d,scales);mask=d["control_mask"];pairs=mask[1:]&mask[:-1]
    metrics={}
    for name in TYPES3:
        j=TYPES.index(name);rgb=intensity_color(name,q[:,j])
        metrics[name]=dict(vertices=len(geometry[name][0]),edges=len(geometry[name][1]),palette=PALETTE[name],
            q_min=float(q[mask,j].min()),q_max=float(q[mask,j].max()),
            rgb_min=rgb[mask].min(0).tolist(),rgb_max=rgb[mask].max(0).tolist(),
            changed_frame_fraction=float(np.any(np.diff(rgb.astype(float),axis=0)[pairs]!=0,axis=1).mean()),
            samples=[dict(sample=k,time=float(d["observation_time"][k]),rms=float(raw[k,j]),q=float(q[k,j]),rgb=rgb[k].tolist())
                for k in [40,int(np.argmin((d["states"][:-1,2:]*d["u_applied"]).sum(1))),len(q)-1]])
    old_colors=[];old_radius=[];contexts=set()
    for chunk in RrdReader(SOURCE/"phase3_demo.rrd").stream():
        b=chunk.to_record_batch();p=chunk.entity_path
        if p.startswith("/brain/context/"):contexts.add(p)
        if p=="/brain/representative" and "LineStrips3D:colors" in b.schema.names:
            old_colors.extend([int(v[0]) for v in b.column("LineStrips3D:colors").to_pylist()])
            old_radius.extend([v[0] for v in b.column("LineStrips3D:radii").to_pylist()])
    assert len(old_colors)==777 and all(v&255==255 for v in old_colors)
    for mode in ["demo","analysis"]:
        audit=json.loads((OUT/("rrd_audit_"+mode+".json")).read_text())
        shots=json.loads(Path("docs/evidence_phase3v/screenshots_"+mode+".json").read_text())
        assert sha256(OUT/("phase3v_"+mode+".rrd"))==audit["rrd_sha256"]==shots["rrd_sha256"]
        for shot in shots["screenshots"]:assert sha256(shot["file"])==shot["sha256"]
    result=dict(status="passed",prior_unchanged=len(prior),new_inference=0,new_control_experiments=0,
        calibration_trials=len(trials),scales_sha256=sha256(SOURCE/"display_scales.json"),
        control_readout_sha256=sha256(SOURCE/"readout.npz"),test_result_unchanged={"approach":[8,8],"near":[2,4]},
        original_phase3=dict(morphology_frames=len(old_colors),context_entities=sorted(contexts),
            all_morphology_alpha_255=True,radii_encoded=sorted(set(old_radius)),unit="um",
            diagnosis="Geometry exists and default blueprint has two 3D views. Terminal RESET clears morphology; also small context projection / split panels / low contrast. User's persisted GUI state unavailable."),
        visibility_metrics=metrics)
    write_json(OUT/"verification.json",result);print(json.dumps(result,indent=2))
if __name__=="__main__":main()
