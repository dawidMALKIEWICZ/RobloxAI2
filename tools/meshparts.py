"""MeshPart instances for models baked by blender/meshkit.py (see assets/meshes/manifest.json).

Asset ids come from tools/mesh_ids.json (written by upload_assets.py). Missing ids leave MeshId
empty so the generators still run before an upload.
"""
import json
import math
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
            # Roblox imports these meshes turned 180 degrees about Y (Blender x -> -x), so
            # every MeshPart is turned back here
            "CFrame": (base * CF(*c) * CF.ry(math.pi)).json(),
            "Anchored": True,
            "CanCollide": collide,
            "CanQuery": query,
            "CanTouch": False,
            "CastShadow": shadow and e["kind"] != "neon",
            "CollisionFidelity": "Box",
            "DoubleSided": False,
        }
        if e["kind"] in ("tex", "part"):
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
        if e["kind"] == "part":
            nm = e["name"]
        else:
            nm = (names or {}).get(e["kind"], {"tex": "Mesh", "neon": "Glow", "glass": "Glass"}
                                   .get(e["kind"], e["role"] or "Mesh"))
        attrs = {"MeshSrc": e["fbx"]}  # lets tools/preview renders find the source mesh
        if e["kind"] == "role":
            attrs["Role"] = e["role"]
        if e["kind"] == "part" and nm.startswith("Wheel"):
            # spins about its local X axis (the axle); the mesh is centred on the axle
            attrs["Wheel"] = True
        out.append(Inst("MeshPart", nm, props, attrs))
    return out


def set_attrs(inst, extra):
    """Adds attributes including Vector3 values (tuples of 3) to an Inst. rbx.ATTRS only knows
    bool/number/string, so the typed Attributes property is written directly."""
    merged = dict(inst.attrs)
    old = inst.props.get("Attributes", {}).get("Attributes", {})
    out = dict(old)
    merged.update(extra)
    for k, v in merged.items():
        if isinstance(v, bool):
            out[k] = {"Bool": v}
        elif isinstance(v, (int, float)):
            out[k] = {"Float64": float(v)}
        elif isinstance(v, (tuple, list)) and len(v) == 3:
            out[k] = {"Vector3": [round(float(c), 4) for c in v]}
        else:
            out[k] = {"String": str(v)}
    inst.attrs = {}
    inst.props["Attributes"] = {"Attributes": out}
    return inst


def animated(name, base, label, anim, scale=1.0, shadow=True, **kw):
    """A baked model as one animated object: a single MeshPart when the model has one mesh,
    else a Model (atomic streaming) whose parts move together. anim: Anim attributes."""
    parts = mesh_parts(name, base=base, scale=scale, shadow=shadow, **kw)
    if len(parts) == 1:
        p = parts[0]
        p.name = label
        return set_attrs(p, anim)
    m = Inst("Model", label, {"ModelStreamingMode": "Atomic"})
    for p in parts:
        m.add(p)
    return set_attrs(m, anim)
