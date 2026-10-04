"""Turns a Blender scene into Roblox-ready meshes.

Every model becomes a few MeshParts instead of dozens of Parts:
  * "tex"  - all opaque surfaces joined into one mesh, UV-mapped onto a shared colour palette
             texture (one image for the whole game, so it is cheap on phones)
  * "neon" - glowing pieces, one mesh per colour (MeshPart Material = Neon)
  * "glass"- see-through pieces, one mesh per colour (Material = Glass)
  * "role:<Name>" - pieces the game recolours at runtime (island grass/dirt/rock)

Objects pick their group with the custom property o["grp"] (default "tex").
bake(name) exports assets/meshes/<name>__<group>.fbx files and records their centre and size
(Roblox axes, studs) in assets/meshes/manifest.json. 1 Blender unit = 1 stud, Z up in Blender
= Y up in Roblox, Blender -Y = Roblox +Z.
"""
import hashlib
import json
import os

import bpy  # noqa: I001
import bmesh
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "meshes")
PALETTE_JSON = os.path.join(OUT, "palette.json")
PALETTE_PNG = os.path.join(OUT, "palette.png")
MANIFEST = os.path.join(OUT, "manifest.json")
GRID = 32          # 32 x 32 swatches
CELL_PX = 32       # -> 1024 x 1024 image


def _load(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


_palette = _load(PALETTE_JSON, [])


def swatch_uv(hexcol):
    """UV at the centre of the palette swatch for this colour (adds new colours at the end,
    so meshes baked earlier stay valid)."""
    hexcol = hexcol.lower()
    if hexcol not in _palette:
        _palette.append(hexcol)
        assert len(_palette) <= GRID * GRID, "palette full"
    i = _palette.index(hexcol)
    col, row = i % GRID, i // GRID
    return ((col + 0.5) / GRID, 1 - (row + 0.5) / GRID)


def save_palette():
    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    with open(PALETTE_JSON, "w") as f:
        json.dump(_palette, f, indent=0)
    img = Image.new("RGB", (GRID * CELL_PX, GRID * CELL_PX), (255, 0, 255))
    px = img.load()
    for i, h in enumerate(_palette):
        c = tuple(int(h[1 + k * 2:3 + k * 2], 16) for k in range(3))
        x0, y0 = (i % GRID) * CELL_PX, (i // GRID) * CELL_PX
        for y in range(y0, y0 + CELL_PX):
            for x in range(x0, x0 + CELL_PX):
                px[x, y] = c
    img.save(PALETTE_PNG)


def grp(o, group):
    o["grp"] = group
    return o


def _hex_of(o, poly=None):
    slots = o.material_slots
    if not slots:
        return "#ff00ff"
    m = slots[poly.material_index if poly is not None else 0].material
    return (m.get("hex") if m else None) or "#ff00ff"


def _to_roblox(v):
    return [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]


def _evaluated_copy(o):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.transform(o.matrix_world)
    return me


def bake(name, origin=(0, 0, 0), keep=False):
    """Exports the scene's meshes (except helpers starting with "_") grouped as described above.
    origin: Blender-space point that becomes the model origin. Returns the manifest entry."""
    groups = {}
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or o.name.startswith("_") or o.hide_render:
            continue
        g = o.get("grp", "tex")
        if g in ("neon", "glass"):
            g = g + _hex_of(o)
        groups.setdefault(g, []).append(o)
    os.makedirs(OUT, exist_ok=True)
    org = Vector(origin)
    entry = []
    for g, objs in sorted(groups.items()):
        bm = bmesh.new()
        for o in objs:
            me = _evaluated_copy(o)
            while len(me.uv_layers) > 1:
                me.uv_layers.remove(me.uv_layers[-1])
            if not me.uv_layers:
                me.uv_layers.new(name="UVMap")
            me.uv_layers[0].name = "UVMap"
            hexes = [_hex_of(o, p) for p in me.polygons]
            tmp = bmesh.new()
            tmp.from_mesh(me)
            tuv = tmp.loops.layers.uv.verify()
            tmp.faces.ensure_lookup_table()
            for f in tmp.faces:
                u = swatch_uv(hexes[f.index]) if g == "tex" else (0.5, 0.5)
                for lp in f.loops:
                    lp[tuv].uv = u
            me2 = bpy.data.meshes.new("tmp")
            tmp.to_mesh(me2)
            tmp.free()
            bm.from_mesh(me2)
            bpy.data.meshes.remove(me2)
            bpy.data.meshes.remove(me)
        if not bm.verts:
            bm.free()
            continue
        lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts),
                     min(v.co.z for v in bm.verts)))
        hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts),
                     max(v.co.z for v in bm.verts)))
        centre = (lo + hi) / 2
        for v in bm.verts:
            v.co -= centre
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        h = hashlib.sha1()
        for v in bm.verts:
            h.update(("%.3f,%.3f,%.3f;" % tuple(v.co)).encode())
        bm.faces.ensure_lookup_table()
        uv = bm.loops.layers.uv.active
        for f in bm.faces:
            h.update((",".join(str(v.index) for v in f.verts) + "|").encode())
            h.update(("%.4f,%.4f;" % tuple(f.loops[0][uv].uv)).encode())
        me = bpy.data.meshes.new(name + "_" + g)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = False
        ob = bpy.data.objects.new("_bake", me)
        bpy.context.scene.collection.objects.link(ob)
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        slug = g.replace("#", "").replace(":", "_")
        fbx = os.path.join(OUT, f"{name}__{slug}.fbx")
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z",
                                 axis_up="Y", use_mesh_modifiers=False, mesh_smooth_type="FACE",
                                 bake_space_transform=True)
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        kind, color = "tex", None
        if g.startswith("neon"):
            kind, color = "neon", g[4:]
        elif g.startswith("glass"):
            kind, color = "glass", g[5:]
        elif g.startswith("role:"):
            kind = "role"
            color = _hex_of(objs[0])
        size = hi - lo
        entry.append({"group": slug, "kind": kind, "color": color,
                      "role": g[5:] if kind == "role" else None,
                      "fbx": os.path.relpath(fbx, ROOT),
                      "center": _to_roblox(centre - org),
                      "size": [round(size.x, 4), round(size.z, 4), round(size.y, 4)],
                      "tris": tris, "hash": h.hexdigest()})
    man = _load(MANIFEST, {})
    man[name] = entry
    with open(MANIFEST, "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
    save_palette()
    total = sum(e["tris"] for e in entry)
    print(f"BAKED {name}: {len(entry)} meshes, {total} tris")
    return entry
