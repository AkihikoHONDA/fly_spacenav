"""Phase 3 sphere geometry; LVLH dynamics are unchanged."""
import numpy as np
from scipy.linalg import solve_discrete_are
from .hcw import Teacher as Phase2Teacher
from .camera import Camera as DiskCamera

class Teacher(Phase2Teacher):
    def __init__(self,cfg):
        goal=cfg["standoff_radius_m"]*np.asarray(cfg["goal_direction"])
        super().__init__({**cfg,"x_goal":float(goal[0])})
        self.goal=np.r_[goal,0.,0.]
        if cfg.get("teacher_cost_frame")=="approach_radial_tangential":
            er=np.asarray(cfg["goal_direction"]);et=np.array([-er[1],er[0]])
            basis=np.column_stack([er,et]);rotation=np.zeros((4,4))
            rotation[:2,:2]=basis;rotation[2:,2:]=basis
            self.Q=rotation@np.diag(cfg["Q_diag"])@rotation.T
            self.P=solve_discrete_are(self.Ad,self.Bd,self.Q,self.R)
            self.K=np.linalg.solve(self.R+self.Bd.T@self.P@self.Bd,self.Bd.T@self.P@self.Ad)
            self.eigenvalues=np.linalg.eigvals(self.Ad-self.Bd@self.K)
            if np.max(np.abs(self.eigenvalues))>=1:raise ValueError("Unstable teacher")
        np.testing.assert_allclose(self.A@self.goal+self.B@self.u_eq,0,atol=1e-14)

class Camera(DiskCamera):
    """Circular conservative envelope of the exact perspective sphere conic.

    In camera coordinates center=(lateral,0,depth). Horizontal tangent
    slopes are tan(beta +/- asin(R/d)). Their midpoint is the circle
    center, and half their separation its radius. The exact off-axis
    pinhole silhouette is an ellipse; its horizontal semiaxis is largest,
    so this circle contains it. On-axis this is exact: f R/sqrt(d*d-R*R).
    We intentionally use the requested circular silhouette, without
    pretending an off-axis perspective sphere is mathematically circular.
    """
    def __init__(self,cfg):
        super().__init__(cfg)
        self.bore=np.asarray(cfg["boresight"],dtype=float)
        if not np.isclose(np.linalg.norm(self.bore),1):raise ValueError("Nonunit boresight")
        self.right=np.array([-self.bore[1],self.bore[0]])
    def project(self,state):
        pos=np.asarray(state)[:2];rel=-pos
        depth=rel@self.bore;lateral=rel@self.right;d=np.linalg.norm(rel);R=self.cfg["target_radius_m"]
        if not np.isfinite(pos).all() or depth<=R or d<=R:
            return np.full(3,np.nan),False
        # Analytic horizontal tangent slopes; avoids the old f*R/depth disk.
        denom=depth*depth-R*R
        center=self.cu+self.f*lateral*depth/denom
        radius=self.f*R*np.sqrt(d*d-R*R)/denom
        p=np.array([center,self.cv,radius])
        visible=(center-radius>=-.5 and center+radius<=self.w-.5 and
                 self.cv-radius>=-.5 and self.cv+radius<=self.h-.5)
        return p,bool(visible)
