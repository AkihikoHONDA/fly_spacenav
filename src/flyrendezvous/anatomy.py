"""Static, attributed region geometry. No undocumented activity projection."""
from pathlib import Path
import json
from .recording import sha256

def load_meshes(manifest_path="docs/assets_manifest.json"):
    import trimesh
    manifest = json.loads(Path(manifest_path).read_text())
    for name in manifest["anatomy"]["meshes"]:
        path = Path("assets/meshes")/(name+".ply")
        if sha256(path) != manifest["files"][path.as_posix()]["sha256"]:
            raise ValueError("Anatomy mesh hash mismatch")
        mesh = trimesh.load_mesh(path, process=False)
        yield name, mesh.vertices * 0.001, mesh.faces, mesh.vertex_normals
