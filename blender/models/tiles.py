"""Track tiles as swept meshes: the road is lofted along the tile's centre line, so curves and
loops are seamless and nothing sticks out of the 10 x 10 cell.

Run: <bpy python> tiles.py [TileId ...]
Writes assets/meshes/Tile_<id>__*.fbx (+ manifest) and renders/tiles/<id>.png + a contact sheet.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bpy  # noqa: E402,I001
import mlib as L  # noqa: E402
import meshkit as K  # noqa: E402
import trackpaths as T  # noqa: E402

TIER = {
    "Common": dict(base="#eef2f7", border="#c3ccd8", road="#4b5160", dash="#ffffff",
                   kerb=("#ff4d4d", "#ffffff"), side="#8a93a3", rail=None, neon=None,
                   accent="#ff8a1f"),
    "Rare": dict(base="#d4ecff", border="#86bdf0", road="#465169", dash="#ffffff",
                 kerb=("#2f8bff", "#ffffff"), side="#5f7fa8", rail="#2f8bff", neon=None,
                 accent="#2f8bff"),
    "Epic": dict(base="#eadcff", border="#b18de6", road="#443c5a", dash="#e6d4ff",
                 kerb=("#a43bff", "#ffffff"), side="#6b4f99", rail="#7b2fd1", neon="#c46bff",
                 accent="#a43bff"),
    "Legendary": dict(base="#fff1c4", border="#efc35a", road="#4d4535", dash="#ffe08a",
                      kerb=("#ffb31a", "#ffffff"), side="#a8792a", rail="#e89a0c",
                      neon="#ffd23f", accent="#ffb31a"),
    "Mythical": dict(base="#ffd9e5", border="#ff8fb0", road="#4a3141", dash="#ffc2d6",
                     kerb=("#ff3b6b", "#ffffff"), side="#a3365c", rail="#d81b60",
                     neon="#ff4f9a", accent="#ff3b6b"),
    "Secret": dict(base="#26263d", border="#3d3d63", road="#16162a", dash="#ffffff",
                   kerb=("#ffffff", "#15152a"), side="#2b2b48", rail="#2b2b48",
                   neon="rainbow", accent="#ffe03b"),
}
# tiles with their own look on top of the tier colours
THEME = {
    "IceTurn": dict(base="#e8f7ff", border="#a8dcff", road="#6b8fae", dash="#e6f8ff",
                    kerb=("#9fdcff", "#ffffff"), side="#8fc3e6", rail="#bfeaff", neon=None),
    "NeonTurn": dict(base="#2a2140", border="#4a3a70", road="#1d1830", dash="#c46bff",
                     neon="#ff4fd8"),
    "RainbowRoad": dict(base="#1c1c33", border="#33335a", road="rainbow", dash="#ffffff",
                        kerb=("#ffffff", "#ff4fd8"), side="#2b2b48", rail="#2b2b48",
                        neon="rainbow"),
    "BlackHole": dict(base="#120d1f", border="#2b1b45", road="#1a1428", dash="#c46bff",
                      kerb=("#7b2fd1", "#000000"), side="#1f1633", rail="#2b1b45",
                      neon="#b14dff"),
    "Tunnel": dict(base="#d9e6f2"),
    "Lift": dict(base="#dff1ff", border="#86bdf0", rail="#2f8bff", neon="#5fd3ff"),
    "Bridge": dict(base="#cfeaff"),
}
RAINBOW = ["#ff3b3b", "#ff9f1a", "#ffe03b", "#4bdc5a", "#3bd1ff", "#7b5cff"]
UNDER = "#5b6273"
KERB_W = 0.45
KERB_H = 0.14
DECK = 0.45
RAIL_W = 0.22
RAIL_H = 0.7


def B(p):
    """Roblox point -> Blender point."""
    return (p[0], -p[2], p[1])


# ------------------------------------------------------------------ sweeping
def _faces_object(name, faces, grp=None):
    """faces: list of (verts[Blender coords], hex). One object, one material per colour."""
    if not faces:
        return []
    if grp in ("neon", "glass"):
        out = []
        by = {}
        for f in faces:
            by.setdefault(f[1], []).append(f)
        for col, fs in by.items():
            out += _faces_object(name + col, [(v, col) for v, _ in fs], None)
            for o in out[-1:]:
                o["grp"] = grp
        return out
    verts, polys, mats, cols = [], [], [], []
    for vs, col in faces:
        base = len(verts)
        verts += list(vs)
        polys.append(tuple(range(base, base + len(vs))))
        if col not in cols:
            cols.append(col)
        mats.append(cols.index(col))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], polys)
    me.update()
    for c in cols:
        me.materials.append(L.mat(c, rough=0.55))
    for p, mi in zip(me.polygons, mats):
        p.material_index = mi
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return [o]


def runs(samples):
    """Split samples into continuous road runs (lists of indices)."""
    out, cur = [], []
    for i, s in enumerate(samples):
        if s[3]:
            cur.append(i)
        else:
            if len(cur) > 1:
                out.append(cur)
            cur = [i] if (i + 1 < len(samples) and samples[i + 1][3]) else []
    if len(cur) > 1:
        out.append(cur)
    return out


def rail_k(w):
    """Rails fade out on narrow loop lanes (lanes sit side by side there)."""
    return max(0.0, min(1.0, (w - 1.6) / 0.3))


def profile(w, st):
    """Closed cross-section, clockwise in (right, up): list of (x0, y0, x1, y1, colour key).
    Same number of edges for every width so neighbouring samples can be joined."""
    k = KERB_W
    f = rail_k(w) if st["rail"] else 0.0
    rw, rh = RAIL_W * f, KERB_H + (RAIL_H - KERB_H) * f
    o = w + k + rw
    e = []
    e += [(-w, 0, -0.12, 0, "road"), (-0.12, 0, 0.12, 0, "dash"), (0.12, 0, w, 0, "road")]
    e += [(w, 0, w, KERB_H, "kerb"), (w, KERB_H, w + k, KERB_H, "kerb"),
          (w + k, KERB_H, w + k, rh, "rail"), (w + k, rh, o, rh, "rail"), (o, rh, o, -DECK, "side"),
          (o, -DECK, -o, -DECK, "under"),
          (-o, -DECK, -o, rh, "side"), (-o, rh, -w - k, rh, "rail"), (-w - k, rh, -w - k, KERB_H, "rail"),
          (-w - k, KERB_H, -w, KERB_H, "kerb"), (-w, KERB_H, -w, 0, "kerb")]
    if not st["rail"]:
        e = [(x0, y0, x1, y1, "side" if key == "rail" else key) for x0, y0, x1, y1, key in e]
    return e


def neon_profile(w):
    f = rail_k(w)
    a, b = w + KERB_W - 0.03 * f, w + KERB_W + (RAIL_W + 0.03) * f
    y0, y1 = RAIL_H, RAIL_H + 0.12 * f
    out = []
    for s in (1, -1):
        xa, xb = (a, b) if s > 0 else (-b, -a)
        out += [(xa, y1, xb, y1, "neon"), (xb, y1, xb, y0, "neon"), (xa, y0, xa, y1, "neon")]
    return out


def _ring(sample, edges):
    """3D (Roblox) endpoints of every profile edge at one sample."""
    p, r, u, _ = T.frame(sample)

    def P(x, y):
        return (p[0] + r[0] * x + u[0] * y, p[1] + r[1] * x + u[1] * y, p[2] + r[2] * x + u[2] * y)
    return [(P(x0, y0), P(x1, y1)) for x0, y0, x1, y1, _k in edges]


def _ahead(q, prev, f):
    """Stops points on the inside of a tight bend from sliding backwards (that would fold the
    mesh and show black flipped triangles); they pinch in place instead."""
    if sum((q[k] - prev[k]) * f[k] for k in range(3)) < 0.02:
        return prev
    return q


def sweep(samples, st, name, prof_fn, grp=None, colour=None):
    faces = []
    for run in runs(samples):
        dist = 0.0
        prev = None
        rings = []
        for idx in run:
            edges = prof_fn(samples[idx][5], st)
            ring = _ring(samples[idx], edges)
            if prev is not None:
                f = T.frame(samples[idx])[3]
                f0 = T.frame(samples[prev[0]])[3]
                fa = (f[0] + f0[0], f[1] + f0[1], f[2] + f0[2])
                ring = [(_ahead(q0, p0, fa), _ahead(q1, p1, fa))
                        for (q0, q1), (p0, p1) in zip(ring, prev[1])]
            rings.append((idx, ring, edges))
            prev = (idx, ring)
        for (a, ra, ea), (b, rb, _eb) in zip(rings, rings[1:]):
            seg = math.dist(samples[a][0], samples[b][0])
            mid = dist + seg / 2
            dist += seg
            band = int(mid / 1.1)
            for (a0, a1), (b0, b1), e in zip(ra, rb, ea):
                col = colour(e[4], band, mid) if colour else _colour(e[4], band, st)
                faces.append(([B(a0), B(a1), B(b1), B(b0)], col))
        if grp is None:
            for (idx, ring, _e), flip in ((rings[0], False), (rings[-1], True)):
                pts = [B(q0) for q0, _q1 in ring]
                faces.append((pts if flip else pts[::-1], st["side"]))
    return _faces_object(name, faces, grp)


def _colour(key, band, st):
    if key == "road" and st["road"] == "rainbow":
        return ["#c0392b", "#d35400", "#c9a227", "#27ae60", "#2980b9", "#6c3fb5"][band % 6]
    if key == "dash":
        if st["road"] == "rainbow":
            return st["dash"]
        return st["dash"] if band % 2 == 0 else st["road"]
    if key == "kerb":
        return st["kerb"][band % 2]
    if key == "under":
        return st["side"] if st["rail"] else UNDER
    return st[key]


def neon_colour(st):
    def f(_key, band, _mid):
        if st["neon"] == "rainbow":
            return RAINBOW[(band // 2) % len(RAINBOW)]
        return st["neon"]
    return f


def road(path, st):
    sweep(path.s, st, "Road", lambda w, s: profile(w, s))
    if st["neon"] and st["rail"]:
        sweep(path.s, st, "RailGlow", lambda w, s: neon_profile(w), grp="neon",
              colour=neon_colour(st))


# ------------------------------------------------------------------ shared decor
def base(st, start=False):
    L.box((9.8, 9.8, 0.3), (0, 0, 0.15), st["border"], bevel=0.12)
    L.box((9.0, 9.0, 0.1), (0, 0, 0.33), st["base"])
    if start:
        for i in range(8):
            for j in range(2):
                L.box((0.75, 0.75, 0.02), (-2.625 + i * 0.75, -(0.375 - j * 0.75), T.ROAD_Y + 0.011),
                      "#ffffff" if (i + j) % 2 else "#16161c")


def neon(o):
    o["grp"] = "neon"
    return o


def pillar(x, z_r, top, color, w=0.5):
    """Square support from the base up to Roblox height `top` at Roblox (x, z)."""
    h = top - 0.38
    if h > 0.3:
        L.box((w, w, h), (x, -z_r, 0.38 + h / 2), color, bevel=0.06)
        L.box((w + 0.3, w + 0.3, 0.16), (x, -z_r, 0.46), color, bevel=0.05)


def supports(path, st, every=2.6, min_h=1.1, skip=None):
    """Pillars under the road wherever it is high enough and upright."""
    dist, nxt = 0.0, every / 2
    s = path.s
    for i in range(1, len(s)):
        dist += math.dist(s[i - 1][0], s[i][0])
        p, f, u, road_, _fl, w = s[i]
        if not road_ or dist < nxt:
            continue
        nxt = dist + every
        if u[1] < 0.85 or (skip and skip(p)):
            continue
        bottom = p[1] - DECK
        if bottom - 0.38 < min_h:
            continue
        pillar(p[0], p[2], bottom, st["side"], 0.55)


def cone(x, z_r, s=1.0):
    L.cyl(0.42 * s, 0.9 * s, (x, -z_r, 0.38 + 0.45 * s), "#ff8a1f", r2=0.08 * s, verts=8)
    L.cyl(0.3 * s, 0.16 * s, (x, -z_r, 0.38 + 0.5 * s), "#ffffff", verts=8)
    L.box((0.95 * s, 0.95 * s, 0.1), (x, -z_r, 0.43), "#ff8a1f")


def lamp(x, z_r, color, glow, h=2.6):
    L.cyl(0.13, h, (x, -z_r, 0.38 + h / 2), color, verts=6)
    L.box((0.5, 0.5, 0.1), (x, -z_r, 0.43), color)
    neon(L.sphere(0.3, (x, -z_r, 0.38 + h + 0.1), glow, subdiv=1))


def chevron(x, z_r, y, color, rot_z=0.0, s=1.0, glow=False):
    pts = [(-0.9 * s, 0), (0, 0.7 * s), (0.9 * s, 0), (0.9 * s, -0.35 * s), (0, 0.35 * s),
           (-0.9 * s, -0.35 * s)]
    o = L.prism(pts, 0.06, (x, -z_r, y), color, rot=(math.pi / 2, 0, rot_z))
    if glow:
        neon(o)
    return o


def ring_torus(center_r, R, r, color, axis="z", glow=True):
    """Ring around the road: axis 'z' = ring faces along the road (Roblox Z)."""
    rot = (math.pi / 2, 0, 0) if axis == "z" else (0, 0, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=16,
                                     minor_segments=5, location=B(center_r), rotation=rot)
    o = bpy.context.active_object
    o.data.materials.append(L.mat(color))
    if glow:
        neon(o)
    return o


# ------------------------------------------------------------------ per tile decor
def d_bump(path, st):
    cone(-4.3, 3.9)
    cone(4.3, -3.9)
    for i in range(6):
        L.box((1.0, 0.5, 0.06), (-2.5 + i, 0, T.ROAD_Y + 0.83), "#ffd21f" if i % 2 else "#222222")


def d_hill(path, st):
    # grassy mound under the road
    for k, (h, wdt) in enumerate(((1.6, 6.5), (1.0, 8.4))):
        L.box((wdt * 0.62, wdt, h), (0, 0, 0.38 + h / 2), "#7ed957" if k == 0 else "#69c24a",
              bevel=0.35, segs=1)
    L.box((1.0, 1.4, 0.8), (-3.6, 3.2, 0.7), "#5cb83c", bevel=0.25)
    L.box((0.9, 1.2, 0.7), (3.7, -3.4, 0.7), "#5cb83c", bevel=0.25)


def d_banked(path, st):
    # tyre stacks on the outside of the corner
    for a in (0.18, 0.5, 0.82):
        ang = a * math.pi / 2
        x, z = 5 - 9.1 * math.cos(ang) * 0.94, 5 - 9.1 * math.sin(ang) * 0.94
        for k in range(2):
            L.cyl(0.42, 0.32, (x, -z, 0.55 + k * 0.34), "#26262c" if k == 0 else "#2f8bff",
                  verts=8)
    lamp(3.9, 3.9, st["rail"], "#bfe6ff", 2.2)


def d_boost(path, st):
    for z in (3.0, 0.6, -1.8):
        chevron(0, z, T.ROAD_Y + 0.02, "#ff9f1a", s=1.15, glow=True)
    for x in (-4.1, 4.1):
        L.box((0.55, 0.55, 4.0), (x, 0, 0.38 + 2.0), st["rail"], bevel=0.08)
    L.box((8.8, 0.6, 0.6), (0, 0, 4.5), st["rail"], bevel=0.12)
    neon(L.box((7.6, 0.66, 0.2), (0, 0, 4.25), "#ffcc33"))
    neon(L.box((0.2, 0.62, 3.2), (-4.1, 0, 2.2), "#5ce1ff"))
    neon(L.box((0.2, 0.62, 3.2), (4.1, 0, 2.2), "#5ce1ff"))


def d_chicane(path, st):
    cone(-4.4, 2.6, 0.9)
    cone(4.4, -2.6, 0.9)
    for x, z, rz in ((-4.4, -1.0, math.pi / 2), (4.4, 1.0, -math.pi / 2)):
        L.box((0.18, 1.6, 1.0), (x, -z, 1.3), "#ffffff", bevel=0.05)
        chevron(x + (0.1 if x < 0 else -0.1), z, 1.3, "#a43bff", rot_z=0, s=0.5)
        L.cyl(0.08, 0.9, (x, -z, 0.75), "#555a66", verts=6)


def d_jump(path, st):
    # ramp supports + gap pit
    L.box((7.2, 2.8, 0.06), (0, 0.1, 0.36), "#3b3f4c")
    for x in (-2.6, 2.6):
        pillar(x, T.JUMP_TAKEOFF + 0.3, T.ROAD_Y + T.JUMP_H - DECK - 0.1, st["side"], 0.45)
        pillar(x, T.JUMP_LAND - 0.3, T.ROAD_Y + T.JUMP_H - 0.2 - DECK - 0.1, st["side"], 0.45)
    for side in (-1, 1):
        L.cyl(0.08, 3.4, (side * 4.4, 0.0, 2.1), "#ffffff", verts=6)
        L.box((0.06, 1.3, 0.8), (side * 4.4, -0.6, 3.35), "#ff3b3b" if side < 0 else "#ffe03b")
    neon(L.box((7.0, 0.14, 0.1), (0, -T.JUMP_TAKEOFF, T.ROAD_Y + T.JUMP_H + 0.02), st["neon"]))


def d_corkscrew(path, st):
    for z in (4.3, -4.3):
        for x in (-3.9, 3.9):
            L.box((0.4, 0.4, 4.6), (x, -z, 0.38 + 2.3), st["rail"], bevel=0.05)
        L.box((8.2, 0.4, 0.4), (0, -z, 5.0), st["rail"], bevel=0.05)
        neon(L.box((7.4, 0.46, 0.12), (0, -z, 4.76), st["neon"]))


def d_loop(path, st, double=False):
    if double:
        for x, z in ((-4.4, 4.4), (4.4, 4.4), (-4.4, -4.4), (4.4, -4.4)):
            lamp(x, z, st["rail"], st["neon"], 2.4)
        return
    xs = (-4.5, 4.5)
    for x in xs:
        L.box((0.35, 0.6, 3.6), (x, 0, 0.38 + 1.8), st["rail"], bevel=0.06)
        L.box((0.35, 2.4, 0.35), (x, 0, 0.55), st["rail"], bevel=0.06)
    L.box((abs(xs[0]) * 2 + 0.35, 0.3, 0.3), (0, 0, 3.98), st["rail"], bevel=0.05)
    neon(L.box((abs(xs[0]) * 2 - 0.5, 0.34, 0.1), (0, 0, 4.18), st["neon"]))
    if not double:
        lamp(-4.4, 4.2, st["rail"], st["neon"], 1.8)
        lamp(4.4, -4.2, st["rail"], st["neon"], 1.8)


def d_spiral(path, st):
    L.cyl(0.5, 6.8, (0, 0, 0.38 + 3.4), st["rail"], verts=10)
    L.cyl(0.85, 0.3, (0, 0, 0.53), st["rail"], verts=10)
    neon(L.sphere(0.75, (0, 0, 7.6), st["neon"], subdiv=1))
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        L.box((1.5, 0.16, 0.16), (0.75 * math.cos(a), 0.75 * math.sin(a), 3.6 + k * 0.9),
              st["rail"], rot=(0, 0, a))
    lamp(4.2, 4.3, st["rail"], st["neon"], 1.8)


def d_wave(path, st):
    # water-coloured base with little wave crests
    L.box((8.4, 8.4, 0.06), (0, 0, 0.4), "#58c7ff")
    for i, z in enumerate((-3.6, -1.2, 1.2, 3.6)):
        for x in (-4.0, 4.0):
            L.box((0.9, 1.0, 0.2), (x, -z, 0.5), "#ffffff" if i % 2 else "#b6ecff", bevel=0.08)
    supports(path, st, every=2.0, min_h=0.8)


def d_wallride(path, st):
    # the wall the road climbs onto
    L.box((0.4, 9.4, 5.8), (-4.55, 0, 0.38 + 2.9), st["side"], bevel=0.08)
    for k in range(5):
        L.box((0.45, 1.0, 5.4), (-4.53, -3.6 + k * 1.8, 0.38 + 2.9),
              st["kerb"][k % 2])
    neon(L.box((0.5, 9.4, 0.14), (-4.55, 0, 6.3), st["neon"]))
    supports(path, st, every=2.2, min_h=0.7)


def d_teleport(path, st):
    for z, col in ((T.TP_IN, "#b54dff"), (T.TP_OUT, "#38d6ff")):
        ring_torus((0, T.ROAD_Y + 2.4, z), 2.6, 0.3, col)
        for x in (-2.9, 2.9):
            L.box((0.5, 0.5, 2.0), (x, -z, 0.38 + 1.0), st["rail"], bevel=0.06)
    L.box((1.2, 1.2, 0.5), (-4.1, -0.0, 0.62), "#3b2b55", bevel=0.1)
    neon(L.sphere(0.4, (-4.1, 0.0, 1.2), "#d9a3ff", subdiv=1))
    L.box((1.2, 1.2, 0.5), (4.1, -0.0, 0.62), "#3b2b55", bevel=0.1)
    neon(L.sphere(0.4, (4.1, 0.0, 1.2), "#9ff0ff", subdiv=1))


def d_skyleap(path, st):
    ring_torus((0, T.ROAD_Y + 2.4, 3.2), 2.6, 0.28, "#ffffff")
    # pillars carrying the sky track
    for i, (x, z) in enumerate(((-4.1, 4.2), (4.1, 4.2), (-4.1, 0.0), (4.1, 0.0))):
        L.box((0.45, 0.45, T.SKY_H), (x, -z, 0.38 + T.SKY_H / 2), st["rail"], bevel=0.05)
        neon(L.box((0.16, 0.5, T.SKY_H - 1.0), (x + (0.2 if x < 0 else -0.2), -z,
                                                  0.38 + T.SKY_H / 2), RAINBOW[i % len(RAINBOW)]))
    L.box((8.6, 0.4, 0.4), (0, -4.2, T.ROAD_Y + T.SKY_H - 0.75), st["rail"])
    L.box((8.6, 0.4, 0.4), (0, 0.0, T.ROAD_Y + T.SKY_H - 0.75), st["rail"])
    neon(L.sphere(0.9, (0, -2.0, T.ROAD_Y + T.SKY_H + 6.2), "#ffe03b", subdiv=1))
    # landing pad stars
    for x, z in ((-3.9, -3.9), (3.9, -3.9)):
        neon(L.sphere(0.35, (x, -z, 0.7), "#ffe03b", subdiv=1))


def d_start(path, st):
    for x in (-4.0, 4.0):
        L.box((0.6, 0.6, 5.2), (x, 0, 0.38 + 2.6), "#2b2b33", bevel=0.08)
    L.box((8.9, 0.8, 1.3), (0, 0, 5.9), "#ff3b6b", bevel=0.15)
    L.outlined_text("START", 0.9, (0, -0.45, 5.9), "#ffffff")
    for x in (-3.0, -1.0, 1.0, 3.0):
        neon(L.sphere(0.18, (x, -0.42, 6.75), "#ffe03b", subdiv=1))


def d_tunnel(path, st):
    rock, rock_d = "#8d8f9e", "#6f7181"
    for z in (-3.6, -1.2, 1.2, 3.6):
        for x in (-4.3, 4.3):
            L.box((1.1, 2.4, 4.6), (x, -z, 0.38 + 2.3), rock if (z > 0) == (x > 0) else rock_d,
                  bevel=0.25)
        L.box((9.6, 2.4, 1.2), (0, -z, 5.1), rock if z > 0 else rock_d, bevel=0.25)
        neon(L.box((7.0, 0.3, 0.14), (0, -z, 4.42), "#ffd23f"))
    for z in (-4.6, 4.6):   # portal frames
        L.box((0.6, 0.5, 4.8), (-4.0, -z, 0.38 + 2.4), "#ffb31a", bevel=0.06)
        L.box((0.6, 0.5, 4.8), (4.0, -z, 0.38 + 2.4), "#ffb31a", bevel=0.06)
        L.box((8.6, 0.5, 0.6), (0, -z, 5.0), "#ffb31a", bevel=0.06)
    L.box((3.0, 1.6, 1.2), (2.2, 0, 6.2), "#5fc048", bevel=0.4)
    L.box((2.2, 1.2, 1.0), (-2.6, -2.0, 6.0), "#4cc23a", bevel=0.4)


def d_bridge(path, st):
    L.box((8.6, 3.0, 0.06), (0, 0, 0.42), "#4fc3ff")            # river
    for x in (-3.0, -0.6, 1.8, 3.6):
        L.box((0.8, 0.3, 0.05), (x, 0.4 * (x % 2), 0.47), "#d6f4ff")
    for x in (-4.2, 4.2):
        for z in (-1.6, 1.6):
            L.box((0.7, 0.7, 1.2), (x, -z, 0.95), "#c9c2b3", bevel=0.1)
    L.cyl(0.35, 0.9, (-3.2, 3.6, 0.85), "#5fc048", verts=6)
    L.box((1.4, 1.1, 0.8), (3.6, -3.7, 0.75), "#5fc048", bevel=0.25)


def d_ice(path, st):
    for x, z, h in ((-3.9, -3.9, 2.4), (-2.6, -4.1, 1.5), (-4.1, -2.4, 1.2), (3.9, 4.0, 1.0)):
        L.cyl(0.42, h, (x, -z, 0.38 + h / 2), "#bfeaff", r2=0.0, verts=5, rough=0.05)
    for x, z in ((-3.4, 3.6), (3.2, -3.3)):
        L.box((1.6, 1.2, 0.4), (x, -z, 0.55), "#ffffff", bevel=0.2)


def d_camel(path, st):
    for z in (2.5, -2.5):
        pillar(-2.5, z, T.ROAD_Y + 1.6 - DECK, st["rail"], 0.4)
        pillar(2.5, z, T.ROAD_Y + 1.6 - DECK, st["rail"], 0.4)
    cone(-4.3, 0, 0.9)
    cone(4.3, 0, 0.9)


def d_halfpipe(path, st):
    supports(path, st, every=1.8, min_h=0.6)
    for x, z in ((-4.4, 4.3), (4.4, -4.3), (-4.4, -4.3), (4.4, 4.3)):
        lamp(x, z, st["rail"], st["neon"], 2.0)


def d_neonturn(path, st):
    lamp(-4.0, -4.0, st["rail"], st["neon"], 2.4)
    lamp(-4.2, 4.2, st["rail"], "#4fe0ff", 1.6)
    lamp(4.2, -4.2, st["rail"], "#4fe0ff", 1.6)
    for a in (0.2, 0.5, 0.8):
        ang = a * math.pi / 2
        neon(L.sphere(0.32, (5 - 1.3 * math.cos(ang), -(5 - 1.3 * math.sin(ang)), 0.9),
                      "#4fe0ff", subdiv=1))


def d_fire_ring(path, st):
    d_jump(path, st)
    ring_torus((0, T.ROAD_Y + 3.4, 0.0), 2.6, 0.32, "#ff6a1a")
    ring_torus((0, T.ROAD_Y + 3.4, 0.0), 2.25, 0.14, "#ffd23f")
    for x in (-2.9, 2.9):
        L.box((0.45, 0.45, 3.4), (x, 0, 0.38 + 1.7), "#3a2b2b", bevel=0.05)


def d_launchpad(path, st):
    for z in (4.0, 2.8):
        chevron(0, z, T.ROAD_Y + 0.02 + (5 - z) ** 2 * 0.06, "#ff9f1a", s=1.0, glow=True)
    for x in (-3.4, 3.4):
        pillar(x, 1.8, T.ROAD_Y + 2.1 - DECK, st["rail"], 0.45)
        pillar(x, -2.4, T.ROAD_Y + 1.2 - DECK, st["rail"], 0.45)
    neon(L.box((6.8, 0.2, 0.14), (0, -1.6, T.ROAD_Y + 2.12), "#ff4fd8"))


def d_twister(path, st):
    d_corkscrew(path, st)
    for x in (-4.4, 4.4):
        neon(L.box((0.2, 7.6, 0.14), (x, 0, 0.55), st["neon"]))


def d_rainbow(path, st):
    rng = __import__("random").Random(3)
    for _ in range(9):
        x, z = rng.choice((-4.3, 4.3)), rng.uniform(-4.2, 4.2)
        neon(L.sphere(0.22, (x, -z, rng.uniform(0.8, 2.4)), rng.choice(RAINBOW), subdiv=1))


def d_blackhole(path, st):
    # swirling dark disc between the two openings
    L.cyl(3.6, 0.12, (0, 0, 0.45), "#05030a", verts=24)
    for k in range(3):
        a0 = k * 2 * math.pi / 3
        for i in range(10):
            a = a0 + i * 0.32
            r = 0.5 + i * 0.3
            neon(L.box((0.5, 0.18, 0.06), (math.cos(a) * r, math.sin(a) * r, 0.53), "#b14dff",
                       rot=(0, 0, a + math.pi / 2)))
    for z, col in ((T.BH_IN, "#b14dff"), (T.BH_OUT, "#4fe0ff")):
        ring_torus((0, T.ROAD_Y + 2.3, z), 2.4, 0.26, col)
    neon(L.sphere(0.5, (0, 0, 3.8), "#ffffff", subdiv=1))


def d_lift(path, st):
    """Sky Ramp: a steel column in the middle of the spiral with arms under the road, glowing
    rings that climb the column and up-arrows at the entry."""
    top = T.ROAD_Y + T.FLOOR_H
    L.cyl(0.62, top + 0.9, (0, 0, (top + 0.9) / 2 + 0.2), "#d9dee8", verts=12, bevel=0.04)
    L.cyl(1.05, 0.35, (0, 0, 0.55), st["rail"], verts=12)
    for k in range(5):
        neon(L.cyl(0.7, 0.16, (0, 0, 1.6 + k * 1.75), st["neon"], verts=12))
    neon(L.sphere(0.65, (0, 0, top + 1.6), st["neon"], subdiv=2))
    L.cyl(0.85, 0.25, (0, 0, top + 1.0), st["rail"], verts=12)
    # arms from the column to the underside of the road: along the spiral and the high exit
    s = path.s
    dist, nxt = 0.0, 1.0
    for i in range(1, len(s)):
        dist += math.dist(s[i - 1][0], s[i][0])
        p = s[i][0]
        r = math.hypot(p[0], p[2])
        on_spiral = abs(r - T.LIFT_R) < 0.25 and p[1] > 1.6
        on_exit = p[1] > top - 1.4 and p[2] < -0.5 and r < 4.6
        if dist < nxt or not (on_spiral or on_exit):
            continue
        nxt = dist + (2.2 if on_spiral else 1.5)
        a = math.atan2(-p[2], p[0])  # Blender angle of the arm (Roblox z -> Blender -y)
        reach = r - 0.55
        mid = reach / 2 + 0.55
        L.box((reach, 0.32, 0.32), (math.cos(a) * mid, math.sin(a) * mid, p[1] - DECK - 0.18),
              st["side"], rot=(0, 0, a), bevel=0.04)
    # up arrows on the entry, a lamp on two corners
    for k in range(2):
        chevron(0, 4.2 - k * 1.1, T.ROAD_Y + 0.06, st["neon"], rot_z=0, s=0.55, glow=True)
    lamp(4.3, 4.3, st["rail"], st["neon"], 2.2)
    lamp(-4.3, -4.3, st["rail"], st["neon"], 2.2)


DECOR = {"SpeedBump": d_bump, "Hill": d_hill, "BankedTurn": d_banked, "BoostPad": d_boost,
         "Chicane": d_chicane, "Jump": d_jump, "Corkscrew": d_corkscrew, "Loop": d_loop,
         "Spiral": d_spiral, "WaveRider": d_wave, "WallRide": d_wallride,
         "DoubleLoop": lambda p, s: d_loop(p, s, True), "TeleportGate": d_teleport,
         "SkyLeap": d_skyleap, "Start": d_start, "Tunnel": d_tunnel, "Bridge": d_bridge,
         "IceTurn": d_ice, "CamelBack": d_camel, "HalfPipe": d_halfpipe, "NeonTurn": d_neonturn,
         "RingOfFire": d_fire_ring, "LaunchPad": d_launchpad, "Twister": d_twister,
         "RainbowRoad": d_rainbow, "BlackHole": d_blackhole, "Lift": d_lift}


# ------------------------------------------------------------------ checks + output
def check_bounds(tid):
    """Everything must stay inside the cell (small tolerance) and above the pad."""
    bad = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.name.startswith("_"):
            continue
        me = o.evaluated_get(dg).to_mesh()
        for v in me.vertices:
            w = o.matrix_world @ v.co
            if abs(w.x) > 5.02 or abs(w.y) > 5.02 or w.z < -0.2:
                bad += 1
                if bad < 4:
                    print("   outside:", o.name, [round(c, 2) for c in w])
        o.evaluated_get(dg).to_mesh_clear()
    print(f"BOUNDS {tid}: {'OK' if not bad else str(bad) + ' vertices outside the cell'}")
    return bad


def build(tile):
    tid, _display, tier, _odds, _value, fn, _ports, _desc = tile
    L.reset()
    st = dict(TIER[tier], **THEME.get(tid, {}))
    path = T.make_path(fn)
    base(st, start=tid == "Start")
    road(path, st)
    if tid not in ("WaveRider", "WallRide", "Hill", "HalfPipe", "Lift"):
        supports(path, st)
    if tid in DECOR:
        DECOR[tid](path, st)
    check_bounds(tid)
    K.bake("Tile_" + tid)
    return path


def render(tid, size=520):
    L.studio(ground=False)
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = size
    sc.cycles.samples = 24
    L.frame(lens=50, elev=34, azim=-38, margin=1.05)
    L.render(os.path.join(ROOT, "renders", "tiles", tid + ".png"))


if __name__ == "__main__":
    want = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    allt = T.TILES + [T.START]
    for t in allt:
        if want and t[0] not in want:
            continue
        build(t)
        render(t[0])
