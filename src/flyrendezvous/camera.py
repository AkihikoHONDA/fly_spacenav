"""Fixed -x camera. Projection diagnostics never enter the learned policy."""
import numpy as np
class Camera:
    def __init__(self,cfg):
        self.cfg=cfg;self.h=cfg["height"];self.w=cfg["width"]
        self.f=(self.w-1)/2/np.tan(np.deg2rad(cfg["hfov_degrees"]/2))
        self.cu=(self.w-1)/2;self.cv=(self.h-1)/2
        self.ss=cfg["supersampling"]
        # Pixel centers are integer coordinates; fixed subpixel quadrature.
        self.xx=(np.arange(self.w*self.ss)+.5)/self.ss-.5
        self.yy=(np.arange(self.h*self.ss)+.5)/self.ss-.5
    def project(self,state):
        x,y=np.asarray(state)[:2]
        if not np.isfinite([x,y]).all() or x<=0:return np.array([np.nan,np.nan,np.nan]),False
        cu=self.cu-self.f*y/x;r=self.f*self.cfg["target_radius_m"]/x
        visible=(cu-r>=-.5 and cu+r<=self.w-.5 and self.cv-r>=-.5 and self.cv+r<=self.h-.5)
        return np.array([cu,self.cv,r]),bool(visible)
    def render(self,state):
        p,visible=self.project(state)
        if not visible:raise ValueError("Target outside camera field")
        cu,cv,r=p
        coverage=((self.xx[None,:]-cu)**2+(self.yy[:,None]-cv)**2<=r*r).reshape(self.h,self.ss,self.w,self.ss).mean((1,3))
        return (self.cfg["background"]+(self.cfg["foreground"]-self.cfg["background"])*coverage).astype(np.float32)
