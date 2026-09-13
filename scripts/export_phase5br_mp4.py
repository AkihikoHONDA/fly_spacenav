"""Export the previously verified native Rerun PNGs to MP4 without new rendering."""
import json,math,subprocess,sys,os
from pathlib import Path
import numpy as np
from PIL import Image
from flyrendezvous.recording import sha256,write_json
from flyrendezvous.screening import assert_unchanged

ROOT=Path(__file__).resolve().parents[1]
CONDITION=os.environ["PHASE5BR_CONDITION"]
DEMO=ROOT/"outputs/phase5br/demo"/CONDITION
OUT=ROOT/"outputs/phase5br/mp4"

def rgb_frame(path):
    with Image.open(path) as im:
        im=im.convert("RGB");im.thumbnail((1600,1000))
        assert im.size==(1600,1000)
        return np.asarray(im).copy()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(ROOT/".tools/video/python"))
    import imageio_ffmpeg
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    meta=json.loads((DEMO/"video_manifest_demo.json").read_text())
    assert sha256(DEMO/"demo.rrd")==meta["rrd_sha256"]
    assert sha256(ROOT/meta["source_record"])==meta["source_sha256"]
    with np.load(ROOT/meta["source_record"]) as z:total_frames=len(z["sample_id"])
    frames=meta["frames"]
    for frame in frames:assert sha256(ROOT/frame["file"])==frame["sha256"]
    # 30 video frames/s and 15 physical seconds/s = one original .5 s sample/frame.
    # Existing captures are every 6 samples plus the last sample. Hold, never interpolate.
    samples=[f["sample"] for f in frames]
    repeat=[samples[i+1]-k if i+1<len(samples) else 1 for i,k in enumerate(samples)]
    assert samples[0]==0 and samples[-1]==total_frames-1 and sum(repeat)==total_frames
    output=OUT/("test00_"+CONDITION+".mp4")
    cmd=[ffmpeg,"-y","-hide_banner","-f","rawvideo","-pixel_format","rgb24","-video_size","1600x1000",
        "-framerate","30","-i","pipe:0","-an","-c:v","libx264","-preset","medium","-crf","16",
        "-pix_fmt","yuv420p","-threads","4","-movflags","+faststart",str(output)]
    with (OUT/(CONDITION+"_encode.log")).open("w") as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
        try:
            for frame,count in zip(frames,repeat):
                raw=rgb_frame(ROOT/frame["file"]).tobytes()
                for _ in range(count):p.stdin.write(raw)
            p.stdin.close()
            assert p.wait()==0
        finally:
            if p.poll() is None:p.kill();p.wait()
    # Decode every output frame and compare to the exact source PNG resized as encoded.
    decode_cmd=[ffmpeg,"-v","error","-i",str(output),"-f","rawvideo","-pix_fmt","rgb24","pipe:1"]
    errors=[];count=0
    with (OUT/(CONDITION+"_decode.log")).open("w") as log:
        p=subprocess.Popen(decode_cmd,stdout=subprocess.PIPE,stderr=log)
        try:
            for frame,n in zip(frames,repeat):
                reference=rgb_frame(ROOT/frame["file"]).astype(np.float32)
                for _ in range(n):
                    data=p.stdout.read(1600*1000*3)
                    assert len(data)==1600*1000*3,"Truncated decoded frame"
                    decoded=np.frombuffer(data,dtype=np.uint8).reshape(1000,1600,3)
                    mse=float(np.mean((decoded.astype(np.float32)-reference)**2))
                    errors.append(mse);count+=1
            assert not p.stdout.read(1),"Unexpected extra frame"
            assert p.wait()==0
        finally:
            if p.poll() is None:p.kill();p.wait()
    # Frame CRC output exposes exact stream time base, PTS and frame durations.
    timing=subprocess.run([ffmpeg,"-v","error","-i",str(output),"-map","0:v:0","-f","framecrc","-"],
        capture_output=True,text=True,check=True).stdout
    (OUT/(CONDITION+"_decoded_timing.txt")).write_text(timing)
    tb=next(line for line in timing.splitlines() if line.startswith("#tb 0:")).split(":",1)[1].strip()
    assert tb=="1/30",tb
    records=[line.split(",") for line in timing.splitlines() if line and not line.startswith("#")]
    assert len(records)==total_frames
    assert [int(r[2]) for r in records]==list(range(total_frames))
    assert all(int(r[3])==1 for r in records)
    psnr=[10*math.log10(255**2/e) if e else 100. for e in errors]
    assert min(psnr)>30,"Unexpectedly large encoding distortion"
    old_count=assert_unchanged(json.loads((ROOT/"outputs/phase4c/prior_hashes.json").read_text()))
    prior_count=old_count
    version=subprocess.run([ffmpeg,"-version"],capture_output=True,text=True,check=True).stdout
    (OUT/(CONDITION+"_ffmpeg-version.txt")).write_text(version)
    meta.update(mp4_created=True,mp4_file=output.relative_to(ROOT).as_posix(),mp4_sha256=sha256(output))
    meta.pop("mp4_reason",None)
    write_json(DEMO/"video_manifest_demo.json",meta)
    result=dict(status="passed",file=output.relative_to(ROOT).as_posix(),sha256=sha256(output),bytes=output.stat().st_size,
        codec="H.264 / libx264",pixel_format="yuv420p",resolution=[1600,1000],fps=30,frames=count,duration_s=count/30,
        playback_speed=15,unique_rendered_frames=len(frames),frame_repeats=repeat,
        timing="Original sample index / 30 seconds; captured images held until the next capture, no interpolated activity",
        psnr_min_db=min(psnr),psnr_mean_db=float(np.mean(psnr)),decoded_frame_time_base=tb,
        source_manifest_sha256=sha256(DEMO/"video_manifest_demo.json"),
        source_rrd_sha256=meta["rrd_sha256"],source_record_sha256=meta["source_sha256"],
        ffmpeg_binary=Path(ffmpeg).relative_to(ROOT).as_posix(),ffmpeg_sha256=sha256(ffmpeg),ffmpeg_version=version.splitlines()[0],
        protected_old_files_unchanged=old_count,protected_prior_files_unchanged=prior_count,
        new_inference=0,new_control_experiments=0,encoder_reused_from=".tools/video/python")
    write_json(OUT/(CONDITION+"_verification.json"),result)
    print(json.dumps({k:v for k,v in result.items() if k!="frame_repeats"},indent=2))

if __name__=="__main__":
    import os
    os.chdir(ROOT);main()
