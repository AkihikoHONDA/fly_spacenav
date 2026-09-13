"""Measured representative geometry and display-only, fixed type color scales."""
import json
from pathlib import Path
import numpy as np
from .recording import sha256
from .morphology import read_precomputed
TYPES3=("T2","T4a","T5d")
PALETTE={"T2":[255,166,65],"T4a":[80,175,255],"T5d":[245,100,225]}
def intensity_color(name,q):
    if name not in PALETTE:raise ValueError("Unsupported representative type")
    q=np.asarray(q,dtype=float)
    if not np.isfinite(q).all():raise ValueError("Nonfinite q")
    return np.rint(np.asarray(PALETTE[name])*(.35+.65*np.clip(q,0,1)[...,None])).astype(np.uint8)
def load_representatives():
    m=json.loads(Path("docs/anatomy_mapping_phase3v.json").read_text())
    assert m["coordinate_system"]=="FAFB14.1" and m["source_units"]=="nm"
    result={}
    for name in TYPES3:
        a=m["morphologies"][name]
        assert a["annotation_row"]["cell_type"]==name and a["side"]=="right"
        assert sha256(a["path"])==a["sha256"]
        xyz,edges,radii=read_precomputed(a["path"])
        result[name]=(xyz.astype(float)*.001,edges)
    return result
