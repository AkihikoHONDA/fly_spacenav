"""Five-type Rerun comparison of saved logs, with one T4a arbor in two scale views."""
import json
from pathlib import Path
import numpy as np
from .recording import sha256,write_json
from .phase2_runtime import checked_trial,load_config
from .display_coordinates import rerun_coordinates
from .viewer import lattice_xy,colors
from .projection import rms_colors
from .morphology import read_precomputed
from .activity_display import TYPES,relative_activity

OUT=Path("outputs/phase2f")
TYPE_COLORS=[[236,166,63],[105,187,143],[116,168,230],[214,130,204],[212,214,115]]

def build():
    import rerun as rr
    import rerun.blueprint as rrb
    cfg=load_config();disp=cfg["display"]
    scales=json.loads((OUT/"display_scales.json").read_text())
    assert scales["types"]==list(TYPES)
    assert scales["readout_sha256"]==sha256("outputs/phase2/readout.npz")
    mapping=json.loads(Path("docs/anatomy_mapping_phase1b.json").read_text())
    for name,m in mapping["files"].items():assert sha256(name)==m["sha256"]
    xyz,edges,_=read_precomputed("assets/phase1b/720575940605852192.precomputed")
    xyz=xyz.astype(float)*.001;center=(xyz.min(0)+xyz.max(0))/2
    eye=rrb.archetypes.EyeControls3D(position=(center+[0,-155,0]).tolist(),look_target=center.tolist(),eye_up=[0,0,1])
    rr.init("FlyRendezvous-Phase2F",spawn=False,strict=True);rr.save(str(OUT/"phase2f.rrd"))
    map_views=[rrb.Spatial2DView(origin="/maps/"+name,name=f"{name}: signed delta +/-{scales['signed_map_limit'][j]:.3f}") for j,name in enumerate(TYPES)]
    rr.send_blueprint(rrb.Blueprint(rrb.Vertical(
        rrb.Horizontal(
            rrb.Spatial2DView(origin="/orbit",name="Orbit: down central body / left along-track"),
            rrb.Spatial2DView(origin="/input",name="Sensor: fixed -x camera"),
            rrb.Spatial2DView(origin="/bars",name="Within-type q [0,1] / raw RMS"),
            rrb.Spatial3DView(origin="/morphology/absolute",name="T4a A: absolute RMS 0..0.22",
                background=[15,20,30],line_grid=False,eye_controls=eye),
            rrb.Spatial3DView(origin="/morphology/relative",name="T4a B: fixed relative p05..p95",
                background=[15,20,30],line_grid=False,eye_controls=eye),
            column_shares=[.9,.75,1.25,1,1]),
        rrb.Horizontal(*map_views),
        rrb.Horizontal(
            rrb.TimeSeriesView(origin="/series/raw",name="Raw RMS / same model-unit scale",
                axis_y=rrb.ScalarAxis(range=[0,.6],zoom_lock=True)),
            rrb.TimeSeriesView(origin="/series/q",name="Relative q / not absolute type comparison",
                axis_y=rrb.ScalarAxis(range=[0,1],zoom_lock=True)),
            rrb.TextDocumentView(origin="/readout",name="Timing / fixed-scale legend"),column_shares=[1,1,1.2]),
        row_shares=[1.3,1.1,.85]),
        rrb.TimePanel(state="collapsed",timeline="physical_display_s",playback_speed=15.,play_state="paused"),
        collapse_panels=True))
    compass=np.array([32.,0.]);directions=np.array([[4,0],[-4,0],[0,5],[0,-5]])
    rr.log("/orbit/axes",rr.Arrows2D(origins=rerun_coordinates(np.repeat(compass[None],4,axis=0)),
        vectors=rerun_coordinates(directions),colors=[180,180,180]),static=True)
    for name,location,label in [("up",[38,0],"+x outward"),("down",[26,0],"-x central body"),
        ("left",[32,12],"+y along-track"),("right",[32,-12],"-y retrograde")]:
        rr.log("/orbit/directions/"+name,rr.Points2D(rerun_coordinates([location]),radii=rr.Radius.ui_points(0),labels=[label],colors=[220,220,220]),static=True)
    rr.log("/orbit/goal",rr.Points2D(rerun_coordinates([[10,0]]),radii=.15,colors=[70,220,160],labels=["goal"]),static=True)
    rr.log("/orbit/target",rr.Points2D([[0,0]],radii=.5,colors=[190,190,190]),static=True)
    rr.log("/orbit/bounds",rr.LineStrips2D(rerun_coordinates([[-3,20],[40,20],[40,-20],[-3,-20],[-3,20]]),colors=[45,50,60]),static=True)
    rows=np.arange(5)*18
    rr.log("/bars/background",rr.LineStrips2D(np.array([[[0,y],[100,y]] for y in rows]),colors=[45,50,60],radii=3.5,draw_order=0),static=True)
    rr.log("/bars/bounds",rr.LineStrips2D([[-5,-14],[105,-14],[105,83],[-5,83],[-5,-14]],colors=[45,50,60]),static=True)
    manifest=[];offset=0.
    for m in json.loads(Path("outputs/phase2/replays.json").read_text()):
        d=checked_trial(m)
        with np.load(OUT/(m["id"]+"_display.npz"),allow_pickle=False) as z:a={k:z[k] for k in z.files}
        np.testing.assert_array_equal(a["physical_time"],d["observation_time"])
        np.testing.assert_allclose(a["q"],relative_activity(a["raw_rms"],scales["p05"],scales["p95"]),atol=1e-12)
        for j,name in enumerate(TYPES):
            for kind in ["raw","q"]:
                rr.log("/series/"+kind+"/"+m["id"]+"/"+name,rr.SeriesLines(colors=TYPE_COLORS[j],names=name),static=True)
        for k,t in enumerate(a["physical_time"]):
            rr.set_time("physical_display_s",duration=offset+float(t))
            s=d["states"][k];xy=rerun_coordinates(s[:2])
            rr.log("/orbit/trail",rr.LineStrips2D(rerun_coordinates(d["states"][:k+1,:2]),colors=[100,180,255]))
            rr.log("/orbit/craft",rr.Points2D([xy],radii=.15,colors=[255,230,120]))
            rr.log("/orbit/velocity",rr.Arrows2D(origins=[xy],vectors=[rerun_coordinates(s[2:])*20],colors=[100,220,255]))
            rr.log("/orbit/acceleration",rr.Arrows2D(origins=[xy],vectors=[rerun_coordinates(d["u_applied"][k])*400],colors=[255,170,70]))
            rr.log("/input/image",rr.Image(np.rint(d["images"][k]*255).astype(np.uint8)))
            q=a["q"][k];raw=a["raw_rms"][k]
            rr.log("/bars/fill",rr.LineStrips2D(np.array([[[0,y],[100*q[j],y]] for j,y in enumerate(rows)]),
                colors=np.column_stack([TYPE_COLORS,np.where(q>0,255,0)]),radii=3.5,draw_order=1))
            labels=[f"{name}   q {q[j]:.3f}   RMS {raw[j]:.5f}" for j,name in enumerate(TYPES)]
            rr.log("/bars/labels",rr.Points2D(np.column_stack([np.full(5,50),rows-6]),labels=labels,colors=[235,235,235],radii=rr.Radius.ui_points(0)))
            for j,name in enumerate(TYPES):
                rr.log("/maps/"+name+"/hex",rr.Points2D(lattice_xy(a["u"][j],a["v"][j]),
                    colors=colors(a["delta"][k,j],scales["signed_map_limit"][j]),radii=.78))
                rr.log("/series/raw/"+m["id"]+"/"+name,rr.Scalars(raw[j]))
                rr.log("/series/q/"+m["id"]+"/"+name,rr.Scalars(q[j]))
            rr.log("/morphology/absolute/arbor",rr.LineStrips3D(xyz[edges],colors=rms_colors(raw[2],.22),radii=rr.Radius.ui_points(1.5)))
            rr.log("/morphology/relative/arbor",rr.LineStrips3D(xyz[edges],colors=rms_colors(q[2],1),radii=rr.Radius.ui_points(1.5)))
            text=(f"# {m['id']} | {a['stage'][k]} | {t:.1f} physical s\n"
                f"Sample {k}; neural {a['neural_input_time'][k]:.2f} -> {a['neural_response_time'][k]:.2f} s. Playback 15x.\n\n"
                f"T4a RMS **{raw[2]:.5f}**; q **{q[2]:.3f}**; fixed p05/p95 **{scales['p05'][2]:.5f}/{scales['p95'][2]:.5f}**.\n\n"
                "**q: within-type test range, not firing rate or absolute type comparison.** Maps: blue negative / white zero / red positive; different FIXED limits by type.\n\n"
                "A/B show the SAME measured T4a arbor (ID 720575940605852192), colored by 721-model-cell RMS. No cell-wise anatomical mapping or branch propagation.\n\n"
                "45,669 model cells computed; these five types are a display selection. Saved learned closed loop, no new inference.")
            rr.log("/readout",rr.TextDocument(text,media_type="text/markdown"))
        manifest.append(dict(id=m["id"],record=m["record"],record_sha256=m["record_sha256"],offset=offset,frames=len(a["physical_time"]),
            display_record=str(OUT/(m["id"]+"_display.npz")),display_sha256=sha256(OUT/(m["id"]+"_display.npz"))))
        rr.set_time("physical_display_s",duration=offset+len(a["physical_time"])*.5)
        for path in ["/input","/maps","/bars/fill","/bars/labels","/morphology","/orbit/trail","/orbit/craft","/orbit/velocity","/orbit/acceleration"]:
            rr.log(path,rr.Clear(recursive=True))
        rr.log("/readout",rr.TextDocument("# RESET\nIndependent episode; no interpolation."))
        offset+=len(a["physical_time"])*.5+10
    rr.get_global_data_recording().flush()
    write_json(OUT/"viewer_manifest.json",dict(episodes=manifest,types=list(TYPES),scales_sha256=sha256(OUT/"display_scales.json"),
        readout_sha256=sha256("outputs/phase2/readout.npz"),timeline="physical_display_s = offset + observation_time",
        playback_speed=15,unique_morphology_count=1,morphology_views=["absolute","relative"],new_inference=False))
    print("Saved",OUT/"phase2f.rrd")
if __name__=="__main__":build()
