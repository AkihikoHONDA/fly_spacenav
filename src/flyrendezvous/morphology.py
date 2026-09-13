"""Read the published skeleton graph without generating or repairing branches."""
from collections import deque
from pathlib import Path
import struct
import numpy as np

def validate_tree(xyz, edges, radii):
    xyz, edges, radii = np.asarray(xyz), np.asarray(edges), np.asarray(radii)
    n = len(xyz)
    if n < 2 or xyz.shape != (n, 3) or radii.shape != (n,):
        raise ValueError("Invalid skeleton coordinate/radius dimensions")
    if not np.isfinite(xyz).all() or not np.isfinite(radii).all() or np.any(radii < 0):
        raise ValueError("Nonfinite coordinates or invalid radii")
    if edges.ndim != 2 or edges.shape[1] != 2 or edges.dtype.kind not in "iu":
        raise ValueError("Invalid edge array")
    if len(edges) != n-1 or np.any(edges < 0) or np.any(edges >= n):
        raise ValueError("Missing/invalid parent endpoint or non-tree edge count")
    adjacent = [[] for _ in range(n)]
    for a, b in edges:
        if a == b:
            raise ValueError("Self connection")
        adjacent[a].append(int(b)); adjacent[b].append(int(a))
    parent = np.full(n, -2, dtype=np.int64)
    parent[0] = -1
    queue = deque([0])
    while queue:
        a = queue.popleft()
        for b in adjacent[a]:
            if b == parent[a]:
                continue
            if parent[b] != -2:
                raise ValueError("Duplicate connection or cycle")
            parent[b] = a
            queue.append(b)
    if np.any(parent == -2):
        raise ValueError("Disconnected skeleton")
    return parent

def read_precomputed(path):
    raw = Path(path).read_bytes()
    if len(raw) < 8:
        raise ValueError("Truncated skeleton header")
    n, e = struct.unpack("<II", raw[:8])
    # Verified publisher info: float32 XYZ and radius, uint32 edge endpoints.
    if len(raw) != 8 + 16*n + 8*e:
        raise ValueError("Truncated or unexpected skeleton attributes")
    xyz = np.frombuffer(raw, dtype="<f4", count=3*n, offset=8).reshape(n,3).copy()
    edges = np.frombuffer(raw, dtype="<u4", count=2*e, offset=8+12*n).reshape(e,2).astype(np.int64)
    radii = np.frombuffer(raw, dtype="<f4", count=n, offset=8+12*n+8*e).copy()
    validate_tree(xyz, edges, radii)
    return xyz, edges, radii

def write_swc(path, xyz_nm, edges, radius_nm):
    parent = validate_tree(xyz_nm, edges, radius_nm)
    with Path(path).open("w") as f:
        f.write("# Published FlyWire 783 skeleton. XYZ and radius converted nm -> um.\n")
        f.write("# Node 1 is an arbitrary graph root, NOT an identified soma. Type 0 = unspecified.\n")
        for i, (xyz, radius, p) in enumerate(zip(xyz_nm*.001, radius_nm*.001, parent)):
            f.write(f"{i+1} 0 {xyz[0]:.9g} {xyz[1]:.9g} {xyz[2]:.9g} {radius:.9g} {p+1 if p>=0 else -1}\n")

def read_swc(path):
    a = np.loadtxt(path, comments="#", ndmin=2)
    if a.ndim != 2 or a.shape[1] != 7 or not np.isfinite(a).all():
        raise ValueError("Invalid SWC rows")
    if not np.equal(a[:,[0,1,6]], np.floor(a[:,[0,1,6]])).all():
        raise ValueError("Non-integer SWC ID")
    ids = a[:,0].astype(np.int64)
    parents = a[:,6].astype(np.int64)
    if len(set(ids)) != len(ids) or np.any(ids<=0) or (parents==-1).sum()!=1:
        raise ValueError("Duplicate SWC ID or invalid root count")
    lookup = {x:i for i,x in enumerate(ids)}
    edges=[]
    for i,p in enumerate(parents):
        if p==-1: continue
        if p not in lookup: raise ValueError("Missing parent ID")
        edges.append([i, lookup[p]])
    edges=np.asarray(edges,dtype=np.int64).reshape(-1,2)
    validate_tree(a[:,2:5],edges,a[:,5])
    return a[:,2:5],edges,a[:,5]
