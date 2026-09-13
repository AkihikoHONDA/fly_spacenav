"""Two views of the SAME saved held-out evaluation; no inference or state update."""
import json
from pathlib import Path
import numpy as np
from .recording import sha256,write_json
from .phase3_runtime import checked_trial,load_config
from .geometry_phase3 import Teacher
from .display_coordinates import rerun_coordinates
from .activity_display import TYPES,relative_activity,check_timing
from .viewer import lattice_xy,colors
from .projection import rms_colors
from .morphology import read_precomputed
from .anatomy import load_meshes

OUT=Path("outputs/phase3v")
SOURCE=Path("outputs/phase3")
from .representatives_phase3v import TYPES3,PALETTE,intensity_color,load_representatives
TYPE_COLORS=[[236,166,63],[105,187,143],[116,168,230],[214,130,204],[212,214,115]]

def display_data(d,scales):
    check_timing(d)
    assert list(d["display_types"])==list(TYPES)
    delta=d["display_activity"].astype(float)-d["baseline"][d["display_indices"]]
    raw=np.sqrt(np.mean(delta**2,axis=2))
    for j,name in enumerate(TYPES):
        np.testing.assert_allclose(raw[:,j],d["type_rms"][:,np.flatnonzero(d["all_types"]==name).item()],atol=1e-12)
    return delta,raw,relative_activity(raw,scales["p05"],scales["p95"])

def phase(state,acceleration,time,goal):
    if time<10:return "OBSERVE (u=0)"
    if np.linalg.norm(state[:2]-goal)<.25 and np.linalg.norm(state[2:])<.01:return "NEAR / HOLD"
    if state[2:]@acceleration<0:return "BRAKING"
    return "APPROACH"

def build(mode):
    import rerun as rr
    import rerun.blueprint as bp
    cfg=load_config();goal=Teacher(cfg).goal[:2]
    scales=json.loads((SOURCE/"display_scales.json").read_text())
    lock=json.loads((SOURCE/"model_lock.json").read_text())
    testlock=json.loads((SOURCE/"test_started.json").read_text())
    assert sha256(SOURCE/"readout.npz")==lock["readout_sha256"]==testlock["readout_sha256"]
    assert sha256(SOURCE/"display_scales.json")==testlock["display_scales_sha256"] and not scales["test_used"]
    representatives=load_representatives()
    brain_eye=bp.archetypes.EyeControls3D(position=[810,86,183],look_target=[708,298,180],eye_up=[0,0,1])
    orbit=bp.Spatial2DView(origin="/orbit",name="Standoff rendezvous [m] | down: central body | left: along-track")
    sensor=bp.Spatial2DView(origin="/input",name="Sensor | fixed boresight | 64 x 64")
    bars=bp.Spatial2DView(origin="/bars",name="Type-relative activity | q + raw RMS")
    brain=bp.Spatial3DView(origin="/brain",contents=["/brain/context/ME_R/**","/brain/context/LO_R/**","/brain/context/LOP_R/**","/brain/representatives/**"],
        name="Brain | T2 orange / T4a blue / T5d magenta | FAFB14.1 [um]",
        background=[10,14,22],line_grid=False,eye_controls=brain_eye)
    maps={name:bp.Spatial2DView(origin="/maps/"+name,name=f"{name} | signed delta +/-{scales['signed_map_limit'][j]:.3f}") for j,name in enumerate(TYPES)}
    status=bp.TextDocumentView(origin="/status",name="Saved learner closed loop | compact status")
    legend=bp.TextDocumentView(origin="/legend",name="How to read the neural displays")
    if mode=="demo":
        layout=bp.Vertical(
            bp.Horizontal(orbit,bp.Vertical(brain,legend,row_shares=[10,1]),column_shares=[1,1.25]),
            bp.Horizontal(sensor,maps["T2"],maps["T4a"],maps["T5d"],
                bp.Vertical(bars,status,row_shares=[1.1,.9]),column_shares=[1,1,1,1,1.25]),
            row_shares=[2.15,1])
    else:
        layout=bp.Vertical(
            bp.Horizontal(orbit,sensor,brain,column_shares=[1,.75,1.5]),
            bp.Horizontal(*maps.values()),
            bp.Horizontal(bp.TimeSeriesView(origin="/series/raw",name="Raw RMS"),
                bp.TimeSeriesView(origin="/series/q",name="Fixed relative q"),
                bp.TimeSeriesView(origin="/series/acceleration",name="Applied a"),
                bp.TimeSeriesView(origin="/series/error",name="Goal error"),
                bp.TimeSeriesView(origin="/series/speed",name="Speed")),
            bp.Horizontal(status,legend,bp.TextDocumentView(origin="/timing",name="Timing")),
            row_shares=[1.4,1,.8,.5])
    rr.init("FlyRendezvous-Phase3V-"+mode,spawn=False,strict=True)
    rr.save(str(OUT/("phase3v_"+mode+".rrd")))
    rr.send_blueprint(bp.Blueprint(layout,bp.TimePanel(state="collapsed",timeline="physical_display_s",
        playback_speed=15.,play_state="paused"),collapse_panels=True))
    # Neutral wireframe context: no opaque surfaces occluding representative branches.
    for name,vertices,faces,normals in load_meshes():
        links=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
        rr.log("/brain/context/"+name,rr.LineStrips3D(vertices[links],colors=[42,49,62],radii=rr.Radius.ui_points(.22)),static=True)
    theta=np.linspace(0,2*np.pi,181);circle=np.column_stack([np.cos(theta),np.sin(theta)])
    rr.log("/orbit/target",rr.Points2D([[0,0]],radii=1,colors=[180,185,195],labels=["target sphere R=1 m"]),static=True)
    rr.log("/orbit/standoff",rr.LineStrips2D(rerun_coordinates(5*circle),colors=[65,150,115],radii=.035),static=True)
    rr.log("/orbit/standoff_label",rr.Points2D([[4,4]],radii=rr.Radius.ui_points(0),colors=[90,200,145],labels=["5 m standoff circle"]),static=True)
    rr.log("/orbit/goal",rr.Points2D([rerun_coordinates(goal)],radii=.18,colors=[70,245,155],labels=["selected goal | clearance 4 m"]),static=True)
    rr.log("/orbit/bounds",rr.LineStrips2D([[-19,-7],[7,-7],[7,19],[-19,19],[-19,-7]],colors=[40,45,55]),static=True)
    rr.log("/orbit/directions",rr.Arrows2D(origins=[[3,13],[3,13]],vectors=[[-4,0],[0,4]],colors=[170,175,190]),static=True)
    rr.log("/orbit/direction_labels",rr.Points2D([[-1,12],[3,18]],radii=rr.Radius.ui_points(0),
        labels=["+y along-track","-x central body"],colors=[210,215,225]),static=True)
    rows=np.arange(5)*18
    rr.log("/bars/background",rr.LineStrips2D([[[0,y],[100,y]] for y in rows],radii=3.5,colors=[45,50,60],draw_order=0),static=True)
    rr.log("/bars/bounds",rr.LineStrips2D([[-5,-14],[105,-14],[105,83],[-5,83],[-5,-14]],colors=[45,50,60]),static=True)
    rr.log("/legend",rr.TextDocument(
        "Representative morphologies · Color intensity = within-type relative response · "
        "No one-to-one mapping to Flyvis model cells",media_type="text/markdown"),static=True)
    results=json.loads((SOURCE/"evaluation.json").read_text())["learner"]
    chosen=[results[0],next(m for m in results if m["category"]=="near")]
    failures=[m for m in results if not m["success"]]
    if failures:chosen.append(failures[0])
    chosen=list({m["id"]:m for m in chosen}.values())
    manifest=[];offset=0.
    for m in chosen:
        d=checked_trial(m);delta,raw,q=display_data(d,scales)
        for j,name in enumerate(TYPES):
            for kind in ["raw","q"]:rr.log(f"/series/{kind}/{m['id']}/{name}",rr.SeriesLines(colors=TYPE_COLORS[j],names=name),static=True)
        for k,t in enumerate(d["observation_time"]):
            rr.set_time("physical_display_s",duration=offset+float(t))
            s=d["states"][k];xy=rerun_coordinates(s[:2]);a=d["u_applied"][k]
            rr.log("/orbit/trail",rr.LineStrips2D(rerun_coordinates(d["states"][:k+1,:2]),colors=[100,180,255]))
            rr.log("/orbit/craft",rr.Points2D([xy],radii=.15,colors=[255,230,120]))
            rr.log("/orbit/velocity",rr.Arrows2D(origins=[xy],vectors=[rerun_coordinates(s[2:])*20],colors=[100,220,255]))
            rr.log("/orbit/acceleration",rr.Arrows2D(origins=[xy],vectors=[rerun_coordinates(a)*400],colors=[255,170,70]))
            rr.log("/input/image",rr.Image(np.rint(d["images"][k]*255).astype(np.uint8)))
            rr.log("/bars/fill",rr.LineStrips2D([[[0,y],[100*q[k,j],y]] for j,y in enumerate(rows)],
                colors=np.column_stack([TYPE_COLORS,np.where(q[k]>0,255,0)]),radii=3.5,draw_order=1))
            rr.log("/bars/labels",rr.Points2D(np.column_stack([np.full(5,50),rows-6]),
                labels=[f"{name}  q {q[k,j]:.2f}  RMS {raw[k,j]:.4f}" for j,name in enumerate(TYPES)],
                radii=rr.Radius.ui_points(0),colors=[235,235,235]))
            for j,name in enumerate(TYPES):
                rr.log("/maps/"+name+"/hex",rr.Points2D(lattice_xy(d["display_u"][j],d["display_v"][j]),
                    colors=colors(delta[k,j],scales["signed_map_limit"][j]),radii=.78))
                rr.log(f"/series/raw/{m['id']}/{name}",rr.Scalars(raw[k,j]))
                rr.log(f"/series/q/{m['id']}/{name}",rr.Scalars(q[k,j]))
            for name,(xyz,edges) in representatives.items():
                j=TYPES.index(name);rgb=intensity_color(name,q[k,j])
                rr.log("/brain/representatives/"+name+"/arbor",rr.LineStrips3D(xyz[edges],colors=rgb,radii=rr.Radius.ui_points(2.8)))
                anchor=xyz[np.argmax(xyz[:,2])]
                rr.log("/brain/representatives/"+name+"/label",rr.Points3D([anchor],radii=rr.Radius.ui_points(0),
                    labels=[f"{name}  q {q[k,j]:.2f}"],colors=PALETTE[name]))
            error=np.linalg.norm(s[:2]-goal);speed=np.linalg.norm(s[2:]);distance=np.linalg.norm(s[:2])
            for j,axis in enumerate(["ax","ay"]):rr.log(f"/series/acceleration/{m['id']}/{axis}",rr.Scalars(a[j]))
            rr.log("/series/error/"+m["id"],rr.Scalars(error));rr.log("/series/speed/"+m["id"],rr.Scalars(speed))
            rr.log("/status",rr.TextDocument(
                f"**{m['id']} · {t:.1f} s · {phase(s,a,t,goal)}**\n\n"
                f"Goal error {error:.3f} m · speed {speed:.4f} m/s\n\n"
                f"Clearance {distance-1:.2f} m · result {m['termination_reason']}\n\n"
                "Saved image-only closed loop · fixed sensor camera",media_type="text/markdown"))
            rr.log("/timing",rr.TextDocument(
                f"Sample {k}; observation {t:.1f} physical s.\n\n"
                f"Neural input {d['neural_input_time'][k]:.2f} → response {d['neural_response_time'][k]:.2f} s.\n\n"
                f"Applied interval [{t:.1f}, {t+.5:.1f}) physical s. Time ratio 50; playback 15×.\n\n"
                "Image-only learned closed loop. Original test recording; no re-inference.",media_type="text/markdown"))
        manifest.append(dict(id=m["id"],offset=offset,frames=m["samples"],record=m["record"],record_sha256=m["record_sha256"],
            outcome=m["termination_reason"]))
        if m["id"]==chosen[-1]["id"]:continue # Keep terminal sample visible; no reset without a next trial.
        rr.set_time("physical_display_s",duration=offset+m["samples"]*.5)
        for path in ["/input","/maps","/bars/fill","/bars/labels","/brain/representatives","/orbit/trail","/orbit/craft","/orbit/velocity","/orbit/acceleration"]:
            rr.log(path,rr.Clear(recursive=True))
        rr.log("/status",rr.TextDocument("RESET | independent next episode"))
        offset+=m["samples"]*.5+10
    rr.get_global_data_recording().flush()
    write_json(OUT/("viewer_"+mode+".json"),dict(mode=mode,episodes=manifest,
        scales_sha256=sha256(SOURCE/"display_scales.json"),new_inference=False,
        source="original once-only held-out learner records",morphology_count=3,
        timeline="physical_display_s",playback_speed=15))
    rr.disconnect()
    print("Saved",mode,flush=True)
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=["demo","analysis","both"],default="both");args=p.parse_args()
    for mode in (["demo","analysis"] if args.mode=="both" else [args.mode]):build(mode)
