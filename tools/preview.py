"""Render Rojo .model.json part trees in Blender for previews (no Studio needed).

Usage: <venv python with bpy> preview.py <shot> [model.json ...]
Roblox (x, y, z) -> Blender (x, -z, y).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
_mats = {}
_meshes = {}


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material(rgb, mat, transp):
    key = (tuple(rgb), mat, round(transp, 2))
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new("m")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    col = (*[srgb_to_lin(c) for c in rgb], 1)
    bsdf.inputs["Base Color"].default_value = col
    rough = {"SmoothPlastic": 0.4, "Glass": 0.05, "Metal": 0.3, "Neon": 0.5, "Ice": 0.1}
    bsdf.inputs["Roughness"].default_value = rough.get(mat, 0.75)
    if mat == "Metal":
        bsdf.inputs["Metallic"].default_value = 0.6
    if mat == "Neon":
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = 3.0
    if transp > 0:
        bsdf.inputs["Alpha"].default_value = 1 - transp
    _mats[key] = m
    return m


def base_mesh(kind):
    if kind in _meshes:
        return _meshes[kind]
    if kind == "Block":
        bpy.ops.mesh.primitive_cube_add(size=1)
    elif kind == "Cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=1,
                                            rotation=(0, math.pi / 2, 0))
        bpy.ops.object.transform_apply(rotation=True)
    elif kind == "Ball":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.5)
    elif kind == "Wedge":
        # roblox local: low front (-Z), high back (+Z) -> blender: y = -z
        verts = [(-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5),
                 (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5)]
        faces = [(0, 1, 3, 2), (2, 3, 5, 4), (0, 2, 4), (1, 5, 3), (0, 4, 5, 1)]
        me = bpy.data.meshes.new("wedge")
        me.from_pydata(verts, [], faces)
        o = bpy.data.objects.new("wedge", me)
        bpy.context.scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o
    o = bpy.context.active_object
    me = o.data
    me.materials.append(None)
    bpy.data.objects.remove(o)
    _meshes[kind] = me
    return me


def walk(node, out):
    cls = node.get("ClassName")
    props = node.get("Properties", {})
    if cls in ("Part", "WedgePart", "SpawnLocation") and "CFrame" in props:
        out.append((cls, props))
    for c in node.get("Children", []):
        walk(c, out)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_parts(parts, offset=(0, 0, 0)):
    for cls, pr in parts:
        tr = pr.get("Transparency", 0)
        if tr >= 0.99:
            continue
        size = pr["Size"]["Vector3"]
        cf = pr["CFrame"]["CFrame"]
        pos = cf["position"]
        R = Matrix(cf["orientation"])
        col = pr.get("Color", {"Color3": [0.64, 0.64, 0.65]})["Color3"]
        mat = pr.get("Material", "Plastic")
        shape = pr.get("Shape", "Block")
        kind = "Wedge" if cls == "WedgePart" else shape
        me = base_mesh(kind)
        o = bpy.data.objects.new("p", me)
        bpy.context.scene.collection.objects.link(o)
        p = (pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2])
        Rb = P @ R @ P.transposed()
        Lb = Rb @ P @ Matrix.Diagonal(size) @ P.transposed()
        m4 = Lb.to_4x4()
        m4.translation = P @ Vector(p)
        o.matrix_world = m4
        o.material_slots[0].link = "OBJECT"
        o.material_slots[0].material = material(col, mat, tr)


def setup(res=(1280, 720), samples=32):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.65, 1.0, 1)
    sc.world = w
    sd = bpy.data.lights.new("sun", "SUN")
    sd.energy = 4.0
    sd.angle = math.radians(6)
    s = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(s)
    s.rotation_euler = (math.radians(40), math.radians(10), math.radians(30))


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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    args = sys.argv[1:]
    shots = args[0].split(",")
    files = args[1:] or [os.path.join(ROOT, "src/Workspace/Map.model.json")]
    parts = []
    if shots == ["pieces"]:
        d = load(os.path.join(ROOT, "src/ReplicatedStorage/Assets/TrackPieces.model.json"))
        want = sys.argv[2].split(",") if len(sys.argv) > 2 else None
        models = [c for c in d["Children"] if not c["Name"].endswith("_L")
                  and (want is None or c["Name"] in want)]
        for i, mdl in enumerate(models):
            pp = []
            walk(mdl, pp)
            add_parts(pp, offset=(i * 140, 0, 0))
        n = len(models)
        cx = (n - 1) * 70
        setup(res=(1600, 900))
        camera((cx + 520, 260, 330), (cx, 20, -120), 22)
        render("preview_pieces.png")
        sys.exit(0)
    if shots[0] == "plot2":
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        from rbx import CF as RCF
        import math as _m
        mp = load(os.path.join(ROOT, "src/Workspace/Map.model.json"))
        tl = {c["Name"]: c for c in load(os.path.join(ROOT,
              "src/ReplicatedStorage/Assets/Tiles.model.json"))["Children"]}
        cars = {c["Name"]: c for c in load(os.path.join(ROOT,
                "src/ReplicatedStorage/Assets/Cars.model.json"))["Children"]}

        def find(node, name):
            if node.get("Name") == name:
                return node
            for c in node.get("Children", []):
                r = find(c, name)
                if r:
                    return r
            return None

        def cfof(d):
            c = d["Properties"]["CFrame"]["CFrame"]
            return RCF(*c["position"], R=tuple(tuple(r) for r in c["orientation"]))
        plot = find(mp, "Plot1")
        go = cfof(find(plot, "GridOrigin"))
        layout = [(7, 7, 0, "Start"), (7, 6, 0, "Straight"), (7, 5, 0, "Turn"), (8, 5, 1, "Turn"),
                  (8, 6, 2, "Loop"), (8, 7, 2, "Corkscrew"), (8, 8, 2, "Jump"), (8, 9, 2, "Turn"),
                  (7, 9, 3, "Turn"), (7, 8, 0, "Hill"), (6, 4, 0, "SkyLeap"),
                  (5, 6, 0, "BoostPad"), (5, 7, 1, "BankedTurn"), (9, 7, 0, "Spiral")]
        extra = []

        def place(model, cf):
            pp = []
            walk(model, pp)
            for cls, pr in pp:
                pr = dict(pr)
                pr["CFrame"] = {"CFrame": (cf * cfof({"Properties": pr})).json()["CFrame"]}
                extra.append((cls, pr))
        for x, z, r, tid in layout:
            cf = go * RCF(x * 10 - 70, 0.3, z * 10 - 70) * RCF.ry(-r * _m.pi / 2)
            place(tl[tid], cf)
        # pad 7x7
        extra.append(("Part", {"Size": {"Vector3": [70, 0.3, 70]},
                               "CFrame": {"CFrame": (go * RCF(0, 0.15, 0)).json()["CFrame"]},
                               "Color": {"Color3": [0.72, 0.94, 0.56]}}))
        place(cars["Muscle"], go * RCF(0, 0.3 + 0.6, -6) * RCF.ry(0))
        mpp = []
        walk(mp, mpp)
        add_parts(mpp)
        add_parts(extra)
        setup(res=(1600, 900))
        g = go.p
        camera((g[0] + 70, g[1] + 55, g[2] + 40), (g[0] + 2, g[1] + 2, g[2] - 3), 30)
        render("preview_plot2.png")
        sys.exit(0)
    if shots[0] == "tiles":
        d = load(os.path.join(ROOT, "src/ReplicatedStorage/Assets/Tiles.model.json"))
        for i, mdl in enumerate(d["Children"]):
            pp = []
            walk(mdl, pp)
            add_parts(pp, offset=((i % 6) * 14, 0, (i // 6) * 16))
        add_parts([("Part", {"Size": {"Vector3": [400, 1, 400]},
                             "CFrame": {"CFrame": {"position": [35, -0.5, 16],
                                                   "orientation": [[1, 0, 0], [0, 1, 0],
                                                                   [0, 0, 1]]}},
                             "Color": {"Color3": [0.55, 0.85, 0.4]}})])
        setup(res=(1600, 1000))
        camera((35, 62, 78), (35, 0, 14), 34)
        render("preview_tiles.png")
        sys.exit(0)
    if shots[0] == "track":
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        from rbx import CF as RCF
        import math as _m
        mp = load(os.path.join(ROOT, "src/Workspace/Map.model.json"))
        tp = load(os.path.join(ROOT, "src/ReplicatedStorage/Assets/TrackPieces.model.json"))
        pieces = {c["Name"]: c for c in tp["Children"]}

        def find(node, name):
            if node.get("Name") == name:
                return node
            for c in node.get("Children", []):
                r = find(c, name)
                if r:
                    return r
            return None
        plot = find(mp, "Plot1")
        o = find(plot, "TrackOrigin")["Properties"]["CFrame"]["CFrame"]
        origin = RCF(*o["position"], R=tuple(tuple(r) for r in o["orientation"]))
        seq = (sys.argv[2] if len(sys.argv) > 2 else
               "Straight,GentleCurve,SharpTurn,Ramp,BankedCurve,Corkscrew,JumpGap,Loop,"
               "SpiralTower,TeleportGate,SkyLeap").split(",")
        turns = {"GentleCurve", "SharpTurn", "BankedCurve"}

        def flat(cf):
            lv = cf.look_vector
            L = _m.hypot(lv[0], lv[2]) or 1
            return (lv[0] / L, 0, lv[2] / L)
        chain = origin
        allp = []
        for pid in seq:
            name = pid
            if pid in turns:
                out, head = flat(origin), flat(chain)
                cy = out[2] * head[0] - out[0] * head[2]
                if cy < -0.1:
                    name = pid + "_L"
                elif cy > 0.1:
                    name = pid + "_R"
                else:
                    rv = (origin.R[0][0], origin.R[1][0], origin.R[2][0])
                    d = [chain.p[i] - origin.p[i] for i in range(3)]
                    lat = sum(d[i] * rv[i] for i in range(3))
                    name = pid + ("_L" if lat > 0 else "_R")
            pp = []
            walk(pieces[name], pp)
            ex = find(pieces[name], "Exit")["Properties"]["CFrame"]["CFrame"]
            for cls, pr in pp:
                c = pr["CFrame"]["CFrame"]
                lc = RCF(*c["position"], R=tuple(tuple(r) for r in c["orientation"]))
                wc = (chain * lc).json()["CFrame"]
                pr = dict(pr)
                pr["CFrame"] = {"CFrame": wc}
                allp.append((cls, pr))
            chain = chain * RCF(*ex["position"], R=tuple(tuple(r) for r in ex["orientation"]))
        mpp = []
        walk(mp, mpp)
        add_parts(mpp)
        add_parts(allp)
        setup(res=(1600, 900))
        cam_pos = (250 + 600, 100 + 420, 520)
        camera(cam_pos, (250 + 330, 100 + 40, 60), 26)
        render("preview_track.png")
        sys.exit(0)
    if shots == ["cars"]:
        d = load(os.path.join(ROOT, "src/ReplicatedStorage/Assets/Cars.model.json"))
        for i, mdl in enumerate(d["Children"]):
            pp = []
            walk(mdl, pp)
            add_parts(pp, offset=((i % 5) * 6 - 12, 0, (i // 5) * 9))
        add_parts([("Part", {"Size": {"Vector3": [200, 1, 200]},
                             "CFrame": {"CFrame": {"position": [0, -0.5, 0],
                                                   "orientation": [[1, 0, 0], [0, 1, 0],
                                                                   [0, 0, 1]]}},
                             "Color": {"Color3": [0.85, 0.87, 0.9]}})])
        setup(res=(1600, 900))
        camera((-16, 13, -18), (0, 1, 4.5), 32)
        render("preview_cars.png")
        sys.exit(0)
    if shots == ["styles"]:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bm", os.path.join(ROOT, "tools/build_map.py"))
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        bm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bm)
        from rbx import Inst as RI
        d = load(os.path.join(ROOT, "src/ReplicatedStorage/Assets/IslandStyles.model.json"))
        for i, st in enumerate(d["Children"]):
            a = {k: list(v.values())[0] for k, v in
                 st["Properties"]["Attributes"]["Attributes"].items()}
            isl = RI("Model", "I")
            bm.floating_island(isl, (0, 0, 0), 50, seed=i)
            js = isl.json()
            pp = []
            walk(js, pp)
            for cls, pr in pp:
                role = list(pr.get("Attributes", {}).get("Attributes", {}).get("Role", {}).values() or ["?"])[0]
                key = {"Grass": "Grass", "Dirt": "Dirt", "Rock": "Rock"}.get(role)
                if key:
                    h = a[key + "Color"].lstrip("#")
                    pr["Color"] = {"Color3": [int(h[j:j + 2], 16) / 255 for j in (0, 2, 4)]}
                    pr["Material"] = a[key + "Material"]
            dec = []
            walk(st["Children"][0], dec)
            off = ((i % 4) * 130, 0, (i // 4) * 150)
            add_parts(pp, offset=off)
            add_parts(dec, offset=off)
        setup(res=(1600, 900))
        camera((195, 260, 420), (195, -10, 75), 30)
        render("preview_styles.png")
        sys.exit(0)
    for f in files:
        walk(load(f), parts)
    print("parts", len(parts))
    add_parts(parts)
    setup()
    T = 100
    views = {
        "overview": ((600, T + 650, 800), (0, T - 40, 0), 26),
        "hub": ((115, T + 60, 115), (0, T + 6, 0), 26),
        "plot": ((360 + 170, T + 110, 140), (360, T, 0), 30),
        "shops": ((-20, T + 30, -30), (40, T + 8, 30), 24),
    }
    for s in shots:
        if s in views:
            pos, tgt, lens = views[s]
            camera(pos, tgt, lens)
            render(f"preview_{s}.png")
