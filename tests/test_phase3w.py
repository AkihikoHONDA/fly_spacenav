import csv,json,io,zipfile
from pathlib import Path
import numpy as np
import pytest,trimesh
from flyrendezvous.multi_phase3w import TYPES3,select_rows,load_groups,load_context
from flyrendezvous.morphology import read_precomputed
from flyrendezvous.recording import sha256
@pytest.fixture(scope="module")
def assets():
    m=json.loads(Path("docs/anatomy_mapping_phase3w.json").read_text())
    with open(m["annotation"]["cache"]) as f:rows=list(csv.DictReader(f,delimiter="\t"))
    return m,rows,load_groups()
@pytest.mark.parametrize("name",TYPES3)
def test_sampling_reproducible_exact_unique_includes_existing(assets,name):
    m,rows,groups=assets;s=m["selection"]
    chosen=select_rows(rows,name,s["existing_ids"][name],s["seeds"][name])
    assert chosen==select_rows(list(reversed(rows)),name,s["existing_ids"][name],s["seeds"][name])
    assert chosen==s["selected_rows"][name]
    ids=[r["root_id"] for r in chosen]
    assert len(ids)==len(set(ids))==12 and s["existing_ids"][name] in ids
    assert all(r["cell_type"]==name and r["side"]=="right" for r in chosen)
@pytest.mark.parametrize("name",TYPES3)
def test_all_geometry_and_root_provenance_preserved(assets,name):
    m,rows,groups=assets;x,e,roots=groups[name];assert len(roots)==12
    assert len(e)==len(x)-12
    for p in roots:
        xyz,edge,_=read_precomputed(p["source"]);assert sha256(p["source"])==p["sha256"]
        np.testing.assert_array_equal(x[p["vertex_start"]:p["vertex_stop"]],xyz.astype(float)*.001)
        np.testing.assert_array_equal(e[p["edge_start"]:p["edge_stop"]]-p["vertex_start"],edge)
def test_exact_sampling_rejects_alias_side_and_duplicate():
    rows=[dict(root_id="1",cell_type="T2",side="right"),dict(root_id="2",cell_type="T2a",side="right"),dict(root_id="3",cell_type="T2",side="left"),dict(root_id="4",cell_type="T2",side="right ")]
    assert select_rows(rows,"T2","1",1)==rows[:1]
    with pytest.raises(ValueError):select_rows(rows+rows[:1],"T2","1",1)
def test_all_local_context_meshes_share_source_coordinates(assets):
    m,_,_=assets;c=m["context"]
    assert sha256(c["archive"])==c["archive_sha256"]
    assert len(c["meshes"])==78
    with zipfile.ZipFile(c["archive"]) as z:
        assert {p["archive_entry"] for p in c["meshes"]}=={n for n in z.namelist() if "/" not in n and n.endswith(".ply")}
        for name,x,e,norm in load_context():
            original=trimesh.load(io.BytesIO(z.read(name+".ply")),file_type="ply",process=False)
            assert np.isfinite(x).all()
            np.testing.assert_array_equal(x,original.vertices*.001)
            np.testing.assert_array_equal(e,original.faces)
def test_same_logs_and_no_extra_morphology_acquisition(assets):
    m,_,_=assets
    assert m["new_morphologies"]==22
    assert len(list(Path("assets/phase3w").glob("*.precomputed")))==22
    assert set(m["morphologies"])==set(TYPES3)
    a=json.loads(Path("outputs/phase3w/viewer_representative.json").read_text())
    b=json.loads(Path("outputs/phase3w/viewer_multi.json").read_text())
    old=json.loads(Path("outputs/phase3v/viewer_demo.json").read_text())
    for k in ["episodes","scales_sha256","timeline","playback_speed","new_inference"]:assert a[k]==b[k]==old[k]
def test_each_type_uses_its_own_rms_and_one_shared_color():
    from rerun.experimental import RrdReader
    manifest=json.loads(Path("outputs/phase3w/viewer_multi.json").read_text())
    scales=json.loads(Path("outputs/phase3/display_scales.json").read_text())
    expected={};base={"T2":[255,166,65],"T4a":[80,175,255],"T5d":[245,100,225]};jmap={"T2":0,"T4a":2,"T5d":3}
    for trial in manifest["episodes"]:
        with np.load(trial["record"]) as d:
            delta=d["display_activity"].astype(float)-d["baseline"][d["display_indices"]]
            rms=np.sqrt((delta*delta).mean(2));q=np.clip((rms-scales["p05"])/(np.array(scales["p95"])-scales["p05"]),0,1)
            for k,t in enumerate(d["observation_time"]):
                expected[round((trial["offset"]+t)*1e9)]={name:np.rint(np.array(base[name])*(.35+.65*q[k,j])).astype(int) for name,j in jmap.items()}
    seen={n:set() for n in TYPES3};static={n:0 for n in TYPES3}
    for chunk in RrdReader("outputs/phase3w/multi.rrd").stream():
        p=chunk.entity_path
        if not p.startswith("/brain/multi/") or not p.endswith("/arbors"):continue
        name=p.split("/")[3];b=chunk.to_record_batch()
        if chunk.is_static:static[name]+=b.num_rows;continue
        for ns,colors in zip(b.column("physical_display_s").cast("int64").to_pylist(),b.column("LineStrips3D:colors").to_pylist()):
            if ns not in expected:assert colors==[0];continue
            rgb=expected[ns][name]
            packed=(int(rgb[0])<<24)|(int(rgb[1])<<16)|(int(rgb[2])<<8)|255
            assert colors==[packed];seen[name].add(ns)
    assert all(len(v)==777 for v in seen.values()) and all(v==1 for v in static.values())
