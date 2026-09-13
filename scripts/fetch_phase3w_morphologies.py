"""Fetch only the preselected 22 missing morphologies; reuse all other assets."""
import csv,json,zipfile,urllib.request,concurrent.futures
from pathlib import Path
from collections import Counter
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.multi_phase3w import TYPES3,select_rows
from flyrendezvous.morphology import read_precomputed
BASE="https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783"
OUT=Path("outputs/phase3w");ASSETS=Path("assets/phase3w")
def main():
    cfg=json.loads(Path("configs/phase3w.json").read_text())
    old=json.loads(Path("docs/anatomy_mapping_phase3v.json").read_text())
    prior=json.loads(Path("docs/anatomy_mapping_phase3p.json").read_text())
    assert sha256(old["annotation"]["cache"])==old["annotation"]["sha256"]
    with open(old["annotation"]["cache"]) as f:rows=list(csv.DictReader(f,delimiter="\t"))
    selection={t:select_rows(rows,t,old["morphologies"][t]["root_id"],cfg["seeds"][t],cfg["count_per_type"]) for t in TYPES3}
    before=dict(algorithm="PCG64; stable integer root sort; existing representative fixed plus uniform 11 without replacement",config_sha256=sha256("configs/phase3w.json"),annotation=old["annotation"],seeds=cfg["seeds"],selected_rows=selection,
        population_counts={t:sum(r["cell_type"]==t and r["side"]=="right" for r in rows) for t in TYPES3},
        existing_ids={t:old["morphologies"][t]["root_id"] for t in TYPES3},before_download=True)
    selection_path=OUT/"selection_before_download.json"
    if selection_path.exists():assert json.loads(selection_path.read_text())==before
    else:write_json(selection_path,before)
    manifest=Path("docs/anatomy_mapping_phase3w.json")
    if manifest.exists():
        m=json.loads(manifest.read_text())
        for group in m["morphologies"].values():
            for a in group:assert sha256(a["path"])==a["sha256"]
        for a in m["context"]["meshes"]:assert sha256(a["path"])==a["sha256"]
        print("Verified saved selection and assets; no download");return
    ASSETS.mkdir(exist_ok=True)
    with urllib.request.urlopen(BASE+"/info",timeout=45) as r:info=r.read(10000)
    assert json.loads(info)==json.loads(Path("assets/phase3v/sources/info.json").read_text())
    (ASSETS/"info.json").write_bytes(info)
    cached={a["root_id"]:a for a in prior["morphologies"]}
    cached.update({a["root_id"]:a for a in old["morphologies"].values()})
    def get(row):
        root=row["root_id"];reused=root in cached
        if reused:
            path=Path(cached[root]["path"]);assert sha256(path)==cached[root]["sha256"]
        else:
            path=ASSETS/(root+".precomputed")
            if not path.exists():
                with urllib.request.urlopen(BASE+"/"+root,timeout=45) as r:
                    assert r.status==200;data=r.read(2_000_001)
                if len(data)>2_000_000:raise ValueError("Unexpected individual asset size")
                path.write_bytes(data)
        xyz,e,r=read_precomputed(path)
        return dict(root_id=root,annotation_row=row,side=row["side"],cell_class=row["cell_class"],
            dataset=old["dataset"],materialization=783,coordinate_system="FAFB14.1",source_units="nm",source_url=BASE+"/"+root,path=str(path),bytes=path.stat().st_size,sha256=sha256(path),
            vertices=len(xyz),edges=len(e),bounds_nm=[xyz.min(0).tolist(),xyz.max(0).tolist()],connected_tree=True,reused=reused)
    morphology={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for t in TYPES3:
            morphology[t]=list(pool.map(get,selection[t]));print(t,len(morphology[t]),"validated",flush=True)
    inventory=json.loads((OUT/"mesh_inventory.json").read_text());assert sha256(inventory["archive"])==inventory["sha256"]
    mesh_dir=ASSETS/"meshes";mesh_dir.mkdir(exist_ok=True);meshes=[]
    with zipfile.ZipFile(inventory["archive"]) as z:
        for a in inventory["meshes"]:
            path=Path("assets/meshes")/(a["name"]+".ply") if a["previously_extracted"] else mesh_dir/(a["name"]+".ply")
            data=z.read(a["archive_entry"])
            if a["previously_extracted"]:assert path.read_bytes()==data
            else:path.write_bytes(data)
            meshes.append({**a,"path":str(path),"sha256":sha256(path)})
    m={k:old[k] for k in ["dataset","materialization","coordinate_system","source_units","display_transform","annotation","coordinate_evidence","terms","one_to_one_model_cell_mapping","model_hemisphere_assigned"]}
    m.update(morphologies=morphology,selection=before,selection_sha256=sha256(selection_path),
        context=dict(archive=inventory["archive"],archive_sha256=inventory["sha256"],source=inventory["source"],meshes=meshes,
            scope="All 78 neuropil surfaces in existing atlas archive; partial brain anatomy context, not complete brain or head"),
        info_sha256=sha256(ASSETS/"info.json"),new_morphologies=sum(not a["reused"] for g in morphology.values() for a in g))
    write_json(manifest,m)
    print("new morphologies",m["new_morphologies"],"meshes",len(meshes),flush=True)
if __name__=="__main__":main()
