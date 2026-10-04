"""World meshes: plot islands, the hub island, bridge pieces, props and landmarks.

Islands are organic rounded shapes sitting in the sea: grass top, short cliff, sandy beach
just above the water line and a rocky base under it. Plot islands keep their parts separated
by role (Grass / Dirt / Rock) so island styles can recolour them.
Run: <bpy python> world.py [name ...]   -> assets/meshes/World_<name>__*.fbx, renders/world/*.png
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)
import bpy  # noqa: E402,I001
import mlib as L  # noqa: E402
import meshkit as K  # noqa: E402
import all_models as P  # noqa: E402

WATER = -8.0           # sea level below the island top
PLOT_W, PLOT_D = 200.0, 220.0
HUB_R = 92.0

GRASS, GRASS_D = "#74d65a", "#5fc048"
DIRT, DIRT_D = "#b5793f", "#9a6534"
SAND, SAND_W = "#f2dc9b", "#e3c47c"
ROCK, ROCK_D = "#8d8f9e", "#6f7181"
STONE, STONE_D = "#efe6d2", "#d9ccad"


# ------------------------------------------------------------------ island builder
def superellipse(a, b, n=5.0, count=96, seed=0, wobble=0.0):
    rng = random.Random(seed)
    phase = [rng.uniform(0, math.tau) for _ in range(3)]
    pts = []
    for i in range(count):
        t = i / count * math.tau
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** (2 / n), c)
        y = b * math.copysign(abs(s) ** (2 / n), s)
        k = 1 + wobble * (0.5 * math.sin(3 * t + phase[0]) + 0.3 * math.sin(5 * t + phase[1])
                          + 0.2 * math.sin(9 * t + phase[2]))
        pts.append((x * k, y * k))
    return pts


def normals(pts):
    out = []
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L_ = math.hypot(dx, dy) or 1
        out.append((dy / L_, -dx / L_))  # outward for counter-clockwise outlines
    return out


def band_mesh(name, outline, rings, colors, grp=None, cap_top=False, cap_bottom=False, seed=0):
    """rings: [(offset, z, jitter)], quads between consecutive rings get colors[i]."""
    rng = random.Random(seed)
    nrm = normals(outline)
    verts, faces, mats = [], [], []
    n = len(outline)
    for (off, z, jit) in rings:
        for i, (x, y) in enumerate(outline):
            j = rng.uniform(-jit, jit)
            verts.append((x + nrm[i][0] * (off + j), y + nrm[i][1] * (off + j),
                          z + rng.uniform(-jit, jit) * 0.3))
    for r in range(len(rings) - 1):
        for i in range(n):
            a, b = r * n + i, r * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
            mats.append(r)
    # caps are fans around a centre vertex (big n-gons triangulate badly)
    if cap_top:
        c = len(verts)
        verts.append((0.0, 0.0, rings[0][1]))
        for i in range(n):
            faces.append((c, i, (i + 1) % n))
            mats.append(len(rings) - 1)
    if cap_bottom:
        last = (len(rings) - 1) * n
        c = len(verts)
        verts.append((0.0, 0.0, rings[-1][1]))
        for i in range(n):
            faces.append((c, last + (i + 1) % n, last + i))
            mats.append(len(rings) - 1)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    cols = list(dict.fromkeys(colors))
    for c in cols:
        me.materials.append(L.mat(c, rough=0.8))
    for p, m in zip(me.polygons, mats):
        p.material_index = cols.index(colors[min(m, len(colors) - 1)])
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    # make sure every face points outwards / up
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if grp:
        o["grp"] = grp
    return o


def island(outline, seed, roles=True, top_color=GRASS):
    """Top grass (+lip), cliff, beach, underwater rock. Returns nothing; adds objects."""
    g = (lambda r: "role:" + r) if roles else (lambda r: None)
    # grass top (cap) + lip
    band_mesh("Grass", outline, [(0.0, 0.0, 0.0), (0.9, -0.9, 0.15)], [GRASS_D, top_color],
              g("Grass"), cap_top=True, seed=seed)
    # cliff (dirt) with jagged rock bands
    band_mesh("Dirt", outline, [(0.9, -0.9, 0.0), (1.7, -3.2, 0.5), (2.6, -5.6, 0.7),
                                (3.4, -6.9, 0.4)], [DIRT, DIRT_D, DIRT], g("Dirt"), seed=seed + 1)
    # beach ledge above the sea, then down under the water
    band_mesh("Rock", outline, [(3.4, -6.9, 0.4), (10.0, -7.4, 1.2), (15.0, -8.6, 1.5),
                                (21.0, -13.0, 2.0), (16.0, -22.0, 2.5)],
              [SAND, SAND_W, ROCK, ROCK_D], g("Rock"), cap_bottom=True, seed=seed + 2)


def blocky_hill(x, y, w, d, h, color=GRASS, color2=GRASS_D, grp="role:Grass"):
    for k, (kw, kh) in enumerate(((1.0, h * 0.55), (0.66, h * 0.8), (0.36, h))):
        o = L.box((w * kw, d * kw, kh), (x, y, kh / 2 - 0.2), color if k % 2 == 0 else color2,
                  bevel=0.4)
        o["grp"] = grp


# ------------------------------------------------------------------ models
def plot_island():
    outline = superellipse(PLOT_W / 2, PLOT_D / 2, n=4.2, count=112, seed=4, wobble=0.025)
    island(outline, 7)
    # raised blocky hills in the two back corners (+Roblox Z = Blender -Y is the back)
    blocky_hill(-88, -98, 22, 18, 7)
    blocky_hill(88, -97, 20, 20, 9)
    # stepping-stone path from the entrance (Roblox z = -104) to the build area (z = -66)
    rng = random.Random(8)
    for i in range(8):
        y = 100 - i * 4.6
        L.box((9.5 + rng.uniform(-1, 1), 3.4, 0.3), (rng.uniform(-0.6, 0.6), y, 0.12), STONE,
              rot=(0, 0, rng.uniform(-0.08, 0.08)), bevel=0.3)
    # flower patches and pebbles along the sides
    for x, y in ((-70, 70), (70, 75), (-95, -55), (95, 10), (-95, 15), (60, -100), (-30, -101)):
        for _ in range(7):
            fx, fy = x + rng.uniform(-4, 4), y + rng.uniform(-3, 3)
            L.box((0.18, 0.18, 1.0), (fx, fy, 0.5), "#3fae2f")
            L.box((0.8, 0.8, 0.5), (fx, fy, 1.15), rng.choice(("#ff6fb5", "#ffd23f", "#ffffff",
                                                                  "#ff5a5a", "#b58cff")))


def hub_island():
    outline = superellipse(HUB_R, HUB_R, n=2.3, count=128, seed=11, wobble=0.03)
    island(outline, 21, roles=False)
    # plaza + 8 paths to the bridges (kept thin so no dark steps show at the joins)
    L.cyl(36, 0.1, (0, 0, 0.05), STONE, verts=32)
    L.cyl(30, 0.12, (0, 0, 0.06), STONE_D, verts=32)
    L.cyl(26, 0.14, (0, 0, 0.07), STONE, verts=32)
    for k in range(8):
        a = k * math.tau / 8
        r = (34 + HUB_R) / 2
        L.box((HUB_R - 34, 13, 0.08), (math.cos(a) * r, math.sin(a) * r, 0.04), STONE,
              rot=(0, 0, a))
        for s in (-1, 1):
            L.box((HUB_R - 38, 0.8, 0.2), (math.cos(a) * (r + 2) - math.sin(a) * 7 * s,
                                             math.sin(a) * (r + 2) + math.cos(a) * 7 * s, 0.1),
                  STONE_D, rot=(0, 0, a))
    # flower beds between the paths
    rng = random.Random(5)
    for k in (1, 3, 5, 7):  # the other four gaps hold the market stalls
        a = (k + 0.5) * math.tau / 8
        r = 48
        cx, cy = math.cos(a) * r, math.sin(a) * r
        L.box((11, 7, 0.9), (cx, cy, 0.45), "#8a5a2b", rot=(0, 0, a), bevel=0.2)
        L.box((10, 6, 0.4), (cx, cy, 0.95), "#5fc048", rot=(0, 0, a))
        for _ in range(6):
            dx, dy = rng.uniform(-3.5, 3.5), rng.uniform(-2, 2)
            x = cx + dx * math.cos(a) - dy * math.sin(a)
            y = cy + dx * math.sin(a) + dy * math.cos(a)
            L.box((0.9, 0.9, 0.9), (x, y, 1.5), rng.choice(("#ff6fb5", "#ffd23f", "#ff5a5a",
                                                             "#ffffff", "#b58cff")))


def landmark():
    """Hub centre: fountain basin with a giant golden die on a pillar."""
    L.cyl(11, 1.6, (0, 0, 0.8), "#c9c2b3", verts=12, bevel=0.2)
    L.cyl(10, 0.2, (0, 0, 1.55), "#5fd3ff", verts=12, emit=0.2)
    L.cyl(2.2, 6.0, (0, 0, 4.0), "#c9c2b3", verts=8)
    L.cyl(4.0, 0.8, (0, 0, 7.2), "#c9c2b3", verts=8, bevel=0.15)
    L.cyl(3.4, 0.2, (0, 0, 7.6), "#5fd3ff", verts=8, emit=0.3)
    die = L.box((6, 6, 6), (0, 0, 12.5), "#ffd23f", rot=(math.radians(35), math.radians(-30), 0),
                bevel=0.7, segs=2)
    _ = die
    pips = [(0, 0), (-1.6, -1.6), (1.6, 1.6)]
    import mathutils
    rot = mathutils.Euler((math.radians(35), math.radians(-30), 0)).to_matrix()
    for face in range(3):
        for dx, dy in pips[: face + 1 + (1 if face == 2 else 0)]:
            v = [mathutils.Vector((dx, -3.05, dy)), mathutils.Vector((3.05, dx, dy)),
                 mathutils.Vector((dx, dy, 3.05))][face]
            p = rot @ v
            L.box((1.1, 1.1, 1.1), (p.x, p.y, 12.5 + p.z), "#2b2f3a")
    # little splash jets around the basin
    for k in range(6):
        a = k * math.tau / 6
        o = L.cyl(0.35, 2.4, (math.cos(a) * 7.5, math.sin(a) * 7.5, 2.7), "#bff1ff", verts=6,
                  r2=0.1)
        o["grp"] = "glass"


def bridge_piece():
    """6 studs long, 14 wide deck at z = 0 (tile it end to end)."""
    for i in range(3):
        L.box((13.6, 1.8, 0.6), (0, -3 + i * 2 + 1, -0.3), "#d99a5b" if i % 2 else "#c9874a",
              bevel=0.1)
    for x in (-6.4, 6.4):
        L.box((0.8, 6, 0.8), (x, 0, -0.9), "#8a5a2b")
        L.box((0.7, 0.7, 3.6), (x * 1.06, -2.6, 1.4), "#8a5a2b", bevel=0.08)
        L.box((1.0, 1.0, 0.35), (x * 1.06, -2.6, 3.3), "#ffffff", bevel=0.06)
        L.box((0.45, 6.05, 0.45), (x * 1.06, 0, 2.6), "#f2d29b")
        L.box((0.3, 6.05, 0.3), (x * 1.06, 0, 1.4), "#f2d29b")


def bridge_pillar():
    L.cyl(2.4, 14, (0, 0, -7), "#9aa0ad", verts=8, bevel=0.2)
    L.cyl(3.0, 1.0, (0, 0, -0.5), "#c9c2b3", verts=8, bevel=0.15)
    L.cyl(3.2, 1.2, (0, 0, -8.6), "#6f7181", verts=8)


def sign_arch():
    """Owner sign frame (the name text is a separate Part with a SurfaceGui)."""
    for x in (-9, 9):
        L.box((1.4, 1.4, 13), (x, 0, 6.5), "#8a5a2b", bevel=0.15)
        L.box((2.0, 2.0, 0.6), (x, 0, 13.2), "#ffffff", bevel=0.1)
        L.box((2.2, 2.2, 0.6), (x, 0, 0.3), "#c9c2b3", bevel=0.1)
    L.prism(L.rounded_rect(20, 7, 1.2), 0.8, (0, 0, 10.5), "#ffffff")


def floating_isle():
    outline = superellipse(14, 12, n=2.4, count=24, seed=3, wobble=0.08)
    band_mesh("Top", outline, [(0, 0, 0), (0.6, -0.8, 0.2)], [GRASS_D, GRASS], cap_top=True,
              seed=1)
    band_mesh("Under", outline, [(0.6, -0.8, 0.2), (-2.0, -5.0, 0.8), (-7.0, -10.0, 0.8),
                                 (-12.0, -15.0, 0.5)], [DIRT, ROCK, ROCK_D], cap_bottom=True,
              seed=2)
    P.tree_round()


def lamp():
    P.lamp_post()


def flowers():
    rng = random.Random(2)
    for _ in range(9):
        x, y = rng.uniform(-2.5, 2.5), rng.uniform(-2.5, 2.5)
        L.box((0.15, 0.15, 1.0), (x, y, 0.5), "#3fae2f")
        L.box((0.7, 0.7, 0.5), (x, y, 1.15), rng.choice(("#ff6fb5", "#ffd23f", "#ffffff",
                                                          "#ff5a5a", "#b58cff")))


def bench():
    for i in range(3):
        L.box((5, 0.6, 0.25), (0, -0.7 + i * 0.7, 1.4), "#d99a5b" if i % 2 else "#c9874a")
    L.box((5, 0.25, 1.2), (0, 1.0, 2.2), "#c9874a")
    for x in (-2.1, 2.1):
        L.box((0.35, 2.2, 1.4), (x, 0.1, 0.7), "#2b2f3a")


MODELS = {
    "PlotIsland": plot_island, "HubIsland": hub_island, "Landmark": landmark,
    "BridgePiece": bridge_piece, "BridgePillar": bridge_pillar, "SignArch": sign_arch,
    "FloatingIsle": floating_isle, "Lamp": lamp, "Flowers": flowers, "Bench": bench,
    "StallCars": P.shop_cars, "StallStyles": P.shop_styles, "StallPotions": P.shop_potions,
    "StallDice": P.shop_dice, "TreeRound": P.tree_round, "TreePine": P.tree_pine,
    "TreePalm": P.tree_palm, "Bush": P.bush, "Rock": P.rock,
}


def mark_glow():
    """Emissive materials (lamps, water) become Neon MeshParts."""
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or "grp" in o or not o.material_slots:
            continue
        m = o.material_slots[0].material
        b = m and m.node_tree and m.node_tree.nodes.get("Principled BSDF")
        if b and b.inputs["Emission Strength"].default_value > 0:
            o["grp"] = "neon"


def render(name):
    L.studio(ground=False)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 640, 480
    sc.cycles.samples = 24
    L.frame(lens=40, elev=30, azim=-35, margin=1.1)
    L.render(os.path.join(ROOT, "renders", "world", name + ".png"))


if __name__ == "__main__":
    want = sys.argv[1:]
    for name, fn in MODELS.items():
        if want and name not in want:
            continue
        L.reset()
        fn()
        mark_glow()
        K.bake("World_" + name)
        render(name)
