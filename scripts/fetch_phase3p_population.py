"""Acquire every pinned exact right T2, retaining unmodified source geometry."""
import json,time,urllib.request,concurrent.futures
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.morphology import read_precomputed
BASE="https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783"
OUT=Path("outputs/phase3p");ASSETS=Path("assets/phase3p")
def main():
    enumeration=json.loads((OUT/"enumeration_before_download.json").read_text())
    old=json.loads(Path("docs/anatomy_mapping_phase3v.json").read_text())
    assert enumeration["count"]==enumeration["unique_count"]==725
    assert sha256(enumeration["annotation"]["cache"])==enumeration["annotation"]["sha256"]
    manifest=Path("docs/anatomy_mapping_phase3p.json")
    if manifest.exists():
        m=json.loads(manifest.read_text())
        for a in m["morphologies"]:assert sha256(a["path"])==a["sha256"]
        print("All existing population sources verified; no download");return
    ASSETS.mkdir(exist_ok=True)
    with urllib.request.urlopen(BASE+"/info",timeout=45) as r:info=r.read(100000)
    assert json.loads(info)==json.loads(Path("assets/phase3v/sources/info.json").read_text())
    (ASSETS/"info.json").write_bytes(info)
    rows=enumeration["rows"];success=[];failures=[];started=time.time()
    def get(row):
        root=row["root_id"];path=ASSETS/(root+".precomputed")
        reused=root==old["morphologies"]["T2"]["root_id"]
        if reused:
            original=old["morphologies"]["T2"];assert sha256(original["path"])==original["sha256"]
            path.write_bytes(Path(original["path"]).read_bytes())
        elif not path.exists():
            with urllib.request.urlopen(BASE+"/"+root,timeout=45) as r:
                assert r.status==200;data=r.read(2_000_001)
            if len(data)>2_000_000:raise ValueError("Unexpected individual size; stop")
            path.write_bytes(data)
        xyz,edges,radii=read_precomputed(path)
        # Broad source-frame guard, not an anatomical cell-selection rule.
        if not ((xyz>=0).all() and (xyz<2_000_000).all()):raise ValueError("Coordinate-frame anomaly")
        return dict(root_id=root,annotation_row=row,side=row["side"],cell_class=row["cell_class"],
            dataset=old["dataset"],materialization=783,coordinate_system="FAFB14.1",source_units="nm",
            source_url=BASE+"/"+root,path=str(path),bytes=path.stat().st_size,sha256=sha256(path),
            vertices=len(xyz),edges=len(edges),bounds_nm=[xyz.min(0).tolist(),xyz.max(0).tolist()],
            connectivity_validation="finite connected acyclic tree; edges=vertices-1; valid endpoints",
            reused_phase3v=reused)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for start in range(0,len(rows),4):
            futures={pool.submit(get,row):row for row in rows[start:start+4]}
            for future,row in futures.items():
                try:success.append(future.result())
                except Exception as e:failures.append(dict(root_id=row["root_id"],error=repr(e)))
            write_json(OUT/"acquisition_progress.json",dict(success=len(success),failures=failures,total=725,elapsed_s=time.time()-started))
            if failures:raise RuntimeError("Acquisition/validation anomaly; no subset mode. See acquisition_progress.json")
            if sum(a["bytes"] for a in success)>100_000_000:raise RuntimeError("Unexpected total bytes; stop")
            if start%100==0:print("Validated",len(success),"/",len(rows),flush=True)
    success.sort(key=lambda a:int(a["root_id"]))
    bounds=np.array([a["bounds_nm"] for a in success])
    m={k:old[k] for k in ["dataset","materialization","coordinate_system","source_units","display_transform","annotation","coordinate_evidence","terms","one_to_one_model_cell_mapping","model_hemisphere_assigned"]}
    m.update(morphologies=success,selection=enumeration["filter"],enumeration_file=str(OUT/"enumeration_before_download.json"),
        enumeration_sha256=sha256(OUT/"enumeration_before_download.json"),count=len(success),failures=failures,
        total_vertices=sum(a["vertices"] for a in success),total_edges=sum(a["edges"] for a in success),
        total_bytes=sum(a["bytes"] for a in success),bounds_nm=[bounds[:,0].min(0).tolist(),bounds[:,1].max(0).tolist()],
        cell_class_distribution=enumeration["cell_class_distribution"],elapsed_s=time.time()-started,
        info_path=str(ASSETS/"info.json"),info_sha256=sha256(ASSETS/"info.json"),
        coloring="Same T2 type-level aggregate RMS/q for every measured neuron; no model-cell mapping",
        other_morphologies={k:old["morphologies"][k] for k in ["T4a","T5d"]})
    write_json(manifest,m);print({k:m[k] for k in ["count","total_vertices","total_edges","total_bytes","bounds_nm"]})
if __name__=="__main__":main()
