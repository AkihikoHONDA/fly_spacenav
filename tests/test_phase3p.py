"""Regression checks for exact population selection and unmodified source geometry."""
import csv,json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.population_phase3p import exact_right_t2,load_population
from flyrendezvous.morphology import read_precomputed
from flyrendezvous.recording import sha256
def test_exact_filter_rejects_aliases_wrong_side_and_whitespace():
    rows=[dict(cell_type=t,side=s,root_id=str(i)) for i,(t,s) in enumerate([
        ("T2","right"),("T2a","right"),("T2","left"),("T2 ","right"),("T2","Right"),("T2","right ")])]
    assert exact_right_t2(rows)==rows[:1]
@pytest.fixture(scope="module")
def population():
    return load_population()
def test_all_pinned_annotation_rows_and_unique_ids(population):
    m=json.loads(Path("docs/anatomy_mapping_phase3p.json").read_text())
    before=json.loads(Path("outputs/phase3p/enumeration_before_download.json").read_text())
    assert before["download_started"] is False
    assert m["enumeration_sha256"]==sha256("outputs/phase3p/enumeration_before_download.json")
    ids=[a["root_id"] for a in m["morphologies"]]
    assert len(ids)==len(set(ids))==before["count"]==725
    assert set(ids)=={r["root_id"] for r in before["rows"]}
    assert m["cell_class_distribution"]=={"ME>LO":724,"ME.LO":1}
    assert not m["one_to_one_model_cell_mapping"] and not m["model_hemisphere_assigned"]
def test_every_vertex_edge_and_provenance_preserves_original(population):
    xyz,edges,provenance=population
    assert len(provenance)==725 and np.isfinite(xyz).all()
    previous_v=previous_e=0
    for p in provenance:
        assert p["vertex_start"]==previous_v and p["edge_start"]==previous_e
        v,e,_=read_precomputed(p["source"])
        np.testing.assert_array_equal(xyz[p["vertex_start"]:p["vertex_stop"]],v.astype(float)*.001)
        np.testing.assert_array_equal(edges[p["edge_start"]:p["edge_stop"]]-p["vertex_start"],e)
        assert len(e)==len(v)-1 and sha256(p["source"])==p["sha256"]
        previous_v=p["vertex_stop"];previous_e=p["edge_stop"]
    assert previous_v==len(xyz) and previous_e==len(edges)
def test_both_modes_use_same_original_records_and_scales():
    a=json.loads(Path("outputs/phase3p/viewer_representative.json").read_text())
    b=json.loads(Path("outputs/phase3p/viewer_t2_population.json").read_text())
    old=json.loads(Path("outputs/phase3v/viewer_demo.json").read_text())
    for key in ["episodes","scales_sha256","timeline","playback_speed","new_inference"]:
        assert a[key]==b[key]==old[key]
    assert a["morphology_count"]==3 and b["morphology_count"]==727
def test_rrd_uniform_population_colors_match_independent_rms():
    from rerun.experimental import RrdReader
    m=json.loads(Path("outputs/phase3p/viewer_t2_population.json").read_text())
    scales=json.loads(Path("outputs/phase3/display_scales.json").read_text())
    expected={}
    for trial in m["episodes"]:
        with np.load(trial["record"]) as d:
            delta=d["display_activity"][:,0].astype(float)-d["baseline"][d["display_indices"][0]]
            rms=np.sqrt((delta*delta).mean(1))
            q=np.clip((rms-scales["p05"][0])/(scales["p95"][0]-scales["p05"][0]),0,1)
            for k,t in enumerate(d["observation_time"]):
                rgb=np.rint(np.array([255,166,65])*(.35+.65*q[k])).astype(int)
                expected[round((trial["offset"]+t)*1e9)]=(int(rgb[0])<<24)|(int(rgb[1])<<16)|(int(rgb[2])<<8)|160
    seen={};geometry_rows=0
    for chunk in RrdReader("outputs/phase3p/t2_population.rrd").stream():
        if chunk.entity_path!="/brain/populations/T2/arbors":continue
        b=chunk.to_record_batch()
        if chunk.is_static:
            geometry_rows+=b.num_rows;continue
        if "LineStrips3D:colors" not in b.schema.names:continue
        for ns,c in zip(b.column("physical_display_s").cast("int64").to_pylist(),b.column("LineStrips3D:colors").to_pylist()):
            if ns in expected:
                assert c==[expected[ns]];seen[ns]=c
            else:assert c==[0] # Explicit trial reset, not response-linked alpha.
    assert len(seen)==len(expected)==777 and geometry_rows==1
