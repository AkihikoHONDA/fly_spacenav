"""Capture two real Rerun renders and verify native viewer timeline controls."""
import json
import os
from pathlib import Path
import select
import subprocess
import time
import numpy as np
from flyrendezvous.recording import write_json,sha256

ROOT=Path(__file__).resolve().parents[1]
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--baseline",action="store_true");parser.add_argument("--mode",choices=["demo","analysis"],default="demo");parser.add_argument("--video",action="store_true");parser.add_argument("--reuse-video",action="store_true");args=parser.parse_args()
    os.chdir(ROOT);condition=os.environ["PHASE5BR_CONDITION"];out=ROOT/"outputs/phase5br/demo"/condition;evidence=ROOT/"docs/evidence_phase5br"/condition;evidence.mkdir(parents=True,exist_ok=True)
    assert not args.baseline,"Use the saved Phase 5B condition only"
    source_dir=out
    prefix="baseline" if args.baseline else args.mode
    rrd=source_dir/(args.mode+".rrd")
    started=time.perf_counter();timings=[];load_time=None
    env={**os.environ,"RERUN_ANALYTICS_ENABLED":"false","RUST_LOG":"error"}
    import rerun_cli
    binary=str(Path(rerun_cli.__file__).parent/"rerun")
    logfile=(out/"native-viewer.log").open("w")
    viewer=subprocess.Popen([binary,str(rrd),"--headless","--bind","127.0.0.1","--port","9890","--window-size","2240x1400"],stdout=logfile,stderr=logfile,env=env)
    mcp=subprocess.Popen([binary,"viewer-mcp"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=logfile,text=True,env=env)
    request_id=0
    def rpc(method,params):
        nonlocal request_id
        request_id+=1
        mcp.stdin.write(json.dumps(dict(jsonrpc="2.0",id=request_id,method=method,params=params))+"\n");mcp.stdin.flush()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if select.select([mcp.stdout],[],[],1)[0]:
                line=mcp.stdout.readline()
                if not line:raise RuntimeError("MCP exited")
                result=json.loads(line)
                if result.get("id")==request_id:
                    if "error" in result:raise RuntimeError(result["error"])
                    return result["result"]
        raise TimeoutError(method)
    def tool(name,args=None):
        begin=time.perf_counter()
        result=rpc("tools/call",dict(name=name,arguments=args or {}))
        if name=="screenshot":timings.append(dict(file=args["save_path"],elapsed_s=time.perf_counter()-begin))
        if result.get("isError"):raise RuntimeError(result)
        return result
    def state():
        result=tool("viewer_state")
        if "structuredContent" in result:return result["structuredContent"]
        return json.loads(next(c["text"] for c in result["content"] if c["type"]=="text"))
    def current(s):
        active=s["active_store_id"]
        return next(r for r in s["recordings"] if r["store_id"]==active)["current_time"]["time"]
    def seek(ns):
        for attempt in range(12):
            tool("set_time",{"timeline":"physical_display_s","time":ns,"play":False})
            tool("wait_for",{"min_steps":5,"timeout_secs":5})
            observed=state()
            if current(observed)==ns:return observed
        raise AssertionError(dict(requested=ns,observed=observed))

    try:
        rpc("initialize",dict(protocolVersion="2024-11-05",capabilities={},clientInfo={"name":"FlyRendezvous-verification","version":"1"}))
        mcp.stdin.write(json.dumps(dict(jsonrpc="2.0",method="notifications/initialized"))+"\n");mcp.stdin.flush()
        time.sleep(2)
        tool("connect",{"endpoint":"http://127.0.0.1:9890"})
        initial=state()
        seek(0);load_time=time.perf_counter()-started
        manifest=json.loads((source_dir/("viewer_"+args.mode+".json")).read_text())
        entry=manifest["episodes"][0]
        with np.load(entry["record"],allow_pickle=False) as z:d={k:z[k] for k in z.files}
        selected=d["display_indices"][2]
        delta=d["display_activity"][:,2].astype(float)-d["baseline"][selected]
        rms=np.sqrt(np.mean(delta**2,axis=1))
        braking=int(np.argmin(np.sum(d["states"][:-1,2:]*d["u_applied"],axis=1)))
        indices=[0,40,len(d["sample_id"])//3,braking,len(d["sample_id"])-1]
        screenshots=[]
        for label,k in zip(["neutral","early","diagonal","braking","last_sample"],indices):
            display_time=float(entry["offset"]+d["observation_time"][k]);ns=round(display_time*1e9)
            observed=seek(ns);assert current(observed)==ns
            path=evidence/(prefix+"_"+label+".png")
            tool("screenshot",{"save_path":str(path),"pixels_per_point":1})
            screenshots.append(dict(file=path.relative_to(ROOT).as_posix(),sha256=sha256(path),
                trial=entry["id"],sample=k,physical_time=float(d["observation_time"][k]),
                neural_input_time=float(d["neural_input_time"][k]),neural_response_time=float(d["neural_response_time"][k]),
                display_time=display_time,rms=float(rms[k]),applied_acceleration=d["u_applied"][k].tolist(),
                state=d["states"][k].tolist(),viewer_time_ns=current(observed),
                source_record=entry["record"],record_sha256=entry["record_sha256"]))
        last_entry=manifest["episodes"][-1]
        terminal_time=last_entry["offset"]+(last_entry["frames"] if args.baseline else last_entry["frames"]-1)*.5
        terminal_ns=round(terminal_time*1e9);seek(terminal_ns)
        terminal_path=evidence/(prefix+"_terminal.png")
        tool("screenshot",{"save_path":str(terminal_path),"pixels_per_point":1})
        terminal=dict(file=terminal_path.relative_to(ROOT).as_posix(),sha256=sha256(terminal_path),
            time_ns=terminal_ns,trial=last_entry["id"],expected="RESET blank" if args.baseline else "last sample retained")
        start_ns=round((entry["offset"]+25.)*1e9)
        tool("set_time",{"timeline":"physical_display_s","time":start_ns,"play":True})
        tool("wait_for",{"min_steps":20,"timeout_secs":5})
        playing=state();advanced=current(playing);assert advanced>start_ns
        tool("set_time",{"timeline":"physical_display_s","time":advanced,"play":False})
        tool("wait_for",{"min_steps":10,"timeout_secs":5})
        paused=state();assert current(paused)==advanced
        result=dict(status="passed",renderer="native Rerun 0.37.1 headless, software rasterizer",
            interface="Rerun viewer-mcp; Windows GUI mouse controls not tested",
            rrd_sha256=sha256(rrd),screenshots=screenshots,
            terminal_frame=terminal,controls=dict(seek=True,play_advanced_from_ns=start_ns,play_advanced_to_ns=advanced,
                          pause_time_ns=current(paused),pause_held=True),initial_viewer_state=initial)
        if args.video:
            from PIL import Image,features
            assert features.check("webp"),"Animated WebP encoder unavailable"
            if args.reuse_video:
                previous=json.loads((out/("video_manifest_"+args.mode+".json")).read_text())
                video=ROOT/previous["file"];assert sha256(video)==previous["sha256"]
                assert previous["rrd_sha256"]==sha256(rrd)
                assert previous["source_sha256"]==entry["record_sha256"]
                frame_meta=previous["frames"];durations=previous["durations_ms"]
            else:
                frames_dir=out/(args.mode+"_video_frames");frames_dir.mkdir(exist_ok=True)
                frame_meta=[];images=[];capture_started=time.perf_counter()
                # Every sixth recorded sample, plus the actual last sample; no interpolation.
                video_indices=sorted(set(list(range(0,len(d["sample_id"]),6))+[len(d["sample_id"])-1]))
                for number,k in enumerate(video_indices):
                    ns=round((entry["offset"]+float(d["observation_time"][k]))*1e9)
                    tool("set_time",{"timeline":"physical_display_s","time":ns,"play":False})
                    tool("wait_for",{"min_steps":2,"timeout_secs":5})
                    assert current(state())==ns
                    path=frames_dir/f"{number:04d}.png"
                    tool("screenshot",{"save_path":str(path),"pixels_per_point":1})
                    frame_meta.append(dict(file=path.relative_to(ROOT).as_posix(),sample=k,
                        physical_time=float(d["observation_time"][k]),sha256=sha256(path)))
                    im=Image.open(path).convert("RGB");im.thumbnail((1600,1000));images.append(im)
                    if number%25==0:print("Captured video frames",number+1,"/",len(video_indices),flush=True)
                result["video_capture_wall_s"]=time.perf_counter()-capture_started
                durations=[max(1,round((video_indices[i+1]-k)*.5/15*1000)) if i+1<len(video_indices) else 33 for i,k in enumerate(video_indices)]
                video=out/(args.mode+"_test00.webp")
                images[0].save(video,save_all=True,append_images=images[1:],duration=durations,loop=0,quality=88,method=4)
                for im in images:im.close()
            # Also test real continuous playback, rather than inferring motion from seeks.
            tool("set_time",{"timeline":"physical_display_s","time":0,"play":True})
            live=[];deadline=time.monotonic()+55
            while time.monotonic()<deadline:
                tool("wait_for",{"min_steps":1,"timeout_secs":2})
                before=current(state())
                if before>=round(d["observation_time"][-1]*1e9):
                    tool("set_time",{"timeline":"physical_display_s","time":round(d["observation_time"][-1]*1e9),"play":False})
                    before=current(state())
                path=evidence/f"{prefix}_live_{len(live):02d}.png"
                tool("screenshot",{"save_path":str(path),"pixels_per_point":1})
                after=current(state());live.append(dict(file=path.relative_to(ROOT).as_posix(),before_ns=before,after_ns=after,sha256=sha256(path)))
                if after>=round(d["observation_time"][-1]*1e9):break
            assert len(live)>=3 and live[-1]["after_ns"]>=round(d["observation_time"][-1]*1e9)
            assert all(b["before_ns"]>=a["before_ns"] for a,b in zip(live,live[1:]))
            tool("set_time",{"timeline":"physical_display_s","time":round(d["observation_time"][-1]*1e9),"play":False})
            write_json(out/("video_manifest_"+args.mode+".json"),dict(file=video.relative_to(ROOT).as_posix(),sha256=sha256(video),
                format="animated WebP, native Rerun renders",
                duration_ms=sum(durations),durations_ms=durations,frames=frame_meta,playback_speed=15,
                source_record=entry["record"],source_sha256=entry["record_sha256"],rrd_sha256=sha256(rrd),
                continuous_playback_frames=live,mp4_created=False,
                mp4_reason="Optional video exported as animated WebP; native Rerun frames"))
            print("Saved",video,flush=True)
        result["performance"]=dict(rrd_bytes=rrd.stat().st_size,load_to_first_seek_s=load_time,
            screenshot_calls=timings,total_elapsed_s=time.perf_counter()-started,
            viewer_memory_status=Path(f"/proc/{viewer.pid}/status").read_text(),
            window=[2240,1400],renderer="native headless software; elapsed includes IPC/readback/PNG; not GUI FPS")
        write_json(evidence/("screenshots_"+prefix+".json"),result)
        print("Verified",prefix,"screenshots",len(screenshots),"elapsed",result["performance"]["total_elapsed_s"],flush=True)
    finally:
        for p in [mcp,viewer]:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        logfile.close()
if __name__=="__main__":main()
