"""Fetch exactly one exact-type T2 and T5d representative; reuse T4a."""
import csv,json,urllib.request
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.morphology import read_precomputed,write_swc,read_swc
BASE="https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783"
OUT=Path("assets/phase3v")
def fetch(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url,timeout=45) as response:
            assert response.status==200
            data=response.read(2_000_001)
            if len(data)>2_000_000:raise ValueError("Unexpectedly large individual resource")
        path.write_bytes(data)
    return sha256(path)
def main():
    table=Path("assets/phase1b/sources/annotations.tsv")
    original=json.loads(Path("docs/anatomy_mapping_phase1b.json").read_text())
    assert sha256(table)==original["annotation"]["sha256"]
    with table.open() as f:rows=list(csv.DictReader(f,delimiter="\t"))
    chosen={name:next(r for r in rows if r["cell_type"]==name and r["side"]=="right") for name in ["T2","T5d"]}
    assert chosen["T2"]["root_id"]=="720575940608937923"
    assert chosen["T5d"]["root_id"]=="720575940623043327"
    manifest_path=Path("docs/anatomy_mapping_phase3v.json")
    if manifest_path.exists():
        old=json.loads(manifest_path.read_text())
        for path,meta in old["files"].items():assert sha256(path)==meta["sha256"]
        print("Verified existing Phase 3V acquisition; no new download");return
    fetch(BASE+"/info",OUT/"sources/info.json")
    info=json.loads((OUT/"sources/info.json").read_text())
    assert info==json.loads(Path("assets/phase1b/sources/skeleton-info.json").read_text())
    morphology={}
    for name,row in chosen.items():
        root=row["root_id"];binary=OUT/(root+".precomputed")
        fetch(BASE+"/"+root,binary)
        xyz,edges,radii=read_precomputed(binary)
        swc=OUT/(root+".swc");write_swc(swc,xyz.astype(float),edges,radii.astype(float))
        x,e,r=read_swc(swc);np.testing.assert_allclose(x,xyz.astype(float)*.001,atol=1e-6,rtol=0)
        assert {tuple(sorted(a)) for a in e}=={tuple(sorted(a)) for a in edges}
        morphology[name]=dict(type=name,root_id=root,side=row["side"],annotation_row=row,
            path=str(binary),sha256=sha256(binary),source_url=BASE+"/"+root,
            vertices=len(xyz),edges=len(edges),bounds_nm=[xyz.min(0).tolist(),xyz.max(0).tolist()])
        print(name,root,len(xyz),len(edges),sha256(binary),flush=True)
    morphology["T4a"]=dict(type="T4a",root_id=original["morphology_id"],side="right",
        annotation_row=original["annotation"]["row"],path="assets/phase1b/720575940605852192.precomputed",
        sha256=original["morphology"]["sha256"],source_url=original["morphology"]["url"],
        vertices=original["morphology"]["vertices"],edges=original["morphology"]["edges"],bounds_nm=original["morphology"]["bounds_nm"])
    fetch("https://flywire.ai/tos",OUT/"sources/flywire-tos.html")
    manifest=dict(morphologies=morphology,selection="first exact cell_type row with side=right in pinned official table; one per type",
        dataset="FlyWire female FAFB",materialization=783,coordinate_system="FAFB14.1",source_units="nm",
        display_transform="0.001 nm to um only; no translation, rotation, reflection or fit",
        annotation={**{k:original["annotation"][k] for k in ["url","commit","sha256"]},"cache":str(table)},
        coordinate_evidence=original["coordinate_evidence"],terms=original["terms"],
        one_to_one_model_cell_mapping=False,model_hemisphere_assigned=False,
        acquired_types=["T2","T5d"],reused_types=["T4a"])
    manifest["terms"]["annotation_citation_source"]="https://raw.githubusercontent.com/flyconnectome/flywire_annotations/8587524c1748ce5ef2080822a2fc890fc03bf597/README.md"
    manifest["terms"]["attribution"]="FlyWire Consortium; Berg et al. 2025; Schlegel et al. 2024; Matsliah et al. 2024; Dorkenwald et al. 2024. JFRC2 background: Jenett et al.; fafbseg."
    paths=[p for p in OUT.rglob("*") if p.is_file()]+[Path(morphology["T4a"]["path"]),table]
    manifest["files"]={str(p):dict(sha256=sha256(p),bytes=p.stat().st_size) for p in paths}
    write_json(manifest_path,manifest)
if __name__=="__main__":main()
