"""Fixed display scales, trial balance and immutable-log alignment."""
import json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.activity_display import TYPES,select_types,trial_equal_quantile,relative_activity,check_timing,map_metrics
from flyrendezvous.viewer import colors
from flyrendezvous.screening import assert_unchanged

def test_equal_trial_mass_not_equal_frame_mass():
    a=np.array([0.,1.]);b=np.linspace(10,11,200)
    quantiles=trial_equal_quantile([a,b],[.05,.95])
    assert quantiles[0]==0
    assert 10<quantiles[1]<=11
    # Replicating one trial's samples cannot increase that trial's total weight.
    np.testing.assert_allclose(quantiles,trial_equal_quantile([np.repeat(a,50),b],[.05,.95]))

def test_empirical_quantiles_and_endpoints():
    np.testing.assert_array_equal(trial_equal_quantile([[0,1,2,3],[4,5,6,7]],[0,.05,.95,1]),[0,0,7,7])

@pytest.mark.parametrize("trials,qs",[([],[.5]),([[]],[.5]),([[np.nan]],[.5]),([[1]],[-.1]),([[1]],[1.1])])
def test_invalid_calibration_rejected(trials,qs):
    with pytest.raises(ValueError):trial_equal_quantile(trials,qs)

def test_fixed_scaling_clipping_and_no_future_normalization():
    data=np.array([0,.1,.2,.3,.4])
    np.testing.assert_allclose(relative_activity(data,.1,.3),[0,0,.5,1,1])
    first=relative_activity(data[:3],.1,.3)
    np.testing.assert_array_equal(first,relative_activity(np.r_[data[:3],10],.1,.3)[:3])

def test_tiny_range_is_neutral_not_amplified():
    np.testing.assert_array_equal(relative_activity([.1,.100000001,10],.1,.100000001),[.5,.5,.5])
    np.testing.assert_array_equal(relative_activity([.1,.2],.1,.1),[.5,.5])

def test_type_selection_preserves_order_and_cells():
    labels=np.array(["T4a","T2","L2","Tm3","T5d","T2"])
    groups=select_types(labels)
    np.testing.assert_array_equal(groups[0],[1,5])
    assert [labels[g[0]] for g in groups]==list(TYPES)
    with pytest.raises(ValueError):select_types(labels,["T4a","missing"])
    with pytest.raises(ValueError):select_types(labels,["T2","T2"])

def test_signed_map_fixed_scale_and_signs():
    delta=np.array([-2.,-.5,0,.5,2.])
    rgb=colors(delta,1)
    np.testing.assert_array_equal(rgb[[0,2,4]],[[40,95,210],[230,230,230],[210,45,45]])
    np.testing.assert_array_equal(colors(delta[:3],1),rgb[:3])
    with pytest.raises(ValueError):colors(delta,0)

def test_spatial_change_separates_pattern_from_global_level():
    d=np.array([[0,2],[1,3],[2,4]],dtype=float)
    m=map_metrics(d,10,np.ones(3,dtype=bool),.5)
    assert m["spatial_std_median"]==1
    assert m["frame_change_rms_per_phys_s_median"]==2
    assert m["centered_pattern_change_per_phys_s_median"]==0
    d=np.array([[-1,1],[1,-1],[-1,1]],dtype=float)
    assert map_metrics(d,10,np.ones(3,dtype=bool),.5)["centered_pattern_change_per_phys_s_median"]==4

def test_real_test_scales_have_equal_weight_cdf():
    scales=json.loads(Path("outputs/phase2f/display_scales.json").read_text())
    trials=[]
    for m in scales["records"]:
        with np.load(m["record"],allow_pickle=False) as z:
            cols=[np.flatnonzero(z["all_types"]==t)[0] for t in TYPES]
            trials.append(z["type_rms"][z["control_mask"]][:,cols])
    for j in range(5):
        for key,p in [("p05",.05),("p95",.95)]:
            v=scales[key][j]
            before=np.mean([np.mean(t[:,j]<v) for t in trials])
            through=np.mean([np.mean(t[:,j]<=v) for t in trials])
            assert before<=p+1e-12 and through>=p-1e-12

def test_replay_rms_map_scale_and_alignment_match_original():
    scales=json.loads(Path("outputs/phase2f/display_scales.json").read_text())
    for ident in ["test_00","test_05"]:
        with np.load("outputs/phase2/replay/"+ident+".npz",allow_pickle=False) as original, np.load("outputs/phase2f/"+ident+"_display.npz",allow_pickle=False) as out:
            check_timing(original)
            for key,newkey in [("observation_time","physical_time"),("sample_id","sample_id"),("neural_response_time","neural_response_time")]:
                np.testing.assert_array_equal(original[key],out[newkey])
            for j,name in enumerate(TYPES):
                idx=np.flatnonzero(original["cell_type"]==name)
                delta=original["activity"][:,idx].astype(float)-original["baseline"][idx]
                np.testing.assert_array_equal(delta,out["delta"][:,j])
                np.testing.assert_allclose(np.sqrt(np.mean(delta**2,axis=1)),out["raw_rms"][:,j],atol=1e-12)
            np.testing.assert_allclose(out["q"],relative_activity(out["raw_rms"],scales["p05"],scales["p95"]),atol=1e-12)

def test_time_alignment_rejects_shifted_response():
    n=25
    d=dict(sample_id=np.arange(n),observation_time=np.arange(n)*.5,neural_input_time=np.arange(n)*.01,
        neural_response_time=(np.arange(n)+1)*.01,control_mask=np.arange(n)>=20,states=np.zeros((n+1,4)))
    check_timing(d)
    d["neural_response_time"]+=.01
    with pytest.raises(AssertionError):check_timing(d)

def test_old_phase_results_and_sources_unchanged():
    snapshot=json.loads(Path("outputs/phase2f/prior_hashes.json").read_text())
    assert assert_unchanged(snapshot)==460
