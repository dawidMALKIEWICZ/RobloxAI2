"""Car modelling helpers (1 Blender unit = 1 stud, +Y = car front, X = right, Z up, road z = 0).

loft()   - smooth car bodies from rounded cross-sections (with painted stripes per face)
strip()  - a bar between two points (pillars, roll cages, frames, arms)
wheel()  - detailed wheel built as its own mesh ("part:Wheel<FL|FR|RL|RR>") centred on the axle
driver() - small cartoon driver with helmet and arms on the steering wheel
"""
import math

import bpy  # noqa: I001
import bmesh
from mathutils import Vector

import mlib as L

TIRE = "#2a2a33"
TIRE_SIDE = "#3a3a45"
RIM = "#dfe4ee"
DARK = "#2b2f3a"
CHROME = "#eef2f8"
HEAD = "#fff6c2"
TAIL = "#ff3348"
SKIN = "#ffcf9e"
SEAT = "#3a3440"


def neon(o):
    o["grp"] = "neon"
    return o


def glass(o):
    o["grp"] = "glass"
    return o


def grp(o, g):
    if g:
        o["grp"] = g
    return o


# ------------------------------------------------------------------ loft
def _ring(wb, wt, z0, z1, rb, rt, nc, top_breaks, side_breaks):
    """Rounded trapezoid outline -> list of (x, z, u, v) (u in -1..1, v in 0..1)."""
    h = max(z1 - z0, 1e-3)
    rb = max(min(rb, wb * 0.98, h * 0.49), 0.005)
    rt = max(min(rt, wt * 0.98, h * 0.49), 0.005)
    rub, rvb = rb / wb, rb / h
    rut, rvt = rt / wt, rt / h
    uv = []

    def corner(cu, cv, ru, rv, a0):
        for i in range(nc + 1):
            a = math.radians(a0 + 90 * i / nc)
            uv.append((cu + ru * math.cos(a), cv + rv * math.sin(a)))

    corner(1 - rub, rvb, rub, rvb, -90)
    for v in side_breaks:
        uv.append((1.0, min(max(v, rvb + 1e-3), 1 - rvt - 1e-3)))
    corner(1 - rut, 1 - rvt, rut, rvt, 0)
    lim = 1 - rut - 1e-3
    for b in sorted(top_breaks, reverse=True):
        uv.append((max(-lim, min(lim, b / wt)), 1.0))
    corner(-1 + rut, 1 - rvt, rut, rvt, 90)
    for v in reversed(side_breaks):
        uv.append((-1.0, min(max(v, rvb + 1e-3), 1 - rvt - 1e-3)))
    corner(-1 + rub, rvb, rub, rvb, 180)
    out = []
    for u, v in uv:
        out.append((u * (wb + (wt - wb) * v), z0 + v * h, u, v))
    return out


def loft(sections, color, paint=None, nc=2, top_breaks=(), side_breaks=(), name="loft",
         group=None, cap=True, x=0.0):
    """sections: [(y, half_width_bottom, half_width_top, z_bottom, z_top, r_bottom, r_top)].
    paint(u, v, y) -> hex or None paints single faces (stripes, two-tone)."""
    verts, faces, cols = [], [], []
    rings = []
    for (y, wb, wt, z0, z1, rb, rt) in sections:
        ring = _ring(wb, wt, z0, z1, rb, rt, nc, top_breaks, side_breaks)
        rings.append([(len(verts) + i, p) for i, p in enumerate(ring)])
        verts += [(px + x, y, pz) for (px, pz, _u, _v) in ring]
    n = len(rings[0])
    for s in range(len(rings) - 1):
        y = (sections[s][0] + sections[s + 1][0]) / 2
        for i in range(n):
            j = (i + 1) % n
            a, b = rings[s][i], rings[s][j]
            c, d = rings[s + 1][j], rings[s + 1][i]
            faces.append((a[0], b[0], c[0], d[0]))
            u = (a[1][2] + b[1][2]) / 2
            v = (a[1][3] + b[1][3]) / 2
            cols.append((paint and paint(u, v, y)) or color)
    if cap:
        faces.append(tuple(i for i, _p in rings[0]))
        cols.append((paint and paint(0, 0.5, sections[0][0] - 1e-3)) or color)
        faces.append(tuple(i for i, _p in reversed(rings[-1])))
        cols.append((paint and paint(0, 0.5, sections[-1][0] + 1e-3)) or color)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    palette = list(dict.fromkeys(cols))
    for c in palette:
        me.materials.append(L.mat(c))
    for p, c in zip(me.polygons, cols):
        p.material_index = palette.index(c)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return grp(o, group)


def section_at(sections, y):
    """Interpolated (half_w_bottom, half_w_top, z_bottom, z_top) of a loft at y."""
    ss = sorted(sections, key=lambda s: s[0])
    if y <= ss[0][0]:
        return ss[0][1:5]
    for a, b in zip(ss, ss[1:]):
        if a[0] <= y <= b[0]:
            t = (y - a[0]) / max(b[0] - a[0], 1e-6)
            return tuple(a[k] + (b[k] - a[k]) * t for k in range(1, 5))
    return ss[-1][1:5]


# ------------------------------------------------------------------ bars
def strip(a, b, w, t, color, up=(0, 0, 1), bevel=0.0, group=None, **kw):
    """Box from point a to point b: width w (across), thickness t (along up)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    ln = d.length
    q = d.to_track_quat("Y", "Z")
    # roll the box so its thickness follows `up`
    o = L.box((w, ln, t), (0, 0, 0), color, bevel=bevel, **kw)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = q
    o.location = (a + b) / 2
    if Vector(up) != Vector((0, 0, 1)):
        upv = Vector(up).normalized()
        ax = d.normalized()
        cur = q @ Vector((0, 0, 1))
        cur = (cur - ax * cur.dot(ax)).normalized()
        want = (upv - ax * upv.dot(ax))
        if want.length > 1e-4:
            want.normalize()
            ang = math.atan2(ax.dot(cur.cross(want)), cur.dot(want))
            from mathutils import Quaternion
            o.rotation_quaternion = Quaternion(ax, ang) @ q
    return grp(o, group)


def tube(a, b, r, color, verts=6, group=None, **kw):
    a, b = Vector(a), Vector(b)
    d = b - a
    o = L.cyl(r, d.length, (0, 0, 0), color, verts=verts, **kw)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    o.location = (a + b) / 2
    return grp(o, group)


def mirror_x(fn):
    """Calls fn(sign) for both sides."""
    for s in (-1, 1):
        fn(s)


# ------------------------------------------------------------------ wheels
def wheel_name(x, y, front_y):
    return "Wheel" + ("F" if y >= front_y - 1e-3 else "R") + ("L" if x < 0 else "R")


def ball(r, loc, color, scale=(1, 1, 1), seg=10, rings=6, **kw):
    """Low-poly UV sphere (rounder than an icosphere for the same triangle count)."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=rings)
    o = bpy.context.active_object
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(L.mat(color, **kw))
    return o


def ring(R, r, loc, color, rot=(0, 0, 0), maj=10, mnr=4, **kw):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=maj, minor_segments=mnr)
    o = bpy.context.active_object
    o.data.materials.append(L.mat(color, **kw))
    return o


def place(o, loc, ax, g=None):
    """Object built at the origin -> rotate about X by ax, then move to loc."""
    o.rotation_euler = (ax, 0, 0)
    o.location = loc
    return grp(o, g)


def wheel(name, x, y, r, w, tire=TIRE, rim=RIM, hub=DARK, style="spoke", knobs=0, z=None,
          rim_r=0.64, accent=None):
    """A wheel as its own mesh (part:<name>), axle along X, centred at (x, y, z).
    About 250-400 triangles. The tyre is symmetric so the mesh centre is the axle."""
    z = r if z is None else z
    g = "part:" + name
    s = 1 if x > 0 else -1
    rot = (0, math.pi / 2, 0)
    grp(L.cyl(r, w, (x, y, z), tire, rot=rot, verts=16, bevel=min(r * 0.2, w * 0.28), segs=1), g)
    if knobs:
        for k in range(knobs):
            a = k / knobs * math.tau
            sx = 1 if k % 2 else -1
            place(L.box((w * 0.5, r * 0.24, r * 0.12), (0, 0, 0), tire),
                  (x + sx * w * 0.2, y + math.cos(a) * r * 0.94, z + math.sin(a) * r * 0.94),
                  a + math.pi / 2, g)
    # rim on the outer face
    ox = x + s * (w / 2 - 0.03)
    rr = r * rim_r
    grp(L.cyl(rr, 0.06, (ox, y, z), rim, rot=rot, verts=16), g)
    grp(L.cyl(rr * 0.8, 0.08, (ox + s * 0.005, y, z), hub, rot=rot, verts=12), g)
    if style in ("spoke", "star"):
        n, wd = (5, 0.24) if style == "spoke" else (6, 0.14)
        for k in range(n):
            a = k / n * math.tau + math.pi / 2
            place(L.box((0.05, rr * 0.8, rr * wd), (0, 0, 0), rim),
                  (ox + s * 0.03, y + math.cos(a) * rr * 0.4, z + math.sin(a) * rr * 0.4), a, g)
    elif style == "disc":
        grp(L.cyl(rr * 0.74, 0.1, (ox + s * 0.01, y, z), rim, rot=rot, verts=12), g)
        for k in range(5):
            a = k / 5 * math.tau + math.pi / 2
            place(L.box((0.11, rr * 0.16, rr * 0.16), (0, 0, 0), hub),
                  (ox + s * 0.02, y + math.cos(a) * rr * 0.5, z + math.sin(a) * rr * 0.5), a, g)
    elif style == "dish":
        grp(L.cyl(rr * 0.78, 0.1, (ox + s * 0.01, y, z), rim, rot=rot, verts=12), g)
        grp(L.cyl(rr * 0.5, 0.12, (ox + s * 0.015, y, z), hub, rot=rot, verts=12), g)
    # centre cap
    grp(L.cyl(rr * 0.26, 0.1, (ox + s * 0.04, y, z), accent or rim, rot=rot, verts=8), g)
    return name


def wheels(xw, yf, yb, r, w, rb=None, wb=None, **kw):
    """Four wheels: front axle at yf, rear at yb (rear can be bigger: rb, wb)."""
    rb = rb or r
    wb = wb or w
    for x in (-xw, xw):
        wheel(wheel_name(x, yf, yf), x, yf, r, w, **kw)
        wheel(wheel_name(x, yb, yf), x, yb, rb, wb, **kw)


def arch(x, y, r, w, color, z=None, thick=0.12, segs=6):
    """Half-ring fender flare over a wheel (static body part)."""
    z = r if z is None else z
    pts = []
    for i in range(segs + 1):
        a = math.pi * i / segs
        pts.append(((r + thick) * math.cos(a), (r + thick) * math.sin(a)))
    for i in range(segs, -1, -1):
        a = math.pi * i / segs
        pts.append((r * math.cos(a), r * math.sin(a)))
    # prism extrudes (x, z) along Y; turn it so the width runs along X
    return L.prism(pts, w, (x, y, z), color, rot=(0, 0, math.pi / 2), bevel=0.0)


# ------------------------------------------------------------------ people & interior
def seat(x, y, z, color=SEAT, w=0.5, s=1.0):
    L.box((w * s, 0.45 * s, 0.14 * s), (x, y, z + 0.07 * s), color, bevel=0.05 * s, segs=1)
    o = L.box((w * s, 0.14 * s, 0.55 * s), (x, y - 0.22 * s, z + 0.32 * s), color, bevel=0.05 * s,
              rot=(math.radians(-12), 0, 0))
    return o


def steering(x, y, z, s=1.0, tilt=55, color=DARK):
    t = math.radians(tilt)
    ring(0.15 * s, 0.03 * s, (x, y, z), color, rot=(t, 0, 0))
    strip((x, y, z), (x, y + 0.3 * s * math.sin(t), z - 0.3 * s * math.cos(t)), 0.05 * s,
          0.05 * s, color)


def driver(x, y, z, suit="#3b8bff", helmet="#ff3b3b", visor="#22283a", s=1.0, stripe="#ffffff",
           wheel_y=None, wheel_z=None, tilt=55, open_face=False):
    """Seated driver: hips at (x, y, z), facing +Y. Adds the steering wheel too."""
    wy = y + 0.38 * s if wheel_y is None else wheel_y
    wz = z + 0.42 * s if wheel_z is None else wheel_z
    L.box((0.4 * s, 0.26 * s, 0.46 * s), (x, y - 0.02 * s, z + 0.25 * s), suit, bevel=0.08 * s,
          segs=1)
    L.box((0.42 * s, 0.1 * s, 0.1 * s), (x, y + 0.08 * s, z + 0.44 * s), stripe, bevel=0.03 * s)
    hz = z + 0.72 * s
    ball(0.13 * s, (x, y + 0.02 * s, hz - 0.17 * s), SKIN, seg=8, rings=4)
    ball(0.22 * s, (x, y, hz), helmet, seg=12, rings=7)
    L.box((0.04 * s, 0.4 * s, 0.05 * s), (x, y, hz + 0.2 * s), stripe)
    if open_face:
        L.box((0.26 * s, 0.1 * s, 0.13 * s), (x, y + 0.17 * s, hz - 0.01 * s), SKIN)
        L.box((0.28 * s, 0.06 * s, 0.07 * s), (x, y + 0.21 * s, hz + 0.05 * s), visor)
    else:
        L.box((0.3 * s, 0.1 * s, 0.13 * s), (x, y + 0.17 * s, hz + 0.01 * s), visor, bevel=0.03 * s)
    steering(x, wy, wz, s, tilt)
    for sx in (-1, 1):
        strip((x + sx * 0.19 * s, y + 0.02 * s, z + 0.4 * s),
              (x + sx * 0.12 * s, wy - 0.02 * s, wz), 0.09 * s, 0.09 * s, suit)
        ball(0.05 * s, (x + sx * 0.12 * s, wy, wz), "#ffffff", seg=6, rings=3)


# ------------------------------------------------------------------ lights & bits
def headlamp(x, y, z, r, color=HEAD, bezel=CHROME, facing=1, verts=12):
    rot = (math.pi / 2, 0, 0)
    L.cyl(r, 0.08, (x, y, z), bezel, rot=rot, verts=verts)
    neon(L.cyl(r * 0.75, 0.06, (x, y + facing * 0.04, z), color, rot=rot, verts=verts))


def lamp_box(size, pos, color, rot=(0, 0, 0)):
    return neon(L.box(size, pos, color, rot=rot))


def grille(x, y, z, w, h, bars=3, frame=CHROME, back=DARK, depth=0.08):
    L.box((w, depth, h), (x, y, z), back)
    L.box((w + 0.06, depth * 0.6, h + 0.06), (x, y - 0.02, z), frame)
    for i in range(bars):
        bz = z - h / 2 + h * (i + 1) / (bars + 1)
        L.box((w * 0.92, depth * 1.2, h * 0.08), (x, y + 0.01, bz), frame)


def mirror(x, y, z, color, s=1):
    strip((x, y, z), (x + s * 0.16, y - 0.02, z + 0.06), 0.04, 0.04, DARK)
    L.box((0.1, 0.07, 0.08), (x + s * 0.2, y - 0.02, z + 0.08), color, bevel=0.02)
    L.box((0.08, 0.02, 0.06), (x + s * 0.2, y - 0.06, z + 0.08), "#bfe9ff")


def exhaust(x, y, z, r=0.07, length=0.3, color=CHROME):
    rot = (math.pi / 2, 0, 0)
    L.cyl(r, length, (x, y, z), color, rot=rot, verts=10)
    L.cyl(r * 0.65, 0.02, (x, y - length / 2 - 0.005, z), "#1a1a20", rot=rot, verts=10)


def plate(y, z, facing=1, color="#ffffff", band="#3b6bff"):
    L.box((0.42, 0.03, 0.14), (0, y, z), color, bevel=0.01)
    L.box((0.06, 0.035, 0.14), (-0.18, y + facing * 0.002, z), band)


def label(s, size, loc, color, rot=(math.pi / 2, 0, 0), extrude=0.02):
    """Low-poly extruded text (numbers on doors / noses)."""
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.data.body = s
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = "CENTER"
    o.data.align_y = "CENTER"
    o.data.resolution_u = 1
    import os
    if os.path.exists(L.FONT):
        o.data.font = bpy.data.fonts.load(L.FONT, check_existing=True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.append(L.mat(color))
    return o
