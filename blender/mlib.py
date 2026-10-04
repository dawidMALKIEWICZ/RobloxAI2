"""Modelling helpers for polished cartoon models (1 Blender unit = 1 Roblox stud, Z up)."""
import math
import os

import bpy  # noqa: I001  (must be imported before bmesh)
import bmesh
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "ui/fonts/Fredoka-Bold.ttf")
_mats = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1,)


def mat(color, rough=0.5, emit=0.0, metal=0.0, alpha=1.0, name=None):
    key = (color, rough, emit, metal, alpha)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name or color)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = lin(color)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    m.diffuse_color = lin(color)
    _mats[key] = m
    return m


def _finish(o, color, bevel, segs, smooth, name, **kw):
    if name:
        o.name = name
    if color:
        o.data.materials.append(mat(color, **kw))
    if bevel:
        m = o.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = segs
        m.limit_method = "ANGLE"
        m.harden_normals = False
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def box(size, loc, color, rot=(0, 0, 0), bevel=0.15, segs=2, smooth=False, name=None, **kw):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, color, bevel, segs, smooth, name, **kw)


def cyl(r, h, loc, color, rot=(0, 0, 0), verts=20, r2=None, bevel=0.08, segs=2, smooth=True,
        name=None, **kw):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc,
                                            rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h,
                                        location=loc, rotation=rot)
    return _finish(bpy.context.active_object, color, bevel, segs, smooth, name, **kw)


def sphere(r, loc, color, scale=(1, 1, 1), subdiv=3, smooth=True, name=None, ico=False, **kw):
    if ico:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
    o = bpy.context.active_object
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(o, color, 0, 0, smooth, name, **kw)


def torus(R, r, loc, color, rot=(0, 0, 0), name=None, half=False, **kw):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=(0, 0, 0),
                                     major_segments=24, minor_segments=8)
    o = bpy.context.active_object
    if half:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y < -1e-3], context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
    o.location = loc
    o.rotation_euler = rot
    return _finish(o, color, 0, 0, True, name, **kw)


def prism(points, depth, loc, color, rot=(0, 0, 0), bevel=0.05, name=None, **kw):
    """Extrude 2D polygon points (x, z) along Y by depth."""
    me = bpy.data.meshes.new("prism")
    n = len(points)
    verts = [(x, -depth / 2, z) for x, z in points] + [(x, depth / 2, z) for x, z in points]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name or "prism", me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    bpy.context.view_layer.objects.active = o
    return _finish(o, color, bevel, 2, False, name, **kw)


def text(s, size, loc, color, rot=(math.pi / 2, 0, 0), extrude=0.1, bevel=0.02, name=None, **kw):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.data.body = s
    o.data.size = size
    o.data.extrude = extrude
    o.data.bevel_depth = bevel
    o.data.align_x = "CENTER"
    o.data.align_y = "CENTER"
    if os.path.exists(FONT):
        o.data.font = bpy.data.fonts.load(FONT)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    return _finish(o, color, 0, 0, False, name, **kw)


def rounded_rect(w, h, r, n=6):
    """2D rounded rectangle points (x, z) centred at origin."""
    pts = []
    for cx, cz, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


def scallops(width, n, loc, color_a, color_b, depth=0.3, r=None, rot=(0, 0, 0)):
    """Row of half-discs hanging down (awning edge) along X."""
    r = r or width / n / 2
    out = []
    for i in range(n):
        x = -width / 2 + r + i * 2 * r
        pts = [(r * math.cos(math.pi + math.pi * k / 10), r * math.sin(math.pi + math.pi * k / 10))
               for k in range(11)]
        o = prism(pts, depth, (loc[0] + x, loc[1], loc[2]), color_a if i % 2 == 0 else color_b,
                  rot=rot, bevel=0.03)
        out.append(o)
    return out


# ------------------------------------------------------------------ scene / output
def studio(ground=True, ground_color="#7ed957", sun=3.2):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.render.resolution_x, sc.render.resolution_y = 1280, 960
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = lin("#cfeaff")
    bg.inputs["Strength"].default_value = 1.1
    sc.world = w
    for e, rot, ang in ((sun, (math.radians(48), math.radians(8), math.radians(35)), 10),
                        (0.8, (math.radians(65), 0, math.radians(-140)), 30)):
        ld = bpy.data.lights.new("sun", "SUN")
        ld.energy = e
        ld.angle = math.radians(ang)
        o = bpy.data.objects.new("sun", ld)
        sc.collection.objects.link(o)
        o.rotation_euler = rot
    if ground:
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=40, depth=1, location=(0, 0, -0.5))
        g = bpy.context.active_object
        g.name = "_ground"
        g.data.materials.append(mat(ground_color, rough=0.9))


def camera(target, dist, elev=28, azim=-35, lens=50):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    c = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(c)
    t = Vector(target)
    e, a = math.radians(elev), math.radians(azim)
    c.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    c.rotation_euler = (t - c.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = c
    return c


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)


def export(name):
    """Saves .blend and .fbx (without helper objects) to assets/models/<name>."""
    d = os.path.join(ROOT, "assets", "models")
    os.makedirs(d, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and not o.name.startswith("_"):
            o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(d, name + ".fbx"), use_selection=True,
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Z", axis_up="Y", use_mesh_modifiers=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(d, name + ".blend"), compress=True)
    tris = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and not o.name.startswith("_"):
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            tris += sum(len(p.vertices) - 2 for p in me.polygons)
            ev.to_mesh_clear()
    print("EXPORTED", name, "triangles:", tris)
