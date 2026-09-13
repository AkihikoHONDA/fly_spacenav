"""Run only existing tests compatible with the user's strict no-computation-experiment scope."""
import json,sys
from pathlib import Path
import pytest

EXCLUDED={
'tests/test_phase2.py::test_hcw_zero_n_and_independent_integration':'New ODE propagation, even though synthetic',
'tests/test_phase2.py::test_ridge_train_only_scaling_intercept_reload':'New synthetic readout fitting and predictions',
'tests/test_phase2.py::test_rollout_time_initial_observation_and_no_state_reset':'New teacher closed-loop rollout',
'tests/test_phase3.py::test_image_only_causal_interface':'New dummy-policy closed-loop rollout',
'tests/test_phase2e.py::test_contributions_use_training_scaling_keep_mask_and_separate_bias':'Invokes readout.predict',
'tests/test_phase2e.py::test_frozen_original_test_reconstruction_and_screening':'Recomputes readout predictions on saved features',
}
class Scope:
    def pytest_collection_modifyitems(self,config,items):
        excluded=[i for i in items if i.nodeid in EXCLUDED]
        items[:]=[i for i in items if i.nodeid not in EXCLUDED]
        config.hook.pytest_deselected(items=excluded)
    def pytest_sessionfinish(self,session,exitstatus):
        Path('outputs/phase5a/test_scope.json').write_text(json.dumps(dict(
            excluded_tests=EXCLUDED,integration='2 tests deselected: new Flyvis inference prohibited',
            original_non_gpu_count=150,analysis_tests=11,expected_executed=155,
            exitstatus=exitstatus,scope='Saved data and synthetic reductions only; no dynamics propagation, fit or prediction'),indent=2)+'\n')
def forbid(frame,event,arg):
    if event=='call':
        file=frame.f_code.co_filename.replace('\\','/');name=frame.f_code.co_name
        if (name=='rollout' and 'phase' in file and '_runtime.py' in file) or \
           (file.endswith('/readout.py') and name in ['fit','predict']) or \
           (file.endswith('/adapter.py') and name in ['__init__','chunk','step']) or name=='solve_ivp':
            raise RuntimeError('Forbidden new simulation/inference/learning during Phase 5A: '+file+':'+name)
if __name__=='__main__':
    sys.setprofile(forbid)
    try:result=pytest.main(['tests','-m','not integration','-q','--junitxml=outputs/phase5a/pytest.xml'],plugins=[Scope()])
    finally:sys.setprofile(None)
    sys.exit(result)
