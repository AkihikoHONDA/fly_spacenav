"""Numerical/malformed-data tests; fixtures are never used in the demo path."""
import json
import struct
import numpy as np
import pytest
from flyrendezvous.projection import response_rms,rms_colors,checked_episode
from flyrendezvous.morphology import read_precomputed,write_swc,read_swc,validate_tree
from flyrendezvous.recording import sha256
from flyrendezvous.sequence_phase1b import make_sequence

def sample():
    return dict(activity=np.array([[2.,100.,2.],[5.,100.,-2.]]),
        baseline=np.array([2.,99.,2.]),cell_type=np.array(["T4a","Mi1","T4a"]),
        input_time=np.array([0.,.01]),response_time=np.array([.01,.02]),
        images=np.zeros((2,3,3)),receptor_input=np.zeros((2,2)),wall_seconds=np.zeros(2),
        cell_index=np.arange(3),u=np.arange(3),v=np.zeros(3))

def test_exact_type_zero_and_mixed_sign_rms():
    selected,delta,rms=response_rms(sample(),"T4a",.01)
    np.testing.assert_array_equal(selected,[0,2])
    np.testing.assert_array_equal(delta,[[0,0],[3,-4]])
    np.testing.assert_allclose(rms,[0,np.sqrt(12.5)])
    with pytest.raises(ValueError,match="not found"):response_rms(sample(),"T4",.01)

@pytest.mark.parametrize("field",["activity","baseline","input_time","response_time"])
@pytest.mark.parametrize("value",[np.nan,np.inf])
def test_reject_nonfinite(field,value):
    data=sample();data[field].flat[0]=value
    with pytest.raises(ValueError):response_rms(data,"T4a",.01)

@pytest.mark.parametrize("field",["baseline","cell_type","input_time","response_time","images","receptor_input","wall_seconds","cell_index","u","v"])
def test_reject_misaligned_arrays(field):
    data=sample();data[field]=data[field][:-1]
    with pytest.raises(ValueError):response_rms(data,"T4a",.01)

def test_time_semantics_and_indices():
    for key,value in [("input_time",np.array([0,.02])),("response_time",np.array([0,.01])),
                      ("cell_index",np.array([2,1,0]))]:
        data=sample();data[key]=value
        with pytest.raises(ValueError):response_rms(data,"T4a",.01)

def test_fixed_palette_and_clip():
    np.testing.assert_array_equal(rms_colors([0,.11,.22,.44],.22),
                                  [[70,110,160],[162,158,112],[255,205,65],[255,205,65]])
    np.testing.assert_array_equal(rms_colors([.11],.22)[0],rms_colors([.01,.11,.21],.22)[1])
    for value,upper in [([-1],.22),([np.nan],.22),([np.inf],.22),([0],0),([0],np.nan)]:
        with pytest.raises(ValueError):rms_colors(value,upper)

def test_source_integrity(tmp_path):
    p=tmp_path/"real.npz";np.savez(p,activity=np.ones(1))
    v=tmp_path/"validation.json"
    manifest=dict(status="passed",parameter_sha256_before="a",parameter_sha256_after="a",
                  record_sha256={p.name:sha256(p)})
    v.write_text(json.dumps(manifest));assert checked_episode(p,v)["activity"][0]==1
    with p.open("ab") as f:f.write(b"modified")
    with pytest.raises(ValueError,match="hash"):checked_episode(p,v)

def test_binary_and_swc_preserve_branching(tmp_path):
    xyz=np.array([[1000,2000,3000],[1100,2100,3000],[1200,2000,3000],[1100,2200,3000]],dtype="<f4")
    edges=np.array([[0,1],[1,2],[1,3]],dtype="<u4");r=np.ones(4,dtype="<f4")
    raw=struct.pack("<II",4,3)+xyz.tobytes()+edges.tobytes()+r.tobytes()
    p=tmp_path/"skeleton";p.write_bytes(raw)
    x,e,radius=read_precomputed(p);np.testing.assert_array_equal(x,xyz)
    swc=tmp_path/"arbor.swc";write_swc(swc,x.astype(float),e,radius.astype(float))
    sx,se,sr=read_swc(swc)
    np.testing.assert_allclose(sx,xyz.astype(float)*.001)
    assert {tuple(sorted(v)) for v in se}=={tuple(sorted(v)) for v in edges}
    for damaged in [raw[:4],raw[:-1],raw+b"x"]:
        p.write_bytes(damaged)
        with pytest.raises(ValueError):read_precomputed(p)

@pytest.mark.parametrize("edges",[
    [[0,1],[1,4],[1,3]],[[0,1],[1,1],[1,3]],[[0,1],[0,1],[1,3]],[[0,1],[1,2],[2,0]]])
def test_reject_invalid_graph(edges):
    with pytest.raises(ValueError):validate_tree(np.zeros((4,3)),np.array(edges),np.ones(4))

@pytest.mark.parametrize("text",[
    "1 0 1 2 3 1 -1\n2 0 2 3 4 1 99\n",
    "1 0 nan 2 3 1 -1\n2 0 2 3 4 1 1\n",
    "1 0 1 2 3 1 -1\n1 0 2 3 4 1 1\n",
    "1 0 1 2 3 1 -1\n2 0 2 3 4 1 2\n"])
def test_reject_invalid_swc(tmp_path,text):
    p=tmp_path/"bad.swc";p.write_text(text)
    with pytest.raises(ValueError):read_swc(p)

def test_swc_ids_are_not_row_numbers(tmp_path):
    p=tmp_path/"unordered.swc"
    p.write_text("20 0 2 3 4 1 10\n10 0 1 2 3 1 -1\n30 0 5 6 7 1 10\n")
    xyz,edges,r=read_swc(p)
    np.testing.assert_array_equal(edges,[[0,1],[2,1]])
    np.testing.assert_array_equal(xyz[1],[1,2,3])

def test_staged_stimulus_bounds_and_motion():
    cfg=json.loads(open("configs/phase1.json").read())
    display=json.loads(open("configs/phase1b.json").read())
    frames,t,stages=make_sequence(cfg,display)
    assert frames.shape==(250,64,64) and t[-1]==2.49
    assert list(stages[::50])==["static","right","stop","left","stop"]
    centers=np.array([np.nonzero(f==cfg["foreground"])[1].mean() for f in frames])
    assert np.all(np.diff(centers[50:101])>=0) and np.all(np.diff(centers[150:201])<=0)
    assert np.all(centers[:50]==centers[0]) and np.all(centers[100:150]==centers[100])
    np.testing.assert_array_equal(frames[0],frames[-1])
    for f in frames:
        assert np.all(f[[0,-1],:]==cfg["background"]) and np.all(f[:,[0,-1]]==cfg["background"])
