"""World layout: main hub island + 8 player islands in a ring, all joined by bridges.

Run: python world.py   (uses the bpy module)
Outputs assets/world/*.fbx and renders/world_*.png
"""
import math
import random
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))

import bpy  # noqa: F401  (loads mathutils)
from mathutils import Vector

import shops
from lib import (box, camera, cyl, empty, export_fbx, join, mat, render, reset, save_blend,
                 setup_scene, sphere, text)

MAIN_R = 90          # hub radius (studs)
PLOT_R = 50          # player island radius
RING = 250           # distance hub centre -> player island centre
PLOT_COLORS = ["#ff4b4b", "#ff9f1a", "#ffe03b", "#4bdc5a", "#3bd1ff", "#3b6bff", "#b54dff",
               "#ff5fc8"]


def floating_island(name, r, loc, grass="#5fd13f", seed=0, parent=None):
    rng = random.Random(seed)
    x, y, z = loc
    g = mat(f"Grass_{grass}", grass, rough=0.8)
    dirt = mat("Dirt", "#9b6634", rough=0.9)
    rock = mat("Rock", "#7d7468", rough=0.9)
    parts = [
        cyl("grass", r, 3, (x, y, z - 1.5), g, verts=28),
        cyl("lip", r + 0.8, 1.2, (x, y, z - 3.2), g, verts=28),
        cyl("dirt", r * 0.97, 8, (x, y, z - 7.5), dirt, verts=28, r2=r * 0.97),
        cyl("rock", r * 0.95, r * 0.75, (x, y, z - 11.5 - r * 0.375), rock, verts=14,
            r2=r * 0.12),
    ]
    # chunky rocks hanging underneath
    for i in range(7):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0.2, 0.6) * r
        s = rng.uniform(0.15, 0.3) * r
        parts.append(box(f"chunk{i}", (s, s, s * 1.4),
                         (x + math.cos(a) * d, y + math.sin(a) * d, z - 14 - s),
                         rock, rot=(rng.random(), rng.random(), rng.random())))
    o = join(parts, name)
    o.parent = parent
    return o


def tree(name, loc, s=1.0, leaf="#3fae2f", parent=None):
    trunk = mat("Trunk", "#8a5a2b", rough=0.9)
    lf = mat(f"Leaf_{leaf}", leaf, rough=0.8)
    lf2 = mat(f"Leaf2_{leaf}", leaf, rough=0.8)
    x, y, z = loc
    o = join([
        box("trunk", (2 * s, 2 * s, 10 * s), (x, y, z + 5 * s), trunk),
        box("l1", (11 * s, 11 * s, 6 * s), (x, y, z + 12 * s), lf, bevel=0.3),
        box("l2", (7 * s, 7 * s, 5 * s), (x, y, z + 17 * s), lf2, bevel=0.3),
    ], name)
    o.parent = parent
    return o


def bridge(name, p1, p2, width=14, parent=None):
    """Wooden plank bridge with posts and rope rails between two points (z=0)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    L = d.length
    ang = math.atan2(d.y, d.x)
    mid = (p1 + p2) / 2
    plank_a = mat("Plank", "#c98a4b", rough=0.8)
    plank_b = mat("PlankB", "#b07438", rough=0.8)
    post = mat("WoodDark", "#7a4a25")
    rope = mat("Rope", "#e0c58f")
    root = empty(name, (mid.x, mid.y, 0), parent)
    root.rotation_euler.z = ang
    parts = []
    n = int(L / 2.2)
    step = L / n
    for i in range(n):
        lx = -L / 2 + step * (i + 0.5)
        sag = -1.2 * math.sin(math.pi * (i + 0.5) / n)
        parts.append(box(f"pl{i}", (step * 0.88, width, 0.8), (lx, 0, -0.4 + sag),
                         plank_a if i % 2 else plank_b))
    beams = []
    for side in (-1, 1):
        beams.append(box("beam", (L, 1.0, 1.0), (0, side * (width / 2 - 0.5), -1.6), post))
    posts = max(2, int(L / 14) + 1)
    for i in range(posts):
        lx = -L / 2 + L * i / (posts - 1)
        sag = -1.2 * math.sin(math.pi * i / (posts - 1))
        for side in (-1, 1):
            parts.append(box("post", (1.2, 1.2, 6), (lx, side * (width / 2 + 0.2), 2 + sag), post,
                             bevel=0.15))
    for side in (-1, 1):
        for h in (2.2, 4.4):
            parts.append(box("rope", (L, 0.4, 0.4), (0, side * (width / 2 + 0.2), h - 0.6), rope))
    b = join(parts + beams, name + "_Mesh")
    b.parent = root
    return root


def player_island(idx, center, parent):
    """Plot for one player: spin machine, track start gate, garage, plot sign."""
    col = PLOT_COLORS[idx]
    cx, cy = center
    face = math.atan2(-cy, -cx)  # direction towards hub
    root = empty(f"Plot_{idx + 1}", (cx, cy, 0), parent)
    root.rotation_euler.z = face - math.pi / 2  # local +Y points to hub
    floating_island(f"Plot_{idx + 1}_Island", PLOT_R, (0, 0, 0), seed=idx + 10, parent=root)
    pc = mat(f"PlotCol_{idx}", col, rough=0.4)
    white = mat("White", "#ffffff")
    dark = mat("Dark", "#2b2b33")
    asphalt = mat("Asphalt", "#3a3a42", rough=0.85)
    kerb_r = mat("KerbRed", "#ff3030")
    # coloured border ring
    ring = join([box(f"b{i}", (2.4, 13.2, 0.6),
                     (math.cos(a) * (PLOT_R - 1.4), math.sin(a) * (PLOT_R - 1.4), 0.3), pc,
                     rot=(0, 0, a))
                 for i, a in enumerate([k * math.tau / 24 for k in range(24)])],
                f"Plot_{idx + 1}_Border")
    ring.parent = root
    # spawn pad (near hub-facing edge)
    sp = join([cyl("pad", 6, 0.8, (0, 34, 0.4), white, verts=24),
               cyl("padc", 4.5, 0.9, (0, 34, 0.45), pc, verts=24)], f"Plot_{idx + 1}_Spawn")
    sp.parent = root
    # plot sign
    sign = join([box("p1", (1, 1, 10), (-8, 40, 5), mat("WoodDark", "#7a4a25")),
                 box("p2", (1, 1, 10), (8, 40, 5), mat("WoodDark", "#7a4a25")),
                 box("bd", (18, 0.8, 5), (0, 40, 9), pc, bevel=0.3)], f"Plot_{idx + 1}_Sign")
    sign.parent = root
    t = text(f"Plot_{idx + 1}_SignText", f"PLOT {idx + 1}", 2.8, (0, 39.5, 9), white,
             rot=(math.pi / 2, 0, math.pi), extrude=0.15)
    t.parent = root
    # SPIN machine (slot-machine style)
    gold = mat("Gold", "#ffc21a", metal=0.4, rough=0.3)
    screen = mat("Screen", "#7fe8ff", emit=1.5)
    spin = join([
        box("base", (12, 8, 3), (-22, 14, 1.5), dark, bevel=0.4),
        box("body", (10, 6, 12), (-22, 14, 9), pc, bevel=0.6),
        box("scr", (7.5, 0.5, 5), (-22, 10.9, 10), screen, bevel=0.2),
        box("top", (11, 7, 2), (-22, 14, 16), gold, bevel=0.4),
        cyl("lever", 0.4, 6, (-16, 14, 11), gold, verts=8),
        sphere("knob", 1.1, (-16, 14, 14.2), kerb_r),
    ], f"Plot_{idx + 1}_SpinMachine")
    spin.parent = root
    st = text(f"Plot_{idx + 1}_SpinText", "SPIN", 2.4, (-22, 10.4, 15.9), dark,
              rot=(math.pi / 2, 0, 0), extrude=0.12)
    st.parent = root
    # garage
    gar = join([
        box("g_back", (16, 1, 10), (24, 22, 5), white, bevel=0.2),
        box("g_l", (1, 14, 10), (16.5, 15, 5), white, bevel=0.2),
        box("g_r", (1, 14, 10), (31.5, 15, 5), white, bevel=0.2),
        box("g_roof", (18, 16, 1.2), (24, 15, 10.6), pc, bevel=0.3),
        box("g_floor", (15, 14, 0.3), (24, 15, 0.15), asphalt),
    ], f"Plot_{idx + 1}_Garage")
    gar.parent = root
    shops.simple_car(f"Plot_{idx + 1}_Car", (24, 14, 0.3), col, root, rz=0)
    # track start: start gate + first straight heading away from hub
    chk_w = mat("CheckW", "#ffffff")
    chk_b = mat("CheckB", "#111111")
    road = [box("road", (16, 46, 0.6), (0, -12, 0.3), asphalt)]
    for i in range(23):
        for side in (-1, 1):
            road.append(box("kerb", (1.2, 2, 0.7), (side * 8.6, -34 + i * 2 + 1, 0.35),
                            kerb_r if i % 2 else chk_w))
    for i in range(8):
        for j in range(2):
            road.append(box("chk", (2, 2, 0.65), (-7 + i * 2, 4 + j * 2, 0.33),
                            chk_w if (i + j) % 2 else chk_b))
    r_obj = join(road, f"Plot_{idx + 1}_TrackStart")
    r_obj.parent = root
    gate = join([
        box("gl", (1.6, 1.6, 14), (-9.5, 5, 7), dark),
        box("gr", (1.6, 1.6, 14), (9.5, 5, 7), dark),
        box("gt", (21, 2, 3.5), (0, 5, 14.5), pc, bevel=0.3),
    ], f"Plot_{idx + 1}_StartGate")
    gate.parent = root
    gt = text(f"Plot_{idx + 1}_StartText", "START", 2.2, (0, 3.9, 14.5), white,
              rot=(math.pi / 2, 0, 0), extrude=0.1)
    gt.parent = root
    rng = random.Random(idx)
    for k in range(5):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(30, 44)
        x, y = math.cos(a) * d, math.sin(a) * d
        if abs(x) < 14 and y < 10:   # keep track lane clear
            continue
        if y > 25 and abs(x) < 12:   # keep spawn clear
            continue
        tree(f"Plot_{idx + 1}_Tree{k}", (x, y, 0), rng.uniform(0.8, 1.2), parent=root)
    return root


def main_island(parent):
    root = empty("MainIsland", (0, 0, 0), parent)
    floating_island("MainIsland_Ground", MAIN_R, (0, 0, 0), seed=1, parent=root)
    stone = mat("Stone", "#d9d4c7", rough=0.7)
    stone2 = mat("Stone2", "#bfb8a8", rough=0.7)
    water = mat("FountainWater", "#4fc8ff", rough=0.1)
    white = mat("White", "#ffffff")
    plaza = join([cyl("plaza", 22, 0.5, (0, 0, 0.25), stone, verts=32),
                  cyl("plaza2", 16, 0.55, (0, 0, 0.28), stone2, verts=32)], "Hub_Plaza")
    plaza.parent = root
    paths = []
    for k in range(8):
        a = k * math.tau / 8
        paths.append(box(f"path{k}", (MAIN_R - 18, 12, 0.5),
                         (math.cos(a) * (MAIN_R / 2 + 9), math.sin(a) * (MAIN_R / 2 + 9), 0.25),
                         stone, rot=(0, 0, a)))
    p = join(paths, "Hub_Paths")
    p.parent = root
    f = join([cyl("f1", 9, 2.5, (0, 0, 1.25), stone2, verts=24),
              cyl("fw", 8, 0.4, (0, 0, 2.3), water, verts=24),
              cyl("f2", 2, 6, (0, 0, 4), stone2, verts=12),
              cyl("f3", 4.5, 1, (0, 0, 7), stone2, verts=16),
              cyl("fw2", 4, 0.3, (0, 0, 7.5), water, verts=16)], "Hub_Fountain")
    f.parent = root
    # Title sign
    title_bg = mat("TitleBg", "#ff3b6b")
    title = join([box("tp1", (1.5, 1.5, 22), (-20, 0, 11), mat("WoodDark", "#7a4a25")),
                  box("tp2", (1.5, 1.5, 22), (20, 0, 11), mat("WoodDark", "#7a4a25")),
                  box("tb", (44, 1.4, 10), (0, 0, 24), title_bg, bevel=0.5),
                  box("tf", (46, 1.2, 12), (0, 0.2, 24), white, bevel=0.5)], "Hub_TitleSign")
    ta = math.radians(112.5)
    title.parent = empty("Hub_TitleRoot", (math.cos(ta) * 45, math.sin(ta) * 45, 0), root)
    title.parent.rotation_euler.z = ta - math.pi / 2
    for side, rz in ((-0.8, 0), (0.8, math.pi)):
        t = text("Hub_TitleText", "TRACK RNG", 6, (0, side, 24), white,
                 rot=(math.pi / 2, 0, rz), extrude=0.3)
        t.parent = title.parent
    # shops in the gaps between bridge entries, facing the fountain
    builders = [shops.build_potion_shop, shops.build_lucky_shop, shops.build_car_shop,
                shops.build_style_shop]
    for k, build in enumerate(builders):
        a = math.radians(22.5 + 90 * k + 45)
        d = 62
        s = build((math.cos(a) * d, math.sin(a) * d, 0.0), a - math.pi / 2)
        s.parent = root
    rng = random.Random(3)
    for k in range(10):
        a = math.radians(22.5 + 90 * (k % 4)) + rng.uniform(-0.15, 0.15)
        d = rng.uniform(70, 84)
        tree(f"Hub_Tree{k}", (math.cos(a) * d, math.sin(a) * d, 0), rng.uniform(0.8, 1.3),
             parent=root)
    return root


def build():
    reset()
    world = empty("World")
    main_island(world)
    plots = []
    for i in range(8):
        a = i * math.tau / 8
        plots.append(player_island(i, (math.cos(a) * RING, math.sin(a) * RING), world))
    bridges = empty("Bridges", parent=world)
    for i in range(8):
        a = i * math.tau / 8
        u = Vector((math.cos(a), math.sin(a), 0))
        bridge(f"Bridge_Hub_{i + 1}", u * (MAIN_R - 3), u * (RING - PLOT_R + 3), parent=bridges)
        b = (i + 1) % 8
        c1 = Vector((math.cos(a), math.sin(a), 0)) * RING
        c2 = Vector((math.cos(b * math.tau / 8), math.sin(b * math.tau / 8), 0)) * RING
        dv = (c2 - c1).normalized()
        bridge(f"Bridge_Ring_{i + 1}_{b + 1}", c1 + dv * (PLOT_R - 3), c2 - dv * (PLOT_R - 3),
               parent=bridges)
    return world, plots, bridges


if __name__ == "__main__":
    world, plots, bridges = build()
    hub = [o for o in world.children if o.name == "MainIsland"][0]
    export_fbx([hub], "world/MainIsland.fbx")
    export_fbx([plots[0]], "world/PlayerPlot.fbx")
    export_fbx([bridges], "world/Bridges.fbx")
    save_blend("world/World.blend")
    setup_scene(water=True, water_z=-120, samples=40)
    which = sys.argv[1:] or ["overview", "hub", "plot"]
    if "overview" in which:
        camera((380, -520, 420), (0, 0, -20), lens=28)
        render("world_overview.png")
    if "hub" in which:
        camera((120, -120, 85), (0, 0, 6), lens=24)
        render("world_hub.png")
    if "plot" in which:
        camera((RING + 75, -70, 55), (RING, 0, 4), lens=26)
        render("world_plot.png")
