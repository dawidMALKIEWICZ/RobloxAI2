"""Generates cars and island style decorations.

src/ReplicatedStorage/Assets/Cars.model.json        - 10 car models (pivot = "Root", faces -Z)
src/ReplicatedStorage/Assets/IslandStyles.model.json - 8 styles (attributes + Decor model in plot
                                                       local space: origin = island top centre,
                                                       -Z towards the hub)
"""
import math
import random

from rbx import CF, Inst, part, write_model

# ------------------------------------------------------------------ cars
CAR_SCALE = 0.42  # mini cars for the 6 stud wide mini track


def cartoon(mat):
    """Only flat cartoon materials: textured ones become SmoothPlastic."""
    return mat if mat in ("Neon", "Glass", "ForceField") else "SmoothPlastic"



class Kit:
    def __init__(self, m, s=1.0):
        self.m = m
        self.s = s

    def _cf(self, pos, rot=None):
        cf = CF(*(c * self.s for c in pos))
        return cf * rot if rot else cf

    def _sz(self, size):
        return tuple(c * self.s for c in size)

    def box(self, name, size, pos, color, mat="SmoothPlastic", rot=None, **kw):
        p = part(name, self._sz(size), self._cf(pos, rot), color, cartoon(mat), collide=False,
                 **kw)
        self.m.add(p)
        return p

    def wedge(self, name, size, pos, color, mat="SmoothPlastic", rot=None, **kw):
        p = part(name, self._sz(size), self._cf(pos, rot), color, cartoon(mat), cls="WedgePart",
                 collide=False, **kw)
        self.m.add(p)
        return p

    def wheel(self, pos, r, w, tire="#2a2a30", rim="#e6e6e6"):
        self.m.add(part("Tire", self._sz((w, r * 2, r * 2)), self._cf(pos), tire,
                        shape="Cylinder", collide=False))
        self.m.add(part("Rim", self._sz((w + 0.1, r * 1.1, r * 1.1)), self._cf(pos), rim,
                        shape="Cylinder", collide=False))

    def ball(self, name, d, pos, color, mat="SmoothPlastic", **kw):
        p = part(name, self._sz((d, d, d)), self._cf(pos), color, cartoon(mat), shape="Ball",
                 collide=False, **kw)
        self.m.add(p)
        return p

    def cyl(self, name, r, length, pos, color, mat="SmoothPlastic", axis="z", **kw):
        rot = {"x": CF(), "y": CF.rz(math.pi / 2), "z": CF.ry(math.pi / 2)}[axis]
        p = part(name, self._sz((length, r * 2, r * 2)), self._cf(pos, rot), color, cartoon(mat),
                 shape="Cylinder", collide=False, **kw)
        self.m.add(p)
        return p


def wheels4(k, x, zf, zb, r, w, y=None, **kw):
    y = r if y is None else y
    for sx in (-1, 1):
        k.wheel((sx * x, y, zf), r, w, **kw)
        k.wheel((sx * x, y, zb), r, w, **kw)


def driver(k, pos, shirt="#3b6bff"):
    x, y, z = pos
    k.box("DriverBody", (1.8, 1.8, 1.2), (x, y + 0.9, z), shirt)
    k.box("DriverHead", (1.3, 1.3, 1.3), (x, y + 2.4, z), "#ffcc99")
    k.box("Helmet", (1.5, 0.8, 1.5), (x, y + 3.1, z), "#ffffff")


def car_buggy(k):
    c = "#ff8a1f"
    k.box("Floor", (6, 0.6, 11), (0, 2.0, 0), "#3a3a42")
    k.box("Nose", (5, 1.4, 3), (0, 2.6, -4.5), c)
    k.wedge("NoseSlope", (5, 1.0, 2), (0, 3.8, -4.0), c, rot=CF.ry(math.pi))
    k.box("Seat", (3, 1.6, 2.4), (0, 3.1, 0.8), "#222222")
    driver(k, (0, 2.3, 0.2), "#ff3b3b")
    for sx in (-1, 1):
        k.box("Cage", (0.4, 5, 0.4), (sx * 2.4, 4.6, 2.2), "#d9d9d9", "Metal")
        k.box("CageF", (0.4, 4, 0.4), (sx * 2.4, 4.1, -1.5), "#d9d9d9", "Metal",
              rot=CF.rx(math.radians(-15)))
    k.box("CageTop", (5.2, 0.4, 4.2), (0, 7.0, 0.4), "#d9d9d9", "Metal")
    k.box("Engine", (3.4, 2, 2.2), (0, 3.3, 4.4), "#555555", "Metal")
    wheels4(k, 3.4, -3.8, 3.8, 1.8, 1.4)


def car_kart(k):
    c = "#ff2d2d"
    k.box("Base", (6, 0.6, 10), (0, 1.0, 0), c)
    k.wedge("Front", (6, 1.0, 2.4), (0, 1.8, -3.9), c, rot=CF.ry(math.pi))
    k.box("Bumper", (7, 0.6, 1), (0, 1.0, -5.3), "#222222")
    k.box("Seat", (2.6, 2.2, 1.0), (0, 2.4, 2.0), "#222222")
    driver(k, (0, 1.3, 1.0), "#ffd23b")
    k.box("Wheel", (1.8, 1.8, 0.4), (0, 3.0, -0.6), "#222222", rot=CF.rx(math.radians(-40)))
    k.box("WingPost", (0.4, 2, 0.4), (0, 2.4, 4.6), "#222222")
    k.box("Wing", (6, 0.3, 1.4), (0, 3.4, 4.8), c)
    wheels4(k, 3.3, -3.4, 3.4, 1.1, 1.6)


def car_hatch(k):
    c = "#3b8bff"
    k.box("Body", (7, 2.6, 12), (0, 2.5, 0), c)
    k.box("Cabin", (6.6, 2.6, 7), (0, 5.1, 1.4), c)
    k.box("Windshield", (6.0, 2.0, 0.3), (0, 5.2, -2.15), "#9fe6ff", "Glass", transparency=0.2)
    k.box("WinL", (0.2, 1.8, 6.0), (-3.31, 5.2, 1.4), "#9fe6ff", "Glass", transparency=0.2)
    k.box("WinR", (0.2, 1.8, 6.0), (3.31, 5.2, 1.4), "#9fe6ff", "Glass", transparency=0.2)
    k.box("LightL", (1.2, 0.8, 0.2), (-2.4, 3.0, -6.05), "#fff7c2", "Neon")
    k.box("LightR", (1.2, 0.8, 0.2), (2.4, 3.0, -6.05), "#fff7c2", "Neon")
    k.box("TailL", (1.2, 0.8, 0.2), (-2.4, 3.0, 6.05), "#ff2d2d", "Neon")
    k.box("TailR", (1.2, 0.8, 0.2), (2.4, 3.0, 6.05), "#ff2d2d", "Neon")
    wheels4(k, 3.5, -3.9, 3.9, 1.6, 1.3)


def car_pickup(k):
    c = "#33b54a"
    k.box("Body", (7.4, 2.8, 15), (0, 3.0, 0), c)
    k.box("Cab", (7.0, 3.0, 5.4), (0, 5.9, -1.6), c)
    k.box("Windshield", (6.4, 2.2, 0.3), (0, 6.0, -4.35), "#9fe6ff", "Glass", transparency=0.2)
    k.box("BedFloor", (6.6, 0.4, 6), (0, 4.5, 4.2), "#2b2b33")
    for sx in (-1, 1):
        k.box("BedSide", (0.4, 1.4, 6.2), (sx * 3.5, 5.0, 4.2), c)
    k.box("Tailgate", (7.0, 1.4, 0.4), (0, 5.0, 7.3), c)
    k.box("Grill", (5, 1.4, 0.3), (0, 3.4, -7.55), "#c8c8c8", "Metal")
    wheels4(k, 3.7, -4.8, 4.6, 2.0, 1.5)


def car_muscle(k):
    c = "#d7263d"
    k.box("Body", (7.6, 2.4, 15), (0, 2.4, 0), c)
    k.box("Cabin", (6.8, 2.2, 5.5), (0, 4.7, 1.8), c)
    k.wedge("WindF", (6.6, 2.2, 2.0), (0, 4.7, -1.95), "#9fe6ff", "Glass", rot=CF.ry(math.pi),
            transparency=0.2)
    k.box("Scoop", (2.6, 0.8, 3), (0, 4.0, -4.5), "#222222")
    for sx in (-0.9, 0.9):
        k.box("Stripe", (1.0, 0.05, 15.05), (sx, 3.62, 0), "#ffffff")
    k.box("Spoiler", (7.4, 0.3, 1.4), (0, 4.4, 7.0), "#222222")
    k.box("Exhaust", (0.6, 0.6, 1.2), (2.4, 1.6, 7.6), "#c8c8c8", "Metal")
    wheels4(k, 3.7, -4.6, 4.6, 1.8, 1.8)


def car_sports(k):
    c = "#ffd23b"
    k.box("Body", (7.6, 1.8, 15), (0, 2.0, 0), c)
    k.wedge("Nose", (7.6, 1.0, 4), (0, 3.4, -4.4), c, rot=CF.ry(math.pi))
    k.box("Cabin", (6.4, 1.8, 5), (0, 3.8, 1.5), "#222222", "Glass", transparency=0.1)
    k.wedge("CabinF", (6.4, 1.8, 2.4), (0, 3.8, -2.2), "#222222", "Glass", rot=CF.ry(math.pi))
    k.box("WingL", (0.4, 1.4, 0.4), (-2.6, 3.6, 6.6), "#222222")
    k.box("WingR", (0.4, 1.4, 0.4), (2.6, 3.6, 6.6), "#222222")
    k.box("Wing", (7.6, 0.3, 1.8), (0, 4.4, 6.8), "#222222")
    k.box("Intake", (0.2, 1, 2.4), (-3.81, 2.4, 2.6), "#222222")
    k.box("Intake2", (0.2, 1, 2.4), (3.81, 2.4, 2.6), "#222222")
    wheels4(k, 3.8, -4.6, 4.7, 1.6, 1.6)


def car_monster(k):
    c = "#8f3bff"
    k.box("Body", (7.6, 2.6, 12), (0, 6.2, 0), c)
    k.box("Cab", (7.0, 2.8, 5.5), (0, 8.9, 0.8), c)
    k.box("Windshield", (6.4, 2.0, 0.3), (0, 9.0, -2.0), "#9fe6ff", "Glass", transparency=0.2)
    k.box("Chassis", (4, 1.2, 12), (0, 4.4, 0), "#2b2b33", "Metal")
    for sz in (-4.2, 4.2):
        k.box("Axle", (9, 0.8, 0.8), (0, 3.4, sz), "#888888", "Metal")
    k.box("Flames", (0.1, 1.6, 6), (-3.82, 6.4, -1.5), "#ff9f1a")
    k.box("Flames2", (0.1, 1.6, 6), (3.82, 6.4, -1.5), "#ff9f1a")
    wheels4(k, 4.8, -4.2, 4.2, 3.4, 2.6, tire="#151515", rim="#ffd23b")


def car_f1(k):
    c = "#e10600"
    k.box("Tub", (3.4, 1.6, 12), (0, 1.8, 0.5), c)
    k.wedge("NoseCone", (2.6, 1.2, 4), (0, 1.6, -7.4), c, rot=CF.ry(math.pi))
    k.box("FrontWing", (8.4, 0.3, 1.8), (0, 0.8, -8.6), "#ffffff")
    k.box("Sidepod", (6.4, 1.4, 4.6), (0, 1.8, 1.8), c)
    k.box("Intake", (1.6, 2.0, 3.0), (0, 3.4, 2.8), "#ffffff")
    driver(k, (0, 1.9, -0.6), "#e10600")
    k.box("RearWingPost", (0.4, 2.4, 0.4), (0, 3.0, 6.4), "#222222")
    k.box("RearWing", (6.6, 0.4, 1.8), (0, 4.3, 6.6), "#ffffff")
    k.box("RearWingEnd", (0.3, 1.6, 2.0), (-3.3, 3.8, 6.6), c)
    k.box("RearWingEnd2", (0.3, 1.6, 2.0), (3.3, 3.8, 6.6), c)
    wheels4(k, 3.8, -5.0, 4.8, 1.6, 2.0, rim="#222222")


def car_hover(k):
    c = "#28d9e6"
    k.box("Body", (7, 2.2, 13), (0, 3.6, 0), c)
    k.box("Canopy", (5, 1.8, 5), (0, 5.5, 0.4), "#9fe6ff", "Glass", transparency=0.25)
    k.wedge("Nose", (7, 1.0, 3), (0, 5.2, -4.9), c, rot=CF.ry(math.pi))
    for sx in (-1, 1):
        k.box("Fin", (0.4, 2.6, 3), (sx * 2.6, 6.0, 5.2), "#ffffff")
        for sz in (-4, 4):
            k.cyl("Pad", 1.6, 0.6, (sx * 3.0, 2.2, sz), "#ffffff", axis="y")
            k.cyl("PadGlow", 1.3, 0.3, (sx * 3.0, 1.8, sz), "#5cf7ff", "Neon", axis="y")
    k.box("Stripe", (7.05, 0.4, 13.05), (0, 3.6, 0), "#ff4fa3", "Neon")


def car_rocket(k):
    c = "#d9d9e6"
    k.box("Body", (6.4, 2.2, 16), (0, 2.6, 0), c, "Metal")
    k.wedge("Nose", (6.4, 1.6, 5), (0, 4.5, -5.5), c, "Metal", rot=CF.ry(math.pi))
    k.box("Canopy", (4.4, 1.6, 4), (0, 4.5, 0.6), "#1d1d26", "Glass", transparency=0.1)
    for sx in (-1, 1):
        k.cyl("Booster", 1.3, 7, (sx * 3.6, 3.2, 4.5), "#ff4b4b", "Metal")
        k.cyl("Flame", 1.0, 3, (sx * 3.6, 3.2, 9.4), "#ff9f1a", "Neon")
        k.box("Fin", (0.4, 3, 3), (sx * 1.8, 5.2, 6.4), "#ff4b4b")
    k.cyl("MainFlame", 1.4, 4, (0, 2.6, 9.8), "#ffe03b", "Neon")
    wheels4(k, 3.4, -5.0, 5.2, 1.4, 1.2, rim="#ff4b4b")


CARS = [
    # id, display, price, speed (studs/s), money multiplier, builder
    ("Buggy", "Dune Buggy", 0, 30, 1.0, car_buggy),
    ("GoKart", "Go-Kart", 1_000, 38, 1.1, car_kart),
    ("Hatchback", "Hatchback", 5_000, 45, 1.25, car_hatch),
    ("Pickup", "Pickup Truck", 20_000, 52, 1.5, car_pickup),
    ("Muscle", "Muscle Car", 75_000, 60, 1.8, car_muscle),
    ("Sports", "Sports Car", 250_000, 70, 2.2, car_sports),
    ("Monster", "Monster Truck", 1_000_000, 76, 2.8, car_monster),
    ("F1", "Formula Racer", 4_000_000, 90, 3.5, car_f1),
    ("Hover", "Hover Car", 15_000_000, 105, 4.5, car_hover),
    ("Rocket", "Rocket Car", 60_000_000, 125, 6.0, car_rocket),
]


def build_cars():
    root = Inst("Folder", "Cars")
    for i, (cid, display, price, speed, mult, builder) in enumerate(CARS):
        m = Inst("Model", cid, attrs={"DisplayName": display, "Price": price, "Speed": speed,
                                      "MoneyMult": mult, "Order": i + 1})
        m.add(part("Root", (1, 0.4, 1), CF(0, 0.2, 0), "#ffffff", transparency=1, collide=False,
                   touch=False))
        builder(Kit(m, CAR_SCALE))
        root.add(m)
    return root


# ------------------------------------------------------------------ island styles
from build_map import DECOR_SPOTS as SPOTS  # noqa: E402  (plot margins around the grid)
BACK_L = (-72, 98)   # free corner spots for big props
BACK_R = (72, 98)


def d_classic(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        s = rng.uniform(0.85, 1.15)
        if i % 3 == 2:
            k.box("Rock", (4 * s, 2.6 * s, 3.4 * s), (x, 1.1 * s, z), "#8d8f9e",
                  rot=CF.ry(rng.uniform(0, 3)))
            k.box("Bush", (3.6, 2.6, 3.6), (x + 5, 1.2, z + 3), "#5fd13f", rot=CF.ry(0.6))
            continue
        k.box("Trunk", (1.6 * s, 6 * s, 1.6 * s), (x, 3 * s, z), "#8a5a2b")
        k.box("Leaves1", (9 * s, 4.5 * s, 9 * s), (x, 7.5 * s, z), "#4cc23a", rot=CF.ry(0.3))
        k.box("Leaves2", (6.5 * s, 4 * s, 6.5 * s), (x, 11.2 * s, z), "#3fae2f",
              rot=CF.ry(0.3 + math.pi / 4))
        k.box("Leaves3", (3.6 * s, 3 * s, 3.6 * s), (x, 14.2 * s, z), "#4cc23a", rot=CF.ry(0.3))


def d_desert(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        if i % 3 == 2:
            k.box("Rock", (6, 4, 5), (x, 2, z), "#c9944a", "Sandstone",
                  rot=CF.ry(rng.uniform(0, 3)))
            continue
        h = rng.uniform(9, 14)
        k.box("Cactus", (2.4, h, 2.4), (x, h / 2, z), "#3f9b3a", "Grass")
        k.box("ArmL", (3, 1.6, 1.6), (x - 2.4, h * 0.45, z), "#3f9b3a", "Grass")
        k.box("ArmLUp", (1.6, 4, 1.6), (x - 3.4, h * 0.45 + 2.2, z), "#3f9b3a", "Grass")
        k.box("ArmR", (3, 1.6, 1.6), (x + 2.4, h * 0.6, z), "#3f9b3a", "Grass")
        k.box("ArmRUp", (1.6, 3, 1.6), (x + 3.4, h * 0.6 + 1.7, z), "#3f9b3a", "Grass")
        k.ball("Flower", 1.2, (x, h + 0.4, z), "#ff5fa2")
    for i in range(4):
        w = 14 - i * 3.5
        k.box("Pyramid", (w, 3, w), (BACK_L[0], 1.5 + i * 3, BACK_L[1]), "#e3b765")


def d_snow(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        if i == 2:
            k.ball("Snow1", 6, (x, 3, z), "#ffffff", "Snow")
            k.ball("Snow2", 4.4, (x, 7.6, z), "#ffffff", "Snow")
            k.ball("Snow3", 3.2, (x, 11.0, z), "#ffffff", "Snow")
            k.box("Nose", (0.5, 0.5, 1.6), (x, 11.0, z - 1.8), "#ff8a1f")
            k.box("Hat", (2.4, 1.6, 2.4), (x, 13.2, z), "#222222")
            continue
        s = rng.uniform(0.9, 1.2)
        k.box("Trunk", (1.8 * s, 4 * s, 1.8 * s), (x, 2 * s, z), "#6b4423", "Wood")
        for j, w in enumerate((10, 7.5, 5, 2.6)):
            y = (4 + j * 3.6) * s
            k.box("Pine", (w * s, 3.4 * s, w * s), (x, y + 1.7 * s, z), "#1f6e4a", "Grass",
                  rot=CF.ry(math.radians(45 * (j % 2))))
            k.box("PineSnow", (w * s * 0.9, 0.6 * s, w * s * 0.9), (x, y + 3.5 * s, z),
                  "#ffffff", "Snow", rot=CF.ry(math.radians(45 * (j % 2))))


def d_candy(k, rng):
    cols = ["#ff5fa2", "#5cc8ff", "#ffe03b", "#8f6bff", "#5fe08a"]
    for i, (x, z) in enumerate(SPOTS):
        c = cols[i % len(cols)]
        if i % 2 == 0:
            h = rng.uniform(10, 14)
            k.box("Stick", (0.8, h, 0.8), (x, h / 2, z), "#ffffff")
            k.cyl("Pop", 4, 1.2, (x, h + 3, z), c, axis="z")
            k.cyl("PopSwirl", 2.4, 1.3, (x, h + 3, z), "#ffffff", axis="z")
            k.cyl("PopDot", 1.0, 1.4, (x, h + 3, z), c, axis="z")
        else:
            for j in range(6):
                k.box("Cane", (1.4, 2, 1.4), (x, 1 + j * 2, z), "#ff3b3b" if j % 2 else "#ffffff")
            k.box("CaneTop", (4, 1.4, 1.4), (x + 1.3, 12.7, z), "#ff3b3b")
            k.box("CaneEnd", (1.4, 2.4, 1.4), (x + 2.6, 11.4, z), "#ffffff")
    for j in range(6):
        a = j * math.tau / 6
        k.ball("Gumdrop", 3.4, (BACK_L[0] + math.cos(a) * 6, 1.2, BACK_L[1] + math.sin(a) * 6),
               cols[j % len(cols)], "Glass", transparency=0.1)


def d_jungle(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        if i % 4 == 3:
            k.box("Ruin", (4, 10, 4), (x, 5, z), "#8a8f7a", "Cobblestone")
            k.box("RuinTop", (6, 1.6, 6), (x, 10.8, z), "#7a7f6a", "Cobblestone")
            k.box("Moss", (4.2, 1.2, 4.2), (x, 6, z), "#3fae2f", "Grass")
            continue
        lean = rng.uniform(-0.25, 0.25)
        top = (x + lean * 14, 15, z)
        for j in range(5):
            k.box("PalmTrunk", (1.8, 3.2, 1.8), (x + lean * j * 3, 1.6 + j * 3, z), "#9c7a4a",
                  "Wood", rot=CF.rz(-lean))
        for a in range(6):
            ang = a * math.tau / 6
            k.box("PalmLeaf", (2.4, 0.5, 9), (top[0] + math.cos(ang) * 4, 15.2,
                                              top[2] + math.sin(ang) * 4),
                  "#2e9b3a", "Grass", rot=CF.ry(-ang + math.pi / 2) * CF.rx(-0.3))
        k.ball("Coconut", 1.4, (top[0], 14.4, top[2] + 0.8), "#6b4423")
    for j, (x, z) in enumerate(SPOTS[:6]):
        k.ball("Bush", 5, (x + 6, 1.4, z + 5), "#3c8f2c")


def d_lava(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        if i % 2 == 0:
            k.cyl("LavaPool", 5, 0.4, (x, 0.15, z), "#ff6a00", "Neon", axis="y")
            k.cyl("PoolRim", 6, 0.6, (x, 0.05, z), "#2b2626", "Basalt", axis="y")
        else:
            h = rng.uniform(5, 9)
            k.box("Obsidian", (3, h, 3), (x, h / 2, z), "#1b1b22", "Basalt",
                  rot=CF.ry(rng.uniform(0, 3)) * CF.rz(0.15))
            k.box("Crack", (0.4, h * 0.8, 3.1), (x, h / 2, z), "#ff6a00", "Neon",
                  rot=CF.ry(rng.uniform(0, 3)) * CF.rz(0.15))
    for j in range(5):
        r = 12 - j * 2.2
        k.cyl("Volcano", r, 3, (BACK_L[0], 1.5 + j * 3, BACK_L[1]), "#3a2a2a", axis="y")
    k.cyl("Crater", 2.6, 0.6, (BACK_L[0], 15.2, BACK_L[1]), "#ff6a00", "Neon", axis="y")


def d_cyber(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        h = rng.uniform(10, 16)
        k.box("Pylon", (2, h, 2), (x, h / 2, z), "#1f1f3a", "Metal")
        for j in range(3):
            k.box("Ring", (4, 0.4, 4), (x, h * (0.35 + 0.25 * j), z),
                  ["#ff2fd6", "#2fe6ff", "#9b5cff"][j], "Neon")
        k.box("Holo", (3, 3, 3), (x, h + 2.5, z), "#2fe6ff", "Neon", transparency=0.35,
              rot=CF.angles(0.6, 0.6, 0))
    for side in (-1, 1):
        k.box("NeonEdgeX", (0.4, 0.3, 216), (side * 97, 0.2, 0), "#2fe6ff", "Neon")
        k.box("NeonEdgeZ", (196, 0.3, 0.4), (0, 0.2, side * 107), "#ff2fd6", "Neon")


def d_space(k, rng):
    for i, (x, z) in enumerate(SPOTS):
        if i % 2 == 0:
            k.cyl("CraterRim", 6, 0.8, (x, 0.2, z), "#9a9aa6", "Slate", axis="y")
            k.cyl("CraterHole", 4.6, 0.85, (x, 0.25, z), "#5c5c6a", "Slate", axis="y")
        else:
            for j in range(3):
                h = rng.uniform(4, 9)
                k.box("Crystal", (1.6, h, 1.6), (x + rng.uniform(-2, 2), h / 2, z + rng.uniform(-2, 2)),
                      "#b54dff", "Neon", rot=CF.angles(rng.uniform(-.3, .3), 0, rng.uniform(-.3, .3)))
    # rocket
    rx, rz = BACK_L
    k.cyl("Rocket", 2.6, 16, (rx, 9, rz), "#ffffff", axis="y")
    k.box("RocketTip", (3.6, 3.6, 3.6), (rx, 18, rz), "#ff3b3b", rot=CF.angles(0.78, 0, 0.78))
    for a in range(3):
        ang = a * math.tau / 3
        k.box("RocketFin", (0.6, 5, 3), (rx + math.cos(ang) * 3, 3, rz + math.sin(ang) * 3),
              "#ff3b3b", rot=CF.ry(-ang))
    fx, fz = BACK_R
    k.box("FlagPole", (0.4, 10, 0.4), (fx, 5, fz), "#d9d9d9")
    k.box("Flag", (0.2, 3, 5), (fx, 8.5, fz + 2.5), "#3b6bff")


STYLES = [
    # id, display, price, money bonus, grass (color, material), dirt, rock, decor
    ("Classic", "Classic Meadow", 0, 0.0, ("#5fd13f", "SmoothPlastic"), ("#9b6634", "SmoothPlastic"),
     ("#7d7468", "SmoothPlastic"), d_classic),
    ("Desert", "Desert Dunes", 10_000, 0.05, ("#e8c872", "SmoothPlastic"), ("#c9944a", "SmoothPlastic"),
     ("#a8743c", "SmoothPlastic"), d_desert),
    ("Snowy", "Snowy Peaks", 40_000, 0.10, ("#f4f8ff", "SmoothPlastic"), ("#8fa9c2", "SmoothPlastic"),
     ("#6b7f99", "SmoothPlastic"), d_snow),
    ("Candy", "Candy Land", 150_000, 0.15, ("#ff9ad5", "SmoothPlastic"), ("#8a4b2a", "SmoothPlastic"),
     ("#f3e0c0", "SmoothPlastic"), d_candy),
    ("Jungle", "Lost Jungle", 500_000, 0.20, ("#2e9b3a", "SmoothPlastic"), ("#5a3a1e", "SmoothPlastic"),
     ("#4a5a3a", "SmoothPlastic"), d_jungle),
    ("Lava", "Lava Lands", 2_000_000, 0.25, ("#3a3030", "SmoothPlastic"), ("#3a2020", "SmoothPlastic"),
     ("#1b1b1b", "SmoothPlastic"), d_lava),
    ("Cyber", "Cyber City", 8_000_000, 0.32, ("#14142a", "SmoothPlastic"), ("#1f1f3a", "SmoothPlastic"),
     ("#0d0d1a", "SmoothPlastic"), d_cyber),
    ("Space", "Moon Base", 30_000_000, 0.40, ("#c9c9d1", "SmoothPlastic"), ("#8a8a96", "SmoothPlastic"),
     ("#5c5c6a", "SmoothPlastic"), d_space),
]


def build_styles():
    root = Inst("Folder", "IslandStyles")
    for i, (sid, display, price, bonus, grass, dirt, rock, decor) in enumerate(STYLES):
        m = Inst("Model", sid, attrs={
            "DisplayName": display, "Price": price, "MoneyBonus": bonus, "Order": i + 1,
            "GrassColor": grass[0], "GrassMaterial": grass[1], "DirtColor": dirt[0],
            "DirtMaterial": dirt[1], "RockColor": rock[0], "RockMaterial": rock[1]})
        d = Inst("Model", "Decor")
        k = Kit(d)
        decor(k, random.Random(i * 7 + 1))
        for p in d.children:
            p.props.pop("CanCollide", None)  # decor is solid on the island
        m.add(d)
        root.add(m)
    return root


if __name__ == "__main__":
    write_model(build_cars(), "ReplicatedStorage/Assets/Cars.model.json")
    write_model(build_styles(), "ReplicatedStorage/Assets/IslandStyles.model.json")
