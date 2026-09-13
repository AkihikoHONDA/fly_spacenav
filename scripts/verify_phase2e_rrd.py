"""Compare actual RRD panel contents with each replay's own neural/HCW record."""
import json
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.viewer import colors
from flyrendezvous.projection import rms_colors
from flyrendezvous.display_coordinates import rerun_coordinates
from flyrendezvous.phase2_runtime import load_config
from flyrendezvous.morphology import read_precomputed

def unpack(a):
    a=np.asarray(a,dtype=np.uint32)
    return np.stack([(a>>24)&255,(a>>16)&255,(a>>8)&255],axis=-1).astype(np.uint8)
def main():
    out=Path("outputs/phase2e");cfg=load_config();disp=cfg["display"]
    manifest=json.loads((out/"viewer_manifest.json").read_text());expected={}
    xyz,edges,_=read_precomputed("assets/phase1b/720575940605852192.precomputed")
    branches=(xyz.astype(float)*.001)[edges].astype(np.float32)
    for m in manifest["episodes"]:
        assert sha256(m["record"])==m["record_sha256"]
        with np.load(m["record"],allow_pickle=False) as z:d={k:z[k] for k in z.files}
        selected=np.flatnonzero(d["cell_type"]=="T4a")
        delta=d["activity"][:,selected].astype(float)-d["baseline"][selected]
        rms=np.sqrt(np.mean(delta**2,axis=1))
        for k,t in enumerate(d["observation_time"]):
            ns=round((m["offset"]+float(t))*1e9);s=d["states"][k];gray=np.rint(d["receptor_input"][k]*255).clip(0,255).astype(np.uint8)
            expected[ns]=dict(id=m["id"],image=np.rint(d["images"][k]*255).astype(np.uint8).reshape(-1),
                grid=colors(delta[k],disp["signed_limit"]),receptors=np.repeat(gray[:,None],3,axis=1),
                shape=rms_colors(rms[k],disp["rms_upper"]),position=rerun_coordinates(s[:2]),
                velocity=rerun_coordinates(s[2:])*disp["velocity_arrow_seconds"],
                acceleration=rerun_coordinates(d["u_applied"][k])*disp["acceleration_arrow_seconds_squared"],
                trail=rerun_coordinates(d["states"][:k+1,:2]),applied=d["u_applied"][k],error=np.linalg.norm(s[:2]-[10,0]),speed=np.linalg.norm(s[2:]))
    counters={key:set() for key in ["image","grid","receptors","shape","position","trail","velocity","acceleration","ax","ay","error","speed"]}
    for c in RrdReader(out/"phase2e.rrd").stream():
        if c.is_static:
            b=c.to_record_batch()
            if c.entity_path in ["/orbit/goal","/orbit/target"]:
                xy=[10.,0.] if c.entity_path.endswith("goal") else [0.,0.]
                np.testing.assert_allclose(b.column("Points2D:positions")[0].as_py(),[rerun_coordinates(xy)])
            continue
        b=c.to_record_batch();names=b.schema.names;p=c.entity_path
        mapping={"/input/image":("image","Image:buffer"),"/grid/hex":("grid","Points2D:colors"),
          "/receptors/hex":("receptors","Points2D:colors"),"/brain/representative":("shape","LineStrips3D:colors"),
          "/orbit/trail":("trail","LineStrips2D:strips"),"/orbit/craft":("position","Points2D:positions"),"/orbit/velocity":("velocity","Arrows2D:vectors"),
          "/orbit/acceleration":("acceleration","Arrows2D:vectors")}
        if p in mapping:key,col=mapping[p]
        elif p.startswith("/acceleration/"):key=p.split("/")[-1];col="Scalars:scalars"
        elif p.startswith("/position_error/"):key="error";col="Scalars:scalars"
        elif p.startswith("/speed/"):key="speed";col="Scalars:scalars"
        else:continue
        if col not in names:continue
        for row,ns in enumerate(b.column("physical_display_s").cast("int64").to_pylist()):
            e=expected[ns];value=b.column(col)[row].as_py()
            assert ns not in counters[key];counters[key].add(ns)
            if key=="image":np.testing.assert_array_equal(value[0],e[key])
            elif key in ["grid","receptors"]:np.testing.assert_array_equal(unpack(value),e[key])
            elif key=="shape":
                np.testing.assert_array_equal(unpack(value),e[key][None])
                np.testing.assert_array_equal(b.column("LineStrips3D:strips")[row].as_py(),branches)
            elif key in ["position","trail","velocity","acceleration"]:
                np.testing.assert_allclose(value,[e[key]],atol=2e-6,rtol=1e-6)
                if key in ["velocity","acceleration"]:
                    np.testing.assert_allclose(b.column("Arrows2D:origins")[row].as_py(),[e["position"]],atol=2e-6,rtol=1e-6)
            else:
                assert e["id"] in p
                reference=e["applied"][0 if key=="ax" else 1] if key in ["ax","ay"] else e[key]
                np.testing.assert_allclose(value,[reference],atol=1e-12)
    assert all(len(v)==len(expected) for v in counters.values())
    result=dict(status="passed",samples_per_panel={k:len(v) for k,v in counters.items()},
        geometry_edges=len(edges),rrd_sha256=sha256(out/"phase2e.rrd"),source="each replay's own images, full neural responses and applied control")
    write_json(out/"rrd_audit.json",result);print(json.dumps(result,indent=2))
if __name__=="__main__":main()
