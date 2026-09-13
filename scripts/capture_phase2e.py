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
    os.chdir(ROOT);out=ROOT/"outputs/phase2e";evidence=ROOT/"docs/evidence_phase2e";evidence.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"RERUN_ANALYTICS_ENABLED":"false","RUST_LOG":"error"}
    binary=str(ROOT/".venv/bin/rerun")
    logfile=(out/"native-viewer.log").open("w")
    viewer=subprocess.Popen([binary,str(out/"phase2e.rrd"),"--headless","--bind","127.0.0.1","--port","9890","--window-size","1920x1200"],stdout=logfile,stderr=logfile,env=env)
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
        manifest=json.loads((out/"viewer_manifest.json").read_text())
        entry=manifest["episodes"][0]
        with np.load(entry["record"],allow_pickle=False) as z:d={k:z[k] for k in z.files}
        selected=np.flatnonzero(d["cell_type"]=="T4a")
        delta=d["activity"][:,selected].astype(float)-d["baseline"][selected]
        rms=np.sqrt(np.mean(delta**2,axis=1))
        indices=[40,int(np.argmax(d["u_applied"][:,0])),len(d["sample_id"])-1]
        screenshots=[]
        for label,k in zip(["approach","braking","hold"],indices):
            display_time=float(entry["offset"]+d["observation_time"][k]);ns=round(display_time*1e9)
            tool("set_time",{"timeline":"physical_display_s","time":ns,"play":False})
            tool("wait_for",{"min_steps":5,"timeout_secs":5})
            observed=state();assert current(observed)==ns
            path=evidence/(label+".png")
            tool("screenshot",{"save_path":str(path),"pixels_per_point":1})
            screenshots.append(dict(file=path.relative_to(ROOT).as_posix(),sha256=sha256(path),
                trial=entry["id"],sample=k,physical_time=float(d["observation_time"][k]),
                neural_input_time=float(d["neural_input_time"][k]),neural_response_time=float(d["neural_response_time"][k]),
                display_time=display_time,rms=float(rms[k]),applied_acceleration=d["u_applied"][k].tolist(),
                state=d["states"][k].tolist(),viewer_time_ns=current(observed),
                source_record=entry["record"],record_sha256=entry["record_sha256"]))
        start_ns=round((entry["offset"]+25.)*1e9)
        tool("set_time",{"timeline":"physical_display_s","time":start_ns,"play":True})
        tool("wait_for",{"min_steps":20,"timeout_secs":5})
        playing=state();advanced=current(playing);assert advanced>start_ns
        tool("set_time",{"timeline":"physical_display_s","time":advanced,"play":False})
        tool("wait_for",{"min_steps":10,"timeout_secs":5})
        paused=state();assert current(paused)==advanced
        result=dict(status="passed",renderer="native Rerun 0.37.1 headless, software rasterizer",
            interface="Rerun viewer-mcp; Windows GUI mouse controls not tested",
            rrd_sha256=sha256(out/"phase2e.rrd"),screenshots=screenshots,
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
