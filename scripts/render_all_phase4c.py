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
    os.chdir(ROOT);out=ROOT/"outputs/phase4c";evidence=ROOT/"docs/evidence_phase4c";evidence.mkdir(parents=True,exist_ok=True)
    source_dir=ROOT/"outputs/phase3" if args.baseline else out
    prefix="baseline" if args.baseline else args.mode
    rrd=source_dir/(args.mode+".rrd")
    started=time.perf_counter();timings=[];load_time=None
    env={**os.environ,"RERUN_ANALYTICS_ENABLED":"false","RUST_LOG":"error"}
    import rerun_cli
    binary=str(Path(rerun_cli.__file__).parent/"rerun")
    logfile=(out/"native-all-frames.log").open("w")
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
        rpc("initialize",dict(protocolVersion="2024-11-05",capabilities={},clientInfo={"name":"FlyRendezvous-4C-all-frames","version":"1"}))
        mcp.stdin.write(json.dumps(dict(jsonrpc="2.0",method="notifications/initialized"))+"\n");mcp.stdin.flush()
        time.sleep(2);tool("connect",{"endpoint":"http://127.0.0.1:9890"})
        manifest=json.loads((out/"viewer_demo.json").read_text())
        from PIL import Image
        records=[];render_started=time.perf_counter()
        path=out/"all_frames_last.png"
        for entry in manifest["episodes"]:
            assert sha256(entry["record"])==entry["record_sha256"]
            with np.load(entry["record"]) as z:
                for k,t in enumerate(z["observation_time"]):
                    ns=round((entry["offset"]+float(t))*1e9)
                    tool("set_time",{"timeline":"physical_display_s","time":ns,"play":False})
                    tool("wait_for",{"min_steps":2,"timeout_secs":5})
                    assert current(state())==ns
                    tool("screenshot",{"save_path":str(path),"pixels_per_point":1})
                    with Image.open(path) as im:
                        assert im.size==(2240,1400)
                        crop=np.array(im.crop((1325,945,1830,1230)).convert("RGB"))
                        assert float(crop.std())>3
                    records.append(dict(trial=entry["id"],sample=k,time_ns=ns,png_sha256=sha256(path),pilot_pixel_std=float(crop.std())))
                    if len(records)%100==0:print("Rendered",len(records),"/777",flush=True)
        assert len(records)==777
        write_json(out/"all_frames_render.json",dict(status="passed",rendered_samples=len(records),
            rrd_sha256=sha256(rrd),window=[2240,1400],renderer="native Rerun 0.37.1 headless software",
            method="seek every saved sample; wait two render steps; verify time; screenshot full real frame; verify nonblank Pilot crop",
            wall_s=time.perf_counter()-render_started,source_episodes=manifest["episodes"],frames=records,
            retained_last_png=str(path.relative_to(ROOT)),note="777 frames actually rendered; hashes retained, scratch PNG overwritten per frame. Pixel checks detect blank panels, not aesthetic quality."))
        print("Verified all",len(records),"frames",flush=True)
    finally:
        for p in [mcp,viewer]:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        logfile.close()
if __name__=="__main__":main()
