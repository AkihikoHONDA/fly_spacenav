"""All measured T2 geometry with explicit root-to-concatenated-array provenance."""
import json,csv
from pathlib import Path
import numpy as np
from .recording import sha256,write_json
from .morphology import read_precomputed
def exact_right_t2(rows):
    return [r for r in rows if r.get("cell_type")=="T2" and r.get("side")=="right"]
def load_population():
    m=json.loads(Path("docs/anatomy_mapping_phase3p.json").read_text())
    assert m["coordinate_system"]=="FAFB14.1" and m["source_units"]=="nm" and m["materialization"]==783
    assert sha256(m["annotation"]["cache"])==m["annotation"]["sha256"]
    with open(m["annotation"]["cache"]) as f:rows=exact_right_t2(csv.DictReader(f,delimiter="\t"))
    byid={r["root_id"]:r for r in rows}
    assert len(byid)==len(rows)==m["count"] and set(byid)=={a["root_id"] for a in m["morphologies"]}
    vertices=[];edges=[];provenance=[];nv=ne=0
    for a in m["morphologies"]:
        assert a["annotation_row"]==byid[a["root_id"]] and a["side"]=="right"
        assert sha256(a["path"])==a["sha256"]
        xyz,e,_=read_precomputed(a["path"])
        assert len(xyz)==a["vertices"] and len(e)==a["edges"]
        vertices.append(xyz.astype(float)*.001);edges.append(e+nv)
        provenance.append(dict(root_id=a["root_id"],vertex_start=nv,vertex_stop=nv+len(xyz),
            edge_start=ne,edge_stop=ne+len(e),source=a["path"],sha256=a["sha256"]))
        nv+=len(xyz);ne+=len(e)
    return np.concatenate(vertices),np.concatenate(edges),provenance
