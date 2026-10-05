"""Living-world props: boats, lighthouse, windmill, balloons, beach sets, piers, buoys, dolphins,
lanterns and a waterfall rock. Pieces that move are baked as their own models (one MeshPart where
possible) so tools/build_map.py can tag them with Anim attributes for src/ReplicatedStorage/Ambient.

Conventions (Blender, 1 unit = 1 stud, Z up): the model origin is where build_map places it;
boats float with the waterline at z = 0 and their bow towards -Y (= the MeshPart's LookVector in
Roblox); spinning parts are centred on their axle.
"""
import math
import random

import mlib as L
import carkit as C

WHITE = "#ffffff"
WOOD, WOOD_D, WOOD_L = "#b9783f", "#8a5a2b", "#d99a5b"
ROCK, ROCK_D, ROCK_L = "#8d8f9e", "#6f7181", "#a9afbb"
DARK = "#2b2f3a"
pi = math.pi


def grp(o, g):
    o["grp"] = g
    return o


# ------------------------------------------------------------------ boats
def hull(length, beam, depth, freeboard, color, bottom="#d9483b", stripe=WHITE, deck=WOOD_L):
    """Boat hull lofted along Y, bow at -Y (raised), stern at +Y."""
    h = length / 2
    secs = [(h, beam * 0.36, beam * 0.46, -depth * 0.6, freeboard, 0.2, 0.08),
            (h * 0.55, beam * 0.42, beam * 0.5, -depth, freeboard, 0.3, 0.1),
            (-h * 0.3, beam * 0.36, beam * 0.48, -depth, freeboard * 1.08, 0.3, 0.1),
            (-h * 0.8, beam * 0.14, beam * 0.3, -depth * 0.7, freeboard * 1.25, 0.12, 0.08),
            (-h, beam * 0.02, beam * 0.06, -depth * 0.2, freeboard * 1.35, 0.01, 0.02)]

    def paint(u, v, y):
        if v < 0.42:
            return bottom
        if 0.72 < v < 0.84:
            return stripe
        return None
    C.loft(secs, color, paint=paint, side_breaks=(0.42, 0.72, 0.84), nc=2)
    # deck
    C.loft([(h - 0.15, beam * 0.42, beam * 0.42, freeboard * 0.7, freeboard * 0.85, 0.1, 0.1),
            (-h * 0.75, beam * 0.24, beam * 0.24, freeboard * 0.85, freeboard * 1.0, 0.05, 0.05)],
           deck)


def sail_tri(points, x, color, stripes=None, thick=0.12):
    """Sail as a flat prism in the YZ plane (points are (y, z))."""
    pts = [(py, pz) for py, pz in points]
    o = L.prism(pts, thick, (x, 0, 0), color, rot=(0, 0, pi / 2))
    return o


def sailboat(sail="#ffffff", stripe="#ff5a5a", body="#ffffff", bottom="#2f6bd9"):
    hull(12, 4.2, 1.6, 1.4, body, bottom=bottom, stripe=stripe)
    # cabin
    L.box((2.4, 3.0, 1.1), (0, 1.4, 2.0), WHITE, bevel=0.2)
    L.box((2.5, 3.1, 0.25), (0, 1.4, 2.6), stripe, bevel=0.08)
    for y in (0.6, 1.4, 2.2):
        L.cyl(0.22, 0.1, (1.22, y, 2.0), "#7fd6ff", rot=(0, pi / 2, 0), verts=8)
        L.cyl(0.22, 0.1, (-1.22, y, 2.0), "#7fd6ff", rot=(0, pi / 2, 0), verts=8)
    # mast, boom, sails
    L.cyl(0.18, 15, (0, -0.6, 8.6), WOOD_D, verts=8)
    C.tube((0, -0.6, 3.2), (0, 4.6, 3.3), 0.13, WOOD_D, verts=6)
    sail_tri([(-0.45, 3.5), (-0.45, 15.6), (4.4, 3.5)], 0, sail)
    for k, z in enumerate((6.0, 9.0)):
        w = 4.4 * (15.6 - z) / 12.1
        L.box((0.16, w - 0.3, 0.6), (0, -0.45 + (w - 0.3) / 2 + 0.05, z), stripe)
    sail_tri([(-1.0, 3.0), (-1.0, 14.5), (-5.6, 1.6)], 0, "#f4f4f4")
    C.tube((0, -0.6, 15.6), (0, -5.7, 1.5), 0.04, DARK, verts=4)
    L.prism([(0, 0), (1.6, 0.5), (0, 1.0)], 0.06, (0, -0.6, 16.0), stripe, rot=(0, 0, pi / 2))
    # railing posts + life ring
    for s in (-1, 1):
        for y in (-3.5, -1.5, 3.8):
            L.box((0.12, 0.12, 0.7), (s * 1.75, y, 1.85), WHITE)
        L.box((0.08, 8.0, 0.08), (s * 1.75, 0.2, 2.2), WHITE)
    C.ring(0.45, 0.13, (0, 5.95, 1.4), "#ff5a5a", rot=(pi / 2, 0, 0), maj=10, mnr=4)


def rowboat(body="#3bb8ff"):
    hull(6.0, 2.4, 0.7, 0.7, body, bottom=WOOD_D, stripe=WHITE, deck=WOOD)
    for y in (-0.8, 0.9):
        L.box((2.0, 0.5, 0.12), (0, y, 0.75), WOOD_L)
    for s in (-1, 1):
        C.tube((s * 0.9, 0.1, 0.9), (s * 2.2, 0.6, 0.1), 0.06, WOOD_L, verts=5)
        L.box((0.12, 0.5, 0.06), (s * 2.25, 0.62, 0.08), WOOD_L, rot=(0, 0, 0.2))
    L.cyl(0.25, 0.4, (0, 2.2, 0.85), "#ffd23f", verts=8)


def motorboat(body="#ff5a5a"):
    hull(8.0, 3.0, 1.0, 1.0, body, bottom=WHITE, stripe="#2b2f3a")
    L.box((2.2, 1.4, 1.0), (0, -0.4, 1.6), WHITE, bevel=0.15)
    L.box((2.1, 0.1, 0.8), (0, -1.15, 1.9), "#7fd6ff", rot=(math.radians(-25), 0, 0))
    L.box((0.9, 0.8, 1.0), (0, 3.95, 0.9), DARK, bevel=0.1)
    L.box((0.3, 0.3, 0.9), (0, 4.2, 0.2), "#5b6273")
    L.cyl(0.08, 1.4, (0.8, 2.6, 1.9), WHITE, verts=4)
    L.prism([(0, 0), (0.7, 0.25), (0, 0.5)], 0.04, (0.8, 2.6, 2.4), "#ffd23f",
            rot=(0, 0, pi / 2))


# ------------------------------------------------------------------ lighthouse
def lighthouse_isle(superellipse, island):
    """Small rocky islet with a striped lighthouse (lamp head is a separate model).
    superellipse/island come from world.py (island builder)."""
    outline = superellipse(20, 17, n=2.2, count=40, seed=31, wobble=0.08)
    island(outline, 33, roles=False)
    rng = random.Random(5)
    for k in range(9):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(8, 16)
        s = rng.uniform(1.4, 3.2)
        L.box((s * 1.4, s, s * 0.8), (math.cos(a) * r, math.sin(a) * r, s * 0.25), ROCK,
              rot=(rng.uniform(-.3, .3), rng.uniform(-.3, .3), rng.uniform(0, 3)))
    # tower: tapered, red and white bands
    bands = 6
    for i in range(bands):
        z0 = 1.0 + i * 4.2
        r0 = 4.0 - i * 0.32
        L.cyl(r0, 4.2, (0, 0, z0 + 2.1), "#ff4b4b" if i % 2 else WHITE, verts=12, r2=r0 - 0.32)
    L.cyl(4.6, 1.2, (0, 0, 0.6), "#c9c2b3", verts=12, bevel=0.2)
    L.box((1.6, 0.3, 2.6), (0, -3.85, 2.6), WOOD_D)        # door
    for z in (9.0, 17.5):
        L.box((0.9, 0.3, 1.3), (0, -3.6 + z * 0.08, z), "#2b4a6b")
    top = 1.0 + bands * 4.2
    L.cyl(3.6, 0.6, (0, 0, top + 0.3), DARK, verts=12)
    for k in range(12):                                    # gallery railing
        a = k / 12 * math.tau
        L.box((0.15, 0.15, 1.2), (math.cos(a) * 3.4, math.sin(a) * 3.4, top + 1.2), WHITE)
    C.ring(3.4, 0.09, (0, 0, top + 1.8), WHITE, maj=12, mnr=3)
    lamp = L.cyl(1.9, 3.0, (0, 0, top + 2.1), "#bff6ff", verts=8, rough=0.05, alpha=0.45)
    grp(lamp, "glass")
    for k in range(8):
        a = (k + 0.5) / 8 * math.tau
        L.box((0.18, 0.18, 3.0), (math.cos(a) * 1.9, math.sin(a) * 1.9, top + 2.1), DARK)
    L.cyl(2.4, 2.6, (0, 0, top + 4.9), "#ff4b4b", verts=8, r2=0.2)
    L.cyl(0.25, 1.2, (0, 0, top + 6.6), DARK, verts=6)
    # keeper's hut + little jetty
    L.box((5, 4, 3.2), (8, 3, 1.6), "#fff4e0", bevel=0.1)
    L.prism([(-3, 0), (3, 0), (0, 2.2)], 4.6, (8, 3, 3.2), "#3b8bff", rot=(0, 0, pi / 2))
    L.box((1.2, 0.2, 1.8), (8, 0.95, 0.9), WOOD_D)


def lighthouse_lamp():
    """Rotating lamp head with two light beams (spins about its vertical axis)."""
    L.cyl(0.9, 1.2, (0, 0, 0), "#fff3b0", verts=8, emit=3.0)
    for s in (-1, 1):
        o = L.cyl(0.35, 7.0, (s * 4.3, 0, 0), "#fff6c2", r2=1.3, verts=8, rot=(0, s * pi / 2, 0),
                  emit=3.0)
        grp(o, "neon")
    L.cyl(1.1, 0.3, (0, 0, -0.75), DARK, verts=8)
    L.cyl(1.1, 0.3, (0, 0, 0.75), DARK, verts=8)


# ------------------------------------------------------------------ windmill
def windmill():
    """Stone windmill body; the blades are WindmillBlades (hub at (0, -3.3, 14.5))."""
    L.cyl(4.2, 3.0, (0, 0, 1.5), "#d8cdb6", verts=8, r2=3.9)
    L.cyl(3.9, 9.0, (0, 0, 7.5), "#fff4e0", verts=8, r2=2.9)
    L.cyl(3.3, 0.5, (0, 0, 12.2), WOOD_D, verts=8)
    L.cyl(3.3, 4.2, (0, 0, 14.4), "#d9483b", verts=8, r2=0.4)
    L.box((1.6, 0.4, 2.6), (0, -3.95, 1.3), WOOD_D, rot=(0.05, 0, 0))      # door
    L.box((2.0, 0.3, 0.3), (0, -4.0, 2.75), WOOD)
    for z, a in ((6.0, 0.6), (9.0, -0.8), (6.5, 2.4)):
        L.box((0.9, 0.3, 1.2), (math.sin(a) * 3.5, -math.cos(a) * 3.5, z), "#2b4a6b",
              rot=(0, 0, a))
    # axle housing pointing forward
    L.box((1.4, 2.2, 1.4), (0, -2.4, 14.5), WOOD_D, bevel=0.15)
    # flower boxes and sacks
    for x in (-2.2, 2.2):
        L.box((1.4, 0.6, 0.5), (x, -3.95, 3.6), WOOD)
        for k in range(3):
            L.box((0.35, 0.35, 0.35), (x - 0.4 + k * 0.4, -4.0, 4.0),
                  ("#ff6fb5", "#ffd23f", "#ff5a5a")[k])
    for x, y in ((3.6, -3.4), (4.4, -2.2)):
        L.box((1.0, 0.8, 1.1), (x, y, 0.55), "#e8d6a8", bevel=0.3)


def windmill_blades():
    """Four sails around the hub, in the XZ plane, spinning about Y (Roblox part local Z)."""
    L.cyl(0.7, 0.8, (0, 0, 0), WOOD_D, rot=(pi / 2, 0, 0), verts=8)
    L.cyl(0.35, 0.9, (0, -0.1, 0), "#ffd23f", rot=(pi / 2, 0, 0), verts=8)
    for k in range(4):
        a = k * pi / 2 + pi / 4
        ca, sa = math.cos(a), math.sin(a)
        C.strip((ca * 0.5, 0, sa * 0.5), (ca * 9.0, 0, sa * 9.0), 0.4, 0.3, WOOD_D,
                up=(0, 1, 0))
        # lattice sail panel beside the spar
        px, pz = -sa, ca
        mid = 5.2
        cx, cz = ca * mid + px * 0.95, sa * mid + pz * 0.95
        C.strip((ca * 1.6 + px * 0.95, 0.05, sa * 1.6 + pz * 0.95),
                (ca * 8.8 + px * 0.95, 0.05, sa * 8.8 + pz * 0.95), 1.5, 0.12,
                WHITE if k % 2 == 0 else "#ffe9d6", up=(0, 1, 0))
        for t in (2.2, 4.0, 5.8, 7.6):
            C.strip((ca * t, -0.08, sa * t), (ca * t + px * 1.75, -0.08, sa * t + pz * 1.75),
                    0.12, 0.1, WOOD, up=(0, 1, 0))
        _ = (cx, cz)


# ------------------------------------------------------------------ balloon
def balloon(c1="#ff5a5a", c2="#ffd23f"):
    """Hot-air balloon, origin at the envelope centre."""
    secs = []
    n = 12
    for i in range(n + 1):
        t = i / n
        a = -pi / 2 + t * pi
        r = math.cos(a) * 6.0 * (1.0 - 0.25 * max(0.0, -math.sin(a)))
        z = math.sin(a) * 7.0
        secs.append((z, max(r, 0.25), z))
    # envelope as vertical gores: loft along Y then rotate (rings around the vertical axis)
    import bpy
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=6.0)
    env = bpy.context.active_object
    me = env.data
    for v in me.vertices:
        z = v.co.z
        k = 1.0 if z > 0 else (1.0 + z / 6.0 * 0.45)
        v.co.x *= k
        v.co.y *= k
        v.co.z *= 1.15
    me.materials.append(L.mat(c1))
    me.materials.append(L.mat(c2))
    me.materials.append(L.mat(WHITE))
    for p in me.polygons:
        ang = math.atan2(p.center.y, p.center.x)
        seg = int((ang + pi) / (math.tau / 12)) % 12
        p.material_index = 0 if seg % 2 == 0 else 1
        if abs(p.center.z) < 1.2:
            p.material_index = 2
    L.cyl(1.4, 0.8, (0, 0, -7.3), "#c98a4b", verts=8)
    for k in range(4):
        a = k * pi / 2 + pi / 4
        C.tube((math.cos(a) * 3.0, math.sin(a) * 3.0, -5.6), (math.cos(a) * 1.1,
                                                              math.sin(a) * 1.1, -9.6),
               0.06, DARK, verts=4)
    L.box((2.4, 2.4, 1.6), (0, 0, -10.4), WOOD, bevel=0.2)
    L.box((2.6, 2.6, 0.3), (0, 0, -9.6), WOOD_D, bevel=0.08)
    L.cyl(0.4, 0.5, (0, 0, -8.6), "#ffb31a", verts=6)
    _ = secs


# ------------------------------------------------------------------ beach & harbour
def beach_set():
    """Umbrella + two loungers + towel + ball (origin on the sand)."""
    L.cyl(0.12, 5.0, (0, 0, 2.5), WHITE, verts=6)
    n = 8
    for k in range(n):
        a = k / n * math.tau
        pts = [(0, 0), (math.cos(a) * 3.4, math.sin(a) * 3.4),
               (math.cos(a + math.tau / n) * 3.4, math.sin(a + math.tau / n) * 3.4)]
        verts = [(0, 0, 5.2)] + [(x, y, 4.3) for x, y in pts[1:]]
        import bpy
        me = bpy.data.meshes.new("canopy")
        me.from_pydata(verts, [], [(0, 1, 2)])
        me.update()
        o = bpy.data.objects.new("canopy", me)
        bpy.context.scene.collection.objects.link(o)
        o.data.materials.append(L.mat("#ff5a5a" if k % 2 else WHITE))
        sol = o.modifiers.new("s", "SOLIDIFY")
        sol.thickness = 0.12
    L.cyl(0.25, 0.3, (0, 0, 5.3), "#ff5a5a", verts=6)
    for x, c in ((-2.2, "#3bb8ff"), (2.2, "#ffd23f")):
        L.box((1.4, 3.4, 0.25), (x, 0.8, 0.55), c, bevel=0.06)
        L.box((1.4, 1.4, 0.25), (x, -1.4, 1.0), c, rot=(math.radians(-35), 0, 0), bevel=0.06)
        for y in (-0.8, 2.2):
            L.box((1.2, 0.15, 0.5), (x, y, 0.25), WHITE)
    L.box((1.6, 2.6, 0.06), (0.1, 3.4, 0.05), "#4bdc5a")
    L.box((1.6, 0.4, 0.07), (0.1, 3.0, 0.06), WHITE)
    C.ball(0.45, (1.0, 4.6, 0.45), "#ff9f1a", seg=8, rings=5)
    L.box((0.9, 0.6, 0.5), (-3.6, 2.6, 0.25), "#3b6bff", bevel=0.08)  # cool box


def pier(length=26.0):
    """Wooden pier along -Y from the origin (land end), deck top at z = 0."""
    n = int(length / 2)
    for i in range(n):
        L.box((5.6, 1.85, 0.4), (0, -1.0 - i * 2.0, -0.2), WOOD_L if i % 2 else WOOD, bevel=0.05)
    for i in range(0, n + 1, 3):
        for s in (-1, 1):
            L.cyl(0.35, 8.0, (s * 2.7, -i * 2.0, -3.6), WOOD_D, verts=6)
            L.box((0.5, 0.5, 1.4), (s * 2.7, -i * 2.0, 0.7), WOOD_D)
    for s in (-1, 1):
        L.box((0.25, length, 0.25), (s * 2.7, -length / 2, 1.3), WOOD_L)
    # end platform with a lamp, crates and a ladder
    L.box((8.0, 4.0, 0.4), (0, -length - 1.8, -0.2), WOOD, bevel=0.05)
    L.cyl(0.14, 4.0, (2.8, -length - 2.8, 2.0), DARK, verts=6)
    L.box((0.8, 0.8, 0.8), (2.8, -length - 2.8, 4.2), "#fff3b0", emit=3.0)
    L.box((1.1, 1.1, 0.2), (2.8, -length - 2.8, 4.7), DARK)
    for (x, y, s) in ((-2.6, -length - 1.0, 1.2), (-1.4, -length - 1.2, 0.9),
                      (-2.3, -length - 1.1, 0.8)):
        L.box((s, s, s), (x, y, s / 2 + (0.9 if s == 0.8 else 0)), "#c98a4b", bevel=0.06)
    for k in range(5):
        L.box((1.0, 0.12, 0.12), (-1.2, -length - 3.85, -0.6 - k * 0.7), WOOD_D)
    for s in (-1, 1):
        L.box((0.12, 0.12, 4.0), (-1.2 + s * 0.5, -length - 3.85, -1.6), WOOD_D)
    C.ring(0.5, 0.15, (1.0, -length - 3.85, 0.8), "#ff5a5a", rot=(pi / 2, 0, 0), maj=10, mnr=4)


def buoy(c="#ff4b4b"):
    """Floating buoy, waterline at z = 0."""
    L.cyl(1.3, 1.4, (0, 0, -0.2), c, verts=10, bevel=0.2)
    L.cyl(1.35, 0.3, (0, 0, 0.35), WHITE, verts=10)
    L.cyl(0.55, 2.4, (0, 0, 1.6), c, verts=8, r2=0.35)
    L.cyl(0.4, 0.4, (0, 0, 2.6), WHITE, verts=8)
    L.cyl(0.32, 0.5, (0, 0, 3.0), "#ffe08a", verts=8)
    L.cyl(0.4, 0.15, (0, 0, 3.3), DARK, verts=8)


def dolphin():
    """Dolphin facing -Y, centre at the origin (jumped by the client)."""
    secs = [(3.2, 0.12, 0.08, -0.15, 0.15, 0.05, 0.05), (2.2, 0.45, 0.35, -0.55, 0.45, 0.25, 0.25),
            (0.4, 0.75, 0.55, -0.8, 0.75, 0.4, 0.4), (-1.4, 0.65, 0.45, -0.7, 0.7, 0.35, 0.35),
            (-2.3, 0.4, 0.3, -0.5, 0.35, 0.2, 0.2), (-3.0, 0.16, 0.12, -0.4, -0.15, 0.06, 0.06)]
    C.loft(secs, "#5f8fc4", paint=lambda u, v, y: "#e8f1ff" if v < 0.3 else None,
           side_breaks=(0.3,))
    L.prism([(-0.6, 0.6), (0.6, 0.6), (0.7, 1.7)], 0.16, (0, 0, 0), "#5f8fc4",
            rot=(0, 0, pi / 2))                       # dorsal fin
    L.prism([(-1.2, 0), (1.2, 0), (0, 0.9)], 0.12, (0, 3.35, 0), "#5f8fc4",
            rot=(pi / 2, 0, 0))                       # tail flukes (flat)
    for s in (-1, 1):
        C.strip((s * 0.6, -0.2, -0.5), (s * 1.3, 0.4, -0.85), 0.5, 0.1, "#5f8fc4")
        C.ball(0.1, (s * 0.38, -2.15, 0.12), DARK, seg=6, rings=3)


def fish(c="#ff9f1a"):
    secs = [(0.9, 0.06, 0.05, -0.1, 0.1, 0.03, 0.03), (0.3, 0.22, 0.18, -0.45, 0.45, 0.12, 0.12),
            (-0.4, 0.2, 0.16, -0.4, 0.4, 0.1, 0.1), (-0.9, 0.04, 0.04, -0.15, 0.15, 0.02, 0.02)]
    C.loft(secs, c, paint=lambda u, v, y: WHITE if 0.4 < v < 0.6 and -0.2 < y < 0.2 else None,
           side_breaks=(0.4, 0.6))
    L.prism([(0, 0), (0.6, 0.5), (0.6, -0.5)], 0.06, (0, 0.85, 0), c, rot=(0, 0, pi / 2))
    for s in (-1, 1):
        C.ball(0.07, (s * 0.15, -0.55, 0.12), DARK, seg=6, rings=3)


def lantern(c="#ff9f1a"):
    """Floating paper lantern (glowing body, wooden caps)."""
    o = L.cyl(1.0, 1.8, (0, 0, 0), c, verts=10, emit=3.0)
    grp(o, "neon")
    L.cyl(0.75, 0.3, (0, 0, 1.0), "#8a3a1a", verts=10)
    L.cyl(0.75, 0.3, (0, 0, -1.0), "#8a3a1a", verts=10)
    L.cyl(0.08, 0.9, (0, 0, -1.55), "#ffd23f", verts=4)
    L.box((0.3, 0.3, 0.3), (0, 0, -2.05), "#ff3b3b")


def waterfall_rock():
    """Cliff of stacked rocks with a waterfall pouring into a pool (origin = island top)."""
    rng = random.Random(12)
    for k in range(14):
        h = rng.uniform(4, 9)
        x = rng.uniform(-7, 7)
        y = rng.uniform(-1, 5)
        z = 0 if k < 8 else rng.uniform(5, 10)
        w = rng.uniform(3.5, 6)
        L.box((w, w * 0.9, h), (x, y, z + h / 2), rng.choice((ROCK, ROCK_D, ROCK_L, "#9aa0ad")),
              rot=(rng.uniform(-.1, .1), rng.uniform(-.1, .1), rng.uniform(0, 1.5)), bevel=0.4)
    for k in range(4):
        L.box((2.5, 2.5, 1.6), (rng.uniform(-6, 6), rng.uniform(1, 4), 15 + rng.uniform(0, 1)),
              "#5fc048", bevel=0.4)
    # water: sheet down the front + pool + splash ring
    w = L.box((3.2, 0.5, 15.0), (0, -2.6, 7.6), "#7fe0ff", rough=0.05, alpha=0.5)
    grp(w, "glass")
    L.box((3.8, 2.6, 0.6), (0, -1.6, 15.3), "#7fe0ff")
    pool = L.cyl(5.5, 0.5, (0, -6.0, 0.25), "#5fd3ff", verts=12, emit=0.2)
    _ = pool
    L.cyl(6.3, 0.8, (0, -6.0, 0.4), ROCK_L, verts=12)
    L.cyl(5.5, 0.9, (0, -6.0, 0.5), "#5fd3ff", verts=12)
    for k in range(6):
        a = k / 6 * math.tau
        L.box((0.6, 0.6, 0.6), (math.cos(a) * 1.8, -6.0 + math.sin(a) * 1.4, 1.1), WHITE,
              bevel=0.2)
    for x, y in ((-6, -4), (6, -5), (-4.5, -8.5)):
        for k in range(5):
            L.box((0.15, 0.15, 1.0), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), 0.5),
                  "#3fae2f")
            L.box((0.6, 0.6, 0.4), (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), 1.1),
                  rng.choice(("#ff6fb5", "#ffd23f", WHITE, "#b58cff")))


def flower_bed():
    """Round bed of blocky flowers with a little border (plot decoration)."""
    L.cyl(3.4, 0.5, (0, 0, 0.25), WOOD_D, verts=10)
    L.cyl(3.0, 0.55, (0, 0, 0.3), "#6b4a2b", verts=10)
    rng = random.Random(6)
    for _ in range(14):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0, 2.4)
        x, y = math.cos(a) * r, math.sin(a) * r
        h = rng.uniform(0.8, 1.6)
        L.box((0.16, 0.16, h), (x, y, 0.5 + h / 2), "#3fae2f")
        L.box((0.7, 0.7, 0.45), (x, y, 0.5 + h + 0.2),
              rng.choice(("#ff6fb5", "#ffd23f", WHITE, "#ff5a5a", "#b58cff", "#ff9f1a")))
        L.box((0.5, 0.2, 0.15), (x + 0.25, y, 0.5 + h * 0.5), "#5fd13f", rot=(0, 0.4, a))


def hedge():
    """Rounded hedge row with flowers (6 long)."""
    L.box((6.0, 1.8, 1.8), (0, 0, 0.9), "#4cbb3a", bevel=0.5, segs=2)
    L.box((5.4, 1.4, 0.6), (0, 0, 1.9), "#5fd13f", bevel=0.25, segs=1)
    rng = random.Random(9)
    for _ in range(7):
        L.box((0.4, 0.4, 0.4), (rng.uniform(-2.6, 2.6), -0.92, rng.uniform(0.6, 1.7)),
              rng.choice(("#ff6fb5", "#ffd23f", WHITE)))
