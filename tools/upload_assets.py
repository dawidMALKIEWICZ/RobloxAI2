"""Uploads baked meshes (assets/meshes/*.fbx), the palette and other files to Roblox with Open Cloud.

Needs environment variables ROBLOX_API_KEY and ROBLOX_USER_ID (never commit the key).
Already uploaded files are skipped: tools/asset_ids.json maps "<sha1>" -> asset id.

  python3 upload_assets.py meshes            # every fbx in the mesh manifest + palette.png
  python3 upload_assets.py file <path> <Image|Audio|Mesh|Decal> [name]
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDS = os.path.join(ROOT, "tools", "asset_ids.json")
API = "https://apis.roblox.com/assets/v1/"
TYPES = {".fbx": ("Mesh", "model/fbx"), ".png": ("Image", "image/png"),
         ".ogg": ("Audio", "audio/ogg"), ".mp3": ("Audio", "audio/mpeg")}


def _ids():
    if os.path.exists(IDS):
        with open(IDS) as f:
            return json.load(f)
    return {}


def _save(ids):
    with open(IDS, "w") as f:
        json.dump(ids, f, indent=1, sort_keys=True)


def _request(method, url, body=None, headers=None):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    req.add_header("x-api-key", os.environ["ROBLOX_API_KEY"])
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def upload(path, asset_type=None, name=None, key=None):
    """Returns the asset id (cached by file content, or by `key` when given)."""
    data = open(path, "rb").read()
    sha = key or hashlib.sha1(data).hexdigest()
    ids = _ids()
    if sha in ids:
        return ids[sha]
    ext = os.path.splitext(path)[1].lower()
    atype, mime = TYPES[ext]
    atype = asset_type or atype
    meta = {"assetType": atype, "displayName": (name or os.path.basename(path))[:50],
            "description": "Track RNG",
            "creationContext": {"creator": {"userId": os.environ["ROBLOX_USER_ID"]}}}
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"request\"\r\n\r\n".encode(),
        json.dumps(meta).encode(), b"\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"fileContent\"; "
        f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
        data, f"\r\n--{boundary}--\r\n".encode()])
    for attempt in range(5):
        try:
            op = _request("POST", API + "assets", body,
                          {"Content-Type": f"multipart/form-data; boundary={boundary}"})
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(4 * (attempt + 1))
                continue
            raise RuntimeError(f"{path}: HTTP {e.code} {e.read()[:300]!r}") from e
    for _ in range(60):
        if op.get("done"):
            break
        time.sleep(2)
        op = _request("GET", API + op["path"])
    resp = op.get("response") or {}
    aid = resp.get("assetId")
    if not aid:
        raise RuntimeError(f"{path}: upload failed {op}")
    ids = _ids()
    ids[sha] = aid
    _save(ids)
    print("uploaded", os.path.relpath(path, ROOT), "->", aid)
    return aid


def mesh_ids():
    """{fbx relative path: asset id} for everything in the manifest (uploads what's missing)."""
    with open(os.path.join(ROOT, "assets", "meshes", "manifest.json")) as f:
        man = json.load(f)
    out = {}
    for _name, entry in sorted(man.items()):
        for e in entry:
            out[e["fbx"]] = upload(os.path.join(ROOT, e["fbx"]), "Mesh",
                                   os.path.basename(e["fbx"])[:-4], key=e.get("hash"))
    out["palette"] = upload(os.path.join(ROOT, "assets", "meshes", "palette.png"), "Image",
                            "TrackRNG palette")
    with open(os.path.join(ROOT, "tools", "mesh_ids.json"), "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    return out


def media_ids():
    """Icons (assets/icons/*.png) and sounds (assets/audio/*.ogg) -> tools/media_ids.json"""
    out = {"icons": {}, "audio": {}}
    for kind, folder, ext, atype in (("icons", "icons", ".png", "Image"),
                                     ("audio", "audio", ".ogg", "Audio")):
        d = os.path.join(ROOT, "assets", folder)
        for f in sorted(os.listdir(d)):
            if f.endswith(ext):
                out[kind][f[:-len(ext)]] = upload(os.path.join(d, f), atype, "TrackRNG " + f[:-4])
    with open(os.path.join(ROOT, "tools", "media_ids.json"), "w") as f:
        json.dump(out, f, indent=1, sort_keys=True)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "media":
        ids = media_ids()
        print(sum(len(v) for v in ids.values()), "media assets ready")
    elif sys.argv[1] == "meshes":
        ids = mesh_ids()
        print(len(ids), "assets ready")
    elif sys.argv[1] == "file":
        print(upload(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None))
