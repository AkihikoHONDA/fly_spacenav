"""Practical A/B measurements with the unchanged Phase 3P full-population reference."""
import json,re
from pathlib import Path
import numpy as np
from flyrendezvous.recording import sha256,write_json
OUT=Path("outputs/phase3w")
def main():
    m=json.loads(Path("docs/anatomy_mapping_phase3w.json").read_text())
    old=json.loads(Path("outputs/phase3p/performance.json").read_text())["modes"]["t2_population"]
    assert old["rrd_sha256"]==sha256("outputs/phase3p/t2_population.rrd")
    regression=json.loads((OUT/"regression.json").read_text())
    modes={}
    for mode in ["representative","multi"]:
        shots=json.loads(Path("docs/evidence_phase3w/screenshots_"+mode+".json").read_text());p=shots["performance"]
        video=json.loads((OUT/("video_manifest_"+mode+".json")).read_text())
        assert p["window"]==[2240,1400] and shots["rrd_sha256"]==video["rrd_sha256"]==sha256(OUT/(mode+".rrd"))
        calls=[c["elapsed_s"] for c in p["screenshot_calls"] if "_video_frames/" in c["file"]]
        assert len(calls)==74
        rss={k:int(v) for k,v in re.findall(r"^(VmRSS|VmHWM):\s+(\d+) kB",p["viewer_memory_status"],flags=re.M)}
        times=[Path(f["file"]).stat().st_mtime for f in video["frames"]]
        nv=sum(a["vertices"] for g in m["morphologies"].values() for a in g) if mode=="multi" else 2559
        ne=nv-(36 if mode=="multi" else 3)
        modes[mode]={**regression["modes"][mode],"morphology_count":36 if mode=="multi" else 3,"morphology_vertices":nv,"morphology_edges":ne,
            "load_to_first_seek_s":p["load_to_first_seek_s"],"screenshot_rpc_mean_s":float(np.mean(calls)),"screenshot_rpc_p95_s":float(np.quantile(calls,.95)),
            "video_screenshot_rpc_sum_s":float(sum(calls)),"video_capture_wall_s":shots["video_capture_wall_s"],
            "video_png_first_to_last_span_s":times[-1]-times[0],"viewer_memory_kib":rss,"continuous_play_frames":len(video["continuous_playback_frames"]),
            "origin":"Phase 3W new native captures; direct binary RSS"}
    modes["full_t2_reference"]={**old,"morphology_count":727,"morphology_vertices":866068,"morphology_edges":865341,"origin":"Reused unchanged Phase 3P recording/captures; memory from separate native probe","source":"outputs/phase3p/performance.json"}
    write_json(OUT/"performance.json",dict(modes=modes,conditions="Same original test_00 and 74 samples, native software Rerun 0.37.1 at 2240x1400. A right closeup / B bilateral 78 meshes / C full T2 right view: different scenes. Wall RPC includes render/readback/PNG/IPC. Native RSS is process memory, not dedicated GPU memory. C reused prior measurement; not a controlled FPS benchmark.",windows_manual_gui_verified=False))
    print(json.dumps(modes,indent=2))
if __name__=="__main__":main()
