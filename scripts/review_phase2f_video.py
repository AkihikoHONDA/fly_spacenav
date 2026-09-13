"""Review the decoded animation and quantify visible palette changes from real logs."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from flyrendezvous.activity_display import TYPES,map_metrics
from flyrendezvous.projection import rms_colors
from flyrendezvous.recording import write_json,sha256

def main():
    out=Path("outputs/phase2f");sc=json.loads((out/"display_scales.json").read_text())
    rows=[];palette=[]
    for ident in ["test_00","test_05"]:
        with np.load(out/(ident+"_display.npz"),allow_pickle=False) as z:
            for j,name in enumerate(TYPES):
                active=z["control_mask"];raw=z["raw_rms"][:,j];q=z["q"][:,j]
                row=dict(id=ident,cell_type=name,rms_min=float(raw[active].min()),rms_max=float(raw[active].max()),
                    q_std=float(q[active].std()),clip_low=float(np.mean(raw[active]<sc["p05"][j])),clip_high=float(np.mean(raw[active]>sc["p95"][j])))
                for phase in ["approach","braking","near_hold"]:
                    mask=z["stage"]==phase;pair=mask[:-1]&mask[1:]
                    row[phase]=dict(samples=int(mask.sum()),q_min=float(q[mask].min()),q_max=float(q[mask].max()),q_median=float(np.median(q[mask])),
                        q_rate_median=float(np.median(np.abs(np.diff(q))[pair])/.5),map_motion=map_metrics(z["delta"][:,j],sc["signed_map_limit"][j],mask))
                rows.append(row)
            active=z["control_mask"];pairs=active[:-1]&active[1:]
            for mode,rgb in [("absolute",rms_colors(z["raw_rms"][:,2],.22).astype(float)),("relative",rms_colors(z["q"][:,2],1).astype(float))]:
                diff=np.diff(rgb,axis=0)[pairs]
                palette.append(dict(id=ident,mode=mode,rgb_component_range=np.ptp(rgb[active],axis=0).tolist(),
                    changed_frame_fraction=float(np.mean(np.any(diff!=0,axis=1))),
                    median_rgb_step=float(np.median(np.linalg.norm(diff,axis=1))),
                    p95_rgb_step=float(np.quantile(np.linalg.norm(diff,axis=1),.95))))
    write_json(out/"replay_visibility.json",dict(metrics=rows,palette=palette,
        relative_gain_T4a=.22/(sc["p95"][2]-sc["p05"][2]),
        note="Replay-only visibility diagnostics; not the original 12-test calibration or performance."))
    meta=json.loads((out/"video_manifest.json").read_text())
    assert sha256(meta["file"])==meta["sha256"]
    assert sha256(meta["source_record"])==meta["source_sha256"]
    assert sha256(out/"phase2f.rrd")==meta["rrd_sha256"]
    # Decode every frame, including timing. The renderer is the source of all pixels.
    decoded=Image.open(meta["file"]);n=decoded.n_frames
    assert n==len(meta["frames"])
    duration=0;last=None;changes=[];size=None
    for k,frame in enumerate(meta["frames"]):
        assert sha256(frame["file"])==frame["sha256"]
        decoded.seek(k);rgb=np.array(decoded.convert("RGB"))
        duration+=decoded.info["duration"];size=decoded.size
        if last is not None:changes.append(float(np.mean(np.abs(rgb.astype(float)-last.astype(float)))))
        last=rgb
    assert duration==meta["duration_ms"]
    assert np.all(np.array(changes)>0)
    live=meta.get("continuous_playback_frames",meta.get("real_time_playback_frames"))
    assert len(live)>=3 and live[-1]["after_ns"]>=210500000000
    for shot in live:assert sha256(shot["file"])==shot["sha256"]
    result=dict(status="passed",format="animated WebP",decoded_frames=n,duration_ms=duration,size=size,
        all_adjacent_frames_differ=True,adjacent_frame_mean_abs_rgb_change_median=float(np.median(changes)),
        video_sha256=sha256(meta["file"]),continuous_playback_samples=len(live),
        live_first_before_ns=live[0]["before_ns"],live_last_after_ns=live[-1]["after_ns"],
        review="Full animation decoded; native Rerun continuous play/pause/seek rendered and inspected. Headless timeline progression does not benchmark real-time GUI performance.",
        browser_review="Unavailable: browser tool failed during bootstrap (sandbox metadata missing). No browser automation fallback or new framework installed.",
        mp4="Not generated: no ffmpeg/ffprobe or installed Python video encoder. RRD primary; existing Pillow/libwebp animation supplementary.")
    write_json(out/"video_review.json",result);print(json.dumps(result,indent=2));print(json.dumps(palette,indent=2))
if __name__=="__main__":main()
