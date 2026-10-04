"""Shop icons for every dice and potion (transparent 256 px PNGs) -> assets/icons/<id>.png

Run: <bpy python> item_icons.py [id ...]
"""
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import bpy  # noqa: E402,I001
import mlib as L  # noqa: E402

OUT = os.path.join(ROOT, "assets", "icons")
DATA = json.load(open(os.path.join(ROOT, "src/ReplicatedStorage/Shared/GameData.json")))
RAINBOW = ["#ff3b3b", "#ff9f1a", "#ffe03b", "#4bdc5a", "#3bd1ff", "#7b5cff"]


def col(c, fallback="#ffffff"):
    return fallback if c == "rainbow" else c


# ------------------------------------------------------------------ dice
PIPS = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)],
        4: [(-1, -1), (1, -1), (-1, 1), (1, 1)], 5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
        6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}


def die(d):
    c1, c2 = col(d["color"]), d.get("color2", "#ffffff")
    pip = "#ffffff" if d["id"] in ("Void", "Cosmic", "Galaxy", "Singularity", "Cyber") else "#2b2f3a"
    if d["id"] == "Golden":
        pip = "#8a5a00"
    metal = 0.8 if d["id"] in ("Golden", "Divine") else 0.0
    emit = 0.6 if d["vfx"] >= 3 else 0.0
    body = L.box((2, 2, 2), (0, 0, 0), c1, bevel=0.32, segs=3, smooth=True, metal=metal,
                 rough=0.3)
    if d["id"] == "Rainbow":
        body.data.materials.clear()
        for c in RAINBOW:
            body.data.materials.append(L.mat(c, rough=0.3))
        for p in body.data.polygons:
            p.material_index = int((p.center.x + p.center.y * 1.7 + p.center.z * 2.3 + 6) * 1.3) % 6
    # pips on the three visible faces (+X, -Y, +Z)
    faces = [((1, 0, 0), 5), ((0, -1, 0), 3), ((0, 0, 1), 6)]
    for n, count in faces:
        for a, b in PIPS[count]:
            if n[0]:
                pos = (1.0, a * 0.5, b * 0.5)
                rot = (0, math.pi / 2, 0)
            elif n[1]:
                pos = (a * 0.5, -1.0, b * 0.5)
                rot = (math.pi / 2, 0, 0)
            else:
                pos = (a * 0.5, b * 0.5, 1.0)
                rot = (0, 0, 0)
            L.cyl(0.17, 0.08, pos, pip, rot=rot, verts=16, smooth=True, emit=emit * 2)
    theme = d["id"]
    rng = random.Random(len(theme))
    if theme == "Frost":
        for i in range(7):
            a = i / 7 * math.tau
            L.cyl(0.18, 0.9, (math.cos(a) * 1.05, math.sin(a) * 1.05, 1.15), "#e6f8ff",
                  r2=0.0, verts=5, rot=(rng.uniform(-.4, .4), rng.uniform(-.4, .4), 0), rough=0.05)
    if theme == "Toxic":
        L.box((2.08, 2.08, 0.3), (0, 0, 0.88), "#b6ff3b", emit=0.6, bevel=0.12)
        for x, y, z in ((-0.55, -1.04, 0.35), (0.35, -1.04, 0.1), (1.04, -0.3, 0.25),
                        (1.04, 0.5, 0.45)):
            L.sphere(0.17, (x, y, z), "#b6ff3b", emit=0.8, subdiv=2, smooth=True,
                     scale=(1, 1, 1.5))
    if theme == "Inferno":
        for i in range(6):
            a = i / 6 * math.tau
            L.cyl(0.32, 1.3, (math.cos(a) * 0.6, math.sin(a) * 0.6, 1.5), "#ffb31a", r2=0.0,
                  verts=6, emit=2.0)
        L.cyl(0.45, 1.8, (0, 0, 1.6), "#ff5a1a", r2=0.0, verts=6, emit=2.0)
    if theme in ("Cosmic", "Galaxy", "Void", "Singularity"):
        for _ in range(10):
            L.sphere(0.05, (rng.uniform(-1.4, 1.4), rng.uniform(-1.4, 1.4), rng.uniform(-1.4, 1.4)),
                     "#ffffff", emit=4.0, subdiv=1)
        ring_c = {"Cosmic": "#d9a3ff", "Galaxy": "#ff6fd8", "Void": "#c46bff",
                  "Singularity": "#ffb31a"}[theme]
        L.torus(1.75, 0.07, (0, 0, 0), ring_c, rot=(math.radians(70), math.radians(20), 0),
                emit=3.0)
    if theme == "Cyber":
        for a in (-0.98, 0.98):
            for b in (-0.98, 0.98):
                L.box((1.6, 0.08, 0.08), (0, a, b), "#14e0ff", emit=4.0)
                L.box((0.08, 1.6, 0.08), (a, 0, b), "#14e0ff", emit=4.0)
                L.box((0.08, 0.08, 1.6), (a, b, 0), "#14e0ff", emit=4.0)
    if theme == "Glitch":
        for k in range(3):
            L.box((2.04, 0.3, 2.04), (rng.uniform(-.15, .15), -0.7 + k * 0.7, 0),
                  ("#2bff8a", "#ff2bd6", "#2b8bff")[k], emit=1.5)
    if theme in ("Celestial", "Divine"):
        L.torus(0.9, 0.1, (0, 0, 1.75), "#ffd23f", emit=3.0)
        for i in range(8):
            a = i / 8 * math.tau
            L.box((0.08, 0.08, 0.7), (math.cos(a) * 1.55, math.sin(a) * 1.55, 0),
                  "#fff3b0", emit=3.0, rot=(0, 0, a))
    body.rotation_euler = (0, 0, 0)


# ------------------------------------------------------------------ potions
def potion(p):
    c = col(p["color"], "#ff6fd8")
    tier = p.get("tier", "Common")
    rank = ["Common", "Rare", "Epic", "Legendary", "Mythical", "Secret"].index(tier)
    glass = "#dff6ff"
    if rank <= 1:      # round flask
        L.sphere(1.0, (0, 0, 0), glass, subdiv=3, smooth=True, alpha=0.22, rough=0.05)
        L.sphere(0.9, (0, 0, -0.08), c, subdiv=3, smooth=True, emit=0.6, scale=(1, 1, 0.85))
        L.cyl(0.32, 0.8, (0, 0, 1.1), glass, verts=16, smooth=True, alpha=0.22)
        L.cyl(0.36, 0.35, (0, 0, 1.55), "#9c6b3c", verts=16, smooth=True)
    elif rank <= 3:    # tall bottle
        L.cyl(0.75, 1.6, (0, 0, -0.1), glass, verts=20, smooth=True, alpha=0.22, bevel=0.2,
              segs=3)
        L.cyl(0.68, 1.2, (0, 0, -0.3), c, verts=20, smooth=True, emit=0.8)
        L.cyl(0.3, 0.7, (0, 0, 1.0), glass, verts=16, smooth=True, alpha=0.22)
        L.cyl(0.34, 0.3, (0, 0, 1.45), "#ffd23f" if rank == 3 else "#9c6b3c", verts=16,
              smooth=True, metal=0.6 if rank == 3 else 0)
    else:              # fancy diamond-shaped elixir
        L.sphere(1.05, (0, 0, 0), glass, subdiv=1, alpha=0.22, rough=0.05)
        L.sphere(0.92, (0, 0, -0.05), c, subdiv=1, emit=1.0)
        L.cyl(0.25, 0.9, (0, 0, 1.2), glass, verts=8, alpha=0.22)
        L.sphere(0.36, (0, 0, 1.75), "#ffd23f", subdiv=1, metal=0.7)
        L.torus(1.2, 0.06, (0, 0, 0), "#ffd23f", rot=(math.radians(75), 0, 0), emit=1.5)
    if p["color"] == "rainbow":
        for i, rc in enumerate(RAINBOW):
            L.cyl(0.7, 0.2, (0, 0, -0.85 + i * 0.2), rc, verts=20, smooth=True, emit=0.8)
    # highlight + bubbles
    L.sphere(0.16, (-0.45, -0.75, 0.35), "#ffffff", emit=2.0, subdiv=2)
    rng = random.Random(len(p["id"]))
    for _ in range(4):
        L.sphere(rng.uniform(0.06, 0.12), (rng.uniform(-.4, .4), -0.7, rng.uniform(-.5, .3)),
                 "#ffffff", emit=1.5, subdiv=1)


def render(name):
    sc = bpy.context.scene
    L.studio(ground=False, sun=3.5)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = sc.render.resolution_y = 256
    sc.cycles.samples = 48
    L.frame(lens=50, elev=24, azim=-35, margin=1.5)
    os.makedirs(OUT, exist_ok=True)
    L.render(os.path.join(OUT, name + ".png"))


if __name__ == "__main__":
    want = sys.argv[1:]
    for d in DATA["Dice"]:
        if want and d["id"] not in want:
            continue
        L.reset()
        die(d)
        render("Dice_" + d["id"])
    for p in DATA["Potions"]:
        if want and p["id"] not in want:
            continue
        L.reset()
        potion(p)
        render("Potion_" + p["id"])
