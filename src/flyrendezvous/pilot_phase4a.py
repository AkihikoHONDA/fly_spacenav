"""Display-only joystick driven by the exact saved, applied LVLH acceleration."""
import json
from pathlib import Path
import numpy as np
from .display_coordinates import display_coordinates
from .recording import sha256
A_REF=.005
BASE=np.array([.65,.25,.18])
PILOT_EYE=np.array([BASE[0],BASE[1],3.8])
PILOT_LOOK=np.array([BASE[0],BASE[1],0.])
LENGTH=1.2
TRAVEL=.55
def command_state(applied):
    a=np.asarray(applied,dtype=float)
    display=display_coordinates(a)
    u=np.clip(display/A_REF,-1,1)
    xy=TRAVEL*u
    z=np.sqrt(LENGTH**2-np.sum(xy*xy,axis=-1))
    tip=BASE+np.concatenate([xy,z[...,None]],axis=-1)
    return dict(applied=a,display=display,normalized=u,tip=tip,clipped=np.any(np.abs(display)>A_REF,axis=-1))
def load_asset():
    manifest=Path("assets/fly_pilot/manifest.json")
    if not manifest.exists():raise FileNotFoundError("External fly asset pending: provide the authorized CadNav or Sketchfab download")
    m=json.loads(manifest.read_text());p=Path(m["converted_path"])
    if sha256(p)!=m["converted_sha256"]:raise ValueError("Fly asset hash mismatch")
    return p,m
def log_static(allow_missing=False):
    import rerun as rr
    import trimesh
    def mesh(path,obj,color):
        rr.log(path,rr.Mesh3D(vertex_positions=obj.vertices,triangle_indices=obj.faces,vertex_normals=obj.vertex_normals,albedo_factor=color),static=True)
    pedestal=trimesh.creation.box(extents=[4.3,3.5,.15]);pedestal.apply_translation([0,-.2,-.12])
    mesh("/pilot/pedestal",pedestal,[95,108,125])
    base=trimesh.creation.cylinder(radius=.42,height=.16,sections=32);base.apply_translation(BASE-[0,0,.08])
    mesh("/pilot/joystick/base",base,[120,132,150])
    ring=BASE+np.array([[-TRAVEL,-TRAVEL,0],[TRAVEL,-TRAVEL,0],[TRAVEL,TRAVEL,0],[-TRAVEL,TRAVEL,0],[-TRAVEL,-TRAVEL,0]])
    rr.log("/pilot/command_range",rr.LineStrips3D(ring,colors=[100,115,135],radii=.01),static=True)
    rr.log("/pilot/directions",rr.Arrows3D(origins=[[.1,1.25,.05],[-1.6,-.5,.05]],vectors=[[-.7,0,0],[0,-.7,0]],colors=[195,200,215],radii=.025),static=True)
    rr.log("/pilot/axis_labels",rr.Points3D([[-.5,1.45,.05],[-1.45,-1.45,.05]],labels=["left: along-track","down: central body"],colors=[215,220,230],radii=rr.Radius.ui_points(0)),static=True)
    try:
        asset,m=load_asset()
        rr.log("/pilot/fly",rr.Asset3D(path=asset),static=True)
    except FileNotFoundError:
        if not allow_missing:raise
        rr.log("/pilot/asset_pending",rr.Points3D([[-.9,-.3,.4]],radii=rr.Radius.ui_points(0),colors=[250,185,70],labels=["EXTERNAL FLY ASSET PENDING"]),static=True)
    return
def log_sample(applied):
    import rerun as rr
    s=command_state(applied);tip=s["tip"]
    rr.log("/pilot/joystick/shaft",rr.LineStrips3D([BASE,tip],colors=[185,195,205],radii=.055))
    rr.log("/pilot/joystick/grip",rr.Points3D([tip],radii=.13,colors=[80,215,225]))
    # Plan-view projection is exactly parallel to the Orbit acceleration arrow.
    rr.log("/pilot/command",rr.Arrows3D(origins=[[BASE[0],BASE[1],BASE[2]+.01]],vectors=[[*(tip[:2]-BASE[:2]),0]],colors=[255,170,70],radii=.025))
    rr.log("/pilot_values",rr.TextDocument(
        f"Illustrative control view; not biological motor output.\nJoystick follows learned 2D translational command.\n"
        f"a_disp X {s['display'][0]:+.5f} · Y {s['display'][1]:+.5f} m/s²"
         ,media_type="text/plain"))
    return s
