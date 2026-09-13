import inspect,json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.phase3_runtime import load_config,make_splits,rollout,safety
from flyrendezvous.geometry_phase3 import Teacher,Camera
from flyrendezvous.display_coordinates import display_coordinates,rerun_coordinates
from flyrendezvous.readout import ImagePolicy

def test_goal_and_display_geometry():
    cfg=load_config();t=Teacher(cfg)
    np.testing.assert_allclose(t.goal,[-5/np.sqrt(2),5/np.sqrt(2),0,0])
    np.testing.assert_allclose(display_coordinates(t.goal[:2]),[-5/np.sqrt(2)]*2)
    np.testing.assert_allclose(rerun_coordinates(t.goal[:2]),[-5/np.sqrt(2),5/np.sqrt(2)])
    assert np.isclose(np.linalg.norm(t.goal[:2])-cfg["camera"]["target_radius_m"],4)

def test_rotated_cost_equilibrium_and_eigenvalues():
    cfg=load_config();t=Teacher(cfg)
    np.testing.assert_allclose(t.A@t.goal+t.B@t.u_eq,0,atol=1e-14)
    np.testing.assert_allclose(t.Ad@t.goal+t.Bd@t.u_eq,t.goal,atol=1e-13)
    np.testing.assert_allclose(np.linalg.eigvalsh(t.Q),sorted(cfg["Q_diag"]))
    assert max(abs(t.eigenvalues))<1
    assert t.u_eq[0]>0 and t.u_eq[1]==0

def test_sphere_onaxis_size_and_goal_fov():
    cfg=load_config();c=Camera(cfg["camera"]);er=np.array(cfg["goal_direction"])
    radii=[]
    for distance in [5,10,20]:
        p,ok=c.project(distance*er);assert ok
        np.testing.assert_allclose(p[:2],[31.5,31.5])
        np.testing.assert_allclose(p[2],c.f/np.sqrt(distance**2-1))
        radii.append(p[2])
    assert radii[0]>radii[1]>radii[2]

def test_sphere_bearing_and_tangent_cone_envelope():
    c=Camera(load_config()["camera"])
    for bearing in [-.1,0,.1]:
        d=10.;rel=d*(np.cos(bearing)*c.bore+np.sin(bearing)*c.right)
        p,visible=c.project(-rel);assert visible
        alpha=np.arcsin(1/d)
        np.testing.assert_allclose([p[0]-p[2],p[0]+p[2]],31.5+c.f*np.tan([bearing-alpha,bearing+alpha]),atol=1e-12)
        assert np.sign(p[0]-31.5)==np.sign(bearing)
        # Independent 3D tangent circle on sphere -> pinhole conic.
        center=np.array([rel@c.right,0,rel@c.bore]);axis=center/d
        a=np.array([0,1,0]);b=np.cross(axis,a)
        angles=np.linspace(0,2*np.pi,2000)
        points=(d-1/d)*axis[None]+np.sqrt(1-1/d**2)*(np.cos(angles)[:,None]*a+np.sin(angles)[:,None]*b)
        xy=c.f*points[:,:2]/points[:,2,None]+31.5
        assert np.max(np.linalg.norm(xy-p[:2],axis=1))<=p[2]+1e-10

@pytest.mark.parametrize("distance",[-10,0,.5,1])
def test_invalid_sphere_camera(distance):
    cfg=load_config();c=Camera(cfg["camera"])
    assert not c.project(distance*np.array(cfg["goal_direction"]))[1]
    with pytest.raises(ValueError):c.render(distance*np.array(cfg["goal_direction"]))

def test_new_disjoint_splits_and_approach_bounds():
    cfg=load_config();splits=make_splits(cfg);er=np.array(cfg["goal_direction"]);et=[-er[1],er[0]]
    assert [len(splits[k]) for k in ["train","validation","test","gate"]]==[24,6,12,30]
    old=json.loads(Path("outputs/phase2/splits.json").read_text())
    oldstates={tuple(c["initial_state"]) for v in old.values() for c in v}
    seen=set()
    for cases in splits.values():
        for c in cases:
            s=np.array(c["initial_state"]);key=tuple(s)
            assert key not in oldstates and key not in seen;seen.add(key)
            if c["category"]=="approach":
                assert 14<=s[:2]@er<=22 and abs(s[:2]@et)<=2
            else:assert abs(s[:2]@er-5)<=.5 and abs(s[:2]@et)<=.5

def test_collision_and_range():
    cfg=load_config();c=Camera(cfg["camera"]);er=np.array(cfg["goal_direction"])
    assert safety(np.r_[1.25*er,0,0],c,cfg)=="collision"
    assert safety(np.r_[41*er,0,0],c,cfg)=="range_exit"
    assert safety(np.array([np.nan,0,0,0]),c,cfg)=="nonfinite"

def test_saved_teacher_gate_all_thirty():
    cfg=load_config();c=Camera(cfg["camera"]);t=Teacher(cfg)
    gate=json.loads(Path("outputs/phase3/phase3a.json").read_text())
    assert len(gate["results"])==30 and all(m["success"] for m in gate["results"])
    for m in gate["results"]:
        with np.load(m["record"]) as d:
            assert all(c.project(s)[1] for s in d["states"])
            np.testing.assert_array_equal(d["u_applied"][:20],0)
            tail=d["states"][-21:]
            assert np.all(np.linalg.norm(tail[:,:2]-t.goal[:2],axis=1)<.25)
            assert np.all(np.linalg.norm(tail[:,2:],axis=1)<.01)

def test_image_only_causal_interface():
    assert list(inspect.signature(ImagePolicy.step).parameters)==["self","image"]
    class Dummy:
        def __init__(self):self.images=[];self.adapter=None;self.baseline=None
        def reset(self):self.images=[]
        def step(self,image):
            assert image.shape==(64,64);self.images.append(image.copy())
            return np.zeros(2),np.zeros(2),None
    cfg=load_config();p=Dummy();case=make_splits(cfg)["train"][0]
    d,m=rollout(cfg,case,"learner",policy=p,max_steps=22)
    assert len(p.images)==22
    t=Teacher(cfg)
    for k in range(22):np.testing.assert_allclose(d["states"][k+1],t.Ad@d["states"][k],atol=1e-12)
