"""Gate 3. All preregistered candidates, no resampling or neural data."""
import json
from pathlib import Path
from flyrendezvous.phase3_runtime import rollout,save_trial,write_json,sha256,Teacher
O=Path('outputs/phase5b')
assert json.loads((O/'physics_validation.json').read_text())['passed']
for p,h in json.loads((O/'contract.json').read_text())['files'].items():assert sha256(p)==h
if (O/'teacher_gate.json').exists():raise RuntimeError('Gate already evaluated')
cfg=json.loads(Path('configs/phase5b/training.json').read_text());splits=json.loads((O/'splits.json').read_text())
write_json(O/'lqr.json',Teacher(cfg).metadata())
results=[]
for cases in splits.values():
    for case in cases:
        a,m=rollout(cfg,case,'teacher')
        results.append(save_trial(O/'teacher_gate',a,m))
        print(case['id'],m['termination_reason'],m['final_time_s'],m['final_position_error_m'],flush=True)
write_json(O/'teacher_gate.json',dict(passed=all(m['success'] for m in results),
    success=sum(m['success'] for m in results),total=len(results),results=results,
    resampling=False,neural_inference=False))
if not all(m['success'] for m in results):raise SystemExit('STOP: teacher gate failed; no data/training/test/truth allowed')
