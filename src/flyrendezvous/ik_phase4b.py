"""Presentation-only analytic IK. No dynamics, no inference, no command smoothing."""
import json
from pathlib import Path
import numpy as np
from .pilot_phase4a import command_state,BASE,LENGTH
PARAMS=Path("assets/fly_pilot_phase4b/design_params.json")
def settings():return json.loads(PARAMS.read_text())
def unit(v):
 v=np.asarray(v,float);n=np.linalg.norm(v)
 if n<1e-12:raise ValueError("Undefined direction")
 return v/n
def solve_ik(shoulder,target,l1,l2,pole):
 s=np.asarray(shoulder,float);t=np.asarray(target,float);d=t-s
 distance=float(np.linalg.norm(d));axis=d/distance if distance>1e-12 else np.array([1.,0,0])
 reach=float(np.clip(distance,abs(l1-l2)+1e-7,l1+l2-1e-7));end=s+axis*reach
 bend=np.asarray(pole,float)-axis*np.dot(pole,axis)
 if np.linalg.norm(bend)<1e-8:
  # Deterministic singular fallback; normal operating targets stay away from it.
  fallback=np.eye(3)[np.argmin(abs(axis))];bend=fallback-axis*np.dot(fallback,axis)
 bend=unit(bend)
 along=(l1*l1-l2*l2+reach*reach)/(2*reach)
 height=np.sqrt(max(0.,l1*l1-along*along))
 elbow=s+axis*along+bend*height
 return dict(shoulder=s,elbow=elbow,end=end,target=t,bend=bend,clamped=abs(reach-distance)>1e-9,error=float(np.linalg.norm(end-t)))
def segment_rotation(direction,pole):
 z=unit(direction);x=np.asarray(pole,float)-z*np.dot(pole,z)
 if np.linalg.norm(x)<1e-8:
  helper=np.eye(3)[np.argmin(abs(z))];x=helper-z*np.dot(helper,z)
 x=unit(x);y=np.cross(z,x)
 return np.column_stack([x,y,z])
def pose(applied,params=None):
 p=params or settings();s=command_state(applied)
 shaft=unit(s['tip']-BASE);side=unit(np.array([0.,1,0])-shaft*shaft[1])
 legs={}
 for name,sign in [('left',1),('right',-1)]:
  shoulder=np.array(p['rig']['shoulders'][name])
  target=s['tip']+sign*p['rig']['hand_offset']*side
  pole=np.array([0.,0.,-1.])
  result=solve_ik(shoulder,target,*p['rig']['lengths'],pole)
  r1=segment_rotation(result['elbow']-shoulder,pole)
  r2=segment_rotation(result['end']-result['elbow'],pole)
  result.update(upper_rotation=r1,lower_local_rotation=r1.T@r2)
  legs[name]=result
 return s,legs
def project(points,params=None):
 p=params or settings();camera=p['camera'];eye=np.array(camera['position'])
 forward=unit(np.array(camera['look_target'])-eye)
 right=unit(np.cross(forward,[0.,0,1.]));up=np.cross(right,forward)
 v=np.asarray(points)-eye;depth=v@forward
 if np.any(depth<=0):raise ValueError('Point behind Pilot camera')
 return np.stack([v@right,-(v@up)],axis=-1)/np.expand_dims(depth,-1)
