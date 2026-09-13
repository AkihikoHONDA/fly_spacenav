"""Fixed, display-only calibration from immutable recorded responses."""
import numpy as np

TYPES=("T2","Tm3","T4a","T5d","L2")
MIN_RANGE=1e-8

def select_types(labels,requested=TYPES):
    labels=np.asarray(labels)
    if labels.ndim!=1 or len(set(requested))!=len(requested):raise ValueError("Invalid type selection")
    result=[]
    for name in requested:
        indices=np.flatnonzero(labels==name)
        if not len(indices):raise ValueError("Missing cell type: "+name)
        result.append(indices)
    return result

def trial_equal_quantile(trials,quantiles):
    """Inverse empirical mixture CDF; every trial has total mass 1/n_trials."""
    qs=np.asarray(quantiles,dtype=float)
    if not len(trials) or not np.isfinite(qs).all() or np.any((qs<0)|(qs>1)):raise ValueError("Invalid quantiles")
    values=[];weights=[]
    for trial in trials:
        a=np.asarray(trial,dtype=float).reshape(-1)
        if not len(a) or not np.isfinite(a).all():raise ValueError("Empty or nonfinite calibration trial")
        values.append(a);weights.append(np.full(len(a),1./len(a)))
    v=np.concatenate(values);w=np.concatenate(weights);order=np.argsort(v,kind="stable")
    v=v[order];w=w[order]
    cdf=np.cumsum(w);cdf/=cdf[-1];cdf[-1]=1.
    return v[np.minimum(np.searchsorted(cdf,qs,side="left"),len(v)-1)]

def relative_activity(rms,lo,hi,min_range=MIN_RANGE):
    a=np.asarray(rms,dtype=float);lo=np.asarray(lo,dtype=float);hi=np.asarray(hi,dtype=float)
    if not np.isfinite(a).all() or np.any(a<0) or not np.isfinite(lo).all() or not np.isfinite(hi).all() or np.any(hi<lo) or min_range<=0:
        raise ValueError("Invalid fixed relative scale")
    span=hi-lo;valid=span>min_range
    # Degenerate scales show neutral mid-bar and must be labelled unavailable.
    q=np.clip((a-lo)/np.where(valid,span,1.),0,1)
    return np.where(valid,q,.5)

def check_timing(d):
    n=len(d["sample_id"])
    np.testing.assert_array_equal(d["sample_id"],np.arange(n))
    np.testing.assert_allclose(d["observation_time"],np.arange(n)*.5,atol=1e-12,rtol=0)
    np.testing.assert_allclose(d["neural_input_time"],np.arange(n)*.01,atol=1e-12,rtol=0)
    np.testing.assert_allclose(d["neural_response_time"],(np.arange(n)+1)*.01,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(d["control_mask"],np.arange(n)>=20)
    assert len(d["states"])==n+1

def map_metrics(delta,limit,mask,dt=.5):
    d=np.asarray(delta,dtype=float);mask=np.asarray(mask,dtype=bool)
    if d.ndim!=2 or len(d)!=len(mask) or not np.isfinite(d).all() or not np.isfinite(limit) or limit<=0:
        raise ValueError("Invalid signed map")
    normalized=np.clip(d/limit,-1,1)
    # Remove each frame's spatial mean to distinguish pattern from uniform shifts.
    centered=d-d.mean(1,keepdims=True)
    pairs=mask[:-1]&mask[1:]
    raw_change=np.sqrt(np.mean(np.diff(d,axis=0)**2,axis=1))/dt
    centered_change=np.sqrt(np.mean(np.diff(centered,axis=0)**2,axis=1))/dt
    visible_change=np.sqrt(np.mean(np.diff(normalized,axis=0)**2,axis=1))/dt
    return dict(spatial_std_median=float(np.median(d[mask].std(1))),
        frame_change_rms_per_phys_s_median=float(np.median(raw_change[pairs])),
        frame_change_rms_per_phys_s_p95=float(np.quantile(raw_change[pairs],.95)),
        centered_pattern_change_per_phys_s_median=float(np.median(centered_change[pairs])),
        centered_pattern_change_per_phys_s_p95=float(np.quantile(centered_change[pairs],.95)),
        normalized_map_change_per_phys_s_median=float(np.median(visible_change[pairs])),
        normalized_map_change_per_phys_s_p95=float(np.quantile(visible_change[pairs],.95)),
        clipped_fraction=float(np.mean(np.abs(d[mask])>limit)))
