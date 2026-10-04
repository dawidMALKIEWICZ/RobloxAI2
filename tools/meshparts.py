"""MeshPart instances for models baked by blender/meshkit.py (see assets/meshes/manifest.json).

Asset ids come from tools/mesh_ids.json (written by upload_assets.py). Missing ids leave MeshId
empty so the generators still run before an upload.
"""
import json
import os

from rbx import CF, C3, V3, Inst

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_man = None
_ids = None


def manifest():
    global _man
    if _man is None:
        with open(os.path.join(ROOT, "assets", "meshes", "manifest.json")) as f:
            _man = json.load(f)
    return _man


def ids():
    global _ids
    if _ids is None:
        p = os.path.join(ROOT, "tools", "mesh_ids.json")
        _ids = json.load(open(p)) if os.path.exists(p) else {}
    return _ids


def asset(aid):
    return f"rbxassetid://{aid}" if aid else ""


def mesh_parts(name, base=None, scale=1.0, collide=False, query=False, shadow=True,
               names=None):
    """MeshParts of a baked model. base: CF placed at the model origin."""
    base = base or CF()
    out = []
    for e in manifest()[name]:
        size = [c * scale for c in e["size"]]
        c = [v * scale for v in e["center"]]
        props = {
            "MeshId": asset(ids().get(e["fbx"])),
            "Size": V3(*size),
            "InitialSize": V3(*e["size"]),
            "CFrame": (base * CF(*c)).json(),
            "Anchored": True,
            "CanCollide": collide,
            "CanQuery": query,
            "CanTouch": False,
            "CastShadow": shadow and e["kind"] != "neon",
            "CollisionFidelity": "Box",
            "DoubleSided": False,
        }
        if e["kind"] == "tex":
            props["TextureID"] = asset(ids().get("palette"))
            props["Material"] = "SmoothPlastic"
            props["Color"] = C3("#ffffff")
        elif e["kind"] == "neon":
            props["Material"] = "Neon"
            props["Color"] = C3(e["color"])
        elif e["kind"] == "glass":
            props["Material"] = "Glass"
            props["Color"] = C3(e["color"])
            props["Transparency"] = 0.35
        else:
            props["Material"] = "SmoothPlastic"
            props["Color"] = C3(e["color"])
        nm = (names or {}).get(e["kind"], {"tex": "Mesh", "neon": "Glow", "glass": "Glass"}
                               .get(e["kind"], e["role"] or "Mesh"))
        attrs = {"MeshSrc": e["fbx"]}  # lets tools/preview renders find the source mesh
        if e["kind"] == "role":
            attrs["Role"] = e["role"]
        out.append(Inst("MeshPart", nm, props, attrs))
    return out
