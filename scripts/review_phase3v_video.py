"""Decode actual Rerun animation and verify its source hashes and timing."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from flyrendezvous.recording import sha256,write_json
out=Path("outputs/phase3v");m=json.loads((out/"video_manifest.json").read_text())
assert sha256(m["file"])==m["sha256"] and sha256(m["source_record"])==m["source_sha256"]
assert sha256(out/"phase3v_demo.rrd")==m["rrd_sha256"]
im=Image.open(m["file"]);assert im.n_frames==len(m["frames"])
total=0;previous=None;diff=[]
for k,f in enumerate(m["frames"]):
    assert sha256(f["file"])==f["sha256"];im.seek(k);a=np.array(im.convert("RGB"));total+=im.info["duration"]
    assert im.info["duration"]==m["durations_ms"][k]
    if previous is not None:diff.append(float(np.abs(a.astype(float)-previous).mean()))
    previous=a.astype(float)
    if k in [0,im.n_frames//2,im.n_frames-1]:im.convert("RGB").save(f"docs/evidence_phase3v/video_decoded_{k:03d}.png")
assert total==m["duration_ms"] and min(diff)>0
live=m["continuous_playback_frames"]
assert len(live)>=3 and all(b["before_ns"]>=a["before_ns"] for a,b in zip(live,live[1:]))
for f in live:assert sha256(f["file"])==f["sha256"]
with np.load(m["source_record"]) as d:assert live[-1]["after_ns"]>=round(d["observation_time"][-1]*1e9)
write_json(out/"video_review.json",dict(status="passed",decoded_frames=im.n_frames,duration_ms=total,
    size=im.size,all_adjacent_frames_differ=True,continuous_frames=len(live),video_sha256=m["sha256"],
    note="Native headless play/seek/pause and decoded frames; not a real-time GUI performance benchmark."))
print(im.n_frames,total)
