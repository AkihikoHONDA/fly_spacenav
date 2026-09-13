"""Thin wrapper around Flyvis 1.2.0 stateful simulation; no GUI or fallback."""
import os
from pathlib import Path
import hashlib
import numpy as np
from .recording import sha256

class FlyvisAdapter:
    def __init__(self, cfg):
        # Must precede Flyvis's import-time configuration.
        os.environ.setdefault("FLYVIS_ROOT_DIR", str(Path("assets/flyvis").resolve()))
        import torch
        import flyvis
        from flyvis.datasets.rendering import BoxEye
        from flyvis.utils.hex_utils import get_hex_coords

        self.torch, self.cfg = torch, dict(cfg)
        self.device = torch.device(cfg["device"])
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable; CPU is not silently substituted")
        flyvis.device = self.device
        torch.set_default_device(self.device)
        self.model_dir = Path(cfg["model_path"]).resolve()
        if not (self.model_dir / "_meta.yaml").is_file():
            raise FileNotFoundError("Official model missing. Run scripts/fetch_assets.py first.")
        view = flyvis.NetworkView(self.model_dir)
        self.checkpoint = Path(view.get_checkpoint("best"))
        if not self.checkpoint.is_file():
            raise FileNotFoundError(self.checkpoint)
        # Require the official, hash-verified asset manifest before unpickling.
        import json
        manifest = json.loads(Path("docs/assets_manifest.json").read_text())
        relative = self.checkpoint.relative_to(Path.cwd()).as_posix()
        if sha256(self.checkpoint) != manifest["files"][relative]["sha256"]:
            raise ValueError("Checkpoint hash differs from verified official asset")
        for asset in (self.model_dir / "_meta.yaml",):
            name = asset.relative_to(Path.cwd()).as_posix()
            if sha256(asset) != manifest["files"][name]["sha256"]:
                raise ValueError("Official model configuration hash mismatch")
        if sha256(flyvis.connectome_file) != manifest["files"]["assets/sources/fib25-fib19_v2.2.json"]["sha256"]:
            raise ValueError("Installed connectome differs from verified asset")
        self.network = view.init_network(checkpoint="best")
        state_dict = torch.load(self.checkpoint, map_location=self.device, weights_only=False)["network"]
        actual = self.network.state_dict()
        if set(state_dict) != set(actual) or not all(torch.equal(actual[k], state_dict[k]) for k in actual):
            raise RuntimeError("Official checkpoint recovery did not load every parameter")
        self.network.eval()
        self.network.requires_grad_(False)
        self.initial_parameter_hash = self.parameter_hash()
        self.eye = BoxEye(extent=cfg["extent"], kernel_size=cfg["kernel_size"])
        self.receptor_u, self.receptor_v = get_hex_coords(cfg["extent"])
        self.nodes = self.network.connectome.nodes.to_df()
        self.state = None
        self.steps = 0
        self.connectome_file = flyvis.connectome_file
        self.flyvis_version = flyvis.__version__

    def parameter_hash(self):
        h = hashlib.sha256()
        for name, tensor in sorted(self.network.state_dict().items()):
            h.update(name.encode())
            h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()

    def assert_frozen(self):
        if self.network.training or any(p.requires_grad for p in self.network.parameters()):
            raise RuntimeError("Network is not frozen")
        if self.parameter_hash() != self.initial_parameter_hash:
            raise RuntimeError("Network parameters changed (including Flyvis clamp)")

    def render(self, images):
        a = np.asarray(images, dtype=np.float32)
        if a.ndim != 3 or len(a) == 0 or not np.isfinite(a).all() or a.min() < 0 or a.max() > 1:
            raise ValueError("Expected finite [frames,height,width] grayscale values in [0,1]")
        with self.torch.no_grad():
            return self.eye(self.torch.as_tensor(a, device=self.device)[None], ftype="mean")

    def reset(self):
        with self.torch.no_grad():
            self.state = self.network.steady_state(
                self.cfg["warmup_seconds"], self.cfg["dt"], 1, value=self.cfg["background"]
            )
        self.steps = 0
        self.assert_frozen()
        return self.state.nodes.activity[0].detach().cpu().numpy().copy()

    def step(self, image):
        return self.chunk(np.asarray(image)[None])[0][0]

    def chunk(self, images):
        return self.advance(self.render(images))

    def advance(self, receptor_input):
        if self.state is None:
            raise RuntimeError("Call reset() before advancing")
        if receptor_input.ndim != 4 or receptor_input.shape[0] != 1 or receptor_input.shape[2:] != (1, len(self.receptor_u)) or receptor_input.shape[1] == 0:
            raise ValueError("Expected [1,frames,1,receptors]")
        with self.torch.no_grad():
            states = self.network.simulate(receptor_input, self.cfg["dt"], initial_state=self.state, as_states=True)
            self.state = states[-1]
            activity = self.torch.stack([s.nodes.activity[0] for s in states]).detach().cpu().numpy()
        self.steps += len(states)
        if not np.isfinite(activity).all():
            raise FloatingPointError("Nonfinite real model response")
        return activity, receptor_input[0, :, 0].detach().cpu().numpy()
