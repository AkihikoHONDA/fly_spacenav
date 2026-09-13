"""Hand-calculable array tests only; never generate a control trajectory."""
import numpy as np
import pytest
from flyrendezvous.analysis_phase5a import (overlap,integrate,reach_time,decomposition,
    distribution,events,condition_times,analyze)

def test_piecewise_integral_variable_dt_and_fractional_boundary():
    intervals=np.array([[0.,1.],[1.,3.]])
    rates=np.array([2.,4.])
    assert integrate(intervals,rates)==10
    np.testing.assert_allclose(overlap(intervals,.5,2),[.5,1])
    assert integrate(intervals,rates,.5,2)==5
    assert reach_time(intervals,rates,.5)==1.75
    assert reach_time(intervals,rates,.8)==2.5
    assert reach_time(intervals,np.zeros(2),.5) is None

def test_braking_decomposition_and_excluded_stationary():
    u=np.array([[3.,4.],[-2.,3.],[5.,5.],[1.,0.]])
    v=np.array([[2.,0.],[2.,0.],[0.,0.],[1e-4,0.]])
    d=decomposition(u,v)
    np.testing.assert_array_equal(d['braking'],[False,True,False,False])
    np.testing.assert_array_equal(d['valid'],[True,True,False,False])
    np.testing.assert_allclose(d['parallel'][:2],[[3,0],[-2,0]])
    np.testing.assert_allclose(d['perp_norm'][:2],[4,3])
    assert np.isnan(d['perp_norm'][2:]).all()
    np.testing.assert_allclose(d['parallel_norm'][:2]**2+d['perp_norm'][:2]**2,np.sum(u[:2]**2,axis=1))

def test_direction_events_do_not_bridge_inactive_gaps():
    intervals=np.column_stack([np.arange(5),np.arange(1,6)])
    u=np.array([[1.,0.],[-1.,0.],[0.,0.],[0.,1.],[1.,0.]])
    e=events(intervals,u,1,.05)
    assert e['number_of_active_intervals']==2
    assert e['direction_changes_45deg']==2
    assert e['direction_changes_90deg']==2
    assert [c['time_s'] for c in e['major_changes']]==[1,4]
    assert e['active_duty_ratio']==.8

@pytest.mark.parametrize('threshold,count,duty',[(.02,4,1.),(.05,2,.7),(.1,1,.4)])
def test_threshold_sensitivity_time_weighting(threshold,count,duty):
    intervals=np.array([[0,1],[1,3],[3,6],[6,10]])
    u=np.array([[.03,0],[.04,0],[.08,0],[.2,0]])
    e=events(intervals,u,1,threshold)
    assert e['active_samples']==count
    assert e['active_duty_ratio']==pytest.approx(duty)

def test_bins_cover_exact_100_percent_once_and_zero():
    intervals=np.column_stack([np.arange(6),np.arange(1,7)])
    bins=distribution(intervals,np.array([0.,.01,.05,.50,1.,1.1]),1,0,6)
    assert sum(b['samples'] for b in bins)==6
    assert [b['samples'] for b in bins]==[1,1,1,0,0,2,1]
    assert sum(b['time_fraction'] for b in bins)==pytest.approx(1)
    assert sum(b['dv_fraction'] for b in bins)==pytest.approx(1)
    bins=distribution(intervals,np.zeros(6),1,0,6)
    assert all(b['dv_fraction'] is None for b in bins)

def test_strict_hold_endpoints_break_at_exact_threshold():
    intervals=np.column_stack([np.arange(5),np.arange(1,6)]).astype(float)
    states=np.zeros((6,4));states[:,0]=[.1,.1,.25,.1,.1,.1]
    c=condition_times(np.arange(6),states,intervals,np.ones(5,bool),
        dict(success_position_m=.25,success_speed_m_s=.01,success_hold_seconds=2),np.zeros(2))
    assert c['good_interval_runs']==[[0.,1.],[3.,5.]]
    assert c['success_hold_start_s']==3
    assert c['criteria_hold_completed_s']==5
    assert c['longest_hold_s']==2

def test_observation_never_counts_as_hold():
    intervals=np.column_stack([np.arange(3),np.arange(1,4)]).astype(float)
    c=condition_times(np.arange(4),np.zeros((4,4)),intervals,np.array([False,False,True]),
        dict(success_position_m=.25,success_speed_m_s=.01,success_hold_seconds=2),np.zeros(2))
    assert c['criteria_hold_completed_s'] is None
    assert c['longest_hold_s']==1

def test_adjacency_at_45_degree_boundary():
    e=events(np.array([[0,1],[1,2]]),np.array([[1.,0.],[1.,1.]]),2.,.05)
    assert e['direction_changes_45deg']==1
    assert e['direction_changes_90deg']==0

def test_bad_saved_interval_alignment_is_rejected():
    cfg=dict(dt_phys=.5,observe_seconds=0,a_max=.005,standoff_radius_m=5,
        goal_direction=[1,0],success_position_m=.25,success_speed_m_s=.01,success_hold_seconds=10)
    d=dict(acceleration_interval=np.array([[0.,.5],[.75,1.25]]),u_applied=np.zeros((2,2)),states=np.zeros((3,4)),
        observation_time=np.array([0,.75]),sample_id=np.arange(2),control_mask=np.ones(2,bool))
    with pytest.raises(AssertionError):analyze(d,{},cfg)
