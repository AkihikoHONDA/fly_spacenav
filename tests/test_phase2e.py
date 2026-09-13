"""Regression contracts for post-hoc display and frozen-record screening."""
import json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.display_coordinates import display_coordinates,rerun_coordinates
from flyrendezvous.screening import type_groups,type_response,classify_stages,contributions,feature_types,assert_unchanged
from flyrendezvous.readout import Readout

@pytest.mark.parametrize("physical,display,canvas",[
    ([1,0],[0,1],[0,-1]),([-1,0],[0,-1],[0,1]),
    ([0,1],[-1,0],[-1,0]),([0,-1],[1,0],[1,0])])
def test_four_directions(physical,display,canvas):
    np.testing.assert_array_equal(display_coordinates(physical),display)
    np.testing.assert_array_equal(rerun_coordinates(physical),canvas)

def test_positions_and_vectors_share_rotation_without_mutation():
    p=np.array([[22.,1.],[10.,0.],[0.,0.]])
    original=p.copy();v=np.array([-.2,.01]);a=np.array([.005,-.002])
    for transform in [display_coordinates,rerun_coordinates]:
        np.testing.assert_allclose(transform(p+20*v),transform(p)+20*transform(v))
        np.testing.assert_allclose(transform(p+400*a),transform(p)+400*transform(a))
        np.testing.assert_allclose(np.linalg.norm(transform(p),axis=1),np.linalg.norm(p,axis=1))
    np.testing.assert_array_equal(p,original)

@pytest.mark.parametrize("bad",[1,[1,2,3],[np.nan,1],[0,np.inf]])
def test_rotation_rejects_invalid(bad):
    with pytest.raises(ValueError):display_coordinates(bad)

def test_grouping_and_signed_cancellation():
    labels=np.array(["T4a","Mi1","T4a","Mi1"])
    np.testing.assert_array_equal(type_groups(labels)["T4a"],[0,2])
    baseline=np.array([2.,3.,4.,5.])
    names,mean,rms=type_response(np.array([[4,2,2,4],[2,5,4,7]]),baseline,labels)
    np.testing.assert_array_equal(names,["Mi1","T4a"])
    np.testing.assert_allclose(mean,[[-1,0],[2,0]])
    np.testing.assert_allclose(rms,[[1,2],[2,0]])
    with pytest.raises(ValueError):type_response([[np.nan]*4],baseline,labels)

def test_feature_groups_follow_saved_assignments_not_contiguous_assumption():
    pool=dict(cell_type=np.array(["R1","T4a","Mi1","T4a"]),
        used_indices=np.array([1,2,3]),used_cell_feature_index=np.array([1,0,1]),feature_counts=np.array([1,2]))
    np.testing.assert_array_equal(feature_types(pool),["Mi1","T4a"])
    pool["used_cell_feature_index"]=np.array([0,0,1])
    with pytest.raises(ValueError):feature_types(pool)

def test_contributions_use_training_scaling_keep_mask_and_separate_bias():
    model=Readout(np.array([10.,20.,30.]),np.array([2.,0.,4.]),
        np.array([True,False,True]),np.array([[2.,3.],[-1.,4.]]),np.array([.3,-.2]),0,.0001)
    phi=np.array([[12.,999.,26.],[8.,-999.,38.]])
    c,bias=contributions(phi,model,np.array(["Mi1","ignored","T4a"]),np.array(["R1","Mi1","T4a"]),.005)
    np.testing.assert_allclose(c[:,0],0)
    np.testing.assert_allclose(c[0,1],[.01,-.005])
    np.testing.assert_allclose(c[0,2],[-.015,-.02])
    np.testing.assert_allclose(bias,[.0015,-.001])
    np.testing.assert_allclose(c.sum(1)+bias,.005*model.predict(phi),atol=1e-15)

def test_stage_priority_and_permutation_independence():
    s=np.array([[22,0,-.1,0],[15,0,-.1,0],[10.1,0,-.001,0],[10.25,0,0,0],
        [10,0,.01,0],[9.8,0,-.02,0],[22,0,-.1,0]])
    u=np.array([[-.001,0],[.001,0],[.001,0],[0,0],[0,0],[.001,0],[.001,0]])
    active=np.array([1,1,1,1,1,1,0],dtype=bool)
    expected=np.array(["approach","braking","near_hold","other","other","other","observation"])
    np.testing.assert_array_equal(classify_stages(s,u,active),expected)
    order=[6,2,4,0,5,3,1]
    np.testing.assert_array_equal(classify_stages(s[order],u[order],active[order]),expected[order])

def test_frozen_original_test_reconstruction_and_screening():
    report=json.loads(Path("outputs/phase2e/cell_type_screening.json").read_text())
    assert report["all_types_evaluated"]==65
    assert report["readout_types"]==57
    assert report["max_readout_reconstruction_error"]<1e-12
    assert report["new_neural_inference"] is False
    model=Readout.load("outputs/phase2/readout.npz")
    with np.load("outputs/phase2e/cell_type_metrics.npz",allow_pickle=False) as z:
        ev=json.loads(Path("outputs/phase2/evaluation.json").read_text())
        for m in ev["learner"]:
            with np.load(m["record"],allow_pickle=False) as d:
                chosen=z["episode"]==m["id"]
                np.testing.assert_allclose(z["contribution"][chosen].sum(1)+z["bias_acceleration"],
                    .005*model.predict(d["phi"]),atol=1e-12)
                control=d["control_mask"]
                np.testing.assert_allclose(.005*model.predict(d["phi"])[control],d["u_raw"][control],atol=1e-12)
                np.testing.assert_array_equal(z["physical_time"][chosen],d["observation_time"])
                np.testing.assert_array_equal(z["type_mean"][chosen],d["type_mean"])
                np.testing.assert_array_equal(z["type_rms"][chosen],d["type_rms"])

def test_protected_phase1_1b_2_files_unchanged():
    manifest=json.loads(Path("outputs/phase2e/prior_hashes.json").read_text())
    assert assert_unchanged(manifest)==409
