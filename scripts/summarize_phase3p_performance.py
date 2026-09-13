"""Summarize matched practical capture measurements (not a real-time GUI benchmark)."""
import json,re
from pathlib import Path
import numpy as np
from flyrendezvous.recording import write_json,sha256
OUT=Path("outputs/phase3p")
def main():
    result={}
    regression=json.loads((OUT/"regression.json").read_text())
    anatomy=json.loads(Path("docs/anatomy_mapping_phase3p.json").read_text())
    for mode in ["representative","t2_population"]:
        shots=json.loads(Path("docs/evidence_phase3p/screenshots_"+mode+".json").read_text())
        perf=shots["performance"];video=json.loads((OUT/("video_manifest_"+mode+".json")).read_text())
        assert perf["window"]==[2240,1400]
        assert shots["rrd_sha256"]==video["rrd_sha256"]==sha256(OUT/(mode+".rrd"))
        calls=perf["screenshot_calls"]
        selected=[r["elapsed_s"] for r in calls if "_video_frames/" in r["file"]]
        assert len(selected)==len(video["frames"])==74
        timestamps=[Path(f["file"]).stat().st_mtime for f in video["frames"]]
        probe=json.loads(Path("docs/evidence_phase3p/memory_probe/screenshots_"+mode+".json").read_text())
        assert probe["rrd_sha256"]==shots["rrd_sha256"]
        rss={k:int(v) for k,v in re.findall(r"^(VmRSS|VmHWM):\s+(\d+) kB",probe["performance"]["viewer_memory_status"],flags=re.M)}
        morphology_segments=anatomy["total_edges"]+828+630 if mode=="t2_population" else 1098+828+630
        result[mode]=dict(**regression["modes"][mode],morphology_segments=morphology_segments,
            all_logged_context_segments=59238,
            load_to_first_seek_s=perf["load_to_first_seek_s"],
            screenshot_rpc_median_s=float(np.median(selected)),screenshot_rpc_mean_s=float(np.mean(selected)),
            screenshot_rpc_p95_s=float(np.quantile(selected,.95)),
            video_screenshot_rpc_sum_s=float(sum(selected)),
            video_png_first_to_last_span_s=timestamps[-1]-timestamps[0],
            video_capture_span_definition="Filesystem write completion from first PNG to last PNG; includes intervening seek/wait/IPC; first capture and encoding excluded",
            video_rendered_frames=len(selected),viewer_memory_kib=rss,viewer_memory_method="Separate direct native binary run after the same 6 screenshots, seek/play/pause; original capture recorded only Python launcher RSS and is not used",
            capture_total_elapsed_s=perf["total_elapsed_s"],continuous_play_frames=len(video["continuous_playback_frames"]))
    write_json(OUT/"performance.json",dict(modes=result,conditions=dict(window=[2240,1400],source="same original test_00",
        renderer="Rerun 0.37.1 native headless software rasterizer",repeat_count=1,
        brain_camera="A original 3V; B pulled back to fit full population. Practical final-view comparison, not identical pixel workload.",
        timing="RPC wall time includes render/readback/PNG/IPC; PNG-span includes seek/wait; no measured GUI FPS",
        windows_realtime_gui_verified=False)))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
