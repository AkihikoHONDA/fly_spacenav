"""Portable arrays; model indices are not FlyWire biological root IDs."""
from pathlib import Path
import hashlib
import json
import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def save_episode(path, *, images, receptor_input, input_time, response_time, activity, baseline, cell_index, cell_type, u, v, receptor_u, receptor_v, wall_seconds):
    arrays = dict(images=images, receptor_input=receptor_input, input_time=input_time,
                  response_time=response_time, activity=activity, baseline=baseline,
                  cell_index=cell_index, cell_type=cell_type, u=u, v=v,
                  receptor_u=receptor_u, receptor_v=receptor_v, wall_seconds=wall_seconds)
    n = len(input_time)
    c = len(cell_index)
    if n == 0 or any(np.asarray(a).shape != (c,) for a in (baseline, cell_type, u, v)):
        raise ValueError("Inconsistent cell metadata dimensions")
    if any(np.asarray(a).shape != (n,) for a in (input_time, response_time, wall_seconds)):
        raise ValueError("Inconsistent time dimensions")
    if receptor_input.ndim != 2 or any(np.asarray(a).shape != (receptor_input.shape[1],) for a in (receptor_u, receptor_v)):
        raise ValueError("Inconsistent receptor coordinates")
    if images.shape[0] != n or activity.shape != (n, len(cell_index)) or receptor_input.shape[0] != n:
        raise ValueError("Inconsistent frame/cell dimensions")
    if not np.array_equal(cell_index, np.arange(len(cell_index))):
        raise ValueError("Expected original contiguous model cell indices")
    if not np.all(np.diff(input_time) > 0) or not np.all(response_time > input_time):
        raise ValueError("Invalid input/response timestamps")
    for key, value in arrays.items():
        a = np.asarray(value)
        if a.dtype.kind == "O":
            raise ValueError(f"Object array prohibited: {key}")
        if a.dtype.kind in "fc" and not np.isfinite(a).all():
            raise ValueError(f"Nonfinite values: {key}")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
