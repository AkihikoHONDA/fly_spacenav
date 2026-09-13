"""Display-only type aggregation. Never used as a control feature."""
from pathlib import Path
import json
import numpy as np
from .recording import sha256

def checked_episode(path, validation_path):
    path=Path(path)
    validation=json.loads(Path(validation_path).read_text())
    if validation.get("status")!="passed":
        raise ValueError("Source validation incomplete")
    if validation["parameter_sha256_before"] != validation["parameter_sha256_after"]:
        raise ValueError("Source model parameters changed")
    expected=validation["record_sha256"].get(path.name)
    if expected is None or sha256(path)!=expected:
        raise ValueError("Source recording hash mismatch")
    with np.load(path,allow_pickle=False) as z:
        return {k:z[k] for k in z.files}

def response_rms(data, cell_type, dt):
    activity=np.asarray(data["activity"])
    base=np.asarray(data["baseline"])
    types=np.asarray(data["cell_type"])
    time=np.asarray(data["input_time"]); end=np.asarray(data["response_time"])
    if activity.ndim!=2 or activity.shape[0]==0:
        raise ValueError("Invalid activity dimensions")
    n,c=activity.shape
    if base.shape!=(c,) or types.shape!=(c,) or time.shape!=(n,) or end.shape!=(n,):
        raise ValueError("Activity, baseline, type or time length mismatch")
    if not np.isfinite(dt) or dt<=0:
        raise ValueError("Invalid dt")
    for a in (activity,base,time,end):
        if not np.isfinite(a).all(): raise ValueError("Nonfinite response or timestamp")
    if not np.allclose(end-time,dt,rtol=0,atol=1e-9) or not np.allclose(time,np.arange(n)*dt,rtol=0,atol=1e-9):
        raise ValueError("Inconsistent input/response time")
    for name in ("images","receptor_input","wall_seconds"):
        if np.asarray(data[name]).shape[0]!=n: raise ValueError("Frame length mismatch")
    for name in ("cell_index","u","v"):
        if np.asarray(data[name]).shape!=(c,): raise ValueError("Cell metadata length mismatch")
    if not np.array_equal(data["cell_index"],np.arange(c)):
        raise ValueError("Original model indices required")
    selected=np.flatnonzero(types==cell_type)
    if len(selected)==0: raise ValueError(f"Cell type not found: {cell_type}")
    # float64 avoids overflow/roundoff in squaring float32 recordings.
    delta=activity[:,selected].astype(np.float64)-base[selected].astype(np.float64)
    rms=np.linalg.norm(delta,axis=1)/np.sqrt(len(selected))
    if not np.isfinite(rms).all(): raise ValueError("Nonfinite RMS")
    return selected,delta,rms

def rms_colors(values, upper):
    values=np.asarray(values,dtype=np.float64)
    if not np.isfinite(upper) or upper<=0 or not np.isfinite(values).all() or np.any(values<0):
        raise ValueError("RMS and fixed upper bound must be finite and nonnegative")
    alpha=np.clip(values/upper,0,1)
    # Distinct from the signed blue-white-red lattice legend.
    low=np.array([70.,110.,160.]); high=np.array([255.,205.,65.])
    return np.rint(low+alpha[...,None]*(high-low)).astype(np.uint8)
