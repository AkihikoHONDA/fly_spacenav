"""Read the actual RRD and compare every displayed sample with source NPZ."""
import json
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.projection import checked_episode
from flyrendezvous.morphology import read_precomputed
from flyrendezvous.viewer import colors,lattice_xy

def unpack(packed):
    a=np.asarray(packed,dtype=np.uint32)
    return np.stack([(a>>24)&255,(a>>16)&255,(a>>8)&255],axis=-1).astype(np.uint8)

def main():
    out=Path("outputs/phase1b");validation=json.loads((out/"display_validation.json").read_text())
    cfg=json.loads((out/"config.json").read_text())
    expected={}
    for trial in validation["trials"]:
        d=checked_episode(trial["source"],trial["source_validation"])
        selected=np.flatnonzero(d["cell_type"]==cfg["cell_type"])
        delta=d["activity"][:,selected].astype(float)-d["baseline"][selected].astype(float)
        rms=np.sqrt(np.mean(delta**2,axis=1))
        rgb=np.rint(np.array([70,110,160])+np.clip(rms/cfg["rms_upper"],0,1)[:,None]*np.array([185,95,-95])).astype(np.uint8)
        for k in range(len(rms)):
            ns=round((trial["offset"]+d["input_time"][k])*1e9)
            gray=np.rint(d["receptor_input"][k]*255).clip(0,255).astype(np.uint8)
            expected[ns]=dict(name=trial["name"],rms=rms[k],rgb=rgb[k],
                image=np.rint(d["images"][k]*255).astype(np.uint8).reshape(-1),
                grid=colors(delta[k],cfg["signed_limit"]),receptors=np.repeat(gray[:,None],3,axis=1),
                positions=lattice_xy(d["u"][selected],d["v"][selected]))
    xyz,edges,_=read_precomputed("assets/phase1b/"+cfg["morphology_id"]+".precomputed")
    branches=(xyz.astype(float)*.001)[edges].astype(np.float32)
    counts={key:0 for key in ["morphology","grid","receptors","input","rms"]}
    seen={key:set() for key in counts}
    for c in RrdReader(out/"phase1b.rrd").stream():
        if c.is_static:continue
        b=c.to_record_batch();names=b.schema.names;entity=c.entity_path
        if entity=="/brain/representative" and "LineStrips3D:colors" in names:key="morphology"
        elif entity=="/grid/hex" and "Points2D:colors" in names:key="grid"
        elif entity=="/receptors/hex" and "Points2D:colors" in names:key="receptors"
        elif entity=="/input/image" and "Image:buffer" in names:key="input"
        elif entity.startswith("/rms/") and "Scalars:scalars" in names:key="rms"
        else:continue
        for row,ns in enumerate(b.column("input_sample_s").cast("int64").to_pylist()):
            e=expected[ns]
            def value(name):return b.column(name)[row].as_py()
            assert ns not in seen[key],"Duplicate sample"
            seen[key].add(ns);counts[key]+=1
            if key=="morphology":
                # One broadcast color for all 828 branches, no branch-specific values.
                np.testing.assert_array_equal(unpack(value("LineStrips3D:colors")),e["rgb"][None])
                np.testing.assert_array_equal(value("LineStrips3D:strips"),branches)
            elif key in ["grid","receptors"]:
                np.testing.assert_array_equal(unpack(value("Points2D:colors")),e[key])
                if key=="grid":np.testing.assert_allclose(value("Points2D:positions"),e["positions"],atol=1e-6)
            elif key=="input":np.testing.assert_array_equal(value("Image:buffer")[0],e["image"])
            else:
                assert entity=="/rms/"+e["name"],"Cross-trial interpolation"
                np.testing.assert_allclose(value("Scalars:scalars"),[e["rms"]],atol=1e-14,rtol=1e-13)
    assert all(v==len(expected) for v in counts.values())
    baseline=json.loads((out/"phase1_before.json").read_text())
    mismatches=[name for name,digest in baseline.items() if sha256(name)!=digest]
    assert not mismatches,mismatches
    write_json(out/"rrd_data_validation.json",dict(status="passed",rrd_sha256=sha256(out/"phase1b.rrd"),
        samples_per_panel=counts,source="original NPZ, independent literal RMS and palette formula",
        branches_per_sample=len(edges),coordinates="exact float32 nm-to-um; no geometry relocation",
        all_display_times_match=True,phase1_files_unchanged=len(baseline),phase1_mismatches=mismatches))
    print("RRD verified:",counts,"; original Phase 1 files unchanged:",len(baseline))
if __name__=="__main__":main()
