"""Fetch one typed published skeleton, preserving provenance and topology."""
from pathlib import Path
import csv
import hashlib
import json
import urllib.request
import numpy as np
from flyrendezvous.morphology import read_precomputed, write_swc, read_swc
from flyrendezvous.recording import sha256, write_json

ROOT=Path(__file__).resolve().parents[1]
COMMIT="8587524c1748ce5ef2080822a2fc890fc03bf597"
ROOT_ID="720575940605852192"
SKELETON_SHA="636df53b81276202a6209a128f5e7636141e14cd44eb094c3f9fff9402877858"
BASE="https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783"

def fetch(url,path,expected=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url,timeout=30) as r: data=r.read()
        if expected and hashlib.sha256(data).hexdigest()!=expected: raise ValueError("Download checksum mismatch")
        path.write_bytes(data)
    if expected and sha256(path)!=expected: raise ValueError("Cached asset checksum mismatch")

def main():
    root=ROOT/"assets/phase1b"; sources=root/"sources"
    table_url=f"https://raw.githubusercontent.com/flyconnectome/flywire_annotations/{COMMIT}/supplemental_files/Supplemental_file1_neuron_annotations.tsv"
    table=sources/"annotations.tsv"
    fetch(table_url,table,"9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be")
    with table.open() as f:
        rows=csv.DictReader(f,delimiter="\t")
        annotation=next(r for r in rows if r["root_id"]==ROOT_ID)
    if annotation["cell_type"]!="T4a" or annotation["side"]!="right":
        raise ValueError("Selected official type or side changed")
    binary=root/(ROOT_ID+".precomputed")
    fetch(BASE+"/"+ROOT_ID,binary,SKELETON_SHA)
    fetch(BASE+"/info",sources/"skeleton-info.json")
    info=json.loads((sources/"skeleton-info.json").read_text())
    if info["transform"]!=[1,0,0,0,0,1,0,0,0,0,1,0]:
        raise ValueError("Unexpected source transform; do not guess a registration")
    xyz,edges,radius=read_precomputed(binary)
    swc=root/(ROOT_ID+".swc")
    write_swc(swc,xyz.astype(float),edges,radius.astype(float))
    sx,se,sr=read_swc(swc)
    np.testing.assert_allclose(sx,xyz.astype(float)*.001,atol=1e-6,rtol=0)
    if {tuple(sorted(e)) for e in edges}!={tuple(sorted(e)) for e in se}:
        raise ValueError("SWC export changed published connections")
    write_json(sources/"selected_annotation.json",annotation)
    manifest={
        "model_cell_type":"T4a","morphology_cell_type":annotation["cell_type"],
        "morphology_id":ROOT_ID,"one_to_one_model_cell_mapping":False,
        "model_hemisphere_assigned":False,"morphology_side":annotation["side"],
        "mapping_granularity":"same-type representative morphology; not individual cells or branch voltages",
        "selection":"first exact T4a row encountered in pinned official table; one morphology, no aggregation or duplication",
        "dataset":"FlyWire female FAFB, materialization 783",
        "annotation":{"url":table_url,"commit":COMMIT,"row":annotation,"sha256":sha256(table)},
        "morphology":{"url":BASE+"/"+ROOT_ID,"format":"Neuroglancer precomputed skeleton graph",
                      "sha256":sha256(binary),"bytes":binary.stat().st_size,"vertices":len(xyz),"edges":len(edges),
                      "source_units":"nm","coordinate_system":"FlyWire FAFB14.1",
                      "display_transform":"nm to um by 0.001 for both geometry and background; no other geometry transform",
                      "bounds_nm":[xyz.min(0).tolist(),xyz.max(0).tolist()],
                      "source_kind":"published skeleton extracted from measured EM reconstruction, not a simulated arbor",
                      "swc_export":"same edges and coordinates; um units; arbitrary graph root, no soma/branch typing inferred"},
        "type_evidence":["Flyvis 1.2.0 fib25-fib19_v2.2.json exact node name T4a",
                         table_url+" exact cell_type=T4a; not inferred from T4"],
        "coordinate_evidence":["https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_skeletons.html",
                               "https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_neuropil_volumes.html",
                               BASE+"/info"],
        "terms":{"flywire":"CC-BY-NC 4.0 for edits/annotations in https://flywire.ai/tos",
                 "schlegel_supplement":"CC-BY-4.0 at https://zenodo.org/records/10877326 (related bulk skeleton release, not downloaded)",
                 "endpoint":"No separate license field in individual endpoint info. Keep upstream attribution and noncommercial restriction; do not infer broader redistribution permission.",
                 "attribution":"FlyWire Consortium; Dorkenwald et al. 2024; Schlegel et al. 2024; Matsliah et al. 2024. JFRC2 background: Jenett et al.; fafbseg."},
        "acquisition_routes":[{"route":"FlyWire annotation repository + fafbseg-documented individual skeleton server",
                               "type_annotation":"T4a and Mi1 both exact labels found; T4a selected",
                               "reachability":"HTTP 200, one 19896-byte skeleton",
                               "coordinate_match":"FAFB14.1 nm, matching existing background",
                               "decision":"adopt T4a; Mi1 morphology not fetched"},
                              {"route":"Independent second acquisition route","decision":"not needed after first route succeeded"}],
        "aggregation":"sqrt(mean((activity_i(t)-baseline_i)^2)) over cell_type == T4a; model units; response-change magnitude",
    }
    manifest["files"]={p.relative_to(ROOT).as_posix():{"sha256":sha256(p),"bytes":p.stat().st_size} for p in [binary,swc,sources/"skeleton-info.json",sources/"selected_annotation.json"]}
    write_json(ROOT/"docs/anatomy_mapping_phase1b.json",manifest)
    print("Verified one T4a morphology:",ROOT_ID,len(xyz),"vertices",len(edges),"edges; SWC roundtrip preserves topology")

if __name__=="__main__": main()
