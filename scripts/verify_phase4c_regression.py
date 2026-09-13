"""Compare every existing component, including Brain, with Phase 4B, and protect all prior results."""
import json,hashlib
from collections import defaultdict
from pathlib import Path
from rerun.experimental import RrdReader
from flyrendezvous.recording import sha256,write_json
OUT=Path("outputs/phase4c")
def signature(path):
    values=defaultdict(list);entities=set();segments=0
    for chunk in RrdReader(path).stream():
        p=chunk.entity_path;entities.add(p);b=chunk.to_record_batch()
        if chunk.is_static and "LineStrips3D:strips" in b.schema.names:
            for row in b.column("LineStrips3D:strips").to_pylist():segments+=sum(len(strip)-1 for strip in row)
        if p.startswith("/pilot") or p == "/__properties":continue # Recording creation time is metadata, not source data.
        times=[None]*b.num_rows if chunk.is_static else b.column("physical_display_s").cast("int64").to_pylist()
        for name in b.schema.names:
            if ":" not in name:continue
            for ns,v in zip(times,b.column(name).to_pylist()):
                if v is None:continue
                digest=hashlib.sha256(json.dumps(v,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
                values[p+"|"+name].append((ns,digest))
    normalized={p:sorted(v,key=lambda row:(-1 if row[0] is None else row[0],row[1])) for p,v in values.items()}
    return normalized,dict(entity_count=len(entities),static_3d_segments=segments,rrd_bytes=Path(path).stat().st_size)
def main():
    prior=json.loads((OUT/"prior_hashes.json").read_text())
    changed=[p for p,h in prior.items() if not Path(p).is_file() or sha256(p)!=h]
    assert not changed,changed
    for old,new in [("prior_README.md","README.md"),("prior_project.md","docs/project.md")]:
        assert (OUT/old).read_text() in Path(new).read_text()
    baseline,_=signature("outputs/phase4b/demo.rrd")
    results={}
    for mode in ["demo","analysis"]:
        actual,metrics=signature(OUT/(mode+".rrd"))
        assert actual==baseline,["Components differ",set(actual)^set(baseline)]
        metrics.update(shared_component_streams=len(actual),shared_component_values=sum(len(v) for v in actual.values()),
            all_existing_components_identical_to_phase4b=True,rrd_sha256=sha256(OUT/(mode+".rrd")))
        results[mode]=metrics
    write_json(OUT/"regression.json",dict(status="passed",prior_unchanged=len(prior),modes=results,
        new_inference=0,new_control_experiments=0,phase3_result={"approach":[8,8],"near":[2,4]}))
    print(json.dumps(results,indent=2))
if __name__=="__main__":main()
