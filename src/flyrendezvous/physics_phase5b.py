"""2D equatorial ECI truth dynamics. No policy or learned state inputs here."""
import numpy as np
def quarter(v):return np.array([-v[1],v[0]])
def basis(r,v):
    er=r/np.linalg.norm(r)
    return np.column_stack((er,quarter(er))),float((r[0]*v[1]-r[1]*v[0])/np.dot(r,r))
def to_inertial(relative,chief):
    r,v=np.asarray(chief).reshape(2,2);B,w=basis(r,v);dr=B@relative[:2]
    return np.r_[r,v,r+dr,v+B@relative[2:]+w*quarter(dr)]
def to_relative(y):
    r,v,rc,vc=np.asarray(y).reshape(4,2);B,w=basis(r,v);dr=rc-r
    return np.r_[B.T@dr,B.T@(vc-v-w*quarter(dr))]
def chief_initial(cfg):
    r=cfg['chief_radius_m'];return np.array([r,0,0,cfg['n']*r])
def two_body(r,cfg):return -cfg['mu_E']*r/np.linalg.norm(r)**3
def j2_general(r,mu,R,J2):
    r=np.asarray(r);radius=np.linalg.norm(r);z2=(r[2]/radius)**2
    return 1.5*J2*mu*R**2/radius**5*r*np.array([5*z2-1,5*z2-1,5*z2-3])
def j2(r,cfg):return j2_general(np.r_[r,0.],cfg['mu_E'],cfg['R_E'],cfg['J2'])[:2]
def shadow(r,cfg):
    sun=np.asarray(cfg['sun_direction_ECI']);along=float(r@sun)
    return bool(along<0 and np.linalg.norm(r-along*sun)<cfg['R_E'])
def srp(r,prop,cfg):
    if cfg['cylindrical_shadow'] and shadow(r,cfg):return np.zeros(2)
    return -cfg['P_srp']*prop['C_R']*prop['A_srp']/prop['mass']*np.asarray(cfg['sun_direction_ECI'])
def drag(r,v,prop,rho,cfg):
    rel=v-cfg['omega_E']*quarter(r)
    return -.5*rho*prop['C_D']*prop['A_drag']/prop['mass']*np.linalg.norm(rel)*rel
def residual(t,condition,cfg):
    on=not condition['midcourse'] or cfg['residual_on_s']<=t<cfg['residual_off_s']
    return condition['residual_m_s2']*np.asarray(cfg['residual_direction_ECI']) if on else np.zeros(2)
def forces(t,y,u,condition,cfg,residual_override=None):
    r,v,rc,vc=np.asarray(y).reshape(4,2);B,_=basis(r,v)
    result={}
    for name,rr,vv in [('target',r,v),('chaser',rc,vc)]:
        p=cfg[name];result[name]=dict(two_body=two_body(rr,cfg),
            j2=j2(rr,cfg) if condition['j2'] else np.zeros(2),
            srp=srp(rr,p,cfg) if condition['srp'] else np.zeros(2),
            drag=drag(rr,vv,p,condition['density_kg_m3'],cfg),
            residual=np.zeros(2) if name=='target' else residual(t,condition,cfg) if residual_override is None else residual_override,
            control=np.zeros(2) if name=='target' else B@u)
    return result
def rhs(t,y,u,condition,cfg,residual_override=None):
    f=forces(t,y,u,condition,cfg,residual_override)
    return np.r_[y[2:4],sum(f['target'].values()),y[6:8],sum(f['chaser'].values())]
def advance(t,y,u,condition,cfg):
    dt=cfg['dt_phys'];steps=cfg['substeps'];h=dt/steps
    # Split at known discontinuities. Every RK stage uses the same side of an
    # interval boundary, so [120,180) receives exactly 60 seconds of forcing.
    boundaries=[t]+[x for x in [cfg['residual_on_s'],cfg['residual_off_s']] if t<x<t+dt]+[t+dt]
    y=y.copy()
    for lo,hi in zip(boundaries[:-1],boundaries[1:]):
        count=int(np.ceil((hi-lo)/h));hh=(hi-lo)/count
        res=residual((lo+hi)/2,condition,cfg)
        for k in range(count):
            tt=lo+k*hh
            f=lambda time,state:rhs(time,state,u,condition,cfg,res)
            a=f(tt,y);b=f(tt+hh/2,y+hh*a/2);c=f(tt+hh/2,y+hh*b/2);d=f(tt+hh,y+hh*c)
            y=y+hh*(a+2*b+2*c+d)/6
    return y
