"""Rerun extension: one representative arbor, same-type RMS, exact spatial panel."""
import argparse
import json
from pathlib import Path
import numpy as np
from .anatomy import load_meshes
from .morphology import read_precomputed
from .projection import checked_episode,response_rms,rms_colors
from .recording import sha256
from .viewer import lattice_xy,colors

def build(input_dir="outputs/phase1b",output=None):
    out=Path(input_dir);cfg=json.loads((out/"config.json").read_text())
    validation=json.loads((out/"display_validation.json").read_text())
    if validation.get("status")!="passed" or sha256(out/"config.json")!=validation["config_sha256"]:
        raise ValueError("Display validation/configuration mismatch")
    if sha256("docs/anatomy_mapping_phase1b.json")!=validation["mapping_sha256"]:
        raise ValueError("Morphology mapping changed")
    mapping=json.loads(Path("docs/anatomy_mapping_phase1b.json").read_text())
    for name,m in mapping["files"].items():
        if sha256(name)!=m["sha256"]:raise ValueError("Morphology asset hash mismatch")
    xyz_nm,edges,_=read_precomputed("assets/phase1b/"+cfg["morphology_id"]+".precomputed")
    xyz=xyz_nm.astype(float)*.001
    center=(xyz.min(0)+xyz.max(0))/2
    import rerun as rr
    import rerun.blueprint as rrb
    rr.init("FlyRendezvous-Phase1B",spawn=False,strict=True)
    rr.save(output or str(out/"phase1b.rrd"))
    rr.send_blueprint(rrb.Blueprint(
        rrb.Horizontal(
            rrb.Vertical(
                rrb.Spatial2DView(origin="/input",name="Input image"),
                rrb.Spatial2DView(origin="/receptors",name="Actual photoreceptor input"),
                rrb.Spatial2DView(origin="/grid",name="T4a / signed cell voltage change"),
                row_shares=[1,1,1.35]),
            rrb.Vertical(
                rrb.Spatial3DView(origin="/brain",contents=["/brain/representative"],name="T4a representative / whole arbor = type RMS",
                    background=[15,20,30],line_grid=False,
                    eye_controls=rrb.archetypes.EyeControls3D(position=(center+[0,-155,0]).tolist(),look_target=center.tolist(),eye_up=[0,0,1])),
                rrb.TimeSeriesView(origin="/rms",name="Response-change magnitude / model units / separate trials"),
                rrb.Spatial2DView(origin="/legend",name=f"RMS: 0 → {cfg['rms_upper']:.2f} (clip); grid: -1.5 → +1.5"),
                row_shares=[3.5,1.4,.35]),
            rrb.Vertical(
                rrb.Spatial3DView(origin="/brain",name="FAFB14.1 context / unchanged anatomical scale",
                    background=[15,20,30],line_grid=False,
                    eye_controls=rrb.archetypes.EyeControls3D(position=[524,262,-420],look_target=[524,262,167],eye_up=[0,-1,0])),
                rrb.TextDocumentView(origin="/readout",name="Current sample and representative mapping"),
                row_shares=[2.2,1.4]),
            column_shares=[1.0,1.8,1.25]),
        rrb.TimePanel(state="collapsed",timeline="input_sample_s",playback_speed=cfg["playback_speed"],play_state="paused"),
        collapse_panels=True))
    for name,vertices,faces,normals in load_meshes():
        if name in cfg["background_regions"]:
            rr.log("/brain/context/"+name,rr.Mesh3D(vertex_positions=vertices,triangle_indices=faces,
                   vertex_normals=normals,albedo_factor=[105,115,130,255]),static=True)
        if name in cfg["outline_regions"]:
            links=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
            rr.log("/brain/context/"+name,rr.LineStrips3D(vertices[links],radii=rr.Radius.ui_points(.35),colors=[65,75,90]),static=True)
    rms_ramp=rms_colors(np.linspace(0,cfg["rms_upper"],256),cfg["rms_upper"])
    signed_ramp=colors(np.linspace(-cfg["signed_limit"],cfg["signed_limit"],256),cfg["signed_limit"])
    rr.log("/legend/colors",rr.Image(np.vstack([np.repeat(rms_ramp[None],12,axis=0),
          np.zeros((3,256,3),dtype=np.uint8),np.repeat(signed_ramp[None],12,axis=0)])),static=True)
    for trial in validation["trials"]:
        if sha256(trial["source"])!=trial["source_sha256"] or sha256(trial["projection"])!=trial["projection_sha256"] or sha256(trial["source_validation"])!=trial["validation_sha256"]:
            raise ValueError("Source or projection changed since validation")
        data=checked_episode(trial["source"],trial["source_validation"])
        selected,delta,rms=response_rms(data,cfg["cell_type"],cfg["dt"])
        with np.load(trial["projection"],allow_pickle=False) as z:
            np.testing.assert_allclose(rms,z["rms"],atol=1e-14,rtol=1e-13)
            np.testing.assert_array_equal(rms_colors(rms,cfg["rms_upper"]),z["rgb"])
            display_time=z["display_time"].copy();rgb=z["rgb"].copy()
        grid_pos=lattice_xy(data["u"][selected],data["v"][selected])
        receptor_pos=lattice_xy(data["receptor_u"],data["receptor_v"])
        # Different series entities prevent lines crossing reset boundaries.
        rr.log("/rms/"+trial["name"],rr.SeriesLines(colors=[255,205,65],names=trial["name"],widths=2),static=True)
        for k,t in enumerate(display_time):
            rr.set_time("input_sample_s",duration=float(t))
            rr.log("/input/image",rr.Image(np.rint(data["images"][k]*255).astype(np.uint8)))
            gray=np.rint(data["receptor_input"][k]*255).clip(0,255).astype(np.uint8)
            rr.log("/receptors/hex",rr.Points2D(receptor_pos,colors=np.repeat(gray[:,None],3,axis=1),radii=.78))
            rr.log("/grid/hex",rr.Points2D(grid_pos,colors=colors(delta[k],cfg["signed_limit"]),radii=.78))
            # One color for every published branch; no local propagation animation.
            rr.log("/brain/representative",rr.LineStrips3D(xyz[edges],colors=rgb[k],radii=rr.Radius.ui_points(1.3)))
            rr.log("/rms/"+trial["name"],rr.Scalars(float(rms[k])))
            stage=str(data["stage"][k]) if "stage" in data else trial["name"]
            msg=(f"# T4a · {trial['name']}\n"
                 f"**{stage}** · sample **{k}**\n\n"
                 f"Input **{data['input_time'][k]:.2f} s** → response **{data['response_time'][k]:.2f} s**\n\n"
                 f"**RMS = {rms[k]:.5f}** model units\n\n"
                 f"721 same-type model cells → one representative arbor.\n"
                 f"ID **{cfg['morphology_id']}**\n"
                 f"Display morphology: **right**; model side unassigned.\n\n"
                 f"**No cell-wise position mapping.\nNot a branch voltage distribution.**\n\n"
                 f"Grey background: activity unassigned.\n"
                 f"RMS scale 0–{cfg['rms_upper']:.2f}, clipped; grid ±{cfg['signed_limit']:.1f}.\n"
                 f"Episode starts with RESET; no interpolation across trials.")
            rr.log("/readout",rr.TextDocument(msg,media_type="text/markdown"))
        # A visible reset interval with no leftover input/shape response.
        rr.set_time("input_sample_s",duration=float(display_time[-1]+cfg["dt"]))
        for entity in ["/input","/receptors","/grid","/brain/representative"]:
            rr.log(entity,rr.Clear(recursive=True))
        rr.log("/readout",rr.TextDocument("# RESET\nIndependent next episode; grey warmup.\nNo response assigned during this display gap."))
    rr.get_global_data_recording().flush()
    print("Saved",output or str(out/"phase1b.rrd"))

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",default="outputs/phase1b");p.add_argument("--output")
    a=p.parse_args();build(a.input,a.output)
if __name__=="__main__":main()
