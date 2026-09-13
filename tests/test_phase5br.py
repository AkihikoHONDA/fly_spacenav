import copy,json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.aggregation_phase5br import *
from flyrendezvous.readout import Readout
C=json.loads(Path('configs/phase5br/training.json').read_text())
def trial(n=1180):
    t=10+np.arange(n)*.5;goal=np.array(C['goal_direction'])*5
    state=np.c_[np.tile(goal+[20,0],(n+1,1)),np.tile([.1,0],(n+1,1))]
    return dict(observation_time=t,sample_id=np.arange(n)+20,states=state),dict(id='train_00',split='train',termination_reason='timeout',final_time_s=t[-1]+.5)
def test_aggregation_rejects_nontrain():
    d,m=trial()
    for split in ['validation','test']:
        with pytest.raises(ValueError):select_samples(d,{**m,'split':split},C,1)
def test_round1_primary_stride_and_critical_caps():
    d,m=trial();idx,e,v,r=select_samples(d,m,C,1)
    np.testing.assert_array_equal(idx,np.arange(0,1180,4));assert len(idx)<=300
    d['states'][:,2:]=0
    idx,e,v,r=select_samples(d,m,C,1)
    assert len(idx)==450 and set(range(0,1180,4)).issubset(idx)
    assert all('speed_lt_0.03' in x for x in r)
def test_safety_tail_and_observation_exclusion():
    d,m=trial(80);m['termination_reason']='range_exit'
    idx,*_=select_samples(d,m,C,1)
    assert set(range(60,80)).issubset(idx)
    d['observation_time']-=10
    idx,*_=select_samples(d,m,C,1);assert np.all(d['observation_time'][idx]>=10)
def test_round2_three_rates_and_cap():
    d,m=trial(120);goal=np.array(C['goal_direction'])*5
    d['states'][40:80,:2]=goal+[3,0];d['states'][80:,:2]=goal+[1,0]
    idx,*_=select_samples(d,m,C,2)
    expected=np.r_[np.arange(0,40,4),np.arange(40,80,2),np.arange(80,120)]
    np.testing.assert_array_equal(idx,expected)
    d,m=trial();d['states'][:,2:]=0
    idx,*_=select_samples(d,m,C,2);assert len(idx)==600
def test_deterministic_strata_cap_and_boundaries():
    x=np.repeat([.1,1,3,7,12],200)
    a=stratified_indices(x,123);b=stratified_indices(x,123)
    np.testing.assert_array_equal(a,b);assert len(np.unique(a))==123
    counts=np.bincount(stratum(x[a]),minlength=5);assert max(counts)-min(counts)<=1
    np.testing.assert_array_equal(stratum([.49,.5,2,5,10,10.01]),[0,1,2,3,3,4])
def test_duplicate_tolerance():
    ensure_unique([[1,2,3,4]],[[5,6,7,8]])
    with pytest.raises(ValueError):ensure_unique([[1,2,3,4]],[[1+5e-13,2,3,4]])
    with pytest.raises(ValueError):ensure_unique([[1,2,3,4],[1,2,3,4]],[])
def test_selection_order_gate_and_single_run():
    r=dict(success=10,catastrophic_exits=1,median_final_goal_error=.5,median_final_speed=.015,
        median_total_dv=.5,validation_mse=.01,lag=0,regularization=.0001)
    assert validation_gate(r);require_test_allowed(r,True,False)
    for k,v in [('success',9),('catastrophic_exits',2),('median_final_goal_error',.501),('median_final_speed',.0151)]:
        assert not validation_gate({**r,k:v})
        with pytest.raises(RuntimeError):require_test_allowed({**r,k:v},True,False)
    with pytest.raises(RuntimeError):require_test_allowed(r,True,True)
    with pytest.raises(RuntimeError):require_test_allowed(r,False,False)
    assert selection_key(r)<selection_key({**r,'catastrophic_exits':2})
def test_scaler_uses_combined_train_only():
    rng=np.random.default_rng(5);teacher=rng.normal(size=(40,5));agg=rng.normal(2,1,size=(20,5))
    X=np.r_[teacher,agg];Y=np.c_[X[:,0],X[:,1]]
    model=Readout.fit(X,Y,0,.01)
    np.testing.assert_allclose(model.mean,X.mean(0));np.testing.assert_allclose(model.std,X.std(0))
    before=model.mean.copy();model.predict(np.full((10,5),100.))
    np.testing.assert_array_equal(before,model.mean)

def test_global_round_cap_and_original_causal_history():
    from flyrendezvous.features import history_matrix
    # Original dt=.5 history remains t-2.5 s even after 2 s sampling.
    phi=np.arange(100*3).reshape(100,3).astype(float);selected=np.arange(20,100,4)
    X=history_matrix(phi,5)[selected]
    np.testing.assert_array_equal(X[:,:3],phi[selected])
    np.testing.assert_array_equal(X[:,3:],phi[selected-5])
    errors=np.tile(np.linspace(0,20,600),36);teacher_count=17900
    first=stratified_indices(errors,teacher_count);second=stratified_indices(errors[::-1],teacher_count)
    assert len(first)<=teacher_count and len(second)<=teacher_count
    assert len(first)+len(second)<=2*teacher_count

def test_terminal_diagnostics_use_endpoint_hold():
    from flyrendezvous.diagnostics_phase5br import terminal
    goal=np.array(C['goal_direction'])*5;n=40;t=np.arange(n)*.5
    states=np.c_[np.tile(goal,(n+1,1)),np.zeros((n+1,2))]
    d=dict(states=states,u_applied=np.zeros((n,2)),control_mask=t>=10,observation_time=t,
        acceleration_interval=np.c_[t,t+.5],sample_id=np.arange(n))
    m=dict(id='validation_00',category='approach',success=True,termination_reason='success',longest_hold_s=10.)
    r=terminal(d,m,C)
    assert r['success_time_s']==20 and r['longest_continuous_joint_hold_s']==10
    assert r['terminal_failure_mode']=='success' and r['post_near_goal_dv_m_s']==0

def test_model_lock_detects_modified_file(tmp_path):
    from flyrendezvous.recording import sha256
    p=tmp_path/'model.bin';p.write_bytes(b'locked readout')
    files={str(p):sha256(p)};check_locked_files(files)
    p.write_bytes(b'changed readout')
    with pytest.raises(RuntimeError):check_locked_files(files)
