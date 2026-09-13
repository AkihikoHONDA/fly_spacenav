"""Ridge on train-only standardized neural features; no simulator access."""
from pathlib import Path
import numpy as np
from scipy.linalg import solve
from .features import History

class Readout:
    def __init__(self,mean,std,keep,W,b,lag,regularization):
        self.mean=mean;self.std=std;self.keep=keep;self.W=W;self.b=b
        self.lag=int(lag);self.regularization=float(regularization)
    @classmethod
    def fit(cls,X,Y,lag,regularization,threshold=1e-8):
        if not np.isfinite(X).all() or not np.isfinite(Y).all():raise ValueError("Nonfinite regression data")
        mean=X.mean(0);std=X.std(0);keep=std>threshold
        if not keep.any():raise ValueError("No varying neural features")
        z=(X[:,keep]-mean[keep])/std[keep];b=Y.mean(0)
        # Objective sum_outputs(mean_samples(error^2)) + lambda*||W||_F^2.
        gram=z.T@z/len(z);rhs=z.T@(Y-b)/len(z)
        gram.flat[::len(gram)+1]+=regularization
        W=solve(gram,rhs,assume_a="pos").T
        return cls(mean,std,keep,W,b,lag,regularization)
    def predict(self,x):
        a=np.asarray(x)
        if not np.isfinite(a).all():raise ValueError("Nonfinite features")
        return ((a[...,self.keep]-self.mean[self.keep])/self.std[self.keep])@self.W.T+self.b
    def save(self,path):
        np.savez_compressed(path,mean=self.mean,std=self.std,keep=self.keep,W=self.W,b=self.b,
            lag=self.lag,regularization=self.regularization)
    @classmethod
    def load(cls,path):
        with np.load(path,allow_pickle=False) as z:return cls(**{k:z[k] for k in z.files})

class ImagePolicy:
    """step receives ONLY an image; no state, time, labels or simulator closure."""
    def __init__(self,adapter,pooling,readout,a_max):
        self.adapter=adapter;self.pooling=pooling;self.readout=readout;self.a_max=a_max
    def reset(self):
        self.baseline=self.adapter.reset()
        self.history=History(self.readout.lag)
    def step(self,image):
        activity,receptors=self.adapter.chunk(np.asarray(image)[None])
        activity=activity[0];receptors=receptors[0]
        phi=self.pooling.extract(activity,self.baseline)
        x=self.history.append(phi)
        prediction=None if x is None else self.readout.predict(x)
        raw=np.zeros(2) if prediction is None else self.a_max*prediction
        applied=np.clip(raw,-self.a_max,self.a_max)
        return raw,applied,dict(phi=phi,activity=activity,receptors=receptors)
