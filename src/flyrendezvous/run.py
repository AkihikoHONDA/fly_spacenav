"""Headless real-model execution and evidence generation."""
import argparse
from itertools import combinations
import json
from pathlib import Path
import platform
import subprocess
import time
import numpy as np
from .adapter import FlyvisAdapter
from .stimuli import generate, validate, KINDS
from .recording import save_episode, write_json, sha256


def sync(torch, device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase1.json")
    parser.add_argument("--output", default="outputs/phase1")
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    validate(cfg)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "validation.json", {"status":"running", "completed":False})
    write_json(out / "config.json", cfg)
    adapter = FlyvisAdapter(cfg)
    torch = adapter.torch
    device = adapter.device
    a = torch.arange(4096, dtype=torch.float32, device=device).reshape(64, 64)
    y = a @ a.T
    sync(torch, device)
    assert torch.isfinite(y).all() and y[0, 0].item() == 85344.0

    # The official custom-stimuli tutorial explicitly offers this small generated
    # dataset instead of downloading Moving MNIST. Use its real API before ours.
    from flyvis.utils.dataset_utils import random_walk_of_blocks
    official_images = random_walk_of_blocks(dataset_size=[1, 8, 64, 64], seed=42)[0].astype(np.float32)
    # Defaults already lie in [0,1] for this seed: no inferred normalization.
    official_input = adapter.render(official_images)
    with torch.no_grad():
        initial = adapter.network.fade_in_state(1.0, cfg["dt"], official_input[:, 0])
        response = adapter.network.simulate(official_input, cfg["dt"], initial_state=initial)
    official_activity = response[0].detach().cpu().numpy()
    assert np.isfinite(official_activity).all()
    adapter.assert_frozen()
    np.savez_compressed(out / "official_smoke.npz", images=official_images,
                        receptor_input=official_input[0, :, 0].cpu().numpy(), activity=official_activity)

    nodes = adapter.nodes
    cell_type = nodes["type"].astype(str).to_numpy(dtype="U")
    if cfg["display_cell_type"] not in cell_type:
        raise ValueError("Configured display cell type does not exist")
    index = nodes["index"].to_numpy(dtype=np.int64)
    assert np.array_equal(index, np.arange(len(nodes)))
    metadata = {
        "cell_index":index, "cell_type":cell_type,
        "u":nodes["u"].to_numpy(dtype=np.int64), "v":nodes["v"].to_numpy(dtype=np.int64),
        "receptor_u":np.asarray(adapter.receptor_u), "receptor_v":np.asarray(adapter.receptor_v),
    }
    nodes.to_csv(out / "cells.csv", index=False)
    check = {}
    responses = {}
    for kind in KINDS:
        frames, input_time = generate(cfg, kind)
        base = adapter.reset()
        with torch.no_grad():
            receptors = adapter.render(frames)
            full, _ = adapter.advance(receptors)
        adapter.reset()
        # End-to-end chunk inference includes BoxEye and CPU transfer, excludes
        # loading/initialization and warmup. Synchronize around wall-clock timing.
        sync(torch, device)
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        start = time.perf_counter()
        chunks, inputs, elapsed = [], [], []
        for i in range(0, len(frames), cfg["chunk_frames"]):
            values, rendered = adapter.chunk(frames[i:i+cfg["chunk_frames"]])
            sync(torch, device)
            chunks.append(values)
            inputs.append(rendered)
            elapsed.extend([time.perf_counter() - start] * len(values))
        wall = time.perf_counter() - start
        peak_memory = torch.cuda.max_memory_allocated(device) if device.type == "cuda" else None
        split = np.concatenate(chunks)
        rendered = np.concatenate(inputs)
        np.testing.assert_allclose(split, full, atol=2e-5, rtol=2e-5)
        np.testing.assert_allclose(rendered, receptors[0, :, 0].cpu().numpy(), atol=1e-6, rtol=1e-6)
        adapter.reset()
        repeated, _ = adapter.chunk(frames)
        np.testing.assert_allclose(repeated, full, atol=2e-5, rtol=2e-5)
        adapter.assert_frozen()
        check[kind] = {
            "max_abs_full_vs_chunk":float(np.max(np.abs(full-split))),
            "max_abs_reset_repeat":float(np.max(np.abs(full-repeated))),
            "wall_seconds":wall, "model_seconds":len(frames)*cfg["dt"],
            "wall_per_model_second":wall/(len(frames)*cfg["dt"]),
            "peak_cuda_allocated_bytes":peak_memory,
            "activity_min":float(split.min()), "activity_max":float(split.max()),
            "display_delta_min":float((split-base)[:,cell_type==cfg["display_cell_type"]].min()),
            "display_delta_max":float((split-base)[:,cell_type==cfg["display_cell_type"]].max()),
            "finite":True,
        }
        save_episode(out / (kind+".npz"), images=frames, receptor_input=rendered,
                     input_time=input_time, response_time=input_time+cfg["dt"],
                     activity=split, baseline=base, wall_seconds=np.array(elapsed), **metadata)
        responses[kind] = split
        print(kind, json.dumps(check[kind]), flush=True)
    differences = {}
    for first, second in combinations(KINDS, 2):
        delta = responses[first]-responses[second]
        differences[first+"__"+second] = {"max_abs":float(np.abs(delta).max()),
                                         "rms":float(np.sqrt(np.mean(delta.astype(float)**2)))}
    # A lack of stimulus-dependent difference must remain a failure, never a visual trick.
    assert all(d["max_abs"] > 1e-5 for d in differences.values())
    adapter.assert_frozen()
    summary = {
        "status":"passed", "completed":True,
        "record_sha256":{k+".npz":sha256(out/(k+".npz")) for k in KINDS},
        "device":str(device), "gpu":torch.cuda.get_device_name(device) if device.type=="cuda" else None,
        "compute_capability":torch.cuda.get_device_capability(device) if device.type=="cuda" else None,
        "torch":torch.__version__, "cuda_build":torch.version.cuda, "flyvis":adapter.flyvis_version,
        "python":platform.python_version(), "platform":platform.platform(), "n_cells":len(nodes),
        "cell_types":sorted(set(cell_type)), "checkpoint":str(adapter.checkpoint),
        "checkpoint_sha256":sha256(adapter.checkpoint), "connectome_sha256":sha256(adapter.connectome_file),
        "parameter_sha256_before":adapter.initial_parameter_hash, "parameter_sha256_after":adapter.parameter_hash(),
        "official_smoke":{"frames":len(official_images),"finite":True,"source":"official custom stimuli / random_walk_of_blocks, seed 42"},
        "gpu_smoke":{"finite":True,"matrix_result_0_0":y[0,0].item()},
        "checks":check, "pairwise_differences":differences,
        "time_semantics":{"input":"frame k held over [k*dt,(k+1)*dt)",
                          "response":"state after Euler step at (k+1)*dt",
                          "warmup":f"{cfg['warmup_seconds']} seconds grey, hidden before episode time zero",
                          "resampling":"none: input dt equals model dt; no future frames",
                          "wall_seconds":"cumulative synchronized chunk-completion times; repeated per frame in each chunk",
                          "viewer":"separate input_sample_s timeline; response corresponds to end of displayed input interval",
                          "hcw_multiplier":None},
        "activity":"PPNeuronIGRSynapses nodes.activity: model voltage in model units; not spikes or calibrated mV",
    }
    write_json(out / "validation.json", summary)
    print("Real-model validation passed:",out / "validation.json")

if __name__ == "__main__":
    main()
