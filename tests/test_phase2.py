import inspect,json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy.integrate import solve_ivp
from flyrendezvous.hcw import matrices,Teacher
from flyrendezvous.camera import Camera
from flyrendezvous.features import Pooling,History,history_matrix
from flyrendezvous.readout import Readout,ImagePolicy
from flyrendezvous.phase2_runtime import load_config,make_splits,rollout

def test_hcw_zero_n_and_independent_integration():
    state=np.array([18.,1.,-.02,.01]);u=np.array([.002,-.001]);dt=.5
    A,B,Ad,Bd=matrices(0,dt)
    np.testing.assert_allclose(Ad@state+Bd@u,np.r_[state[:2]+state[2:]*dt+.5*u*dt*dt,state[2:]+u*dt],atol=1e-13)
    A,B,Ad,Bd=matrices(.0011,dt)
    independent=solve_ivp(lambda t,s:A@s+B@u,[0,dt],state,method="DOP853",rtol=1e-12,atol=1e-13).y[:,-1]
    np.testing.assert_allclose(Ad@state+Bd@u,independent,atol=1e-12)

def test_equilibrium_stability_saturation():
    t=Teacher(load_config())
    np.testing.assert_allclose(t.A@t.goal+t.B@t.u_eq,0,atol=1e-14)
    np.testing.assert_allclose(t.Ad@t.goal+t.Bd@t.u_eq,t.goal,atol=1e-13)
    assert np.max(np.abs(t.eigenvalues))<1
    raw,applied=t.command(np.array([1000,-1000,1,-1]))
    assert np.any(np.abs(raw)>t.limit) and np.max(np.abs(applied))<=t.limit

def test_camera_sign_inverse_size_subpixel_fov():
    c=Camera(load_config()["camera"])
    centered,_=c.project([20,0,0,0]);offset,_=c.project([20,1,0,0]);near,_=c.project([10,0,0,0])
    assert offset[0]<centered[0] and near[2]==2*centered[2]
    a=c.render([20,0,0,0]);b=c.render([20,.01,0,0])
    assert 0<np.max(np.abs(a-b))<.15
    assert not c.project([10,10,0,0])[1] and not c.project([-1,0,0,0])[1]

def test_pooling_excludes_direct_input_and_retains_space():
    nodes=pd.read_csv("outputs/phase1/cells.csv");p=Pooling(nodes,4)
    assert set(p.cell_type[p.excluded])=={"R1","R2","R3","R4","R5","R6","R7","R8"}
    assert len(p.used)==39901 and p.dimension==912
    a=np.zeros(len(nodes));b=a.copy();b[p.excluded]=100
    np.testing.assert_array_equal(p.extract(a,a),p.extract(b,a))
    b[p.used[0]]=1
    assert np.count_nonzero(p.extract(b,a))==1

def test_history_is_causal():
    phi=np.arange(80).reshape(20,4).astype(float)
    expected=history_matrix(phi,5);history=History(5)
    for k,row in enumerate(phi):
        value=history.append(row)
        if k<5:assert value is None
        else:np.testing.assert_array_equal(value,expected[k])
    other=phi.copy();other[12:]+=1000
    np.testing.assert_array_equal(history_matrix(phi,5)[5:12],history_matrix(other,5)[5:12])

def test_ridge_train_only_scaling_intercept_reload(tmp_path):
    rng=np.random.default_rng(5);X=rng.normal(size=(100,6));X[:,0]=3
    Y=np.column_stack([2*X[:,1]+.5,-X[:,2]-.2])
    m=Readout.fit(X,Y,0,.01);mean=m.mean.copy();std=m.std.copy()
    test=rng.normal(100,3,size=(10,6));m.predict(test)
    np.testing.assert_array_equal(m.mean,mean);np.testing.assert_array_equal(m.std,std)
    np.testing.assert_allclose(mean,X.mean(0));assert not m.keep[0]
    z=(X[:,m.keep]-m.mean[m.keep])/m.std[m.keep]
    gradient=(z.T@(z@m.W.T+m.b-Y)/len(X)+.01*m.W.T)
    np.testing.assert_allclose(gradient,0,atol=1e-12)
    np.testing.assert_allclose((m.predict(X)-Y).mean(0),0,atol=1e-12)
    path=tmp_path/"readout.npz";m.save(path)
    np.testing.assert_array_equal(Readout.load(path).predict(test),m.predict(test))
    assert np.linalg.norm(m.predict(test[0])-m.predict(test[0]+np.arange(6)))>0

def test_split_and_policy_interface():
    splits=make_splits(load_config())
    sets=[{tuple(c["initial_state"]) for c in cases} for cases in splits.values()]
    assert all(not sets[i]&sets[j] for i in range(3) for j in range(i))
    assert [len(s) for s in sets]==[24,6,12]
    assert list(inspect.signature(ImagePolicy.step).parameters)==["self","image"]
    assert ImagePolicy.step.__closure__ is None

def test_rollout_time_initial_observation_and_no_state_reset():
    cfg=load_config();case=make_splits(cfg)["train"][0]
    d,m=rollout(cfg,case,"teacher",max_steps=24)
    t=Teacher(cfg);c=Camera(cfg["camera"])
    assert len(d["states"])==25
    np.testing.assert_array_equal(d["u_applied"][:20],0)
    np.testing.assert_array_equal(d["control_mask"],np.arange(24)>=20)
    for k in range(24):
        np.testing.assert_allclose(d["states"][k+1],t.Ad@d["states"][k]+t.Bd@d["u_applied"][k],atol=1e-13)
        np.testing.assert_array_equal(d["images"][k],c.render(d["states"][k]))
    np.testing.assert_allclose(d["neural_response_time"]-d["neural_input_time"],.01)
    np.testing.assert_allclose(d["acceleration_interval"],np.column_stack([np.arange(24)*.5,(np.arange(24)+1)*.5]))
    assert not np.array_equal(d["states"][0],d["states"][20])

@pytest.mark.integration
def test_phase2_real_images_policy_prefix_and_weight_freeze():
    from flyrendezvous.adapter import FlyvisAdapter
    from flyrendezvous.phase2_runtime import adapter_config
    cfg=load_config();adapter=FlyvisAdapter(adapter_config());pool=Pooling(adapter.nodes,4)
    model_path=Path("outputs/phase2/readout.npz")
    assert model_path.exists(),"Phase 2 learning must run before this real policy integration test"
    model=Readout.load(model_path);policy=ImagePolicy(adapter,pool,model,cfg["a_max"])
    camera=Camera(cfg["camera"])
    images=np.stack([camera.render([16-.04*k,.3,0,0]) for k in range(16)])
    def run(frames):
        policy.reset();outputs=[];features=[]
        for image in frames:
            raw,u,data=policy.step(image);outputs.append(raw);features.append(data["phi"])
        return np.stack(outputs),np.stack(features)
    first,features=run(images)
    changed=images.copy();changed[10:]=np.stack([camera.render([20,-.7,0,0])]*6)
    second,_=run(changed)
    np.testing.assert_allclose(first[:10],second[:10],atol=2e-7,rtol=2e-5)
    assert np.max(np.abs(first[10:]-second[10:]))>1e-7
    assert np.max(np.abs(features[5:]-features[5]))>1e-5
    adapter.assert_frozen()
