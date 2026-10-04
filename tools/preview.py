"""Render Rojo .model.json trees in Blender for previews (no Studio needed).

Parts become boxes/cylinders/balls, MeshParts load their baked FBX (attribute MeshSrc) with the
palette texture. Usage: <venv python with bpy> preview.py <shot,shot,...>
Shots: overview, hub, shops, plot (sample track + car on plot 1), bridge.
Roblox (x, y, z) -> Blender (x, -z, y).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from rbx import CF as RCF  # noqa: E402

P = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
_mats = {}
_meshes = {}
_fbx = {}


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(rgb, mat, transp, textured=False):
    key = (tuple(rgb), mat, round(transp, 2), textured)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new("m")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    col = (*[lin(c) for c in rgb], 1)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = {"Glass": 0.05, "Neon": 0.5}.get(mat, 0.6)
    if textured:
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(os.path.join(ROOT, "assets/meshes/palette.png"),
                                         check_existing=True)
        img.interpolation = "Closest"
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    if mat == "Neon":
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = 2.5
    if transp > 0:
        bsdf.inputs["Alpha"].default_value = 1 - transp
    _mats[key] = m
    return m


def prim(kind):
    if kind in _meshes:
        return _meshes[kind]
    if kind == "Cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.5, depth=1,
                                            rotation=(0, math.pi / 2, 0))
        bpy.ops.object.transform_apply(rotation=True)
    elif kind == "Ball":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.5)
    else:
        bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    me = o.data
    me.materials.append(None)
    bpy.data.objects.remove(o)
    _meshes[kind] = me
    return me


def fbx_mesh(rel):
    """Mesh data of a baked fbx (normalised to a 1x1x1 box like a Roblox MeshPart)."""
    if rel in _fbx:
        return _fbx[rel]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, rel))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    o = new[0]
    me = o.data
    me.transform(o.matrix_world)
    lo = Vector((min(v.co[i] for v in me.vertices) for i in range(3)))
    hi = Vector((max(v.co[i] for v in me.vertices) for i in range(3)))
    size = hi - lo
    c = (lo + hi) / 2
    me.transform(Matrix.Translation(-c))
    me.transform(Matrix.Diagonal((1 / max(size.x, 1e-4), 1 / max(size.y, 1e-4),
                                  1 / max(size.z, 1e-4), 1)))
    for ob in [x for x in bpy.data.objects if x not in before]:
        bpy.data.objects.remove(ob)
    me.materials.clear()
    me.materials.append(None)
    _fbx[rel] = me
    return me


def cfof(props):
    c = props["CFrame"]["CFrame"]
    return RCF(*c["position"], R=tuple(tuple(r) for r in c["orientation"]))


def attr(props, name):
    a = props.get("Attributes", {}).get("Attributes", {}).get(name)
    return list(a.values())[0] if a else None


def walk(node, out, cf=None):
    """Collects (class, props) of visible parts; cf re-bases model-space templates."""
    cls = node.get("ClassName")
    props = node.get("Properties", {})
    if cls in ("Part", "WedgePart", "MeshPart") and "CFrame" in props:
        if cf is not None:
            props = dict(props)
            props["CFrame"] = {"CFrame": (cf * cfof(props)).json()["CFrame"]}
        out.append((cls, props))
    if node.get("Name") == "Path":
        return
    for c in node.get("Children", []):
        walk(c, out, cf)


def add(parts):
    for cls, pr in parts:
        tr = pr.get("Transparency", 0)
        if tr >= 0.99:
            continue
        size = pr["Size"]["Vector3"]
        cf = pr["CFrame"]["CFrame"]
        R = Matrix(cf["orientation"])
        col = pr.get("Color", {"Color3": [0.64, 0.64, 0.65]})["Color3"]
        mat = pr.get("Material", "Plastic")
        textured = False
        if cls == "MeshPart":
            src = attr(pr, "MeshSrc")
            if not src:
                continue
            me = fbx_mesh(src)
            textured = "TextureID" in pr
        else:
            me = prim(pr.get("Shape", "Block"))
        o = bpy.data.objects.new("p", me)
        bpy.context.scene.collection.objects.link(o)
        Rb = P @ R @ P.transposed()
        if cls == "MeshPart":
            # fbx meshes are already in Blender axes: scale them in Blender axes, then apply the
            # same 180 degree turn Roblox applies when it imports a mesh
            sb = (size[0], size[2], size[1])
            m3 = Rb @ Matrix.Rotation(math.pi, 3, "Z") @ Matrix.Diagonal(sb)
        else:
            m3 = Rb @ P @ Matrix.Diagonal(size) @ P.transposed()
        m4 = m3.to_4x4()
        m4.translation = P @ Vector(cf["position"])
        o.matrix_world = m4
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = material(col, mat, tr, textured)


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def find(node, name):
    if node.get("Name") == name:
        return node
    for c in node.get("Children", []):
        r = find(c, name)
        if r:
            return r
    return None


def setup(res=(1600, 900), samples=40):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.7, 1.0, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.2
    sc.world = w
    sd = bpy.data.lights.new("sun", "SUN")
    sd.energy = 3.6
    sd.angle = math.radians(5)
    s = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(s)
    s.rotation_euler = (math.radians(42), math.radians(8), math.radians(35))


def camera(rb_pos, rb_target, lens=30):
    cd = bpy.data.cameras.new("c")
    cd.lens = lens
    cd.clip_end = 20000
    c = bpy.data.objects.new("c", cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = P @ Vector(rb_pos)
    d = P @ Vector(rb_target) - c.location
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = c


def render(name):
    path = os.path.join(ROOT, "renders", name)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


SAMPLE_TRACK = [  # x, z, r, id on the 15x15 grid (start = 7,7 heading -Z)
    (7, 7, 0, "Start"), (7, 6, 0, "BoostPad"), (7, 5, 0, "Turn"), (8, 5, 1, "Loop"),
    (9, 5, 1, "Turn"), (9, 6, 2, "Corkscrew"), (9, 7, 2, "Hill"), (9, 8, 2, "Turn"),
    (8, 8, 3, "DoubleLoop"), (7, 8, 3, "Turn"), (6, 3, 0, "SkyLeap"), (5, 6, 0, "Spiral"),
    (5, 7, 0, "WaveRider"), (5, 8, 0, "TeleportGate")]


def plot_track(mp):
    plot = find(mp, "Plot1")
    go = cfof(find(plot, "GridOrigin")["Properties"])
    tiles = {c["Name"]: c for c in load("src/ReplicatedStorage/Assets/Tiles.model.json")["Children"]}
    cars = {c["Name"]: c for c in load("src/ReplicatedStorage/Assets/Cars.model.json")["Children"]}
    out = []
    out.append(("Part", {"Size": {"Vector3": [90, 0.3, 90]}, "Color": {"Color3": [0.72, 0.94, 0.56]},
                         "CFrame": {"CFrame": (go * RCF(0, 0.15, 0)).json()["CFrame"]}}))
    for x, z, r, tid in SAMPLE_TRACK:
        cf = go * RCF((x - 7) * 10, 0.3, (z - 7) * 10) * RCF.ry(-r * math.pi / 2)
        walk(tiles[tid], out, cf)
    walk(cars["Sports"], out, go * RCF(0, 0.3 + 0.6 - 0.2 + 0.05, 7) * RCF.ry(0))
    walk(cars["Monster"], out, go * RCF(0, 0.3 + 0.6 - 0.2 + 0.05, -6))
    return go, out


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    shots = (sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else sys.argv[1]).split(",")
    mp = load("src/Workspace/Map.model.json")
    parts = []
    walk(mp, parts)
    add(parts)
    go, track = plot_track(mp)
    add(track)
    setup()
    T = 100
    g = go.p
    views = {
        "overview": ((700, T + 520, 760), (0, T - 30, 0), 24),
        "hub": ((92, T + 46, 108), (0, T + 6, 0), 24),
        "shops": ((-8, T + 14, -20), (40, T + 6, 24), 22),
        "plot": ((g[0] + 60, g[1] + 48, g[2] + 62), (g[0], g[1] + 2, g[2]), 26),
        "bridge": ((150, T + 26, 60), (300, T, 0), 22),
    }
    for s in shots:
        pos, tgt, lens = views[s]
        camera(pos, tgt, lens)
        render(f"preview_{s}.png")
