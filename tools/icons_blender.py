"""Renders cartoon 3D UI icons (transparent PNG, black outline) -> renders/icons/<name>.png

Run with the bpy python: python icons_blender.py [name ...]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders", "icons")
_mats = {}


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1,)


def mat(color, rough=0.35, emit=0.0, metal=0.0):
    key = (color, rough, emit, metal)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(color)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = 0.3
    if emit:
        b.inputs["Emission Color"].default_value = lin(color)
        b.inputs["Emission Strength"].default_value = emit
    _mats[key] = m
    return m


def finish(o, color, bevel=0.0, smooth=True, **kw):
    o.data.materials.append(mat(color, **kw))
    if bevel:
        bm = o.modifiers.new("b", "BEVEL")
        bm.width = bevel
        bm.segments = 4
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    return o


def cube(size, loc, color, rot=(0, 0, 0), bevel=0.05, **kw):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return finish(o, color, bevel, **kw)


def cyl(r, h, loc, color, rot=(0, 0, 0), verts=48, r2=None, bevel=0.03, **kw):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc,
                                            rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h,
                                        location=loc, rotation=rot)
    return finish(bpy.context.active_object, color, bevel, **kw)


def sphere(r, loc, color, scale=(1, 1, 1), **kw):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=48, ring_count=24)
    o = bpy.context.active_object
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return finish(o, color, **kw)


def torus(R, r, loc, color, rot=(0, 0, 0), arc=None, **kw):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=48, minor_segments=16)
    o = bpy.context.active_object
    if arc is not None:  # keep only the upper half
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(o.data)
        kill = [v for v in bm.verts if v.co.y < -0.02]
        bmesh.ops.delete(bm, geom=kill, context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
    return finish(o, color, **kw)


def text(s, size, loc, color, rot=(math.pi / 2, 0, 0), extrude=0.06):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.data.body = s
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = "CENTER"
    o.data.align_y = "CENTER"
    try:
        o.data.font = bpy.data.fonts.load(os.path.join(ROOT, "ui/fonts/Fredoka-Bold.ttf"))
    except Exception:
        pass
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    return finish(o, color, smooth=False)


def prism(points, depth, loc, color, rot=(0, 0, 0), bevel=0.02):
    """Extrude a 2D polygon (x, z) along y."""
    me = bpy.data.meshes.new("prism")
    n = len(points)
    verts = [(x, -depth / 2, z) for x, z in points] + [(x, depth / 2, z) for x, z in points]
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new("prism", me)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    bpy.context.view_layer.objects.active = o
    return finish(o, color, bevel, smooth=False)


# ------------------------------------------------------------------ icons
def i_coin():
    cyl(1.0, 0.28, (0, 0, 0), "#ffc21a", rot=(math.pi / 2, 0, 0), bevel=0.06, metal=0.3)
    cyl(0.78, 0.30, (0, 0, 0), "#ffd84d", rot=(math.pi / 2, 0, 0), bevel=0.02)
    text("$", 1.1, (0, -0.17, 0.02), "#e09400")


def i_basket():
    cyl(1.15, 1.0, (0, 0, -0.2), "#ff4f8b", verts=4, r2=0.85, rot=(0, 0, math.pi / 4), bevel=0.08)
    cyl(1.2, 0.18, (0, 0, 0.33), "#ffffff", verts=4, rot=(0, 0, math.pi / 4), bevel=0.06)
    for x in (-0.45, 0, 0.45):
        cube((0.12, 0.05, 0.6), (x, -0.83, -0.22), "#c41f5e", bevel=0.03)
    torus(0.75, 0.09, (0, 0, 0.35), "#9aa3b5", rot=(math.pi / 2, 0, 0), arc=True)


def i_book():
    cube((1.6, 0.42, 2.0), (0, 0, 0), "#2f8bff", bevel=0.1)
    cube((1.45, 0.36, 1.86), (0.12, -0.04, 0), "#ffffff", bevel=0.04)
    cube((1.5, 0.12, 2.0), (0.02, -0.24, 0), "#2f8bff", bevel=0.06)
    cyl(0.42, 0.1, (0.05, -0.32, 0.1), "#ffd23b", rot=(math.pi / 2, 0, 0))
    text("i", 0.7, (0.05, -0.38, 0.1), "#e08a00")


def i_calendar():
    cube((1.8, 0.35, 1.8), (0, 0, 0), "#ffffff", bevel=0.12)
    cube((1.82, 0.38, 0.55), (0, 0, 0.66), "#ff3b5c", bevel=0.1)
    for x in (-0.5, 0.5):
        cyl(0.1, 0.5, (x, -0.1, 1.0), "#6d6d78")
    text("31", 0.85, (0, -0.2, -0.18), "#2b2b38")


def i_ticket():
    shape = [(-1.3, 0.75), (1.3, 0.75), (1.3, 0.28)] + \
        [(1.3 - 0.28 * math.sin(math.pi * i / 10), 0.28 * math.cos(math.pi * i / 10)) for i in range(11)] + \
        [(1.3, -0.75), (-1.3, -0.75), (-1.3, -0.28)] + \
        [(-1.3 + 0.28 * math.sin(math.pi * i / 10), -0.28 * math.cos(math.pi * i / 10)) for i in range(11)]
    prism(shape, 0.3, (0, 0, 0), "#ffc21a")
    prism([(-1.0, 0.5), (1.0, 0.5), (1.0, -0.5), (-1.0, -0.5)], 0.32, (0, -0.02, 0), "#ff8a1f")
    text("★", 0.8, (0, -0.2, 0), "#fff27a")


def i_hammer():
    th = math.radians(-35)
    up = (math.sin(th), 0, math.cos(th))
    cyl(0.16, 2.4, (0, 0, 0), "#c9874a", rot=(0, th, 0))
    top = (up[0] * 1.15, 0, up[2] * 1.15)
    cube((1.5, 0.62, 0.62), top, "#aeb6c8", rot=(0, th, 0), bevel=0.12, metal=0.3)
    side = (math.cos(th), 0, -math.sin(th))
    cube((0.34, 0.7, 0.7), (top[0] + side[0] * 0.75, 0, top[2] + side[2] * 0.75), "#7d8496",
         rot=(0, th, 0), bevel=0.08)


def i_dice():
    cube((1.6, 1.6, 1.6), (0, 0, 0), "#ffffff", rot=(math.radians(18), math.radians(-12), math.radians(30)),
         bevel=0.3)
    o = bpy.context.active_object
    bpy.context.view_layer.update()
    pips = [(0, -0.81, 0), (-0.42, -0.81, 0.42), (0.42, -0.81, -0.42), (0.81, 0, 0), (0.81, 0.4, 0.4),
            (0, 0.42, 0.81), (0.42, -0.42, 0.81), (-0.42, 0.42, 0.81)]
    for p in pips:
        s = sphere(0.17, p, "#1b1b24", scale=(1, 1, 1))
        s.location = o.matrix_world @ Vector(p)


def i_skills():
    def arrow(x, z, s, color):
        pts = [(0, 1.0), (0.9, 0.05), (0.38, 0.05), (0.38, -0.9), (-0.38, -0.9), (-0.38, 0.05),
               (-0.9, 0.05)]
        prism([(px * s, pz * s) for px, pz in pts], 0.4 * s, (x, 0, z), color, bevel=0.05)
    arrow(-0.85, -0.25, 0.65, "#8f3bff")
    arrow(0.85, -0.25, 0.65, "#8f3bff")
    arrow(0, 0.2, 1.0, "#b56bff")


def i_clover():
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        x, z = math.cos(ang) * 0.55, math.sin(ang) * 0.55
        sphere(0.55, (x, 0, z), "#3fd14a", scale=(1, 0.35, 1))
    cyl(0.09, 1.0, (0.25, 0.05, -0.85), "#2c9c10", rot=(0, math.radians(20), 0))
    sphere(0.18, (0, -0.15, 0), "#7dff6b", scale=(1, 0.5, 1))


def i_gift():
    cube((1.7, 1.7, 1.3), (0, 0, -0.3), "#b54dff", bevel=0.08)
    cube((1.85, 1.85, 0.4), (0, 0, 0.45), "#c97bff", bevel=0.08)
    cube((0.35, 1.9, 1.75), (0, 0, -0.05), "#ffd23b", bevel=0.03)
    cube((1.9, 0.35, 1.75), (0, 0, -0.05), "#ffd23b", bevel=0.03)
    torus(0.38, 0.13, (-0.38, 0, 0.85), "#ffd23b", rot=(math.pi / 2, 0, math.radians(20)))
    torus(0.38, 0.13, (0.38, 0, 0.85), "#ffd23b", rot=(math.pi / 2, 0, math.radians(-20)))


def i_car():
    cube((2.4, 1.2, 0.7), (0, 0, -0.1), "#ff3b3b", bevel=0.2)
    cube((1.3, 1.05, 0.6), (-0.1, 0, 0.45), "#ff3b3b", bevel=0.18)
    cube((1.1, 1.08, 0.42), (-0.1, 0, 0.47), "#9fe6ff", bevel=0.1)
    for x in (-0.8, 0.8):
        for y in (-0.55, 0.55):
            cyl(0.33, 0.25, (x, y, -0.45), "#2b2b38", rot=(math.pi / 2, 0, 0))
            cyl(0.15, 0.27, (x, y, -0.45), "#e6e6e6", rot=(math.pi / 2, 0, 0))


def i_house():
    cube((1.7, 1.4, 1.2), (0, 0, -0.4), "#fff1d6", bevel=0.06)
    prism([(-1.1, 0.2), (1.1, 0.2), (0, 1.15)], 1.6, (0, 0, 0), "#ff4f4f", bevel=0.05)
    cube((0.45, 0.1, 0.75), (0, -0.7, -0.62), "#8a5a2b", bevel=0.04)
    cube((0.4, 0.1, 0.35), (0.55, -0.7, -0.3), "#9fe6ff", bevel=0.03)


def i_palette():
    sphere(1.2, (0, 0, 0), "#f2d29b", scale=(1.1, 0.2, 0.85))
    cyl(0.22, 0.4, (0.55, 0, -0.35), "#d9b37a", rot=(math.pi / 2, 0, 0))
    for i, c in enumerate(("#ff3b3b", "#ffd23b", "#3bd16b", "#3b8bff", "#b54dff")):
        a = math.radians(150 - i * 55)
        sphere(0.24, (math.cos(a) * 0.72, -0.2, math.sin(a) * 0.55 + 0.05), c, scale=(1, 0.5, 1))


def i_trophy():
    cyl(0.75, 1.0, (0, 0, 0.35), "#ffc21a", r2=0.45, rot=(math.pi, 0, 0), metal=0.4)
    torus(0.35, 0.09, (-0.8, 0, 0.45), "#ffc21a", rot=(math.pi / 2, 0, 0), metal=0.4)
    torus(0.35, 0.09, (0.8, 0, 0.45), "#ffc21a", rot=(math.pi / 2, 0, 0), metal=0.4)
    cyl(0.12, 0.5, (0, 0, -0.35), "#e09400")
    cube((0.9, 0.6, 0.3), (0, 0, -0.72), "#8a5a2b", bevel=0.06)
    text("1", 0.55, (0, -0.62, 0.42), "#fff27a")


def i_potion():
    sphere(0.9, (0, 0, -0.3), "#b54dff", emit=0.4)
    cyl(0.3, 0.6, (0, 0, 0.75), "#d9a3ff")
    cyl(0.36, 0.3, (0, 0, 1.15), "#9c6b3c")
    sphere(0.22, (-0.35, -0.75, 0.0), "#ffffff", scale=(0.6, 0.3, 1), emit=1.0)


def i_crate():
    cube((1.8, 1.8, 1.6), (0, 0, 0), "#e8a052", rot=(0, 0, math.radians(35)), bevel=0.08)
    cube((1.82, 0.4, 0.05), (0, 0, 0.8), "#c97a2f", rot=(0, 0, math.radians(35)))
    cube((0.4, 1.82, 0.05), (0, 0, 0.8), "#c97a2f", rot=(0, 0, math.radians(35)))


ICONS = {
    "coin": i_coin, "shop": i_basket, "index": i_book, "daily": i_calendar, "pass": i_ticket,
    "build": i_hammer, "dice": i_dice, "skills": i_skills, "luck": i_clover, "gift": i_gift,
    "car": i_car, "home": i_house, "palette": i_palette, "trophy": i_trophy, "potion": i_potion,
    "crate": i_crate,
}


def setup():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 512
    sc.view_settings.view_transform = "Standard"
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 3
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("Outline")
    style = bpy.data.linestyles.new("Outline")
    style.color = (0.06, 0.05, 0.1)
    style.thickness = 3
    ls.linestyle = style
    ls.select_by_visibility = True
    ls.select_silhouette = True
    ls.select_border = False
    ls.select_crease = False
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    sc.world = w
    for e, rot in ((3.5, (math.radians(50), 0, math.radians(30))),
                   (1.2, (math.radians(70), 0, math.radians(-120)))):
        ld = bpy.data.lights.new("sun", "SUN")
        ld.energy = e
        o = bpy.data.objects.new("sun", ld)
        sc.collection.objects.link(o)
        o.rotation_euler = rot


def frame_camera():
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2
    cd = bpy.data.cameras.new("c")
    cd.type = "ORTHO"
    c = bpy.data.objects.new("c", cd)
    bpy.context.scene.collection.objects.link(c)
    d = Vector((0.35, -1, 0.35)).normalized()
    c.rotation_euler = (-d).to_track_quat("-Z", "Z").to_euler()
    bpy.context.view_layer.update()
    rot = c.rotation_euler.to_matrix()
    right, upv = rot.col[0], rot.col[1]
    xs = [p.dot(right) for p in pts]
    ys = [p.dot(upv) for p in pts]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    center = right * cx + upv * cy + d * (center.dot(d))
    cd.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.12
    c.location = center + d * 20
    bpy.context.scene.camera = c


def render_icon(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    ICONS[name]()
    setup()
    frame_camera()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("ICON", path)


if __name__ == "__main__":
    for n in (sys.argv[1:] or list(ICONS)):
        render_icon(n)
