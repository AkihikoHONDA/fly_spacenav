"""Audit every plotted value against original full neural logs, not screenshots."""
import json
from pathlib import Path
import numpy as np
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.viewer import lattice_xy,colors
from flyrendezvous.projection import rms_colors
from flyrendezvous.display_coordinates import rerun_coordinates
from flyrendezvous.morphology import read_precomputed
from flyrendezvous.activity_display import TYPES
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.viewer_phase3 import TYPE_COLORS
from flyrendezvous.representatives_phase3v import TYPES3,PALETTE,intensity_color,load_representatives

def unpack(a):
    a=np.asarray(a,dtype=np.uint32)
    return np.stack([(a>>24)&255,(a>>16)&255,(a>>8)&255],axis=-1).astype(np.uint8)
def verify(mode):
    out=Path("outputs/phase3p");source=Path("outputs/phase3");scales=json.loads((source/"display_scales.json").read_text())
    manifest=json.loads((out/("viewer_"+mode+".json")).read_text())
    assert sha256(source/"display_scales.json")==manifest["scales_sha256"]
    expected={}
    geometry={name:(xyz,xyz[edges].astype(np.float32)) for name,(xyz,edges) in load_representatives().items()}
    sources={m["id"]:m for m in json.loads((source/"evaluation.json").read_text())["learner"]}
    for m in manifest["episodes"]:
        assert m["record"]==sources[m["id"]]["record"] and m["record_sha256"]==sources[m["id"]]["record_sha256"]
        d=checked_trial(sources[m["id"]])
        indices=d["display_indices"]
        pos=[lattice_xy(d["display_u"][j],d["display_v"][j]) for j in range(5)]
        for k,t in enumerate(d["observation_time"]):
            delta=d["display_activity"][k].astype(float)-d["baseline"][indices]
            raw=np.sqrt(np.mean(delta**2,axis=1))
            q=np.clip((raw-np.array(scales["p05"]))/(np.array(scales["p95"])-scales["p05"]),0,1)
            s=d["states"][k];ns=round((m["offset"]+float(t))*1e9)
            expected[ns]=dict(id=m["id"],sample=k,physical_time=float(t),image=np.rint(d["images"][k]*255).astype(np.uint8).reshape(-1),
                delta=delta,positions=pos,raw=raw,q=q,
                trail=rerun_coordinates(d["states"][:k+1,:2]),position=rerun_coordinates(s[:2]),
                velocity=rerun_coordinates(s[2:])*20,acceleration=rerun_coordinates(d["u_applied"][k])*400,applied=d["u_applied"][k],
                error=float(np.linalg.norm(s[:2]-np.array([-5/np.sqrt(2),5/np.sqrt(2)]))),speed=float(np.linalg.norm(s[2:])))
    population=None
    if mode=="t2_population":
        from flyrendezvous.population_phase3p import load_population
        xyz_p,edges_p,provenance=load_population();population=xyz_p[edges_p].astype(np.float32)
        assert provenance==json.loads((out/"population_provenance.json").read_text())["roots"]
    counters={};static_seen=set()
    from flyrendezvous.anatomy import load_meshes
    from flyrendezvous.phase3_runtime import load_config
    meshes={name:(vertices,faces,normals) for name,vertices,faces,normals in load_meshes()}
    anatomy=json.loads(Path("configs/phase1b.json").read_text())
    goal=np.array([-5/np.sqrt(2),5/np.sqrt(2)])
    for chunk in RrdReader(out/(mode+".rrd")).stream():
        b=chunk.to_record_batch();p=chunk.entity_path;names=b.schema.names
        if chunk.is_static:
            if p in ["/orbit/target","/orbit/goal"]:
                v=[0,0] if p.endswith("target") else rerun_coordinates(goal)
                np.testing.assert_allclose(b.column("Points2D:positions")[0].as_py(),[v])
                static_seen.add(p)
            if p=="/orbit/standoff":
                values=np.array(b.column("LineStrips2D:strips")[0].as_py())[0]
                np.testing.assert_allclose(np.linalg.norm(values,axis=1),5,atol=1e-6)
                static_seen.add(p)
            if p.startswith("/brain/context/"):
                name=p.split("/")[-1];vertices,faces,normals=meshes[name]
                links=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
                np.testing.assert_array_equal(b.column("LineStrips3D:strips")[0].as_py(),vertices[links].astype(np.float32))
                np.testing.assert_array_equal(unpack(b.column("LineStrips3D:colors")[0].as_py()),[[42,49,62]])
                static_seen.add(p)
            if p=="/brain/populations/T2/arbors":
                np.testing.assert_array_equal(b.column("LineStrips3D:strips")[0].as_py(),population)
                static_seen.add(p)
            continue
        col=None
        if p=="/input/image":col="Image:buffer"
        elif p in ["/status","/timing"]:col="TextDocument:text"
        elif p=="/bars/fill":col="LineStrips2D:strips"
        elif p=="/bars/labels":col="Points2D:labels"
        elif p.startswith("/maps/"):col="Points2D:colors"
        elif p.startswith("/brain/representatives/"):col="LineStrips3D:colors" if p.endswith("/arbor") else "Points3D:labels"
        elif p.startswith("/brain/populations/"):col="LineStrips3D:colors" if p.endswith("arbors") else "Points3D:labels"
        elif p.startswith("/series/"):col="Scalars:scalars"
        elif p=="/orbit/trail":col="LineStrips2D:strips"
        elif p=="/orbit/craft":col="Points2D:positions"
        elif p in ["/orbit/velocity","/orbit/acceleration"]:col="Arrows2D:vectors"
        if not col or col not in names:continue
        seen=counters.setdefault(p,set())
        for row,ns in enumerate(b.column("physical_display_s").cast("int64").to_pylist()):
            v=b.column(col)[row].as_py()
            if ns not in expected:
                if p=="/brain/populations/T2/arbors":assert v==[0]
                else:assert p=="/status" and v[0].startswith("RESET")
                continue
            e=expected[ns];assert ns not in seen;seen.add(ns)
            if p=="/input/image":np.testing.assert_array_equal(v[0],e["image"])
            elif p=="/status":
                assert f"{e['id']} · {e['physical_time']:.1f} s" in v[0]
                assert f"Goal error {e['error']:.3f} m" in v[0]
            elif p=="/timing":
                assert f"Sample {e['sample']}; observation {e['physical_time']:.1f}" in v[0]
            elif p=="/bars/fill":
                target=np.array([[[0,j*18],[e["q"][j]*100,j*18]] for j in range(5)])
                np.testing.assert_allclose(v,target,atol=1e-5,rtol=1e-6)
                np.testing.assert_array_equal(unpack(b.column("LineStrips2D:colors")[row].as_py()),TYPE_COLORS)
            elif p=="/bars/labels":
                labels=[f"{n}  q {e['q'][j]:.2f}  RMS {e['raw'][j]:.4f}" for j,n in enumerate(TYPES)]
                assert v==labels
            elif p.startswith("/maps/"):
                j=TYPES.index(p.split("/")[2])
                np.testing.assert_array_equal(unpack(v),colors(e["delta"][j],scales["signed_map_limit"][j]))
                np.testing.assert_allclose(b.column("Points2D:positions")[row].as_py(),e["positions"][j],atol=2e-6)
            elif p.startswith("/brain/representatives/"):
                name=p.split("/")[3];j=TYPES.index(name);xyz,branches=geometry[name]
                if p.endswith("/arbor"):
                    np.testing.assert_array_equal(unpack(v),intensity_color(name,e["q"][j])[None])
                    np.testing.assert_array_equal(b.column("LineStrips3D:strips")[row].as_py(),branches)
                    rgba=np.array(b.column("LineStrips3D:colors")[row].as_py(),dtype=np.uint32)
                    assert np.all((rgba&255)==255)
                else:
                    assert v==[f"{name}  q {e['q'][j]:.2f}"]
                    np.testing.assert_array_equal(b.column("Points3D:positions")[row].as_py(),xyz[[np.argmax(xyz[:,2])]].astype(np.float32))
            elif p.startswith("/brain/populations/"):
                if p.endswith("arbors"):
                    np.testing.assert_array_equal(unpack(v),intensity_color("T2",e["q"][0])[None])
                    assert len(v)==1 and (int(v[0])&255)==160
                else:
                    assert v==[f"T2 x725  q {e['q'][0]:.2f}"]
                    np.testing.assert_array_equal(b.column("Points3D:positions")[row].as_py(),xyz_p[[np.argmax(xyz_p[:,2])]].astype(np.float32))
            elif p.startswith("/series/"):
                parts=p.split("/");kind=parts[2];ident=parts[3];assert ident==e["id"]
                if kind in ["raw","q"]:target=e[kind][TYPES.index(parts[4])]
                elif kind=="acceleration":target=e["applied"][["ax","ay"].index(parts[4])]
                else:target=e[kind]
                np.testing.assert_allclose(v,[target],atol=1e-12)
            else:
                key=p.split("/")[-1];key="position" if key=="craft" else key
                np.testing.assert_allclose(v,[e[key]],atol=2e-6,rtol=1e-6)
                if key in ["velocity","acceleration"]:
                    np.testing.assert_allclose(b.column("Arrows2D:origins")[row].as_py(),[e["position"]],atol=2e-6,rtol=1e-6)
    for path,ns in counters.items():
        target={t for t,e in expected.items() if e["id"] in path} if path.startswith("/series/") else set(expected)
        assert ns==target,(path,len(ns),len(target))
    assert len(counters)==20+14*len(manifest["episodes"]),len(counters)
    assert {"/orbit/target","/orbit/goal","/orbit/standoff"}<=static_seen
    assert all("/brain/context/"+name in static_seen for name in anatomy["background_regions"]+anatomy["outline_regions"])
    if population is not None:assert "/brain/populations/T2/arbors" in static_seen
    result=dict(status="passed",total_frames=len(expected),entity_frames={p:len(v) for p,v in counters.items()},
        scales_sha256=sha256(source/"display_scales.json"),rrd_sha256=sha256(out/(mode+".rrd")),
        unique_morphology_count=727 if population is not None else 3,population_edges=len(population) if population is not None else 0,geometry_edges={name:len(branches) for name,(xyz,branches) in geometry.items() if population is None or name!="T2"},source="unchanged original Phase 3 held-out records; three representatives or 725 measured T2 plus T4a/T5d representatives")
    write_json(out/("rrd_audit_"+mode+".json"),result);print(json.dumps(result,indent=2))
if __name__=="__main__":
    for mode in ["representative","t2_population"]:verify(mode)
