"""Generates src/Workspace/Map.model.json - cartoony low-poly world.

Octagon hub island with 4 shop buildings + 8 square player plots (building grid) around it,
all joined by bridges. Everything SmoothPlastic / Neon for a clean cartoon look.
"""
import math
import random

from rbx import CF, Inst, add, mul, norm, part, sub, text_sign, write_model

TOP = 100.0
CELL = 10
MAX_CELLS = 15
HUB_R = 80             # octagon inradius
RING = 360
PLOT_W, PLOT_D = 200, 220
GRID_Z = 10            # grid centre (local z) - hub side is -Z
PLOT_COLORS = ["#ff5a5a", "#ff9f1a", "#ffd83b", "#5ad65a", "#3bd1ff", "#4b7bff", "#b54dff",
               "#ff5fc8"]
GRASS = "#74d65a"
GRASS_DARK = "#5fc048"
DIRT = "#a8713e"
ROCK = "#8d8f9e"
ROCK_DARK = "#6f7181"


class B:
    def __init__(self, base, parent):
        self.base = base
        self.parent = parent

    def cf(self, x, y, z, rot=None):
        c = self.base * CF(x, y, z)
        return c * rot if rot else c

    def box(self, name, size, pos, color, mat="SmoothPlastic", rot=None, **kw):
        p = part(name, size, self.cf(*pos, rot=rot), color, mat, **kw)
        self.parent.add(p)
        return p

    def wedge(self, name, size, pos, color, rot=None, **kw):
        p = part(name, size, self.cf(*pos, rot=rot), color, "SmoothPlastic", cls="WedgePart",
                 **kw)
        self.parent.add(p)
        return p

    def ball(self, name, d, pos, color, mat="SmoothPlastic", **kw):
        p = part(name, (d, d, d), self.cf(*pos), color, mat, shape="Ball", **kw)
        self.parent.add(p)
        return p

    def cyl(self, name, r, h, pos, color, mat="SmoothPlastic", **kw):
        p = part(name, (h, r * 2, r * 2), self.cf(*pos, rot=CF.rz(math.pi / 2)), color, mat,
                 shape="Cylinder", **kw)
        self.parent.add(p)
        return p

    def sign(self, name, text, pos, size, bg, rot=None, **kw):
        p = text_sign(name, text, 40, self.cf(*pos, rot=rot), size, bg, **kw)
        self.parent.add(p)
        return p


# ------------------------------------------------------------------ low poly props
def lp_tree(b, x, z, s=1.0, leaf="#4cc23a", leaf2="#3fae2f", name="Tree"):
    m = Inst("Model", name)
    tb = B(b.base, m)
    tb.box("Trunk", (1.6 * s, 6 * s, 1.6 * s), (x, 3 * s, z), "#8a5a2b", attrs={"Role": "Trunk"})
    tb.box("Leaves1", (9 * s, 4.5 * s, 9 * s), (x, 7.5 * s, z), leaf, rot=CF.ry(0.3),
           attrs={"Role": "Leaves"})
    tb.box("Leaves2", (6.5 * s, 4 * s, 6.5 * s), (x, 11.2 * s, z), leaf2,
           rot=CF.ry(0.3 + math.pi / 4), attrs={"Role": "Leaves"})
    tb.box("Leaves3", (3.6 * s, 3 * s, 3.6 * s), (x, 14.2 * s, z), leaf, rot=CF.ry(0.3),
           attrs={"Role": "Leaves"})
    b.parent.add(m)


def lp_rock(b, x, z, s=1.0, color=ROCK, rng=None):
    rng = rng or random.Random(int(x * 7 + z * 13))
    b.box("Rock", (4 * s, 2.6 * s, 3.4 * s), (x, 1.1 * s, z), color,
          rot=CF.angles(rng.uniform(-0.2, 0.2), rng.uniform(0, 3), rng.uniform(-0.2, 0.2)))


def lp_bush(b, x, z, s=1.0, color="#5fd13f"):
    b.box("Bush", (3.6 * s, 2.6 * s, 3.6 * s), (x, 1.2 * s, z), color, rot=CF.ry(0.6))
    b.box("Bush2", (2.6 * s, 2.2 * s, 2.6 * s), (x + 1.2 * s, 1.6 * s, z + 0.6 * s), color,
          rot=CF.ry(1.4))


def square_island(m, cf, w, d, grass=GRASS, seed=0, roles=True):
    """Flat-topped square island with stepped low-poly cliffs underneath."""
    rng = random.Random(seed)
    b = B(cf, m)
    ra = (lambda r: {"Role": r}) if roles else (lambda r: None)
    b.box("Grass", (w, 3, d), (0, -1.5, 0), grass, attrs=ra("Grass"))
    b.box("GrassLip", (w + 1.6, 1.4, d + 1.6), (0, -3.4, 0), GRASS_DARK if grass == GRASS else grass,
          attrs=ra("Grass"))
    b.box("Dirt", (w - 2, 7, d - 2), (0, -7.5, 0), DIRT, attrs=ra("Dirt"))
    steps = [(0.86, 7), (0.66, 7), (0.44, 7), (0.22, 6)]
    y = -11
    for i, (k, h) in enumerate(steps):
        y -= h / 2
        b.box(f"Rock{i}", (w * k, h, d * k), (rng.uniform(-3, 3), y, rng.uniform(-3, 3)),
              ROCK if i % 2 == 0 else ROCK_DARK, rot=CF.ry(rng.uniform(-0.08, 0.08)),
              attrs=ra("Rock"))
        y -= h / 2
    for i in range(10):
        x = rng.uniform(-0.45, 0.45) * w
        z = rng.uniform(-0.45, 0.45) * d
        s = rng.uniform(5, 11)
        b.box(f"Chunk{i}", (s, s * 1.3, s), (x, -13 - rng.uniform(0, 10), z), ROCK_DARK,
              rot=CF.angles(rng.uniform(-.4, .4), rng.uniform(0, 3), rng.uniform(-.4, .4)),
              attrs=ra("Rock"))


def octagon_island(m, center, r, seed=1):
    rng = random.Random(seed)
    b = B(CF(*center), m)
    side = 2 * r
    for k in range(2):
        rot = CF.ry(k * math.pi / 4)
        dy = 0.05 * k  # never let the two squares share a top face
        b.box("Grass", (side, 3, side), (0, -1.5 - dy, 0), GRASS, rot=rot)
        b.box("GrassLip", (side + 1.6, 1.4, side + 1.6), (0, -3.4 - dy, 0), GRASS_DARK, rot=rot)
        b.box("Dirt", (side - 2, 7, side - 2), (0, -7.5 - dy, 0), DIRT, rot=rot)
    y = -11
    for i, (k, h) in enumerate([(0.86, 7), (0.66, 7), (0.44, 7), (0.22, 6)]):
        y -= h / 2
        for j in range(2):
            b.box(f"Rock{i}", (side * k, h, side * k), (0, y - 0.05 * j, 0),
                  ROCK if i % 2 == 0 else ROCK_DARK,
                  rot=CF.ry(j * math.pi / 4 + i * 0.2))
        y -= h / 2
    for i in range(8):
        a = rng.uniform(0, math.tau)
        dd = rng.uniform(0.2, 0.6) * r
        s = rng.uniform(6, 12)
        b.box("Chunk", (s, s * 1.3, s), (math.cos(a) * dd, -14 - rng.uniform(0, 10), math.sin(a) * dd),
              ROCK_DARK, rot=CF.angles(rng.uniform(-.4, .4), rng.uniform(0, 3), 0))


def bridge(parent, name, p1, p2, width=12):
    m = Inst("Model", name)
    d = sub(p2, p1)
    L = math.hypot(d[0], d[2])
    f = norm((d[0], 0, d[2]))
    base = CF.look(((p1[0] + p2[0]) / 2, TOP, (p1[2] + p2[2]) / 2), f)
    b = B(base, m)
    n = max(4, int(L / 3))
    step = L / n
    for i in range(n):
        lz = -L / 2 + step * (i + 0.5)
        b.box(f"Plank{i}", (width, 0.8, step * 0.86), (0, -0.33, lz),
              "#d99a5b" if i % 2 else "#c9874a")
    for side in (-1, 1):
        b.box("Beam", (1.0, 1.2, L), (side * (width / 2 - 0.4), -1.3, 0), "#8a5a2b")
    posts = max(2, int(L / 16) + 1)
    for i in range(posts):
        lz = -L / 2 + L * i / (posts - 1)
        for side in (-1, 1):
            b.box("Post", (1.2, 4.6, 1.2), (side * (width / 2 + 0.3), 1.6, lz), "#8a5a2b")
            b.box("PostCap", (1.6, 0.6, 1.6), (side * (width / 2 + 0.3), 4.1, lz), "#ffffff")
    for side in (-1, 1):
        b.box("Rail", (0.6, 0.6, L), (side * (width / 2 + 0.3), 3.2, 0), "#f2d29b")
    parent.add(m)


# ------------------------------------------------------------------ shops
def shop_building(parent, key, title, c_main, c_roof, cf, prop):
    m = Inst("Model", f"Shop_{key}", attrs={"Shop": key})
    b = B(cf, m)
    W, D, H = 30, 20, 14
    b.box("Floor", (W + 4, 1, D + 6), (0, 0.5, -2), "#e8e2d6")
    b.box("Back", (W, H, 2), (0, H / 2 + 1, D / 2 - 1), c_main)
    b.box("SideL", (2, H, D), (-W / 2 + 1, H / 2 + 1, 0), c_main)
    b.box("SideR", (2, H, D), (W / 2 - 1, H / 2 + 1, 0), c_main)
    b.box("FrontL", (7, H, 2), (-W / 2 + 3.5, H / 2 + 1, -D / 2 + 1), c_main)
    b.box("FrontR", (7, H, 2), (W / 2 - 3.5, H / 2 + 1, -D / 2 + 1), c_main)
    b.box("FrontTop", (W - 14, 4, 2), (0, H - 1, -D / 2 + 1), c_main)
    b.box("Window", (W - 14.2, H - 4.2, 0.4), (0, (H - 4) / 2 + 1, -D / 2 + 1.2), "#bfefff",
          "Glass", transparency=0.55, collide=False)
    b.box("Inside", (W - 4, 0.2, D - 4), (0, 1.1, 0), "#fff6e0")
    # gable roof from two wedges
    rh = 7
    b.wedge("RoofL", (W + 4, rh, D / 2 + 2), (0, H + 1 + rh / 2, -(D / 4 + 1)), c_roof)
    b.wedge("RoofR", (W + 4, rh, D / 2 + 2), (0, H + 1 + rh / 2, D / 4 + 1), c_roof,
            rot=CF.ry(math.pi))
    b.box("RoofEdge", (W + 4.4, 1, D + 4.4), (0, H + 1.2, 0), "#ffffff")
    # awning stripes over the door
    for i in range(6):
        b.box(f"Awning{i}", (16 / 6, 0.5, 5), (-8 + 16 / 6 * (i + 0.5), H - 3.4, -D / 2 - 2.2),
              c_roof if i % 2 == 0 else "#ffffff", rot=CF.rx(math.radians(20)))
    b.sign("Sign", title, (0, H + 3.2, -D / 2 - 1.6), (24, 5, 1), c_roof, rot=CF.rx(0.15))
    pp = b.box("PromptPart", (12, 8, 2), (0, 5, -D / 2 - 5), "#ffffff", transparency=1,
               collide=False)
    pp.attrs["Shop"] = key
    pp.add(Inst("ProximityPrompt", "Prompt", {
        "ActionText": "Open", "ObjectText": title.title(), "HoldDuration": 0,
        "MaxActivationDistance": 18, "RequiresLineOfSight": False, "KeyboardKeyCode": "E"}))
    b.box(f"TP_{key}", (4, 1, 4), (0, 3, -D / 2 - 12), "#ffffff", transparency=1,
          collide=False, touch=False, rot=CF.ry(math.pi))
    prop(b, H, D)
    parent.add(m)
    return m


def prop_dice(b, H, D):
    b.box("BigDice", (8, 8, 8), (0, H + 13, 0), "#ffffff", rot=CF.angles(0.4, 0.6, 0.2))
    for dx, dz in ((-1.8, -1.8), (1.8, 1.8), (0, 0)):
        b.box("Pip", (1.4, 1.4, 0.3), (dx * 0.6, H + 13 + dz * 0.6, -4.1), "#222222",
              rot=CF.angles(0.4, 0.6, 0.2))
    for i, c in enumerate(("#ffcc1a", "#3fa9ff", "#b54dff", "#ff3b6b")):
        b.box(f"Dice{i}", (3, 3, 3), (-9 + i * 6, 6.6, 2), c, rot=CF.ry(i * 0.5))


def prop_potion(b, H, D):
    b.ball("BigPotion", 7, (0, H + 12, 0), "#b54dff", "Neon", transparency=0.1)
    b.cyl("Neck", 1.4, 3, (0, H + 16.6, 0), "#d9a3ff", "Glass")
    b.cyl("Cork", 1.6, 1.6, (0, H + 18.6, 0), "#9c6b3c")
    b.cyl("Cauldron", 4, 4, (0, 3, 2), "#2b2b33")
    b.cyl("Brew", 3.6, 0.4, (0, 5, 2), "#7dff4f", "Neon")


def prop_car(b, H, D):
    b.cyl("Podium", 6, 1, (0, 1.6, 1), "#ffffff")
    b.cyl("PodiumGlow", 6.4, 0.6, (0, 1.2, 1), "#5cc8ff", "Neon")
    b.box("CarBody", (5, 2, 9), (0, 3.4, 1), "#ff3b3b")
    b.box("CarCab", (4.2, 1.8, 4.5), (0, 5.2, 1.5), "#9fe6ff", "Glass", transparency=0.2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            b.parent.add(part("Wheel", (1, 2.2, 2.2), b.cf(sx * 2.6, 2.6, 1 + sz * 3),
                              "#222222", shape="Cylinder"))
    b.box("RoofCar", (6, 3, 10), (0, H + 10, 0), "#ff3b3b", rot=CF.ry(0.4))
    b.box("RoofCab", (5, 2.4, 5), (0, H + 12.6, 0.4), "#9fe6ff", rot=CF.ry(0.4))


def prop_style(b, H, D):
    b.box("Palette", (12, 1, 9), (0, H + 10, 0), "#f2d29b", rot=CF.rx(-1.1))
    for i, c in enumerate(("#ff3b3b", "#3bd16b", "#3b8bff", "#ffd23b", "#b54dff")):
        a = i * 1.1
        b.box(f"Blob{i}", (2, 0.6, 2), (math.cos(a) * 3.4, H + 10 + math.sin(a) * 2.5, -1.2),
              c, rot=CF.rx(-1.1))
    for i, c in enumerate(("#ff3b3b", "#3bd16b", "#3b8bff", "#ffd23b")):
        b.cyl(f"Bucket{i}", 1.6, 2.6, (-9 + i * 6, 2.3, 3), "#d0d0d8")
        b.cyl(f"Paint{i}", 1.4, 0.3, (-9 + i * 6, 3.6, 3), c)


SHOPS = [
    ("Cars", "CAR DEALER", "#3b8bff", "#1f5fc9", prop_car),
    ("Styles", "ISLAND STYLES", "#ff6fb5", "#c2307c", prop_style),
    ("Potions", "POTIONS", "#a94dff", "#6a1fc9", prop_potion),
    ("Dice", "DICE SHOP", "#ffc61a", "#e58a00", prop_dice),
]


def hub(parent):
    m = Inst("Model", "Hub")
    octagon_island(m, (0, TOP, 0), HUB_R)
    b = B(CF(0, TOP, 0), m)
    for k in range(2):
        b.box("Plaza", (44, 0.7, 44), (0, 0.15 + 0.03 * k, 0), "#efe6d2",
              rot=CF.ry(k * math.pi / 4))
    for k in range(8):
        a = k * math.tau / 8
        r = HUB_R / 2 + 11
        m.add(part(f"Path{k}", (HUB_R - 22, 0.6, 12),
                   CF(math.cos(a) * r, TOP + 0.12, math.sin(a) * r) * CF.ry(-a), "#efe6d2"))
    # low poly fountain
    for k in range(2):
        b.box("FountainBase", (16, 2.4, 16), (0, 1.2 + 0.03 * k, 0), "#c9c2b3",
              rot=CF.ry(k * math.pi / 4))
        b.box("FountainWater", (14, 0.4, 14), (0, 2.3 + 0.03 * k, 0), "#4fc8ff",
              rot=CF.ry(k * math.pi / 4), transparency=0.15)
    b.box("FountainPillar", (2.4, 6, 2.4), (0, 4.5, 0), "#c9c2b3", rot=CF.ry(0.785))
    b.box("FountainTop", (6, 1, 6), (0, 7.5, 0), "#c9c2b3", rot=CF.ry(0.785))
    b.ball("FountainSpout", 2.4, (0, 8.6, 0), "#4fc8ff", "Neon", transparency=0.2)
    m.add(Inst("SpawnLocation", "HubSpawn", {
        "Anchored": True, "Size": {"Vector3": [8, 1, 8]}, "CFrame": CF(0, TOP + 0.3, 16).json(),
        "Transparency": 1, "CanCollide": False, "Neutral": True, "Duration": 0}))
    # title sign
    ta = math.radians(112.5)
    tcf = CF.look((math.cos(ta) * 30, TOP, math.sin(ta) * 30), (-math.cos(ta), 0, -math.sin(ta)))
    tb = B(tcf, m)
    tb.box("TitlePostL", (1.6, 20, 1.6), (-18, 10, 0), "#8a5a2b")
    tb.box("TitlePostR", (1.6, 20, 1.6), (18, 10, 0), "#8a5a2b")
    tb.box("TitleFrame", (42, 11, 1.0), (0, 21, 0), "#ffffff")
    tb.sign("Title", "TRACK RNG", (0, 21, -0.7), (40, 9, 0.5), "#ff3b6b")
    tb.sign("TitleBack", "TRACK RNG", (0, 21, 0.7), (40, 9, 0.5), "#ff3b6b", rot=CF.ry(math.pi))
    for k, (key, title, c1, c2, prop) in enumerate(SHOPS):
        a = math.radians(22.5 + 90 * k)
        pos = (math.cos(a) * 54, TOP, math.sin(a) * 54)
        shop_building(m, key, title, c1, c2, CF.look(pos, (-math.cos(a), 0, -math.sin(a))), prop)
    rng = random.Random(3)
    for k in range(16):
        a = math.radians(22.5 + 45 * k / 2) + rng.uniform(-0.06, 0.06)
        if (k % 2) == 0:
            continue
        d = rng.uniform(64, 74)
        lp_tree(b, math.cos(a) * d, math.sin(a) * d, rng.uniform(0.9, 1.2))
    parent.add(m)


# ------------------------------------------------------------------ plots
DECOR_SPOTS = [(-88, -60), (-90, -20), (-88, 25), (-90, 65), (88, -60), (90, -20), (88, 25),
               (90, 65), (-55, 98), (-15, 100), (25, 98), (65, 100), (-60, -95), (60, -95)]


def plot(parent, idx, center):
    cx, cz = center
    col = PLOT_COLORS[idx]
    cf = CF.look((cx, TOP, cz), (-cx, 0, -cz))
    m = Inst("Model", f"Plot{idx + 1}", attrs={"PlotIndex": idx + 1, "PlotColor": col})
    b = B(cf, m)
    b.box("Pivot", (1, 1, 1), (0, 0.5, 0), "#ffffff", transparency=1, collide=False, touch=False)
    island = Inst("Model", "Island")
    m.add(island)
    square_island(island, cf, PLOT_W, PLOT_D, seed=idx + 10)
    # locked build area (darker) - the unlocked pad is built by the server
    b.box("GridArea", (MAX_CELLS * CELL + 2, 0.3, MAX_CELLS * CELL + 2), (0, 0.05, GRID_Z),
          GRASS_DARK, attrs={"Role": "Grass"})
    b.box("GridOrigin", (1, 1, 1), (0, 0, GRID_Z), "#ffffff", transparency=1, collide=False,
          touch=False)
    # border tiles in plot colour
    for side in (-1, 1):
        b.box("BorderX", (1.2, 0.8, PLOT_D - 4), (side * (PLOT_W / 2 - 1.2), 0.2, 0), col,
              attrs={"Role": "Accent"})
        b.box("BorderZ", (PLOT_W - 4, 0.8, 1.2), (0, 0.2, side * (PLOT_D / 2 - 1.2)), col,
              attrs={"Role": "Accent"})
    # spawn + owner sign arch on the hub side
    b.box("SpawnPad", (10, 0.8, 10), (0, 0.2, -92), "#ffffff", rot=CF.ry(math.pi / 4))
    b.box("SpawnPadInner", (7, 0.9, 7), (0, 0.25, -92), col, rot=CF.ry(math.pi / 4),
          attrs={"Role": "Accent"})
    b.box("SpawnPoint", (2, 1, 2), (0, 3, -92), "#ffffff", transparency=1, collide=False,
          touch=False)
    b.box("SignPostL", (1.2, 12, 1.2), (-8.5, 6, -104), "#8a5a2b")
    b.box("SignPostR", (1.2, 12, 1.2), (8.5, 6, -104), "#8a5a2b")
    b.box("SignFrame", (19, 6, 0.6), (0, 11, -104), "#ffffff")
    s = b.sign("OwnerSign", f"Empty Plot {idx + 1}", (0, 11, -104.4), (18, 5, 0.6), col)
    s.attrs["Role"] = "Accent"
    b.sign("OwnerSignBack", f"PLOT {idx + 1}", (0, 11, -103.6), (18, 5, 0.6), col,
           rot=CF.ry(math.pi))
    decor = Inst("Model", "Decor")
    db = B(cf, decor)
    rng = random.Random(idx)
    for k, (x, z) in enumerate(DECOR_SPOTS):
        if k % 3 == 2:
            lp_rock(db, x, z, rng.uniform(0.9, 1.4), rng=rng)
            lp_bush(db, x + 5, z + 3, 0.9)
        else:
            lp_tree(db, x, z, rng.uniform(0.85, 1.15))
    m.add(decor)
    m.add(Inst("Folder", "Track"))
    m.add(Inst("Folder", "Pad"))
    parent.add(m)
    return cf


def exit_point(cf, w, d, direction):
    """Point on the rectangle edge of a plot (local half sizes) towards a world direction."""
    inv = cf.inverse()
    ld = inv.vector(direction)
    t = min((w / 2) / abs(ld[0]) if abs(ld[0]) > 1e-6 else 1e9,
            (d / 2) / abs(ld[2]) if abs(ld[2]) > 1e-6 else 1e9)
    return cf.point((ld[0] * t, 0, ld[2] * t))


def build():
    root = Inst("Folder", "Map")
    hub(root)
    plots = Inst("Folder", "Plots")
    root.add(plots)
    cfs = []
    for i in range(8):
        a = i * math.tau / 8
        cfs.append(plot(plots, i, (math.cos(a) * RING, math.sin(a) * RING)))
    bridges = Inst("Folder", "Bridges")
    root.add(bridges)
    for i in range(8):
        a = i * math.tau / 8
        u = (math.cos(a), 0, math.sin(a))
        p_plot = exit_point(cfs[i], PLOT_W, PLOT_D, neg3(u))
        bridge(bridges, f"HubBridge{i + 1}", mul(u, HUB_R - 2), add(p_plot, mul(u, 2)))
        j = (i + 1) % 8
        c1, c2 = cfs[i].p, cfs[j].p
        dv = norm(sub(c2, c1))
        e1 = exit_point(cfs[i], PLOT_W, PLOT_D, dv)
        e2 = exit_point(cfs[j], PLOT_W, PLOT_D, neg3(dv))
        bridge(bridges, f"RingBridge{i + 1}_{j + 1}", sub(e1, mul(dv, 2)), add(e2, mul(dv, 2)))
    root.add(part("VoidCatcher", (2048, 4, 2048), CF(0, TOP - 140, 0), "#000000",
                  transparency=1, collide=False))
    for ix in (-1, 0, 1):
        for iz in (-1, 0, 1):
            root.add(part("Ocean", (2048, 2, 2048), CF(ix * 2048, TOP - 170, iz * 2048),
                          "#4cc3ff", transparency=0.1, touch=False))
    return root


def neg3(v):
    return (-v[0], -v[1], -v[2])


if __name__ == "__main__":
    write_model(build(), "Workspace/Map.model.json")
