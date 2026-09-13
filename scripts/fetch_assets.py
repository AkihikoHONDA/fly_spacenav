"""Fetch only the official model bundle and small neuropil archive, with cache checks."""
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MESH_COMMIT = "d0da95123ee606e204ae2c702e7bc78538646fbd"
MODEL_ID = "13cJr2nMn89j-jBAd5RduYRJpBcXwoNrC"
MODEL_SHA = "71c78d4070556a536b13b23ee3139cd2788aa2a9d07d430a223b4edead281db1"
MESH_NAMES = ("ME_L", "ME_R", "LO_L", "LO_R", "LOP_L", "LOP_R", "FB", "EB")

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def download(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        # No credentials or signed URL in logs.
        request = urllib.request.Request(url, headers={"User-Agent": "FlyRendezvous-Phase1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Downloaded asset failed official SHA-256 check")
        path.write_bytes(data)
    if expected and digest(path) != expected:
        raise ValueError(f"Cached asset hash mismatch: {path}")

def main():
    dist = importlib.metadata.distribution("flyvis")
    source = Path(dist.locate_file("flyvis_cli/download_pretrained_models.py"))
    tree = ast.parse(source.read_text())
    # Use the publisher's downloader configuration, never search user credentials.
    key = next(ast.literal_eval(n.value) for n in ast.walk(tree)
               if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "api_key")
    archive = ROOT / "assets/results_pretrained_models.zip"
    url = "https://www.googleapis.com/drive/v3/files/" + MODEL_ID + "?" + urllib.parse.urlencode({"alt":"media","key":key})
    download(url, archive, MODEL_SHA)
    tracked = [archive]
    with zipfile.ZipFile(archive) as z:
        prefix = "results/flow/0000/000/"
        for name in z.namelist():
            if name.startswith(prefix) and not name.endswith("/"):
                relative = Path(name)
                if ".." in relative.parts or relative.is_absolute():
                    raise ValueError("Unsafe archive path")
                target = ROOT / "assets/flyvis" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
                tracked.append(target)
    mesh_url = f"https://raw.githubusercontent.com/navis-org/fafbseg-py/{MESH_COMMIT}/fafbseg/data/JFRC2NP.surf.fw.zip"
    mesh_zip = ROOT / "assets/JFRC2NP.surf.fw.zip"
    download(mesh_url, mesh_zip)
    # Verify against the pinned Git blob obtained from the official Git tree.
    blob = hashlib.sha1(b"blob " + str(mesh_zip.stat().st_size).encode() + b"\0" + mesh_zip.read_bytes()).hexdigest()
    if blob != "f9c843c8c46c430ccb37b4b9f787a6f99edaba47":
        raise ValueError("Pinned mesh Git blob mismatch")
    tracked.append(mesh_zip)
    with zipfile.ZipFile(mesh_zip) as z:
        for name in MESH_NAMES:
            target = ROOT / "assets/meshes" / (name + ".ply")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name + ".ply"))
            tracked.append(target)
    connectome = Path(dist.locate_file("flyvis/connectome/fib25-fib19_v2.2.json"))
    target = ROOT / "assets/sources/fib25-fib19_v2.2.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(connectome.read_bytes())
    tracked.append(target)
    manifest = {
        "model": {"id":"flow/0000/000", "checkpoint":"chkpts/chkpt_00000", "flyvis_version":dist.version,
                  "archive_url":"https://drive.google.com/uc?id="+MODEL_ID+"&export=download",
                  "archive_sha256":MODEL_SHA, "archive_bytes":archive.stat().st_size,
                  "scope":"official bundle contains 50; only model 000 extracted and executed",
                  "code_license":"MIT (PyPI package metadata)", "weights_terms":"Publisher distributes with Flyvis; no separate weights license found; no redistribution performed"},
        "anatomy": {"source":mesh_url, "commit":MESH_COMMIT,
                    "original":"https://doi.org/10.5281/zenodo.10567",
                    "original_license":"CC0-1.0 (Zenodo record 10567)",
                    "distribution_license":"fafbseg GPL-3.0-or-later repository; preserve notices",
                    "coordinate_system":"FlyWire FAFB14.1", "source_units":"nm", "display_units":"um",
                    "transform":"uniform scale 0.001; no registration, reflection, or translation",
                    "hemisphere":"L/R suffixes retained from source; model hemisphere unresolved",
                    "meshes":list(MESH_NAMES), "scope":"8 region surfaces, not a whole-brain neuron reconstruction"},
        "files": {p.relative_to(ROOT).as_posix(): {"sha256":digest(p), "bytes":p.stat().st_size} for p in tracked},
    }
    (ROOT / "docs/assets_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("Verified official model 000 and 8 region meshes; docs/assets_manifest.json written.")

if __name__ == "__main__":
    main()
