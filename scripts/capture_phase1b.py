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
    os.chdir(ROOT);out=ROOT/"outputs/phase1b";evidence=ROOT/"docs/evidence_phase1b";evidence.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"RERUN_ANALYTICS_ENABLED":"false","RUST_LOG":"error"}
    binary=str(ROOT/".venv/bin/rerun")
    logfile=(out/"native-viewer.log").open("w")
    viewer=subprocess.Popen([binary,str(out/"phase1b.rrd"),"--headless","--bind","127.0.0.1","--port","9890","--window-size","1800x1050"],stdout=logfile,stderr=logfile,env=env)
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
        result=rpc("tools/call",dict(name=name,arguments=args or {}))
        if result.get("isError"):raise RuntimeError(result)
        return result
    def state():
        result=tool("viewer_state")
        if "structuredContent" in result:return result["structuredContent"]
        return json.loads(next(c["text"] for c in result["content"] if c["type"]=="text"))
    def current(s):return s["recordings"][0]["current_time"]["time"]
    try:
        rpc("initialize",dict(protocolVersion="2024-11-05",capabilities={},clientInfo={"name":"FlyRendezvous-verification","version":"1"}))
        mcp.stdin.write(json.dumps(dict(jsonrpc="2.0",method="notifications/initialized"))+"\n");mcp.stdin.flush()
        time.sleep(2)
        tool("connect",{"endpoint":"http://127.0.0.1:9890"})
        initial=state()
        with np.load(out/"sequence_projection.npz",allow_pickle=False) as z:p={k:z[k] for k in z.files}
        with np.load(out/"sequence.npz",allow_pickle=False) as z:stages=z["stage"].copy()
        # Select real extrema after 0.5 s, excluding initial stimulus onset.
        candidates=np.flatnonzero(p["input_time"]>=.5)
        indices=[int(candidates[np.argmin(p["rms"][candidates])]),int(candidates[np.argmax(p["rms"][candidates])])]
        screenshots=[]
        for label,k in zip(["low","high"],indices):
            ns=round(float(p["display_time"][k])*1e9)
            tool("set_time",{"timeline":"input_sample_s","time":ns,"play":False})
            tool("wait_for",{"min_steps":5,"timeout_secs":5})
            observed=state();assert current(observed)==ns
            path=evidence/(label+".png")
            tool("screenshot",{"save_path":str(path),"pixels_per_point":1})
            screenshots.append(dict(file=path.relative_to(ROOT).as_posix(),sha256=sha256(path),
                trial="sequence",stage=str(stages[k]),sample=k,input_time=float(p["input_time"][k]),
                response_time=float(p["response_time"][k]),display_time=float(p["display_time"][k]),
                rms=float(p["rms"][k]),rgb=p["rgb"][k].tolist(),viewer_time_ns=current(observed)))
        start_ns=round(float(p["display_time"][50])*1e9)
        tool("set_time",{"timeline":"input_sample_s","time":start_ns,"play":True})
        tool("wait_for",{"min_steps":20,"timeout_secs":5})
        playing=state();advanced=current(playing);assert advanced>start_ns
        tool("set_time",{"timeline":"input_sample_s","time":advanced,"play":False})
        tool("wait_for",{"min_steps":10,"timeout_secs":5})
        paused=state();assert current(paused)==advanced
        result=dict(status="passed",renderer="native Rerun 0.37.1 headless, software rasterizer",
            interface="Rerun viewer-mcp; Windows GUI mouse controls not tested",
            rrd_sha256=sha256(out/"phase1b.rrd"),screenshots=screenshots,
            controls=dict(seek=True,play_advanced_from_ns=start_ns,play_advanced_to_ns=advanced,
                          pause_time_ns=current(paused),pause_held=True),initial_viewer_state=initial)
        write_json(evidence/"screenshots.json",result)
        print(json.dumps(result,indent=2))
    finally:
        for p in [mcp,viewer]:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        logfile.close()
if __name__=="__main__":main()
