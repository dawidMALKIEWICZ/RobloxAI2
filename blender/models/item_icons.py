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
# the shop icons show the same 3D dice the game uses (blender/models/dice.py)
sys.path.insert(0, HERE)
import dice as D  # noqa: E402


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


def fit(cam, fill=0.86):
    """Moves the camera along its view axis so every vertex fills `fill` of the frame."""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in sc.objects:
        if o.type == "MESH" and not o.name.startswith("_"):
            me = o.evaluated_get(dg).to_mesh()
            pts += [o.matrix_world @ v.co for v in me.vertices]
    centre = sum(pts, Vector()) / len(pts)
    fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
    for _ in range(12):
        bpy.context.view_layer.update()
        ext = 0.0
        for p in pts:
            c = world_to_camera_view(sc, cam, p)
            ext = max(ext, abs(c.x - 0.5) * 2, abs(c.y - 0.5) * 2)
        d = (cam.location - centre).length
        cam.location = centre - fwd * d * (ext / fill) ** 0.85


def render(name, margin=1.5):
    sc = bpy.context.scene
    L.studio(ground=False, sun=3.5)
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = sc.render.resolution_y = 256
    sc.cycles.samples = 48
    cam = L.frame(lens=50, elev=24, azim=-35, margin=margin)
    fit(cam)
    os.makedirs(OUT, exist_ok=True)
    L.render(os.path.join(OUT, name + ".png"))


if __name__ == "__main__":
    want = sys.argv[1:]
    for d in DATA["Dice"]:
        if want and d["id"] not in want:
            continue
        D.build(d["id"])
        # a soft rim light from behind makes dark dice read on dark UI cards
        ld = bpy.data.lights.new("rim", "SUN")
        ld.energy = 2.2
        o = bpy.data.objects.new("rim", ld)
        bpy.context.scene.collection.objects.link(o)
        o.rotation_euler = (math.radians(-60), 0, math.radians(20))
        render("Dice_" + d["id"], margin=1.18)
    for p in DATA["Potions"]:
        if want and p["id"] not in want:
            continue
        L.reset()
        potion(p)
        render("Potion_" + p["id"])
