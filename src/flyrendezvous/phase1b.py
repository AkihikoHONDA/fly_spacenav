"""Prepare and verify representative-morphology display from real recordings."""
import argparse
import json
from pathlib import Path
import numpy as np
from .projection import checked_episode,response_rms,rms_colors
from .recording import sha256,write_json
from .viewer import colors

def prepare(config_path="configs/phase1b.json",include_extended=False):
    cfg=json.loads(Path(config_path).read_text())
    out=Path(cfg["output_directory"]); out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(Path("docs/anatomy_mapping_phase1b.json").read_text())
    if cfg["cell_type"]!=manifest["model_cell_type"] or cfg["morphology_id"]!=manifest["morphology_id"]:
        raise ValueError("Configuration does not match typed morphology")
    for name,meta in manifest["files"].items():
        if sha256(name)!=meta["sha256"]:raise ValueError("Morphology asset changed")
    source=Path(cfg["source_directory"])
    sources=[(name,source/(name+".npz"),source/"validation.json") for name in cfg["existing_trials"]]
    if include_extended:
        sources.append(("sequence",out/"sequence.npz",out/"sequence_validation.json"))
    plan=[];offset=0.;calibration=[]
    write_json(out/"display_validation.json",{"status":"running"})
    write_json(out/"config.json",cfg)
    for name,path,validation_path in sources:
        data=checked_episode(path,validation_path)
        selected,delta,rms=response_rms(data,cfg["cell_type"],cfg["dt"])
        # independent direct formula, not the production norm implementation
        reference=np.sqrt(np.mean((data["activity"][:,selected].astype(float)-data["baseline"][selected].astype(float))**2,axis=1))
        np.testing.assert_allclose(rms,reference,atol=1e-14,rtol=1e-13)
        rgb=rms_colors(rms,cfg["rms_upper"])
        grid_rgb=colors(delta,cfg["signed_limit"])
        projection_path=out/(name+"_projection.npz")
        np.savez_compressed(projection_path,selected_model_indices=data["cell_index"][selected],
             delta_voltage=delta,rms=rms,rgb=rgb,grid_rgb=grid_rgb,
             input_time=data["input_time"],response_time=data["response_time"],
             display_time=data["input_time"]+offset)
        with np.load(projection_path,allow_pickle=False) as saved:
            np.testing.assert_array_equal(saved["rgb"],rms_colors(reference,cfg["rms_upper"]))
            np.testing.assert_allclose(saved["rms"],reference,atol=1e-14,rtol=1e-13)
        trial={"name":name,"source":path.as_posix(),"source_sha256":sha256(path),
               "source_validation":validation_path.as_posix(),"validation_sha256":sha256(validation_path),
               "projection":projection_path.as_posix(),"projection_sha256":sha256(projection_path),
               "offset":offset,"frames":len(rms),"selected_cells":len(selected),
               "rms_min":float(rms.min()),"rms_max":float(rms.max()),
               "rms_clipped_samples":int((rms>cfg["rms_upper"]).sum()),
               "grid_clipped_fraction":float(np.mean(np.abs(delta)>cfg["signed_limit"])),
               "max_rms_recalculation_error":float(np.max(np.abs(rms-reference)))}
        plan.append(trial)
        if name!="sequence":calibration.append(float(rms.max()))
        offset+=len(rms)*cfg["dt"]+cfg["reset_gap_seconds"]
    expected_upper=np.ceil(max(calibration)*100)/100
    if not np.isclose(expected_upper,cfg["rms_upper"],rtol=0,atol=1e-12):
        raise ValueError("Fixed RMS scale no longer matches the recorded calibration")
    validation={"status":"passed","config_sha256":sha256(out/"config.json"),
                "mapping_sha256":sha256("docs/anatomy_mapping_phase1b.json"),
                "trials":plan,"rms_upper":cfg["rms_upper"],"calibration_max":max(calibration),
                "aggregation":"RMS of per-cell voltage changes; display only",
                "timeline":"display_time = episode offset + input_time; paired response at input_time + dt; reset gaps explicit",
                "one_to_one_model_cell_mapping":False}
    write_json(out/"display_validation.json",validation)
    print(json.dumps(validation,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="configs/phase1b.json")
    p.add_argument("--include-extended",action="store_true")
    a=p.parse_args();prepare(a.config,a.include_extended)

if __name__=="__main__":main()
