"""LVLH x radial outward, y along-track; SI units and ZOH dynamics."""
import numpy as np
from scipy.signal import cont2discrete
from scipy.linalg import solve_discrete_are

def matrices(n,dt):
    if not np.isfinite([n,dt]).all() or n<0 or dt<=0:raise ValueError("Invalid n or dt")
    A=np.array([[0,0,1,0],[0,0,0,1],[3*n*n,0,0,2*n],[0,0,-2*n,0]],dtype=float)
    B=np.array([[0,0],[0,0],[1,0],[0,1]],dtype=float)
    Ad,Bd,_,_,_=cont2discrete((A,B,np.eye(4),np.zeros((4,2))),dt,method="zoh")
    return A,B,Ad,Bd

class Teacher:
    def __init__(self,cfg):
        self.A,self.B,self.Ad,self.Bd=matrices(cfg["n"],cfg["dt_phys"])
        self.goal=np.array([cfg["x_goal"],0,0,0.])
        self.u_eq=np.array([-3*cfg["n"]**2*cfg["x_goal"],0.])
        self.limit=cfg["a_max"]
        self.Q=np.diag(cfg["Q_diag"]);self.R=np.diag(cfg["R_diag"])
        self.P=solve_discrete_are(self.Ad,self.Bd,self.Q,self.R)
        self.K=np.linalg.solve(self.R+self.Bd.T@self.P@self.Bd,self.Bd.T@self.P@self.Ad)
        self.eigenvalues=np.linalg.eigvals(self.Ad-self.Bd@self.K)
        if np.max(np.abs(self.eigenvalues))>=1:raise ValueError("Unstable unsaturated LQR")
        np.testing.assert_allclose(self.A@self.goal+self.B@self.u_eq,0,atol=1e-14)
    def command(self,state):
        raw=self.u_eq-self.K@(np.asarray(state)-self.goal)
        return raw,np.clip(raw,-self.limit,self.limit)
    def advance(self,state,applied):
        if not np.isfinite(state).all() or not np.isfinite(applied).all():raise ValueError("Nonfinite dynamics input")
        if np.any(np.abs(applied)>self.limit+1e-12):raise ValueError("Unsaturated acceleration")
        return self.Ad@state+self.Bd@applied
    def metadata(self):
        return {key:getattr(self,key).tolist() for key in ["A","B","Ad","Bd","goal","u_eq","Q","R","P","K"]}|{
            "closed_loop_eigenvalues_real":self.eigenvalues.real.tolist(),
            "closed_loop_eigenvalues_imag":self.eigenvalues.imag.tolist(),
            "spectral_radius":float(np.max(np.abs(self.eigenvalues))),
            "method":"discrete DARE; componentwise clipped feedback, not constrained optimum"}
