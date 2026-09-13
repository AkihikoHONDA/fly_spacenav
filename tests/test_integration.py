"""Never substitutes a dummy for the official checkpoint."""
import json
from pathlib import Path
import numpy as np
import pytest

pytestmark = pytest.mark.integration

def test_official_checkpoint_stateful():
    cfg = json.loads(Path("configs/phase1.json").read_text())
    if not (Path(cfg["model_path"])/"chkpts/chkpt_00000").exists():
        pytest.skip("Official checkpoint missing; this is not a successful model validation")
    import torch
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable; GPU verification not achieved")
    from flyrendezvous.adapter import FlyvisAdapter
    from flyrendezvous.stimuli import generate
    adapter = FlyvisAdapter(cfg)
    frames, _ = generate(dict(cfg, frames=6), "right")
    adapter.reset()
    full, _ = adapter.chunk(frames)
    adapter.reset()
    streamed = np.stack([adapter.step(f) for f in frames])
    np.testing.assert_allclose(full, streamed, atol=2e-5, rtol=2e-5)
    adapter.reset()
    repeated, _ = adapter.chunk(frames)
    np.testing.assert_allclose(full, repeated, atol=2e-5, rtol=2e-5)
    assert np.isfinite(full).all()
    adapter.assert_frozen()
