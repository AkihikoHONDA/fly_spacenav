"""Final provenance check; preserves a failed existing GPU regression as a failure."""
import json
from pathlib import Path
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.screening import assert_unchanged

def main():
    out=Path("outputs/phase2e")
    count=assert_unchanged(json.loads((out/"prior_hashes.json").read_text()))
    audit=json.loads((out/"phase2_numerical_audit.json").read_text())
    rrd=json.loads((out/"rrd_audit.json").read_text())
    screen=json.loads((out/"cell_type_screening.json").read_text())
    capture=json.loads(Path("docs/evidence_phase2e/screenshots.json").read_text())
    assert audit["status"]==rrd["status"]==screen["status"]==capture["status"]=="passed"
    assert sha256(out/"phase2e.rrd")==rrd["rrd_sha256"]==capture["rrd_sha256"]
    assert sha256(out/"cell_type_metrics.npz")==screen["metrics_sha256"]
    for shot in capture["screenshots"]:
        assert sha256(shot["file"])==shot["sha256"]
        assert sha256(shot["source_record"])==shot["record_sha256"]
    assert "68 passed" in (out/"unit-tests.log").read_text()
    gpu_logs=[(out/name).read_text() for name in ["integration-tests.log","integration-tests-retry.log"]]
    assert all("1 failed, 1 passed" in log for log in gpu_logs)
    result=dict(status="display_and_saved_record_checks_passed; existing_GPU_regression_failed",
        protected_files_unchanged=count,unit_tests_passed=68,gpu_tests_per_run=dict(passed=1,failed=1,skipped=0),gpu_runs=2,
        numerical_audit=audit,rrd_audit=rrd,screening_types=screen["all_types_evaluated"],
        candidate_types=[r["cell_type"] for r in json.loads((out/"candidate_selection.json").read_text())["candidates"]],
        original_test_results=screen["original_test_success"],
        new_control_experiments=0,new_morphologies=0,screening_or_viewer_neural_inference=0,
        regression_test_inference="Existing CUDA tests only, two runs; no retraining",
        figure_sha256={str(p):sha256(p) for folder in [Path("docs/evidence_phase2e"),out] for p in folder.glob("*.png")},
        code_sha256={str(p):sha256(p) for pattern in ["src/flyrendezvous/*phase2e*.py","src/flyrendezvous/display_coordinates.py","src/flyrendezvous/screening.py","scripts/*phase2e*.py","tests/test_phase2e.py"] for p in Path(".").glob(pattern)})
    write_json(out/"final_checks.json",result);print(json.dumps(result,indent=2))
if __name__=="__main__":main()
