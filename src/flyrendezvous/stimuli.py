"""Causal, reproducible grayscale stimuli. No temporal normalization."""
import numpy as np

KINDS = ("static", "right", "left", "expand")


def validate(cfg):
    for key in ("height", "width", "frames", "chunk_frames", "extent", "kernel_size"):
        if not isinstance(cfg[key], int) or cfg[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("dt", "warmup_seconds", "radius_px", "color_limit"):
        if not np.isfinite(cfg[key]) or cfg[key] <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if cfg["dt"] > 0.02:
        raise ValueError("Phase 1 requires dt <= 0.02 seconds")
    for key in ("background", "foreground"):
        if not 0 <= cfg[key] <= 1:
            raise ValueError(f"{key} must be in [0,1]")
    for key in ("speed_px_per_second", "expansion_px_per_second"):
        if not np.isfinite(cfg[key]) or cfg[key] < 0:
            raise ValueError(f"{key} must be nonnegative and finite")


def generate(cfg, kind):
    validate(cfg)
    if kind not in KINDS:
        raise ValueError(f"Unknown stimulus: {kind}")
    y, x = np.mgrid[:cfg["height"], :cfg["width"]]
    t = np.arange(cfg["frames"], dtype=np.float64) * cfg["dt"]
    cx = np.full(len(t), (cfg["width"] - 1) / 2)
    cy = (cfg["height"] - 1) / 2
    r = np.full(len(t), cfg["radius_px"], dtype=np.float64)
    if kind in ("right", "left"):
        cx += (1 if kind == "right" else -1) * cfg["speed_px_per_second"] * t
    elif kind == "expand":
        r += cfg["expansion_px_per_second"] * t
    mask = (x[None] - cx[:, None, None]) ** 2 + (y[None] - cy) ** 2 <= r[:, None, None] ** 2
    frames = np.where(mask, cfg["foreground"], cfg["background"]).astype(np.float32)
    return frames, t
