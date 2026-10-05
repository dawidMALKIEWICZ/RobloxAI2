"""Themed 3D dice (13, see tools/gamedata.py DICE). Each die is about 2x2x2 studs, centred at the
origin, with inset pips (+Z = 6, -Z = 1, -Y = 5, +Y = 2, +X = 4, -X = 3) and its own flair.

Run: <bpy python> dice.py [id ...]
  -> assets/meshes/Dice_<id>__*.fbx (bake), renders/dice/<id>.png, renders/dice_sheet.png
blender/models/item_icons.py renders the shop icons from the same builders.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import bpy  # noqa: E402,I001
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402
import mlib as L  # noqa: E402
import meshkit as K  # noqa: E402
import carkit as C  # noqa: E402

PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
        4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
        6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}
FACES = [((0, 0, 1), 6), ((0, 0, -1), 1), ((0, -1, 0), 5), ((0, 1, 0), 2), ((1, 0, 0), 4),
         ((-1, 0, 0), 3)]
RAINBOW = ["#ff3b3b", "#ff9f1a", "#ffe03b", "#4bdc5a", "#3bd1ff", "#7b5cff"]
H = 1.0          # half size of the die body
SP = 0.5         # pip spacing


def neon(o, color=None):
    o["grp"] = "neon"
    if color:
        o.data.materials.clear()
        o.data.materials.append(L.mat(color, emit=3.0))
    return o


def glow(color):
    """Material for neon pieces (glows in the renders)."""
    return L.mat(color, emit=3.0)


def face_frame(n):
    """(normal, tangent a, tangent b) for a face normal."""
    n = Vector(n)
    if abs(n.z) > 0.5:
        a, b = Vector((1, 0, 0)), Vector((0, 1, 0))
    elif abs(n.y) > 0.5:
        a, b = Vector((1, 0, 0)), Vector((0, 0, 1))
    else:
        a, b = Vector((0, 1, 0)), Vector((0, 0, 1))
    return n, a, b


def pip_spots(h=H, sp=SP):
    """[(position on the face surface, normal, count)]"""
    out = []
    for n, k in FACES:
        n, a, b = face_frame(n)
        for u, v in PIPS[k]:
            out.append((n * h + a * u * sp + b * v * sp, n, k))
    return out


def orient(o, n):
    """Turn an object built facing +Z so it faces normal n."""
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(n))
    return o


def apply(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def join(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    return bpy.context.active_object


def body(color, h=H, bevel=0.32, segs=3, **kw):
    o = L.box((2 * h, 2 * h, 2 * h), (0, 0, 0), color, bevel=bevel, segs=segs, **kw)
    o.modifiers["bevel"].limit_method = "NONE"
    return apply(o)


def carve(target, cutters):
    """Boolean-subtract the cutters (their material lines the holes)."""
    cut = join(cutters)
    cut.name = "_cut"
    m = target.modifiers.new("bool", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.solver = "EXACT"
    m.object = cut
    try:
        m.material_mode = "TRANSFER"
    except (AttributeError, TypeError):
        pass
    apply(target)
    bpy.data.objects.remove(cut)
    return target


def dimples(target, color, r=0.17, depth=0.07, h=H, sp=SP, shape="round", skip=()):
    cutters = []
    for pos, n, k in pip_spots(h, sp):
        if k in skip:
            continue
        if shape == "round":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(0, 0, 0), segments=10,
                                                 ring_count=5)
            o = bpy.context.active_object
            o.scale = (1, 1, 0.7)
        elif shape == "square":
            o = L.box((r * 1.7, r * 1.7, r * 1.2), (0, 0, 0), color)
        else:  # star
            pts = []
            for i in range(10):
                a = math.pi / 2 + i * math.pi / 5
                rr = r * 1.35 if i % 2 == 0 else r * 0.6
                pts.append((math.cos(a) * rr, math.sin(a) * rr))
            o = L.prism(pts, r * 1.2, (0, 0, 0), color, rot=(math.pi / 2, 0, 0))
            apply(o)
        if not o.data.materials:
            o.data.materials.append(L.mat(color))
        else:
            o.data.materials[0] = L.mat(color)
        orient(o, n)
        o.location = pos + n * (r * 0.7 - depth)
        cutters.append(o)
    carve(target, cutters)


def neon_pips(color, r=0.15, h=H, sp=SP, shape="round", lift=0.02, skip=()):
    """Glowing pips sitting on (or just in) the face: one neon mesh."""
    objs = []
    for pos, n, k in pip_spots(h, sp):
        if k in skip:
            continue
        if shape == "round":
            o = L.cyl(r, 0.06, (0, 0, 0), color, verts=10)
        elif shape == "square":
            o = L.box((r * 1.6, r * 1.6, 0.06), (0, 0, 0), color)
        else:
            pts = []
            for i in range(10):
                a = math.pi / 2 + i * math.pi / 5
                rr = r * 1.4 if i % 2 == 0 else r * 0.6
                pts.append((math.cos(a) * rr, math.sin(a) * rr))
            o = L.prism(pts, 0.06, (0, 0, 0), color, rot=(math.pi / 2, 0, 0))
            apply(o)
        orient(o, n)
        o.location = pos + n * lift
        objs.append(o)
    o = join(objs)
    return neon(o, color)


def edge_bars(color, h=H, t=0.09, bev=0.32, grp=None, length=None):
    """12 bars hugging the rounded cube edges (trim / glowing seams)."""
    out = []
    e = (h - bev) + bev * 0.7071 + t * 0.2
    ln = length or 2 * h - 0.5
    for ax in range(3):
        for s1 in (-1, 1):
            for s2 in (-1, 1):
                p = [0, 0, 0]
                o1, o2 = [i for i in range(3) if i != ax]
                p[o1], p[o2] = s1 * e, s2 * e
                size = [t, t, t]
                size[ax] = ln
                o = L.box(tuple(size), tuple(p), color, bevel=t * 0.3)
                if grp:
                    o["grp"] = grp
                out.append(o)
    return out


def sparkle(pos, size, color="#ffffff", rot=0.0):
    """4-point star (neon)."""
    pts = []
    for i in range(8):
        a = i * math.pi / 4 + rot
        rr = size if i % 2 == 0 else size * 0.28
        pts.append((math.cos(a) * rr, math.sin(a) * rr))
    o = L.prism(pts, size * 0.25, pos, color, rot=(0, 0, math.radians(-35)))
    return neon(o, color)


def cone(a, b, r1, r2, color, verts=8):
    a, b = Vector(a), Vector(b)
    d = b - a
    o = L.cyl(r1, d.length * 1.06, (0, 0, 0), color, verts=verts, r2=r2)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    o.location = (a + b) / 2
    return o


def shard(base, tip, w, color, sides=4, **kw):
    """Crystal: double pyramid from base to tip."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    o = L.cyl(w, d.length * 0.75, (0, 0, 0), color, verts=sides, r2=0.0, **kw)
    o2 = L.cyl(w, d.length * 0.25, (0, 0, -d.length * 0.5), color, verts=sides, r2=0.0,
               rot=(math.pi, 0, 0), **kw)
    o2.location = (0, 0, -d.length * 0.375 - d.length * 0.125)
    o = join([o, o2])
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    o.location = base + d * 0.4
    return o


# ------------------------------------------------------------------ the 13 dice
def d_golden():
    b = body("#ffcc1a", rough=0.25, metal=0.6)
    dimples(b, "#8a5a00")
    edge_bars("#ffe58a", t=0.1, length=1.3)
    sparkle((0.75, -0.9, 1.45), 0.24)
    sparkle((-1.3, -0.9, 1.1), 0.14)


def d_frost():
    b = body("#8fdcff", rough=0.15)
    dimples(b, "#1f6fb3")
    # snow cap with icicles hanging over the edges
    cap = L.box((2.08, 2.08, 0.3), (0, 0, 0.92), "#ffffff", bevel=0.14, segs=2)
    rng = random.Random(4)
    for k in range(16):
        side = k % 4
        t = -0.8 + 1.6 * (k // 4) / 3 + rng.uniform(-0.1, 0.1)
        x, y = [(t, -1.04), (1.04, t), (t, 1.04), (-1.04, t)][side]
        ln = rng.uniform(0.25, 0.55)
        L.cyl(0.07, ln, (x, y, 0.8 - ln / 2), "#e6f8ff", verts=5, r2=0.0, rot=(math.pi, 0, 0))
    _ = cap
    # ice crystals sprouting from the top corners
    for sx, sy, h in ((1, 1, 0.9), (-1, 1, 0.6), (1, -1, 0.55), (-1, -1, 1.0)):
        base = (sx * 0.75, sy * 0.75, 1.0)
        tip = (sx * (0.95 + h * 0.35), sy * (0.95 + h * 0.35), 1.0 + h)
        shard(base, tip, 0.16, "#bff4ff", rough=0.05)
        shard((sx * 0.7, sy * 0.85, 1.0), (sx * 0.8, sy * 1.3, 1.0 + h * 0.6), 0.1, "#e6fbff",
              rough=0.05)


def d_toxic():
    b = body("#4fd21f")
    dimples(b, "#1d4a0b")
    neon_pips("#d6ff3b", r=0.1, lift=-0.035)
    # dripping slime over the top
    L.box((2.1, 2.1, 0.32), (0, 0, 0.9), "#9dff3b", bevel=0.15, segs=2)
    rng = random.Random(7)
    for k in range(10):
        side = k % 4
        t = rng.uniform(-0.75, 0.75)
        x, y = [(t, -1.06), (1.06, t), (t, 1.06), (-1.06, t)][side]
        ln = rng.uniform(0.3, 0.9)
        L.cyl(0.11, ln, (x, y, 0.8 - ln / 2), "#9dff3b", verts=8, r2=0.07)
        C.ball(0.13, (x, y, 0.8 - ln), "#9dff3b", seg=8, rings=4)
    # bubbles
    for p, r in (((0.4, 0.3, 1.1), 0.12), ((-0.5, -0.2, 1.08), 0.08), ((0.1, -0.6, 1.07), 0.06)):
        neon(C.ball(r, p, "#e8ff7a", seg=8, rings=4), "#e8ff7a")


def d_inferno():
    b = body("#3a1410", rough=0.6)
    dimples(b, "#ff5a1a", r=0.18, depth=0.09)
    neon_pips("#ffb31a", r=0.11, lift=-0.05)
    # lava cracks on the visible faces
    rng = random.Random(3)
    cracks = []
    for n, a, bb in (face_frame((0, -1, 0)), face_frame((-1, 0, 0)), face_frame((1, 0, 0)),
                     face_frame((0, 1, 0))):
        p = Vector(n) * 1.005 + a * rng.uniform(-0.8, -0.5) + bb * rng.uniform(-0.8, 0.8)
        for _ in range(4):
            q = p + a * rng.uniform(0.25, 0.45) + bb * rng.uniform(-0.35, 0.35)
            if max(abs(q.dot(a)), abs(q.dot(bb))) > 0.9:
                break
            o = C.strip(p, q, 0.05, 0.03, "#ff7b1a", up=tuple(n))
            cracks.append(o)
            p = q
    if cracks:
        neon(join(cracks), "#ff7b1a")
    # horns
    for s in (-1, 1):
        prev = Vector((s * 0.55, 0.0, 0.95))
        for k in range(4):
            nxt = Vector((s * (0.7 + 0.18 * k), 0.0, 1.2 + 0.25 * k - 0.04 * k * k))
            cone(prev, nxt, 0.19 - 0.045 * k, 0.19 - 0.045 * (k + 1) + 0.005,
                 "#5a1a12" if k < 2 else "#f2e6d0")
            prev = nxt
    # flames
    fl = []
    for x, y, h, r in ((0, 0, 1.0, 0.32), (0.35, 0.25, 0.7, 0.2), (-0.3, 0.3, 0.6, 0.18),
                       (0.25, -0.35, 0.55, 0.17), (-0.3, -0.3, 0.75, 0.2)):
        fl.append(L.cyl(r, h, (x, y, 1.0 + h / 2), "#ff7b1a", verts=6, r2=0.0))
    neon(join(fl), "#ff7b1a")
    inner = [L.cyl(0.18, 0.6, (0, 0, 1.3), "#ffe03b", verts=6, r2=0.0)]
    neon(join(inner), "#ffe03b")


def d_cosmic():
    b = body("#5a2bb0", rough=0.3)
    dimples(b, "#2a124f", r=0.2, depth=0.06, shape="star")
    neon_pips("#ffd6ff", r=0.12, shape="star", lift=-0.04)
    rng = random.Random(11)
    dots = []
    for _ in range(26):
        n, a, bb = face_frame(rng.choice([(0, 0, 1), (0, -1, 0), (-1, 0, 0), (1, 0, 0),
                                          (0, 1, 0)]))
        p = Vector(n) * 1.0 + a * rng.uniform(-0.85, 0.85) + bb * rng.uniform(-0.85, 0.85)
        dots.append(C.ball(0.025, tuple(p), "#ffffff", seg=4, rings=2))
    neon(join(dots), "#ffffff")
    # tiny moon orbiting on a thin ring
    C.ring(1.42, 0.03, (0, 0, 0), "#d9a3ff", rot=(math.radians(68), math.radians(18), 0), maj=24,
           mnr=3)["grp"] = "neon"
    C.ball(0.2, (1.1, -0.85, 0.3), "#ffd6ff", seg=10, rings=6)
    sparkle((-0.8, -1.2, 0.9), 0.2, "#ffffff")


def d_void():
    # 8 dark blocks around a glowing core: the purple light leaks through the seams
    g = 0.07
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                o = L.box((1 - g, 1 - g, 1 - g), (sx * 0.5, sy * 0.5, sz * 0.5), "#1a0d2b",
                          bevel=0.18, segs=2, rough=0.4)
                apply(o)
    neon(L.box((1.75, 1.75, 1.75), (0, 0, 0), "#b14dff", bevel=0.2), "#b14dff")
    neon_pips("#d68cff", r=0.13, lift=0.02)
    # orbiting shards
    for k, (a, z) in enumerate(((0.4, 0.6), (2.5, -0.3), (4.2, 0.9), (5.4, -0.8))):
        p = (math.cos(a) * 1.45, math.sin(a) * 1.45, z)
        shard(p, (p[0] * 1.1, p[1] * 1.1, p[2] + 0.35), 0.1, "#2b1640")


def d_cyber():
    b = body("#0d1a33", bevel=0.18, segs=2, rough=0.35)
    dimples(b, "#14e0ff", r=0.17, depth=0.07, shape="square")
    neon_pips("#14e0ff", r=0.1, shape="square", lift=-0.045)
    # circuit traces with pads, on every face
    rng = random.Random(5)
    traces, pads = [], []
    for n, k in FACES:
        n, a, bb = face_frame(n)
        for _ in range(3):
            u, v = rng.choice((-0.85, 0.85)), rng.uniform(-0.8, 0.8)
            if rng.random() < 0.5:
                u, v = v, u
            p = n * 1.005 + a * u + bb * v
            for _s in range(2):
                if rng.random() < 0.5:
                    q = p + a * rng.uniform(-0.35, 0.35)
                else:
                    q = p + bb * rng.uniform(-0.35, 0.35)
                q = n * 1.005 + a * max(-0.85, min(0.85, q.dot(a))) + bb * max(-0.85, min(0.85,
                                                                                q.dot(bb)))
                if (q - p).length > 0.05:
                    traces.append(C.strip(p, q, 0.035, 0.02, "#14e0ff", up=tuple(n)))
                p = q
            pads.append(orient(L.cyl(0.05, 0.03, (0, 0, 0), "#14e0ff", verts=6), n))
            pads[-1].location = p
    neon(join(traces + pads), "#14e0ff")
    edge_bars("#22324f", t=0.12, bev=0.18, length=1.5)
    # antenna + chip on top
    L.box((0.5, 0.5, 0.08), (0.45, 0.45, 1.03), "#1c2a44", bevel=0.02)


def d_rainbow():
    # rounded cube lofted along X so every vertical band takes a rainbow colour
    secs = []
    xs = [-1.0, -0.96, -0.86, -0.6, -0.33, 0.0, 0.33, 0.6, 0.86, 0.96, 1.0]
    for x in xs:
        k = min(1.0, (1 - abs(x)) / 0.14)
        e = 0.32 * (1 - math.sqrt(max(0.0, 1 - (1 - k) ** 2)))
        w = 1.0 - e
        secs.append((x, w, w, -w, w, 0.32 - e * 0.8, 0.32 - e * 0.8))

    def paint(u, v, y):
        i = min(5, max(0, int((y + 1.0) / 2.0 * 6)))
        return RAINBOW[i]
    o = C.loft(secs, "#ffffff", paint=paint, nc=3)
    o.rotation_euler = (0, 0, math.pi / 2)
    o.location = (0, 0, 0)
    apply(o)
    # loft runs along Y; turned so the bands run across X
    dimples(o, "#ffffff", r=0.17, depth=0.07)
    # little cloud puffs at the bottom corners + a sparkle
    for p in ((0.95, -0.95, -0.85), (-0.95, -0.95, -0.85)):
        for d, r in (((0, 0, 0), 0.22), ((0.18, 0, 0.08), 0.17), ((-0.18, 0, 0.05), 0.16)):
            C.ball(r, (p[0] + d[0], p[1] + d[1], p[2] + d[2]), "#ffffff", seg=8, rings=5)
    sparkle((0.8, -0.9, 1.45), 0.22)


def d_galaxy():
    b = body("#1d1f6b", rough=0.3)
    dimples(b, "#ff6fd8", r=0.17, depth=0.07)
    neon_pips("#ff9ae6", r=0.1, lift=-0.04)
    rng = random.Random(21)
    dots = []
    for _ in range(40):
        n, a, bb = face_frame(rng.choice(FACES)[0])
        p = Vector(n) * 1.0 + a * rng.uniform(-0.85, 0.85) + bb * rng.uniform(-0.85, 0.85)
        dots.append(C.ball(rng.uniform(0.02, 0.04), tuple(p), "#ffffff", seg=4, rings=2))
    neon(join(dots), "#ffffff")
    # nebula swirl patches
    for p, n, c in (((0.4, -1.0, 0.45), (0, -1, 0), "#7b5cff"), ((-1.0, 0.3, -0.4), (-1, 0, 0),
                                                                 "#ff6fd8")):
        o = orient(L.cyl(0.42, 0.02, (0, 0, 0), c, verts=10), n)
        o.location = p
    # orbiting ring with a small planet
    tilt = (math.radians(72), math.radians(-20), 0)
    neon(C.ring(1.62, 0.05, (0, 0, 0), "#ff6fd8", rot=tilt, maj=28, mnr=3), "#ff6fd8")
    C.ring(1.78, 0.03, (0, 0, 0), "#9aa6ff", rot=tilt, maj=28, mnr=3)
    C.ball(0.24, (-1.45, -0.55, 0.45), "#ffb31a", seg=10, rings=6)
    C.ring(0.34, 0.03, (-1.45, -0.55, 0.45), "#ffe08a", rot=(math.radians(60), 0, 0), maj=12,
           mnr=3)


def d_glitch():
    # three slices shifted sideways + loose voxels
    for k, (dx, c) in enumerate(((0.12, "#ff2bd6"), (-0.1, "#2b2b3a"), (0.06, "#2bff8a"))):
        z = -2 / 3 + k * 2 / 3
        o = L.box((2.0, 2.0, 0.62), (dx, 0, z), c, bevel=0.12, segs=1)
        apply(o)
    cut = []
    for pos, n, k in pip_spots():
        o = L.box((0.3, 0.3, 0.3), (0, 0, 0), "#111118")
        orient(o, n)
        o.location = pos + n * 0.08 + Vector((0.1 if abs(n.x) < 0.5 else 0, 0, 0))
        cut.append(o)
    blocks = [o for o in bpy.context.scene.objects if o.type == "MESH" and o not in cut]
    b = join(blocks)
    carve(b, cut)
    rng = random.Random(13)
    vox = []
    for _ in range(14):
        n, a, bb = face_frame(rng.choice(FACES)[0])
        p = Vector(n) * rng.uniform(1.15, 1.6) + a * rng.uniform(-0.9, 0.9) + bb * rng.uniform(
            -0.9, 0.9)
        s = rng.uniform(0.12, 0.26)
        vox.append(L.box((s, s, s), tuple(p), rng.choice(("#ff2bd6", "#2bff8a", "#2b8bff",
                                                           "#ffffff"))))
    for c, z in (("#2bffff", 0.34), ("#ff2b6b", -0.3)):
        neon(L.box((2.3, 0.04, 0.05), (0.1, -1.04, z), c), c)
        neon(L.box((0.04, 2.3, 0.05), (-1.04, 0.0, z + 0.06), c), c)


def d_celestial():
    b = body("#fff6d6", rough=0.25)
    dimples(b, "#e3a92b", r=0.17, depth=0.07)
    edge_bars("#ffd23f", t=0.09, length=1.25)
    # feathered wings on both sides (flat, facing the front)
    outline = [(0.0, 0.35), (0.45, 0.8), (0.95, 1.08), (1.5, 1.15), (1.35, 0.82), (1.55, 0.66),
               (1.25, 0.42), (1.38, 0.22), (1.02, 0.08), (1.08, -0.16), (0.7, -0.18),
               (0.66, -0.42), (0.3, -0.3), (0.12, -0.45), (0.0, -0.2)]
    for s in (-1, 1):
        for k, (sc, c, dy) in enumerate(((1.0, "#ffffff", 0.0), (0.68, "#ffe08a", -0.07))):
            pts = [(s * x * sc, z * sc) for x, z in outline]
            o = L.prism(pts, 0.1, (s * 0.92, 0.25 + dy, 0.25), c, rot=(0, 0, 0))
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
            bm.to_mesh(o.data)
            bm.free()
    # halo
    neon(C.ring(0.62, 0.07, (0, 0, 1.55), "#ffe08a", maj=20, mnr=4), "#ffe08a")
    sparkle((0.7, -1.2, 1.1), 0.2, "#fff3b0")
    sparkle((-0.9, -1.2, -0.6), 0.14, "#8fe3ff")


def d_divine():
    b = body("#fffaf0", rough=0.3)
    dimples(b, "#ffb31a", r=0.17, depth=0.07)
    edge_bars("#ffd23f", t=0.12, length=1.4)
    # crown
    ring = L.cyl(0.78, 0.3, (0, 0, 1.15), "#ffd23f", verts=16, metal=0.6, rough=0.3)
    _ = ring
    L.cyl(0.84, 0.1, (0, 0, 1.03), "#e3a92b", verts=16)
    gems = []
    for k in range(8):
        a = k / 8 * math.tau
        x, y = math.cos(a) * 0.72, math.sin(a) * 0.72
        L.cyl(0.18, 0.5, (x, y, 1.55), "#ffd23f", verts=4, r2=0.0, rot=(0, 0, a + math.pi / 4))
        C.ball(0.07, (x * 1.03, y * 1.03, 1.82), "#fff3b0", seg=6, rings=3)
        g = C.ball(0.07, (x * 1.1, y * 1.1, 1.18), ("#ff3b6b", "#3bd1ff", "#4bdc5a")[k % 3],
                   seg=6, rings=3)
        gems.append(g)
    for g in gems:
        g["grp"] = "neon"
    sparkle((0.9, -0.9, 1.7), 0.22, "#fff3b0")
    sparkle((-1.25, -0.8, 0.9), 0.16, "#ffffff")


def d_singularity():
    C.ball(0.95, (0, 0, 0), "#07070c", seg=20, rings=12, rough=0.2)
    # glowing pips on the sphere where a die's faces would be
    pts = []
    for pos, n, k in pip_spots(1.0, 0.42):
        p = Vector(pos).normalized() * 0.95
        o = C.ball(0.07, tuple(p), "#ffb31a", seg=6, rings=3)
        pts.append(o)
    neon(join(pts), "#ffb31a")
    tilt = (math.radians(16), math.radians(-12), 0)
    # accretion disk: inner hot ring, outer cooler bands, photon ring
    neon(C.ring(1.22, 0.1, (0, 0, 0), "#fff3b0", rot=tilt, maj=28, mnr=3), "#fff3b0")
    neon(C.ring(1.5, 0.12, (0, 0, 0), "#ffb31a", rot=tilt, maj=28, mnr=3), "#ffb31a")
    C.ring(1.82, 0.13, (0, 0, 0), "#d9480f", rot=tilt, maj=28, mnr=3)
    C.ring(2.08, 0.07, (0, 0, 0), "#7a2a0a", rot=tilt, maj=28, mnr=3)
    neon(C.ring(1.0, 0.03, (0, 0, 0), "#ffe08a", rot=(math.radians(66), 0, math.radians(-35)),
                maj=24, mnr=3), "#ffe08a")
    for p in ((1.5, -1.2, 1.0), (-1.6, -0.8, -0.9)):
        sparkle(p, 0.16, "#ffd6a0")


DICE = {"Golden": d_golden, "Frost": d_frost, "Toxic": d_toxic, "Inferno": d_inferno,
        "Cosmic": d_cosmic, "Void": d_void, "Cyber": d_cyber, "Rainbow": d_rainbow,
        "Galaxy": d_galaxy, "Glitch": d_glitch, "Celestial": d_celestial, "Divine": d_divine,
        "Singularity": d_singularity}


def build(did):
    L.reset()
    DICE[did]()
    # neon materials glow in renders
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and o.get("grp") == "neon" and o.material_slots:
            h = o.material_slots[0].material.get("hex")
            for i in range(len(o.material_slots)):
                o.material_slots[i].material = glow(h)


def render(path, res=420, transparent=False):
    sc = bpy.context.scene
    L.studio(ground=False, sun=3.4)
    sc.render.film_transparent = transparent
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.cycles.samples = 48
    L.frame(lens=50, elev=24, azim=-35, margin=1.25)
    L.render(path)


def sheet(ids):
    from PIL import Image, ImageDraw
    cell = 300
    cols = 5
    rows = (len(ids) + cols - 1) // cols
    img = Image.new("RGB", (cell * cols, (cell + 22) * rows), "#20222c")
    d = ImageDraw.Draw(img)
    for i, did in enumerate(ids):
        p = os.path.join(ROOT, "renders", "dice", did + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGBA").resize((cell, cell))
        x, y = (i % cols) * cell, (i // cols) * (cell + 22)
        img.paste(im, (x, y + 22), im)
        d.text((x + 8, y + 5), f"{i + 1}. {did}", fill="#ffffff")
    img.save(os.path.join(ROOT, "renders", "dice_sheet.png"))


if __name__ == "__main__":
    want = sys.argv[1:]
    for did in DICE:
        if want and did not in want:
            continue
        build(did)
        K.bake("Dice_" + did)
        render(os.path.join(ROOT, "renders", "dice", did + ".png"))
    sheet(list(DICE))
