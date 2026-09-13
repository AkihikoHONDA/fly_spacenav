import json
from pathlib import Path
import numpy as np
import pytest
from flyrendezvous.stimuli import generate, KINDS

@pytest.fixture
def cfg():
    return json.loads(Path("configs/phase1.json").read_text())

def test_directions_and_expansion(cfg):
    movies = {k: generate(cfg, k)[0] for k in KINDS}
    np.testing.assert_array_equal(movies["right"], movies["left"][:, :, ::-1])
    np.testing.assert_array_equal(movies["static"][0], movies["static"][-1])
    assert (movies["expand"][-1] > cfg["background"]).sum() > (movies["expand"][0] > cfg["background"]).sum()
    for k in KINDS:
        assert np.isfinite(movies[k]).all()
        assert movies[k].min() >= 0 and movies[k].max() <= 1

def test_prefix_is_causal(cfg):
    for kind in KINDS:
        full, _ = generate(cfg, kind)
        shorter, t = generate(dict(cfg, frames=5), kind)
        np.testing.assert_array_equal(full[:5], shorter)
        np.testing.assert_allclose(t, np.arange(5)*cfg["dt"])

@pytest.mark.parametrize("key,value", [("dt", 0), ("dt", 0.1), ("frames", 0), ("foreground", 2), ("speed_px_per_second", float("nan"))])
def test_bad_config(cfg, key, value):
    with pytest.raises(ValueError):
        generate(dict(cfg, **{key:value}), "static")
