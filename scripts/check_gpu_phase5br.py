"""Run unchanged existing integration tests once, recording exact prefix differences."""
import json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.recording import write_json
from flyrendezvous.adapter import FlyvisAdapter
O=Path('outputs/phase5br')
if (O/'gpu_started.json').exists():raise RuntimeError('GPU check already run')
write_json(O/'gpu_started.json',dict(single_run=True))
orig=np.testing.assert_allclose;original_init=FlyvisAdapter.__init__;instances=[];checks=[];failures=[];nonfinite=[]
def capture(a,b,*args,**kwargs):
    x,y=np.asarray(a),np.asarray(b)
    if x.dtype.kind in 'fc' and (not np.isfinite(x).all() or not np.isfinite(y).all()):nonfinite.append(True)
    if x.shape==y.shape==(10,2):
        checks.append(dict(max_abs_diff_m_s2=float(np.max(np.abs(x-y))),
            actual=x.tolist(),desired=y.tolist(),atol=kwargs.get('atol'),rtol=kwargs.get('rtol')))
    return orig(a,b,*args,**kwargs)
def init(self,*a,**kw):
    original_init(self,*a,**kw);instances.append(self)
class Plugin:
    def pytest_runtest_logreport(self,report):
        if report.failed:failures.append(report.nodeid)
np.testing.assert_allclose=capture;FlyvisAdapter.__init__=init
try:
    code=pytest.main(['tests','-m','integration','-q'],plugins=[Plugin()])
finally:
    np.testing.assert_allclose=orig;FlyvisAdapter.__init__=original_init
mutation=False;hashes=[]
for a in instances:
    hashes.append(dict(before=a.initial_parameter_hash,after=a.parameter_hash()))
    try:a.assert_frozen()
    except Exception:mutation=True
allowed='tests/test_phase2.py::test_phase2_real_images_policy_prefix_and_weight_freeze'
maximum=max((r['max_abs_diff_m_s2'] for r in checks),default=float('inf'))
safe=bool(checks and maximum<=1e-4 and not mutation and not nonfinite and all(f==allowed for f in failures) and code in [0,1])
write_json(O/'gpu_reproducibility.json',dict(safe_to_continue=safe,pytest_exit_code=int(code),failures=failures,
    prefix_max_abs_diff_m_s2=maximum,prefix_checks=checks,parameter_hashes=hashes,
    parameter_mutation=mutation,nonfinite=bool(nonfinite),unchanged_tests_once=True,
    known_issue=bool(failures and safe),stop_threshold_m_s2=1e-4,thresholds_unchanged=True))
if not safe:raise SystemExit('STOP: GPU safety/reproducibility gate')
