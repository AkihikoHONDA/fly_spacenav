"""Post-hoc display screening of frozen records; never used by the policy."""
import numpy as np

def type_groups(cell_types):
    labels=np.asarray(cell_types)
    if labels.ndim!=1 or labels.dtype.kind not in "US":raise ValueError("Expected cell type labels")
    return {str(name):np.flatnonzero(labels==name) for name in sorted(set(labels))}

def type_response(activity,baseline,cell_types):
    a=np.asarray(activity,dtype=float);b=np.asarray(baseline,dtype=float)
    if a.ndim!=2 or b.shape!=(a.shape[1],) or len(cell_types)!=len(b) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Invalid full response or baseline")
    groups=type_groups(cell_types);mean=[];rms=[]
    for indices in groups.values():
        d=a[:,indices]-b[indices]
        mean.append(d.mean(1));rms.append(np.sqrt(np.mean(d*d,axis=1)))
    return np.array(list(groups)),np.array(mean).T,np.array(rms).T

def classify_stages(states,applied,control_mask,goal=10.,position_tol=.25,speed_tol=.01):
    s=np.asarray(states);u=np.asarray(applied);active=np.asarray(control_mask,dtype=bool)
    if s.shape!=(len(u),4) or u.shape!=(len(active),2) or not np.isfinite(s).all() or not np.isfinite(u).all():
        raise ValueError("Invalid stage inputs")
    error=np.linalg.norm(s[:,:2]-[goal,0],axis=1);speed=np.linalg.norm(s[:,2:],axis=1)
    stages=np.full(len(s),"other",dtype="U12")
    # Mutually exclusive priority: observation, near/hold, commanded radial braking,
    # approach from the high-x side, then other. No timestamp-based phase labels.
    approach=active&(s[:,0]>goal+position_tol)&(s[:,2]<0)
    braking=active&(s[:,0]>goal)&(s[:,2]<0)&(u[:,0]>0)
    near=active&(error<position_tol)&(speed<speed_tol)
    stages[approach]="approach";stages[braking]="braking";stages[near]="near_hold"
    stages[~active]="observation"
    return stages

def feature_types(pool):
    types=pool["cell_type"][pool["used_indices"]]
    assignment=pool["used_cell_feature_index"];counts=pool["feature_counts"]
    result=np.full(len(counts),"",dtype=pool["cell_type"].dtype)
    for i in range(len(counts)):
        labels=np.unique(types[assignment==i])
        if len(labels)!=1 or len(types[assignment==i])!=counts[i]:
            raise ValueError("Ambiguous or empty feature group")
        result[i]=labels[0]
    return result

def contributions(phi,model,feature_labels,all_types,a_max):
    """c[t,type,axis], plus separate intercept. Before clipping; no causality claim."""
    phi=np.asarray(phi,dtype=float);labels=np.asarray(feature_labels)
    if model.lag!=0:raise ValueError("This audit targets the frozen Phase 2 current-only readout")
    if phi.ndim!=2 or phi.shape[1]!=len(labels) or model.mean.shape!=(len(labels),) or not np.isfinite(phi).all():
        raise ValueError("Feature metadata mismatch")
    z=(phi[:,model.keep]-model.mean[model.keep])/model.std[model.keep]
    kept_labels=labels[model.keep]
    c=np.zeros((len(phi),len(all_types),2))
    for j,name in enumerate(all_types):
        columns=np.flatnonzero(kept_labels==name)
        if len(columns):c[:,j]=a_max*(z[:,columns]@model.W[:,columns].T)
    bias=a_max*model.b
    np.testing.assert_allclose(c.sum(1)+bias,a_max*model.predict(phi),atol=1e-12,rtol=1e-12)
    return c,bias

def robust_range(values,axis=0):
    return np.quantile(values,.95,axis=axis)-np.quantile(values,.05,axis=axis)

def assert_unchanged(manifest):
    from .recording import sha256
    changed=[p for p,digest in manifest.items() if sha256(p)!=digest]
    if changed:raise ValueError("Protected files changed: "+", ".join(changed))
    return len(manifest)
