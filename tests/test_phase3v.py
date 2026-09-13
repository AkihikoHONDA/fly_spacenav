import json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.representatives_phase3v import TYPES3,PALETTE,intensity_color,load_representatives
from flyrendezvous.activity_display import relative_activity
from flyrendezvous.morphology import read_precomputed
from flyrendezvous.recording import sha256

@pytest.mark.parametrize("name",TYPES3)
def test_color_has_fixed_hue_nonzero_floor_monotonic_brightness(name):
    q=np.linspace(0,1,101);c=intensity_color(name,q)
    np.testing.assert_array_equal(c[0],np.rint(np.array(PALETTE[name])*.35))
    np.testing.assert_array_equal(c[-1],PALETTE[name])
    assert np.all(np.diff(c.astype(float),axis=0)>=0)
    assert np.linalg.norm(c[-1])>np.linalg.norm(c[0])>0
    np.testing.assert_array_equal(intensity_color(name,[-1,2]),c[[0,-1]])

@pytest.mark.parametrize("name",TYPES3)
def test_geometry_is_exact_published_coordinates_and_edges(name):
    manifest=json.loads(Path("docs/anatomy_mapping_phase3v.json").read_text())
    m=manifest["morphologies"][name];assert m["annotation_row"]["cell_type"]==name
    assert m["side"]=="right" and sha256(m["path"])==m["sha256"]
    xyz,edges,_=read_precomputed(m["path"]);actual=load_representatives()[name]
    np.testing.assert_array_equal(actual[0],xyz.astype(float)*.001)
    np.testing.assert_array_equal(actual[1],edges)
    assert len(edges)==len(xyz)-1

def test_palette_input_rejection():
    with pytest.raises(ValueError):intensity_color("T5",.5)
    with pytest.raises(ValueError):intensity_color("T2",np.nan)

def test_test_scales_are_original_nontest_lock():
    p=Path("outputs/phase3")
    scales=json.loads((p/"display_scales.json").read_text())
    lock=json.loads((p/"test_started.json").read_text())
    assert not scales["test_used"]
    assert sha256(p/"display_scales.json")==lock["display_scales_sha256"]
    assert len(scales["sources"])==30 and {m["split"] for m in scales["sources"]}=={"train","validation"}
    lo=np.array(scales["p05"]);hi=np.array(scales["p95"])
    np.testing.assert_array_equal(relative_activity(lo,lo,hi),np.zeros(5))
    np.testing.assert_array_equal(relative_activity(hi,lo,hi),np.ones(5))

def test_only_two_new_morphologies_and_three_unique_representatives():
    m=json.loads(Path("docs/anatomy_mapping_phase3v.json").read_text())
    assert m["acquired_types"]==["T2","T5d"] and m["reused_types"]==["T4a"]
    assert len(list(Path("assets/phase3v").glob("*.precomputed")))==2
    assert len({a["root_id"] for a in m["morphologies"].values()})==3
    assert not m["one_to_one_model_cell_mapping"] and not m["model_hemisphere_assigned"]

def test_terminal_sample_is_not_cleared():
    from rerun.experimental import RrdReader
    manifest=json.loads(Path("outputs/phase3v/viewer_demo.json").read_text())
    last=manifest["episodes"][-1];end_ns=round((last["offset"]+(last["frames"]-1)*.5)*1e9)
    last_arbor={};clear_times=[]
    for chunk in RrdReader("outputs/phase3v/phase3v_demo.rrd").stream():
        if chunk.is_static:continue
        b=chunk.to_record_batch();p=chunk.entity_path
        if "physical_display_s" not in b.schema.names:continue
        times=b.column("physical_display_s").cast("int64").to_pylist()
        if p.startswith("/brain/representatives/") and p.endswith("/arbor") and "LineStrips3D:colors" in b.schema.names:
            last_arbor[p]=max(last_arbor.get(p,0),max(times))
        if p=="/brain/representatives" and any("Clear" in x for x in b.schema.names):clear_times.extend(times)
    assert len(last_arbor)==3 and all(t==end_ns for t in last_arbor.values())
    assert len(set(clear_times))==len(manifest["episodes"])-1 and max(clear_times)<end_ns
