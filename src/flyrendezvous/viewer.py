"""Convert portable real recordings into a synchronized Rerun recording."""
import argparse
import os
os.environ.setdefault("RERUN_ANALYTICS_ENABLED", "false")
import json
from pathlib import Path
import numpy as np
from .anatomy import load_meshes
from .recording import sha256
from .stimuli import KINDS

def lattice_xy(u, v):
    # Flyvis default hex plane, with y negated for Rerun screen coordinates
    # (positive down). This keeps image and receptor vertical directions aligned.
    return np.column_stack((1.5*v, np.sqrt(3)*(u+v/2)))

def colors(delta, limit):
    if not np.isfinite(delta).all() or not np.isfinite(limit) or limit <= 0:
        raise ValueError("Invalid fixed color scale")
    x = np.clip(np.asarray(delta)/limit, -1, 1)
    neutral = np.array([230.,230.,230.])
    blue = np.array([40.,95.,210.])
    red = np.array([210.,45.,45.])
    rgb = neutral + np.abs(x)[...,None]*(np.where((x>=0)[...,None],red,blue)-neutral)
    return rgb.astype(np.uint8)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="outputs/phase1")
    p.add_argument("--output",default="outputs/phase1/phase1.rrd")
    args=p.parse_args()
    source=Path(args.input)
    cfg=json.loads((source/"config.json").read_text())
    # Refuse to build a neural demo from partial/unvalidated or dummy records.
    validation=json.loads((source/"validation.json").read_text())
    if validation.get("status") != "passed":
        raise ValueError("Real-model validation did not complete successfully")
    assert validation["parameter_sha256_before"]==validation["parameter_sha256_after"]
    for name, expected in validation["record_sha256"].items():
        if sha256(source/name) != expected:
            raise ValueError("Recording differs from the validated numerical data")
    import rerun as rr
    import rerun.blueprint as rrb
    rr.init("FlyRendezvous-Phase1",spawn=False,strict=True)
    rr.save(args.output)
    rr.send_blueprint(rrb.Blueprint(
        rrb.Horizontal(
            rrb.Vertical(
                rrb.Spatial2DView(origin="/input",name="Sensor image / [0,1]"),
                rrb.Spatial2DView(origin="/receptors",name="Actual BoxEye input / [0,1]"),
                rrb.Spatial2DView(origin="/activity",name=cfg["display_cell_type"]+" / model voltage change"),
                row_shares=[1,1,1]),
            rrb.Vertical(
                rrb.Spatial3DView(origin="/brain",name="Anatomy / static / micrometers",
                    background=[18,23,32], line_grid=False,
                    eye_controls=rrb.archetypes.EyeControls3D(position=[524,262,-350],look_target=[524,262,167],eye_up=[0,-1,0])),
                rrb.TextDocumentView(origin="/explanation",name="Meaning, timing and limitations"),
                rrb.Spatial2DView(origin="/legend",name="Fixed scale / model voltage units"),
                row_shares=[3,2,0.45]),
            column_shares=[1,1.65]),
        rrb.TimePanel(expanded=False,timeline="input_sample_s",playback_speed=0.25),
        collapse_panels=True))
    for name, vertices, faces, normals in load_meshes():
        rr.log("/brain/"+name,rr.Mesh3D(vertex_positions=vertices,triangle_indices=faces,
               vertex_normals=normals,albedo_factor=[150,160,175,255]),static=True)
    limit=cfg["color_limit"]
    ramp=np.linspace(-limit,limit,256)
    legend=np.repeat(colors(ramp,limit)[None],12,axis=0)
    rr.log("/legend/scale",rr.Image(legend),static=True)
    offset=0.
    for kind in KINDS:
        with np.load(source/(kind+".npz"),allow_pickle=False) as data:
            sel=data["cell_type"]==cfg["display_cell_type"]
            pos=lattice_xy(data["u"][sel],data["v"][sel])
            receptor_pos=lattice_xy(data["receptor_u"],data["receptor_v"])
            for k,t in enumerate(data["input_time"]):
                rr.set_time("input_sample_s",duration=offset+float(t))
                rr.log("/input/image",rr.Image((data["images"][k]*255).round().astype(np.uint8)))
                gray=np.clip(data["receptor_input"][k]*255,0,255).astype(np.uint8)
                rr.log("/receptors/hex",rr.Points2D(receptor_pos,colors=np.repeat(gray[:,None],3,axis=1),radii=0.78))
                delta=data["activity"][k,sel]-data["baseline"][sel]
                rr.log("/activity/hex",rr.Points2D(pos,colors=colors(delta,limit),radii=0.78,
                       labels=[str(i) for i in data["cell_index"][sel]],show_labels=False))
                message=(
                    f"# FlyRendezvous — Phase 1\n"
                    f"Stimulus: **{kind}**, frame {k}\n\n"
                    f"Episode input: {t:.3f} s; response after update: {data['response_time'][k]:.3f} s. "
                    f"Input held for {cfg['dt']:.3f} model s.\n\n"
                    f"Pretrained Flyvis **flow/0000/000**; {validation['n_cells']:,} model cells. "
                    f"Panel: **{cfg['display_cell_type']}**, {int(sel.sum())} cells.\n\n"
                    f"Color = model voltage minus each cell's state after {cfg['warmup_seconds']:g} s grey warmup. "
                    f"Fixed scale: **blue = -{limit:g}; white = 0; red = +{limit:g}**, clipped beyond limits. "
                    f"No per-frame normalization; model units, not mV or spike frequency.\n\n"
                    f"**Anatomical activity projection: NOT ACHIEVED.**\n"
                    f"All grey meshes are static anatomical context; grey means **activity not assigned**, not zero activity. "
                    f"No one-to-one cell registration or left/right duplication. "
                    f"Eight region surfaces only; not whole-brain dynamics.\n\n"
                    f"JFRC2 → FAFB14.1 (fafbseg); nm scaled to micrometers. L/R are source labels. "
                    f"JFRC2: CC0, doi:10.5281/zenodo.10567; fafbseg distribution: GPL-3.0-or-later.\n\n"
                    f"Timeline joins four independently reset episodes. Viewer playback speed is independent "
                    f"of computation wall time and future HCW physical time. Pause/scrub with Rerun controls."
                )
                rr.log("/explanation",rr.TextDocument(message,media_type="text/markdown"))
            offset += len(data["input_time"])*cfg["dt"]
    rr.get_global_data_recording().flush()
    print("Saved",args.output,"(GUI inspection is a separate check)")

if __name__=="__main__":
    main()
