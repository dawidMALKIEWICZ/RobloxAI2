"""Mini cars, cartoon low-poly, rarer = shinier (1 unit = 1 stud).

Blender axes: front = +Y (Roblox -Z), Z up, wheels touch z = 0. Every car fits a 2.2 stud wide
lane (loop lanes are 2.3-2.4 wide). Run: <bpy python> cars.py [CarId ...]
Writes assets/meshes/Car_<id>__*.fbx and renders/cars/<id>.png + renders/cars_sheet.png
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import bpy  # noqa: E402,I001
import mlib as L  # noqa: E402
import meshkit as K  # noqa: E402

TIRE = "#26262e"
RIM = "#d9dee8"
DARK = "#2b2f3a"
GLASS = "#9fe3ff"
CHROME = "#e6ebf2"
HEAD = "#fff6c2"
TAIL = "#ff3348"


def glass(o):
    o["grp"] = "glass"
    return o


def neon(o):
    o["grp"] = "neon"
    return o


def side(points, width, color, x=0.0, bevel=0.06):
    """Side profile [(forward, up)] extruded across the car."""
    return L.prism(points, width, (x, 0, 0), color, rot=(0, 0, math.pi / 2), bevel=bevel)


def wheel(x, y, r, w, tire=TIRE, rim=RIM, z=None):
    z = r if z is None else z
    L.cyl(r, w, (x, y, z), tire, rot=(0, math.pi / 2, 0), verts=12, bevel=0.04)
    s = 1 if x > 0 else -1
    L.cyl(r * 0.55, 0.06, (x + s * w / 2, y, z), rim, rot=(0, math.pi / 2, 0), verts=8)
    L.cyl(r * 0.2, 0.08, (x + s * (w / 2 + 0.03), y, z), DARK, rot=(0, math.pi / 2, 0), verts=6)


def wheels(xw, yf, yb, r, w, **kw):
    for x in (-xw, xw):
        for y in (yf, yb):
            wheel(x, y, r, w, **kw)


def lights(y, z, xs=(-0.6, 0.6), color=HEAD, size=(0.34, 0.08, 0.2)):
    for x in xs:
        neon(L.box(size, (x, y, z), color))


def driver(y, z, helmet="#ff3b3b", visor="#2b2f3a"):
    L.sphere(0.36, (0, y, z), helmet, subdiv=2)
    L.box((0.5, 0.12, 0.18), (0, y + 0.3, z + 0.02), visor)


def spoiler(y, z, w, color, h=0.35):
    for x in (-w / 2 + 0.15, w / 2 - 0.15):
        L.box((0.1, 0.12, h), (x, y, z - h / 2), DARK)
    L.box((w, 0.45, 0.08), (0, y - 0.05, z), color, bevel=0.03)


# ------------------------------------------------------------------ cars
def buggy():
    wheels(0.85, 1.05, -1.0, 0.42, 0.34)
    L.box((1.3, 2.6, 0.22), (0, 0, 0.5), DARK, bevel=0.05)
    side([(-1.35, 0.55), (1.45, 0.55), (1.2, 0.85), (0.4, 0.95), (-1.2, 0.95)], 1.5, "#ff8a1f")
    # roll cage
    for x in (-0.6, 0.6):
        L.box((0.09, 0.09, 0.9), (x, 0.35, 1.35), "#ffd23f", rot=(math.radians(-15), 0, 0))
        L.box((0.09, 0.09, 0.9), (x, -0.75, 1.35), "#ffd23f")
        L.box((0.09, 1.2, 0.09), (x, -0.2, 1.8), "#ffd23f")
    L.box((1.3, 0.09, 0.09), (0, -0.75, 1.8), "#ffd23f")
    L.box((1.3, 0.09, 0.09), (0, 0.45, 1.75), "#ffd23f")
    driver(-0.25, 1.3, "#3b8bff")
    lights(1.47, 0.78, size=(0.26, 0.06, 0.16))
    L.box((1.0, 0.25, 0.25), (0, -1.45, 0.75), DARK)


def kart():
    wheels(0.8, 1.05, -0.95, 0.3, 0.32)
    L.box((1.25, 2.9, 0.16), (0, 0, 0.3), DARK, bevel=0.04)
    side([(-1.2, 0.3), (1.55, 0.3), (1.55, 0.5), (0.6, 0.62), (-0.2, 0.62), (-1.2, 0.55)], 1.1,
         "#ff3b3b")
    L.box((1.75, 0.25, 0.22), (0, 1.5, 0.42), "#ffffff", bevel=0.05)
    L.box((0.55, 0.6, 0.55), (0, -0.55, 0.85), DARK, bevel=0.1)
    driver(-0.45, 1.4, "#ffe03b")
    L.cyl(0.24, 0.06, (0, 0.25, 1.0), DARK, rot=(math.radians(60), 0, 0), verts=10)
    L.box((1.5, 0.18, 0.1), (0, -1.45, 0.55), "#ffffff")


def hatch():
    wheels(0.86, 1.05, -1.0, 0.36, 0.3)
    side([(-1.6, 0.35), (1.65, 0.35), (1.7, 0.75), (1.0, 0.95), (-1.6, 0.95)], 1.85, "#3ba7ff",
         bevel=0.12)
    side([(-1.5, 0.9), (0.65, 0.9), (0.2, 1.7), (-1.3, 1.7), (-1.5, 1.45)], 1.65, "#3ba7ff",
         bevel=0.12)
    glass(side([(-1.42, 0.98), (0.55, 0.98), (0.15, 1.62), (-1.22, 1.62), (-1.42, 1.4)], 1.7,
               GLASS, bevel=0.02))
    L.box((1.68, 0.2, 0.08), (0, 0.0, 1.72), "#ffffff")
    lights(1.68, 0.72)
    lights(-1.62, 0.75, color=TAIL, size=(0.3, 0.06, 0.16))
    L.box((1.95, 0.2, 0.22), (0, 1.68, 0.42), DARK, bevel=0.05)
    L.box((1.95, 0.2, 0.22), (0, -1.62, 0.42), DARK, bevel=0.05)


def pickup():
    wheels(0.86, 1.15, -1.15, 0.42, 0.34)
    side([(-1.9, 0.45), (1.85, 0.45), (1.9, 0.95), (0.9, 1.05), (-1.9, 1.05)], 1.9, "#4bdc5a",
         bevel=0.1)
    side([(-0.35, 1.0), (0.85, 1.0), (0.55, 1.75), (-0.35, 1.75)], 1.75, "#4bdc5a", bevel=0.1)
    glass(side([(-0.28, 1.08), (0.78, 1.08), (0.5, 1.68), (-0.28, 1.68)], 1.8, GLASS, bevel=0.02))
    # open bed
    L.box((1.6, 1.45, 0.08), (0, -1.12, 1.06), "#2f9b3c")
    L.box((0.6, 0.5, 0.35), (0.3, -1.2, 1.28), "#c98a4b", bevel=0.05)
    L.box((1.92, 0.12, 0.3), (0, -1.9, 0.98), "#2f9b3c")
    L.box((2.0, 0.22, 0.3), (0, 1.86, 0.55), CHROME, bevel=0.05)
    L.box((2.0, 0.22, 0.3), (0, -1.95, 0.55), CHROME, bevel=0.05)
    lights(1.9, 0.85)
    lights(-1.96, 0.85, xs=(-0.75, 0.75), color=TAIL, size=(0.2, 0.06, 0.26))
    for x in (-0.55, 0.55):
        neon(L.box((0.12, 0.12, 0.08), (x, 0.2, 1.8), "#ffb31a"))


def muscle():
    wheels(0.84, 1.2, -1.15, 0.4, 0.38)
    side([(-1.95, 0.35), (1.95, 0.35), (2.0, 0.78), (0.6, 0.9), (-1.95, 0.92)], 1.95, "#ffd23f",
         bevel=0.1)
    side([(-1.0, 0.85), (0.45, 0.85), (0.05, 1.4), (-0.85, 1.4)], 1.65, "#ffd23f", bevel=0.1)
    glass(side([(-0.92, 0.92), (0.38, 0.92), (0.02, 1.33), (-0.8, 1.33)], 1.7, GLASS, bevel=0.02))
    for x in (-0.22, 0.22):
        L.box((0.2, 2.6, 0.04), (x, 0.65, 0.93), DARK)
        L.box((0.2, 0.75, 0.04), (x, -0.45, 1.42), DARK)
    L.box((0.6, 0.7, 0.2), (0, 1.0, 0.95), DARK, bevel=0.05)
    spoiler(-1.85, 1.15, 1.8, DARK)
    L.box((2.02, 0.2, 0.22), (0, 1.97, 0.45), CHROME, bevel=0.05)
    for x in (-0.35, 0.35):
        L.cyl(0.09, 0.4, (x, -2.0, 0.42), CHROME, rot=(math.pi / 2, 0, 0), verts=8)
    lights(1.97, 0.68, xs=(-0.72, 0.72), size=(0.26, 0.06, 0.2))
    lights(-1.97, 0.72, xs=(-0.65, 0.65), color=TAIL, size=(0.45, 0.06, 0.12))


def sports():
    wheels(0.86, 1.2, -1.15, 0.37, 0.36, rim="#2b2f3a")
    side([(-1.95, 0.3), (2.0, 0.3), (2.05, 0.5), (0.9, 0.75), (-1.95, 0.85)], 1.95, "#ff2d55",
         bevel=0.12)
    side([(-0.9, 0.75), (0.95, 0.75), (0.05, 1.3), (-0.75, 1.28)], 1.6, "#ff2d55", bevel=0.12)
    glass(side([(-0.82, 0.8), (0.86, 0.8), (0.04, 1.23), (-0.7, 1.22)], 1.65, "#2b3a55",
               bevel=0.02))
    spoiler(-1.8, 1.2, 1.9, "#1c1c24", h=0.4)
    L.box((1.4, 0.4, 0.06), (0, 1.3, 0.72), "#1c1c24")
    for x in (-0.99, 0.99):
        L.box((0.06, 0.9, 0.18), (x, -0.4, 0.55), "#1c1c24")
    lights(2.0, 0.55, xs=(-0.7, 0.7), color="#e6faff", size=(0.4, 0.06, 0.1))
    lights(-1.97, 0.72, xs=(-0.6, 0.6), color=TAIL, size=(0.55, 0.06, 0.08))
    neon(L.box((1.5, 2.8, 0.04), (0, 0, 0.22), "#ff4f86"))   # under-glow


def monster():
    wheels(0.78, 1.05, -1.05, 0.68, 0.5, rim="#ffe03b")
    L.box((1.0, 2.6, 0.25), (0, 0, 0.72), DARK)
    for y in (1.05, -1.05):
        L.box((1.6, 0.18, 0.18), (0, y, 0.72), "#8a8f9a")
        for x in (-0.45, 0.45):
            L.cyl(0.08, 0.6, (x, y, 1.0), "#ffe03b", verts=6)
    side([(-1.6, 1.15), (1.65, 1.15), (1.7, 1.55), (0.7, 1.65), (-1.6, 1.65)], 1.7, "#9b4dff",
         bevel=0.12)
    side([(-0.85, 1.6), (0.6, 1.6), (0.3, 2.25), (-0.75, 2.25)], 1.5, "#9b4dff", bevel=0.1)
    glass(side([(-0.78, 1.68), (0.53, 1.68), (0.27, 2.18), (-0.7, 2.18)], 1.55, GLASS,
               bevel=0.02))
    for x in (-0.45, -0.15, 0.15, 0.45):
        neon(L.box((0.16, 0.16, 0.1), (x, 0.0, 2.32), "#ffe03b"))
    lights(1.7, 1.42, xs=(-0.55, 0.55), size=(0.3, 0.06, 0.2))
    lights(-1.62, 1.45, xs=(-0.55, 0.55), color=TAIL, size=(0.3, 0.06, 0.15))
    for x in (-0.86, 0.86):
        L.box((0.12, 1.3, 0.3), (x, -0.1, 1.35), "#ffe03b", bevel=0.04)


def f1():
    wheels(0.82, 1.35, -1.2, 0.36, 0.42)
    side([(-1.7, 0.25), (2.0, 0.25), (2.05, 0.38), (0.4, 0.62), (-0.6, 0.85), (-1.7, 0.75)], 0.85,
         "#ffffff", bevel=0.08)
    L.box((2.1, 0.5, 0.06), (0, 2.0, 0.28), "#e10600", bevel=0.02)      # front wing
    for x in (-1.0, 1.0):
        L.box((0.06, 0.55, 0.25), (x, 2.0, 0.36), "#e10600")
    L.box((1.9, 0.45, 0.08), (0, -1.75, 1.05), "#e10600", bevel=0.02)   # rear wing
    for x in (-0.9, 0.9):
        L.box((0.06, 0.5, 0.5), (x, -1.75, 0.82), "#e10600")
    for x in (-0.62, 0.62):
        L.box((0.4, 1.4, 0.35), (x, -0.2, 0.42), "#e10600", bevel=0.08)  # side pods
    L.box((0.06, 1.6, 0.04), (0, 0.6, 0.66), "#e10600")
    driver(-0.15, 0.95, "#ffd23f")
    L.box((0.6, 0.12, 0.08), (0, 0.1, 1.08), DARK)                       # halo
    neon(L.box((0.2, 0.06, 0.12), (0, -1.95, 0.5), TAIL))


def hover():
    side([(-1.8, 0.45), (1.6, 0.45), (2.0, 0.7), (1.5, 0.95), (-1.8, 1.0)], 1.9, "#e8f4ff",
         bevel=0.14)
    glass(L.sphere(0.85, (0, -0.1, 1.05), "#7ce7ff", scale=(0.95, 1.5, 0.6), subdiv=2))
    for x in (-1.0, 1.0):
        L.box((0.25, 2.6, 0.3), (x * 0.95, -0.1, 0.55), "#38d6ff", bevel=0.08)
        neon(L.box((0.08, 2.4, 0.08), (x * 1.08, -0.1, 0.55), "#38d6ff"))
    for y in (1.0, -1.1):
        for x in (-0.65, 0.65):
            L.cyl(0.32, 0.18, (x, y, 0.3), "#1c2a3a", verts=10)
            neon(L.cyl(0.24, 0.05, (x, y, 0.2), "#7cf3ff", verts=10))
    lights(1.95, 0.72, xs=(-0.55, 0.55), color="#bff6ff", size=(0.4, 0.06, 0.1))
    neon(L.box((1.3, 0.06, 0.12), (0, -1.82, 0.75), "#ff4f9a"))
    L.box((1.6, 0.35, 0.06), (0, -1.6, 1.2), "#38d6ff", bevel=0.02)


def rocket():
    side([(-1.8, 0.35), (1.7, 0.35), (2.1, 0.55), (1.6, 0.9), (-1.8, 1.05)], 1.7, "#1c1c28",
         bevel=0.14)
    for x in (-0.3, 0.3):
        L.box((0.18, 3.6, 0.04), (x, 0.0, 1.03), "#ffd23f")
    glass(side([(-0.7, 0.95), (0.7, 0.95), (0.15, 1.42), (-0.55, 1.42)], 1.3, "#ffb31a",
               bevel=0.02))
    wheels(0.86, 1.15, -1.1, 0.35, 0.32, rim="#ffd23f")
    for x in (-1.0, 1.0):   # wings
        L.prism([(-1.3, 0.0), (0.4, 0.0), (-0.9, 0.5)], 0.08, (x * 0.62, 0, 0.75), "#ffd23f",
                rot=(0, 0, math.pi / 2))
    for x in (-0.45, 0.45):  # thrusters
        L.cyl(0.3, 0.7, (x, -1.95, 0.75), "#5b6273", rot=(math.pi / 2, 0, 0), verts=10)
        neon(L.cyl(0.22, 0.08, (x, -2.32, 0.75), "#ff7b1a", rot=(math.pi / 2, 0, 0), verts=10))
    lights(2.0, 0.62, xs=(-0.5, 0.5), color="#fff3b0", size=(0.35, 0.06, 0.1))
    neon(L.box((1.4, 3.0, 0.04), (0, 0, 0.18), "#ffb31a"))


CARS = {"Buggy": buggy, "GoKart": kart, "Hatchback": hatch, "Pickup": pickup, "Muscle": muscle,
        "Sports": sports, "Monster": monster, "F1": f1, "Hover": hover, "Rocket": rocket}


def check(cid):
    pts = []
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and not o.name.startswith("_"):
            pts += [o.matrix_world @ v.co for v in o.data.vertices]
    w = max(abs(p.x) for p in pts) * 2
    ln = max(p.y for p in pts) - min(p.y for p in pts)
    h = max(p.z for p in pts)
    print(f"SIZE {cid}: width {w:.2f} length {ln:.2f} height {h:.2f}"
          + ("  <-- TOO WIDE" if w > 2.25 else ""))


def render(cid):
    L.studio(ground=True, ground_color="#d8e3ee")
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = 520
    sc.cycles.samples = 32
    L.frame(lens=50, elev=24, azim=145, margin=1.9)
    L.render(os.path.join(ROOT, "renders", "cars", cid + ".png"))


if __name__ == "__main__":
    want = sys.argv[1:]
    for cid, fn in CARS.items():
        if want and cid not in want:
            continue
        L.reset()
        fn()
        check(cid)
        K.bake("Car_" + cid)
        render(cid)
