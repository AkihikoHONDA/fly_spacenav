"""Freeze display scales using only control-period train/validation teachers."""
import json
from pathlib import Path
import numpy as np
from flyrendezvous.phase3_runtime import checked_trial
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.activity_display import TYPES,trial_equal_quantile
OUT=Path("outputs/phase3")
def main():
    if (OUT/"display_scales.json").exists():raise RuntimeError("Scales already frozen")
    if (OUT/"test_started.json").exists():raise RuntimeError("Test already started")
    episodes=json.loads((OUT/"data.json").read_text())["episodes"]
    raw=[[] for _ in TYPES];delta=[[] for _ in TYPES]
    for m in episodes:
        assert m["split"] in ("train","validation")
        d=checked_trial(m);mask=d["control_mask"]
        for j,name in enumerate(TYPES):
            idx=np.flatnonzero(d["all_types"]==name).item()
            raw[j].append(d["type_rms"][mask,idx])
            delta[j].append(np.abs(d["display_activity"][mask,j].astype(float)-d["baseline"][d["display_indices"][j]]))
    bounds=np.array([trial_equal_quantile(a,[.05,.95]) for a in raw])
    limits=np.array([trial_equal_quantile(a,[.99])[0] for a in delta])
    assert np.all(bounds[:,1]-bounds[:,0]>1e-8) and np.all(limits>0)
    write_json(OUT/"display_scales.json",dict(types=list(TYPES),p05=bounds[:,0].tolist(),p95=bounds[:,1].tolist(),
        signed_map_limit=limits.tolist(),calibration="30 train+validation teacher trials; equal weight per trial; control only",
        sources=[{k:m[k] for k in ["id","split","record","record_sha256"]} for m in episodes],
        test_used=False,immutable_before_test=True,config_sha256=sha256("configs/phase3.json")))
    print("Frozen non-test display scales",bounds,limits)
if __name__=="__main__":main()
