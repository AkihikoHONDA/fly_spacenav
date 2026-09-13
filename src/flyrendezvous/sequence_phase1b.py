"""One short real-model trial, using the existing stimulus generator and adapter."""
import json
import time
from pathlib import Path
import numpy as np
from .stimuli import generate
from .recording import save_episode,write_json,sha256

def make_sequence(base_cfg,display_cfg):
    spec=display_cfg["additional_stimulus"]
    dt=base_cfg["dt"];seconds=spec["stage_seconds"]
    count=round(seconds/dt)
    displacement=seconds*spec["speed_px_per_second"]
    if not np.isclose(count*dt,seconds) or not np.isclose(displacement,round(displacement)):
        raise ValueError("This small sequence requires whole sample counts and pixel displacement")
    if spec["stages"]!=["static","right","stop","left","stop"]:
        raise ValueError("Unexpected stage order")
    shift=round(displacement)
    cx=(base_cfg["width"]-1)/2;cy=(base_cfg["height"]-1)/2;r=base_cfg["radius_px"]
    if min(cx-r,cy-r)<0 or cx+shift+r>=base_cfg["width"] or cy+r>=base_cfg["height"]:
        raise ValueError("Object would leave the field of view")
    cfg={**base_cfg,"frames":count,"speed_px_per_second":spec["speed_px_per_second"]}
    still,_=generate(cfg,"static");right,_=generate(cfg,"right");left,_=generate(cfg,"left")
    # Translation is an integer shift of the existing generator's images. Bounds
    # above guarantee that np.roll never wraps foreground across the image edge.
    images=np.concatenate([still,right,np.roll(still,shift,axis=2),
                           np.roll(left,shift,axis=2),still])
    stages=np.repeat(np.asarray(spec["stages"],dtype="U"),count)
    return images,np.arange(len(images))*dt,stages

def main():
    from .adapter import FlyvisAdapter
    from .run import sync
    cfg=json.loads(Path("configs/phase1.json").read_text())
    display=json.loads(Path("configs/phase1b.json").read_text())
    if cfg["dt"]!=display["dt"]:raise ValueError("Model/display dt mismatch")
    out=Path(display["output_directory"]);out.mkdir(parents=True,exist_ok=True)
    write_json(out/"sequence_validation.json",{"status":"running","completed":False})
    frames,t,stage=make_sequence(cfg,display)
    write_json(out/"sequence_config.json",{"base_config":cfg,"stimulus":display["additional_stimulus"],
        "frames":len(frames),"duration_seconds":len(frames)*cfg["dt"],
        "stage_intervals":"[0,.5) static; [.5,1) right; [1,1.5) stop; [1.5,2) left; [2,2.5) stop",
        "center_x_pixels":"31.5 -> 43.5 -> 31.5; continuous piecewise linear at stage boundaries",
        "reset":"one grey warmup before the complete sequence; no reset between stages"})
    adapter=FlyvisAdapter(cfg);base=adapter.reset()
    sync(adapter.torch,adapter.device)
    adapter.torch.cuda.reset_peak_memory_stats(adapter.device)
    start=time.perf_counter();chunks=[];inputs=[];elapsed=[]
    for k in range(0,len(frames),cfg["chunk_frames"]):
        values,rendered=adapter.chunk(frames[k:k+cfg["chunk_frames"]])
        sync(adapter.torch,adapter.device)
        chunks.append(values);inputs.append(rendered)
        elapsed.extend([time.perf_counter()-start]*len(values))
    wall=time.perf_counter()-start
    activity=np.concatenate(chunks);receptors=np.concatenate(inputs)
    adapter.assert_frozen()
    nodes=adapter.nodes
    save_episode(out/"sequence.npz",images=frames,receptor_input=receptors,input_time=t,
        response_time=t+cfg["dt"],activity=activity,baseline=base,
        cell_index=nodes["index"].to_numpy(dtype=np.int64),
        cell_type=nodes["type"].astype(str).to_numpy(dtype="U"),
        u=nodes["u"].to_numpy(dtype=np.int64),v=nodes["v"].to_numpy(dtype=np.int64),
        receptor_u=np.asarray(adapter.receptor_u),receptor_v=np.asarray(adapter.receptor_v),
        wall_seconds=np.array(elapsed))
    with np.load(out/"sequence.npz",allow_pickle=False) as z:data={k:z[k] for k in z.files}
    np.savez_compressed(out/"sequence.npz",**data,stage=stage)
    summary={"status":"passed","completed":True,"record_sha256":{"sequence.npz":sha256(out/"sequence.npz")},
        "parameter_sha256_before":adapter.initial_parameter_hash,
        "parameter_sha256_after":adapter.parameter_hash(),"checkpoint_sha256":sha256(adapter.checkpoint),
        "connectome_sha256":sha256(adapter.connectome_file),"device":str(adapter.device),
        "gpu":adapter.torch.cuda.get_device_name(adapter.device),"frames":len(frames),"n_cells":activity.shape[1],
        "finite":True,"model_seconds":len(frames)*cfg["dt"],"wall_seconds":wall,
        "peak_cuda_allocated_bytes":adapter.torch.cuda.max_memory_allocated(adapter.device),
        "sequence_config_sha256":sha256(out/"sequence_config.json"),
        "reset_count":1,"state_retained_between_chunks":True,"weight_updates":0}
    if summary["parameter_sha256_before"]!=summary["parameter_sha256_after"]:raise ValueError("Weights changed")
    write_json(out/"sequence_validation.json",summary)
    print(json.dumps(summary,indent=2))

if __name__=="__main__":main()
