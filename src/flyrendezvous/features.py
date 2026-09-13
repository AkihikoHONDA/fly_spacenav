"""Fixed artificial spatial pooling, excluding all role=input nodes."""
from collections import deque
import numpy as np
from .viewer import lattice_xy

class Pooling:
    def __init__(self,nodes,bins=4):
        self.types=np.array(sorted(nodes["type"].astype(str).unique()),dtype="U")
        self.cell_type=nodes["type"].astype(str).to_numpy(dtype="U")
        self.cell_index=nodes["index"].to_numpy(dtype=np.int64)
        self.roles=nodes["role"].astype(str).to_numpy(dtype="U")
        self.xy=lattice_xy(nodes["u"].to_numpy(),nodes["v"].to_numpy()).astype(float)
        self.used=np.flatnonzero(self.roles!="input")
        self.excluded=np.flatnonzero(self.roles=="input")
        self.used_types=np.array(sorted(set(self.cell_type[self.used])),dtype="U")
        self.boundaries=[np.linspace(self.xy[:,axis].min(),self.xy[:,axis].max(),bins+1) for axis in range(2)]
        coords=[np.clip(np.searchsorted(b[1:-1],self.xy[:,i],side="right"),0,bins-1) for i,b in enumerate(self.boundaries)]
        type_lookup={name:i for i,name in enumerate(self.used_types)}
        self.assignment=np.array([type_lookup[self.cell_type[j]]*bins*bins+coords[1][j]*bins+coords[0][j] for j in self.used])
        self.dimension=len(self.used_types)*bins*bins
        self.counts=np.bincount(self.assignment,minlength=self.dimension)
        self.type_assignment=np.searchsorted(self.types,self.cell_type)
        self.type_counts=np.bincount(self.type_assignment,minlength=len(self.types))
    def extract(self,activity,baseline):
        delta=np.asarray(activity,dtype=float)-baseline
        if delta.shape!=(len(self.cell_type),) or not np.isfinite(delta).all():raise ValueError("Invalid neural response")
        sums=np.bincount(self.assignment,weights=delta[self.used],minlength=self.dimension)
        return np.divide(sums,self.counts,out=np.zeros_like(sums),where=self.counts>0)
    def summaries(self,activity,baseline):
        delta=np.asarray(activity,dtype=float)-baseline
        mean=np.bincount(self.type_assignment,weights=delta,minlength=len(self.types))/self.type_counts
        rms=np.sqrt(np.bincount(self.type_assignment,weights=delta*delta,minlength=len(self.types))/self.type_counts)
        return mean,rms
    def save(self,path):
        np.savez_compressed(path,cell_index=self.cell_index,cell_type=self.cell_type,role=self.roles,
            used_indices=self.used,excluded_indices=self.excluded,used_types=self.used_types,
            all_types=self.types,xy=self.xy,boundaries=np.array(self.boundaries),
            used_cell_feature_index=self.assignment,feature_counts=self.counts,
            empty_feature_indices=np.flatnonzero(self.counts==0))

class History:
    def __init__(self,lag):self.lag=int(lag);self.values=deque(maxlen=self.lag+1)
    def append(self,phi):
        self.values.append(np.asarray(phi).copy())
        if not self.lag:return self.values[-1]
        if len(self.values)<=self.lag:return None
        return np.concatenate([self.values[-1],self.values[0]])

def history_matrix(phi,lag):
    if not lag:return np.asarray(phi).copy()
    x=np.full((len(phi),2*phi.shape[1]),np.nan)
    x[lag:]=np.concatenate([phi[lag:],phi[:-lag]],axis=1)
    return x
