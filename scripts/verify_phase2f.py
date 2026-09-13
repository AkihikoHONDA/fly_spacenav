"""Final Phase 2F provenance audit, including known GPU regression status."""
import json,re
from pathlib import Path
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.screening import assert_unchanged
def main():
    out=Path("outputs/phase2f")
    protected=assert_unchanged(json.loads((out/"prior_hashes.json").read_text()))
    sc=json.loads((out/"display_scales.json").read_text())
    metrics=json.loads((out/"motion_metrics.json").read_text())
    viewer=json.loads((out/"viewer_manifest.json").read_text())
    rrd=json.loads((out/"rrd_audit.json").read_text())
    capture=json.loads(Path("docs/evidence_phase2f/screenshots.json").read_text())
    video=json.loads((out/"video_review.json").read_text())
    assert all(x["status"]=="passed" for x in [metrics,rrd,capture,video])
    assert sha256(out/"display_scales.json")==metrics["scales_sha256"]==viewer["scales_sha256"]==rrd["scales_sha256"]
    assert sha256(out/"phase2f.rrd")==rrd["rrd_sha256"]==capture["rrd_sha256"]
    assert sha256("outputs/phase2/readout.npz")==sc["readout_sha256"]
    for m in sc["records"]+sc["map_records"]:assert sha256(m["record"])==m["sha256"]
    for m in viewer["episodes"]:assert sha256(m["display_record"])==m["display_sha256"]
    for shot in capture["screenshots"]:assert sha256(shot["file"])==shot["sha256"]
    unit=(out/"unit-tests.log").read_text();gpu=(out/"integration-tests.log").read_text()
    assert "84 passed" in unit and "failed" not in unit
    gpu_counts={key:int(n) for n,key in re.findall(r"(\d+) (passed|failed|skipped)",gpu)}
    result=dict(status="display_and_record_checks_passed; GPU regression reported separately",
        protected_files_unchanged=protected,unit_passed=84,integration=gpu_counts,
        original_test_success=metrics["original_test_results"],rrd_frames=rrd["total_frames"],
        rrd_entities=len(rrd["entity_frames"]),scales_sha256=sha256(out/"display_scales.json"),
        video_sha256=video["video_sha256"],new_morphologies=0,new_control_experiments=0,
        visualization_inference=0,gpu_test_inference="existing regression tests only",
        dependencies_added=0,artifact_bytes=sum(p.stat().st_size for p in out.rglob("*") if p.is_file()),
        code_sha256={str(p):sha256(p) for pattern in ["src/flyrendezvous/*phase2f*.py","src/flyrendezvous/activity_display.py","scripts/*phase2f*.py","tests/test_phase2f.py"] for p in Path(".").glob(pattern)})
    write_json(out/"final_checks.json",result);print(json.dumps(result,indent=2))
if __name__=="__main__":main()
