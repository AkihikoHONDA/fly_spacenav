"""Phase 2E: display-only rotation of frozen Phase 2 replays."""
import json
from pathlib import Path
import numpy as np
from .recording import sha256,write_json
from .phase2_runtime import checked_trial,load_config
from .morphology import read_precomputed
from .anatomy import load_meshes
from .viewer import lattice_xy,colors
from .projection import rms_colors
from .display_coordinates import rerun_coordinates

def build(input_dir="outputs/phase2", output_dir="outputs/phase2e"):
    import rerun as rr
    import rerun.blueprint as rrb
    cfg=load_config();disp=cfg["display"];out=Path(input_dir);dest=Path(output_dir)
    dest.mkdir(parents=True,exist_ok=True)
    lock=json.loads((out/"model_lock.json").read_text())
    assert sha256(out/"readout.npz")==lock["readout_sha256"]
    mapping=json.loads(Path("docs/anatomy_mapping_phase1b.json").read_text())
    for name,m in mapping["files"].items():
        if sha256(name)!=m["sha256"]:raise ValueError("Morphology asset changed")
    xyz,edges,_=read_precomputed("assets/phase1b/720575940605852192.precomputed");xyz=xyz.astype(float)*.001
    center=(xyz.min(0)+xyz.max(0))/2
    rr.init("FlyRendezvous-Phase2E",spawn=False,strict=True);rr.save(str(dest/"phase2e.rrd"))
    rr.send_blueprint(rrb.Blueprint(
        rrb.Horizontal(
            rrb.Vertical(rrb.Spatial2DView(origin="/input",name="Fixed -x camera / 64 x 64"),
                rrb.Spatial2DView(origin="/receptors",name="Actual BoxEye input"),
                rrb.Spatial2DView(origin="/grid",name="T4a: signed voltage change / +/-1.5"),
                row_shares=[1,1,1.4]),
            rrb.Vertical(rrb.Spatial2DView(origin="/orbit",name="Orbit [m]: down = central body, left = along-track; v x20 s; a x400 s^2"),
                rrb.TimeSeriesView(origin="/acceleration",name="Applied acceleration [m/s^2] / learned control"),
                rrb.TimeSeriesView(origin="/position_error",name="Position error [m]"),
                rrb.TimeSeriesView(origin="/speed",name="Speed [m/s]"),row_shares=[3.4,1.2,1,1]),
            rrb.Vertical(
                rrb.Spatial3DView(origin="/brain",contents=["/brain/representative"],name="T4a representative / type RMS 0..0.22 (clip)",
                    background=[15,20,30],line_grid=False,
                    eye_controls=rrb.archetypes.EyeControls3D(position=(center+[0,-155,0]).tolist(),look_target=center.tolist(),eye_up=[0,0,1])),
                rrb.Spatial3DView(origin="/brain",name="FAFB14.1 context [um] / grey = unassigned",
                    background=[15,20,30],line_grid=False,
                    eye_controls=rrb.archetypes.EyeControls3D(position=[524,262,-420],look_target=[524,262,167],eye_up=[0,-1,0])),
                rrb.TextDocumentView(origin="/readout",name="Image-only learned closed loop / current sample"),
                row_shares=[1.6,.9,1.7]),column_shares=[1,1.8,1.4]),
        rrb.TimePanel(state="collapsed",timeline="physical_display_s",playback_speed=disp["playback_speed"],play_state="paused"),
        collapse_panels=True))
    anatomy_cfg=json.loads(Path("configs/phase1b.json").read_text())
    for name,vertices,faces,normals in load_meshes():
        if name in anatomy_cfg["background_regions"]:
            rr.log("/brain/context/"+name,rr.Mesh3D(vertex_positions=vertices,triangle_indices=faces,vertex_normals=normals,
                albedo_factor=[105,115,130,255]),static=True)
        if name in anatomy_cfg["outline_regions"]:
            links=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
            rr.log("/brain/context/"+name,rr.LineStrips3D(vertices[links],colors=[65,75,90],radii=rr.Radius.ui_points(.35)),static=True)
    # Logical display X=-y, Y=x (up). Rerun Spatial2D canvas has Y down.
    compass=np.array([32.,0.])
    directions=np.array([[4.,0.],[-4.,0.],[0.,5.],[0.,-5.]])
    rr.log("/orbit/axes",rr.Arrows2D(origins=rerun_coordinates(np.repeat(compass[None],4,axis=0)),
        vectors=rerun_coordinates(directions),colors=[180,180,180]),static=True)
    for label,location in [("Radial outward (+x)",[38.,0.]),("Central body (-x)",[26.,0.]),
                           ("Along-track (+y)",[32.,11.]),("Retrograde (-y)",[32.,-11.])]:
        rr.log("/orbit/directions/"+label.split()[0],rr.Points2D(rerun_coordinates([location]),
            radii=rr.Radius.ui_points(0),labels=[label],colors=[210,210,210]),static=True)
    rr.log("/orbit/target",rr.Points2D(rerun_coordinates([[0,0]]),colors=[190,190,190],radii=.5),static=True)
    rr.log("/orbit/goal",rr.Points2D(rerun_coordinates([[cfg["x_goal"],0]]),colors=[70,220,160],radii=.15,labels=["goal"]),static=True)
    # Fixed frame, no camera-follow or autoscale tied to the learned trajectory.
    rr.log("/orbit/bounds",rr.LineStrips2D(rerun_coordinates([[-3,18],[40,18],[40,-18],[-3,-18],[-3,18]]),colors=[45,50,60]),static=True)
    offset=0.;manifest=[]
    for m in json.loads((out/"replays.json").read_text()):
        d=checked_trial(m);selected=np.flatnonzero(d["cell_type"]==disp["cell_type"])
        delta=d["activity"][:,selected].astype(float)-d["baseline"][selected]
        rms=np.sqrt(np.mean(delta**2,axis=1));rgb=rms_colors(rms,disp["rms_upper"])
        pos=lattice_xy(d["u"][selected],d["v"][selected]);recpos=lattice_xy(d["receptor_u"],d["receptor_v"])
        paths={axis:"/acceleration/"+m["id"]+"/"+axis for axis in ["ax","ay"]}
        for axis,color in [("ax",[255,170,70]),("ay",[100,180,255])]:
            rr.log(paths[axis],rr.SeriesLines(colors=color,names=m["id"]+" "+axis),static=True)
        for path in ["/position_error/"+m["id"],"/speed/"+m["id"]]:
            rr.log(path,rr.SeriesLines(colors=[150,220,150],names=m["id"]),static=True)
        times=d["observation_time"]+offset
        for k,t in enumerate(times):
            rr.set_time("physical_display_s",duration=float(t))
            s=d["states"][k];xy=rerun_coordinates(s[:2]);v=rerun_coordinates(s[2:]);applied=d["u_applied"][k]
            rr.log("/orbit/trail",rr.LineStrips2D(rerun_coordinates(d["states"][:k+1,:2]),colors=[100,180,255]))
            rr.log("/orbit/craft",rr.Points2D([xy],colors=[255,230,120],radii=.15))
            rr.log("/orbit/velocity",rr.Arrows2D(origins=[xy],vectors=[v*disp["velocity_arrow_seconds"]],colors=[100,220,255]))
            rr.log("/orbit/acceleration",rr.Arrows2D(origins=[xy],vectors=[rerun_coordinates(applied)*disp["acceleration_arrow_seconds_squared"]],colors=[255,170,70]))
            rr.log("/input/image",rr.Image(np.rint(d["images"][k]*255).astype(np.uint8)))
            gray=np.rint(d["receptor_input"][k]*255).clip(0,255).astype(np.uint8)
            rr.log("/receptors/hex",rr.Points2D(recpos,colors=np.repeat(gray[:,None],3,axis=1),radii=.78))
            rr.log("/grid/hex",rr.Points2D(pos,colors=colors(delta[k],disp["signed_limit"]),radii=.78))
            rr.log("/brain/representative",rr.LineStrips3D(xyz[edges],colors=rgb[k],radii=rr.Radius.ui_points(1.3)))
            for i,axis in enumerate(["ax","ay"]):rr.log(paths[axis],rr.Scalars(float(applied[i])))
            error=np.linalg.norm(s[:2]-[cfg["x_goal"],0]);speed=np.linalg.norm(s[2:])
            rr.log("/position_error/"+m["id"],rr.Scalars(float(error)))
            rr.log("/speed/"+m["id"],rr.Scalars(float(speed)))
            stage="CONTROL" if d["control_mask"][k] else "OBSERVE / u=0"
            text=(f"# {m['id']} · {stage}\n"
                  f"Sample **{k}** · physical **{d['observation_time'][k]:.1f} s**\n\n"
                  f"Neural {d['neural_input_time'][k]:.2f} → {d['neural_response_time'][k]:.2f} s; time ratio 50\n\n"
                  f"Position error **{error:.3f} m**; speed **{speed:.4f} m/s**\n\n"
                  f"Applied a (LVLH ax, ay): **{applied[0]:+.5f}, {applied[1]:+.5f} m/s²**\n\n"
                  f"**45,669 model cells computed.** Readout: 57 non-input types.\n"
                  f"T4a: **721 model cells → 1 measured arbor**; RMS **{rms[k]:.5f}**.\n"
                  f"ID 720575940605852192; right, model side unassigned.\n\n"
                  f"**Not the measured cell's activity. No cell-wise position mapping or branch propagation.**\n\n"
                  f"Fixed RMS 0..0.22, clipped. Display type ≠ readout selection.\n"
                  f"Episode result: **{m['termination_reason']}** at {m['final_time_s']:.1f} s.")
            rr.log("/readout",rr.TextDocument(text,media_type="text/markdown"))
        manifest.append(dict(id=m["id"],offset=offset,frames=len(times),record=m["record"],record_sha256=m["record_sha256"],
            rms_clipped_samples=int((rms>disp["rms_upper"]).sum()),grid_clipped_values=int((np.abs(delta)>disp["signed_limit"]).sum()),
            rms_min=float(rms.min()),rms_max=float(rms.max()),outcome=m["termination_reason"]))
        rr.set_time("physical_display_s",duration=float(times[-1]+cfg["dt_phys"]))
        for path in ["/input","/receptors","/grid","/brain/representative","/orbit/trail","/orbit/craft","/orbit/velocity","/orbit/acceleration"]:
            rr.log(path,rr.Clear(recursive=True))
        rr.log("/readout",rr.TextDocument("# RESET\nIndependent next episode; no interpolation across trials."))
        offset+=len(times)*cfg["dt_phys"]+10
    rr.get_global_data_recording().flush()
    write_json(dest/"viewer_manifest.json",dict(display_transform="X=-y, Y=x (Y up)",
        rerun_canvas_transform="X=-y, canvas_Y=-x (canvas Y down)",source_directory=str(out),episodes=manifest,config_sha256=sha256("configs/phase2.json"),
        readout_sha256=lock["readout_sha256"],timeline="physical_display_s = episode offset + observation_time",
        arrows={"velocity_seconds":disp["velocity_arrow_seconds"],"acceleration_seconds_squared":disp["acceleration_arrow_seconds_squared"]}))
    print("Saved",dest/"phase2e.rrd")
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--input",default="outputs/phase2")
    parser.add_argument("--output",default="outputs/phase2e")
    args=parser.parse_args();build(args.input,args.output)
