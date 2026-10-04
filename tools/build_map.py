"""Generates src/Workspace/Map.model.json: hub island with 4 shops, 8 player plots, bridges."""
import math
import random

from rbx import (CF, C3, FONT, Inst, U2, UD, add, ball, beam_between, folder, mul, norm,
                 part, sub, text_sign, vcyl, wedge, write_model)

TOP = 100.0          # walking height of every island
MAIN_R = 90
PLOT_R = 50
RING = 250
PLOT_COLORS = ["#ff4b4b", "#ff9f1a", "#ffd83b", "#4bdc5a", "#3bd1ff", "#3b6bff", "#b54dff",
               "#ff5fc8"]
SHOP_DEFS = [
    # key, title, main, dark, stripe
    ("Potions", "POTIONS", "#9b3fe0", "#5e1f99", "#c86bff"),
    ("LuckyBlocks", "LUCKY BLOCKS", "#ffb800", "#c46f00", "#ffe066"),
    ("Cars", "CAR DEALER", "#2f7dff", "#1747a8", "#7fb6ff"),
    ("Styles", "ISLAND STYLES", "#ff4fa3", "#b0236a", "#ff9fd0"),
]


class B:
    """Builds parts in a local frame."""

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

    def cyl(self, name, r, h, pos, color, mat="SmoothPlastic", **kw):
        """Vertical cylinder in local frame."""
        p = part(name, (h, r * 2, r * 2), self.cf(*pos, rot=CF.rz(math.pi / 2)), color, mat,
                 shape="Cylinder", **kw)
        self.parent.add(p)
        return p

    def hcyl(self, name, r, h, pos, color, mat="SmoothPlastic", axis="x", **kw):
        rot = None if axis == "x" else CF.ry(math.pi / 2)
        p = part(name, (h, r * 2, r * 2), self.cf(*pos, rot=rot), color, mat, shape="Cylinder",
                 **kw)
        self.parent.add(p)
        return p

    def ball(self, name, d, pos, color, mat="SmoothPlastic", **kw):
        p = part(name, (d, d, d), self.cf(*pos), color, mat, shape="Ball", **kw)
        self.parent.add(p)
        return p

    def wedge(self, name, size, pos, color, mat="SmoothPlastic", rot=None, **kw):
        p = part(name, size, self.cf(*pos, rot=rot), color, mat, cls="WedgePart", **kw)
        self.parent.add(p)
        return p

    def sign(self, name, text, pos, size, bg, fg="#ffffff", rot=None, face="Front", **kw):
        p = text_sign(name, text, 40, self.cf(*pos, rot=rot), size, bg, fg, face=face, **kw)
        self.parent.add(p)
        return p


def floating_island(m, center, r, seed, grass="#5fd13f"):
    rng = random.Random(seed)
    x, y, z = center
    m.add(vcyl("Grass", r, 3, (x, y - 1.5, z), grass, "Grass", attrs={"Role": "Grass"}))
    m.add(vcyl("GrassLip", r + 0.8, 1.2, (x, y - 3.4, z), grass, "Grass",
               attrs={"Role": "Grass"}))
    m.add(vcyl("Dirt", r * 0.97, 8, (x, y - 7.5, z), "#9b6634", "Ground",
               attrs={"Role": "Dirt"}))
    for i, (k, h) in enumerate([(0.85, 6), (0.66, 6), (0.46, 6), (0.26, 6)]):
        m.add(vcyl(f"Rock{i}", r * k, h, (x, y - 14.5 - i * 6, z), "#7d7468", "Rock",
                   attrs={"Role": "Rock"}))
    for i in range(7):
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0.2, 0.55) * r
        s = rng.uniform(0.12, 0.22) * r
        m.add(part(f"Chunk{i}", (s, s * 1.4, s),
                   CF(x + math.cos(a) * d, y - 20 - s, z + math.sin(a) * d)
                   * CF.angles(rng.random(), rng.random(), rng.random()),
                   "#6e665c", "Rock", attrs={"Role": "Rock"}))


def tree(parent, pos, s=1.0, name="Tree"):
    x, y, z = pos
    t = Inst("Model", name)
    t.add(part("Trunk", (2 * s, 10 * s, 2 * s), CF(x, y + 5 * s, z), "#8a5a2b", "Wood",
               attrs={"Role": "Trunk"}))
    t.add(part("Leaves", (11 * s, 6 * s, 11 * s), CF(x, y + 12 * s, z), "#3fae2f", "Grass",
               attrs={"Role": "Leaves"}))
    t.add(part("LeavesTop", (7 * s, 5 * s, 7 * s), CF(x, y + 17 * s, z), "#4cc23a", "Grass",
               attrs={"Role": "Leaves"}))
    parent.add(t)
    return t


def bridge(parent, name, p1, p2, width=14):
    """Plank bridge with posts and rope rails; walking surface at TOP."""
    m = Inst("Model", name)
    d = sub(p2, p1)
    L = math.hypot(d[0], d[2])
    f = norm((d[0], 0, d[2]))
    base = CF.look(((p1[0] + p2[0]) / 2, TOP, (p1[2] + p2[2]) / 2), f)
    b = B(base, m)
    n = max(4, int(L / 2.4))
    step = L / n
    for i in range(n):
        lz = -L / 2 + step * (i + 0.5)
        b.box(f"Plank{i}", (width, 0.8, step * 0.9), (0, -0.4, lz),
              "#c98a4b" if i % 2 else "#b07438", "WoodPlanks")
    for side in (-1, 1):
        b.box("Beam", (1.0, 1.0, L), (side * (width / 2 - 0.5), -1.3, 0), "#7a4a25", "Wood")
    posts = max(2, int(L / 14) + 1)
    for i in range(posts):
        lz = -L / 2 + L * i / (posts - 1)
        for side in (-1, 1):
            b.box("Post", (1.2, 6, 1.2), (side * (width / 2 + 0.2), 2, lz), "#7a4a25", "Wood")
    for side in (-1, 1):
        for h in (1.6, 3.8):
            b.box("Rope", (0.4, 0.4, L), (side * (width / 2 + 0.2), h, 0), "#e0c58f", "Fabric")
    parent.add(m)


def shop_stall(parent, key, title, c_main, c_dark, c_stripe, cf):
    """Market stall; front (counter) faces local -Z. Contains a ProximityPrompt."""
    m = Inst("Model", f"Shop_{key}", attrs={"Shop": key})
    b = B(cf, m)
    b.box("Floor", (34, 1.4, 22), (0, 0.5, 0), "#7a4a25", "WoodPlanks")
    b.box("Back", (34, 16, 1.5), (0, 9.2, 10.25), c_main)
    b.box("SideL", (1.5, 16, 20), (-16.25, 9.2, 0), c_main)
    b.box("SideR", (1.5, 16, 20), (16.25, 9.2, 0), c_main)
    b.box("Counter", (30, 4.5, 4), (0, 3.45, -7), "#b8773f", "Wood")
    b.box("CounterTop", (31, 0.8, 5), (0, 6.1, -7), c_dark)
    b.box("PillarL", (2, 18, 2), (-16, 9.6, -10), c_dark)
    b.box("PillarR", (2, 18, 2), (16, 9.6, -10), c_dark)
    b.box("Roof", (36, 1.5, 24), (0, 18.6, 0), c_dark)
    n = 9
    w = 36 / n
    for i in range(n):
        x = -18 + w * (i + 0.5)
        col = c_stripe if i % 2 == 0 else "#ffffff"
        b.box(f"Awning{i}", (w, 0.6, 9), (x, 17.2, -14.3), col, "Fabric",
              rot=CF.rx(math.radians(22)))
        b.hcyl(f"Scallop{i}", w / 2, 0.6, (x, 15.3, -18.4), col, "Fabric", axis="z")
    b.box("SignFrame", (27.5, 8.5, 1.0), (0, 23.5, 1.6), "#ffffff")
    b.sign("Sign", title, (0, 23.5, 1.0), (26, 7, 1.2), c_dark)
    b.sign("SignBack", title, (0, 23.5, 2.2), (26, 7, 1.2), c_dark, rot=CF.ry(math.pi))
    # interaction prompt in front of the counter
    pp = b.box("PromptPart", (12, 8, 2), (0, 5, -11), "#ffffff", transparency=1, collide=False)
    pp.add(Inst("ProximityPrompt", "Prompt", {
        "ActionText": "Open", "ObjectText": title.title(), "HoldDuration": 0,
        "MaxActivationDistance": 16, "RequiresLineOfSight": False, "KeyboardKeyCode": "E"}))
    pp.attrs["Shop"] = key
    # shop-specific props
    if key == "Potions":
        cols = ["#ff3b3b", "#3bff6b", "#3bb8ff", "#ffd23b", "#ff6bf0", "#ff8a1f"]
        for row in range(3):
            b.box(f"Shelf{row}", (28, 0.6, 2.5), (0, 5 + row * 4.5, 8.6), "#b8773f", "Wood")
            for i in range(8):
                c = cols[(row * 8 + i) % len(cols)]
                x = -12 + i * 3.4
                y = 5.3 + row * 4.5
                b.ball(f"Potion{row}_{i}", 1.8, (x, y + 0.9, 8.6), c, "Glass", transparency=0.15)
                b.cyl(f"Neck{row}_{i}", 0.35, 1.0, (x, y + 2.2, 8.6), c, "Glass")
                b.cyl(f"Cork{row}_{i}", 0.4, 0.5, (x, y + 2.9, 8.6), "#9c6b3c", "Wood")
        for i, c in enumerate(cols[:4]):
            x = -9 + i * 6
            b.ball(f"BigPotion{i}", 3, (x, 8.0, -7), c, "Neon", transparency=0.1)
            b.cyl(f"BigNeck{i}", 0.6, 1.6, (x, 10.2, -7), c, "Glass")
            b.cyl(f"BigCork{i}", 0.7, 0.8, (x, 11.3, -7), "#9c6b3c", "Wood")
    elif key == "LuckyBlocks":
        colors = ["#ffcc1a", "#3fa9ff", "#b54dff", "#ff3b6b"]
        for i, c in enumerate(colors):
            lucky_block(b, f"Block{i}", (-10.5 + i * 7, 6.5, -7), 4.5, c)
        for i in range(5):
            lucky_block(b, f"Stack{i}", (-12 + i * 6, 1.2, 7), 5, colors[i % 4])
        lucky_block(b, "StackTop1", (-3, 6.2, 7), 5, "#ffcc1a")
        lucky_block(b, "StackTop2", (3, 6.2, 7), 5, "#ff3b6b")
    elif key == "Cars":
        b.cyl("Turntable", 9, 1, (0, 1.7, 1), "#e6e6e6")
        b.cyl("TurntableRing", 9.4, 0.8, (0, 1.5, 1), c_stripe, "Neon")
        mini_car(b, (0, 2.2, 1), "#ff2d2d", 1.0, math.radians(35))
        mini_car(b, (-11, 6.5, -7), "#33d17a", 0.35, math.radians(90))
        mini_car(b, (11, 6.5, -7), "#ffd23b", 0.35, math.radians(90))
    elif key == "Styles":
        cols = ["#ff3b3b", "#3bd16b", "#3b8bff", "#ffd23b", "#b54dff", "#ff8a1f", "#3be0e0",
                "#ffffff"]
        for i, c in enumerate(cols):
            back = i < 4
            x = (-13, -8.5, 8.5, 13)[i % 4] if back else -12 + (i % 4) * 8
            y = 1.2 if back else 6.5
            z = 7 if back else -7
            b.cyl(f"Bucket{i}", 2.3, 3.5, (x, y + 1.75, z), "#c8c8c8", "Metal")
            b.cyl(f"Paint{i}", 2.1, 0.3, (x, y + 3.55, z), c)
        b.cyl("Pedestal", 2.5, 4, (0, 3.2, 7), c_dark)
        b.cyl("MiniGrass", 4, 1, (0, 5.7, 7), "#4fc23a", "Grass")
        b.cyl("MiniDirt", 3.4, 2.5, (0, 3.9, 7), "#8a5a2b", "Ground")
        b.box("MiniTree", (1.6, 1.6, 1.6), (1.5, 7.0, 7), "#3fae2f", "Grass")
    parent.add(m)
    return m


def lucky_block(b, name, pos, s, color):
    x, y, z = pos
    p = b.box(name, (s, s, s), (x, y + s / 2, z), color, "SmoothPlastic")
    for face in ("Front", "Back", "Left", "Right"):
        sg = Inst("SurfaceGui", f"Q{face}", {"Face": face, "LightInfluence": 0,
                                            "SizingMode": "PixelsPerStud", "PixelsPerStud": 30})
        lbl = Inst("TextLabel", "Q", {"Size": U2(1, 0, 1, 0), "BackgroundTransparency": 1,
                                      "Text": "?", "TextScaled": True, "FontFace": FONT(),
                                      "TextColor3": C3("#ffffff")})
        lbl.add(Inst("UIStroke", "Stroke", {"Color": C3("#8a5a00"), "Thickness": 4}))
        sg.add(lbl)
        p.add(sg)
    return p


def mini_car(b, pos, color, s, rz):
    """Static decorative car (used in the car shop)."""
    x, y, z = pos
    rot = CF.ry(rz)
    base = b.cf(x, y, z) * rot
    cb = B(base, b.parent)
    cb.box("CarBody", (7 * s, 2.4 * s, 13 * s), (0, 2.0 * s, 0), color)
    cb.box("CarCab", (6 * s, 2.2 * s, 6.5 * s), (0, 4.2 * s, 0.8 * s), "#9fe6ff", "Glass",
           transparency=0.2)
    cb.box("CarRoof", (6.2 * s, 0.5 * s, 5.5 * s), (0, 5.4 * s, 0.8 * s), color)
    for sx in (-1, 1):
        for sz in (-1, 1):
            cb.hcyl("Wheel", 1.5 * s, 1.2 * s, (sx * 3.5 * s, 1.5 * s, sz * 4.2 * s), "#222222")


def plot(parent, idx, center):
    cx, cz = center
    col = PLOT_COLORS[idx]
    pos = (cx, TOP, cz)
    cf = CF.look(pos, (-cx, 0, -cz))  # LookVector -> hub
    m = Inst("Model", f"Plot{idx + 1}", attrs={"PlotIndex": idx + 1, "PlotColor": col})
    b = B(cf, m)
    b.box("Pivot", (1, 1, 1), (0, 0.5, 0), "#ffffff", transparency=1, collide=False,
                  touch=False)
    island = Inst("Model", "Island")
    m.add(island)
    floating_island(island, pos, PLOT_R, seed=idx + 10)
    # coloured border tiles
    border = Inst("Model", "Border")
    for k in range(28):
        a = k * math.tau / 28
        lx, lz = math.cos(a) * (PLOT_R - 1.5), math.sin(a) * (PLOT_R - 1.5)
        p = part(f"B{k}", (2.4, 0.8, 11.5), b.cf(lx, 0.2, lz) * CF.ry(-a), col, "SmoothPlastic",
                 attrs={"Role": "Accent"})
        border.add(p)
    m.add(border)
    # spawn pad near the hub side (-Z local)
    b.cyl("SpawnPad", 6, 1.0, (0, 0.3, -32), "#ffffff")
    b.cyl("SpawnPadInner", 4.5, 1.1, (0, 0.35, -32), col, attrs={"Role": "Accent"})
    b.box("SpawnPoint", (2, 1, 2), (0, 3, -32), "#ffffff", transparency=1, collide=False,
          touch=False)
    # owner sign arching over the bridge entrance
    b.box("SignPostL", (1, 12, 1), (-8.5, 6, -42), "#7a4a25", "Wood")
    b.box("SignPostR", (1, 12, 1), (8.5, 6, -42), "#7a4a25", "Wood")
    b.box("SignFrame", (19, 6, 0.6), (0, 11, -42), "#ffffff")
    s = b.sign("OwnerSign", f"Empty Plot {idx + 1}", (0, 11, -42.4), (18, 5, 0.6), col)
    s.attrs["Role"] = "Accent"
    # back face too (seen from inside the plot)
    b.sign("OwnerSignBack", f"PLOT {idx + 1}", (0, 11, -41.6), (18, 5, 0.6), col,
           rot=CF.ry(math.pi))
    # spin machine (slot machine)
    sm = Inst("Model", "SpinMachine")
    m.add(sm)
    sb = B(b.cf(-24, 0, -12) * CF.ry(math.radians(-30)), sm)
    sb.box("Base", (12, 3, 8), (0, 1.5, 0), "#2b2b33")
    sb.box("Body", (10, 12, 6), (0, 9, 0), col, attrs={"Role": "Accent"})
    sb.box("Screen", (7.5, 5, 0.5), (0, 10, -3.1), "#7fe8ff", "Neon")
    sb.box("Top", (11, 2, 7), (0, 16, 0), "#ffc21a", "Metal")
    sb.box("Lever", (0.8, 6, 0.8), (6, 11, 0), "#ffc21a", "Metal")
    sb.ball("Knob", 2.2, (6, 14.2, 0), "#ff3030")
    sb.sign("SpinLabel", "SPIN!", (0, 16, -3.6), (9, 2, 0.2), "#2b2b33", transparent_part=True)
    sp = sb.box("PromptPart", (10, 10, 2), (0, 6, -5), "#ffffff", transparency=1, collide=False)
    sp.add(Inst("ProximityPrompt", "Prompt", {
        "ActionText": "Spin", "ObjectText": "Track RNG", "HoldDuration": 0,
        "MaxActivationDistance": 14, "RequiresLineOfSight": False, "KeyboardKeyCode": "E"}))
    # garage
    gar = Inst("Model", "Garage")
    m.add(gar)
    gb = B(b.cf(24, 0, -14), gar)
    gb.box("Back", (16, 10, 1), (0, 5, -7), "#ffffff")
    gb.box("WallL", (1, 10, 14), (-7.5, 5, 0), "#ffffff")
    gb.box("WallR", (1, 10, 14), (7.5, 5, 0), "#ffffff")
    gb.box("Roof", (18, 1.2, 16), (0, 10.6, 0), col, attrs={"Role": "Accent"})
    gb.box("Floor", (15, 0.5, 14), (0, 0.1, 0), "#3a3a42", "Asphalt")
    gb.sign("GarageSign", "GARAGE", (0, 8.2, 7.2), (12, 2.5, 0.4), col, rot=CF.ry(math.pi))
    # start area: road from the gate to the island edge (+Z local = outward)
    track = Inst("Model", "TrackStart")
    m.add(track)
    tb = B(cf, track)
    road_len = PLOT_R + 2
    tb.box("Road", (16, 1, road_len), (0, 0.5, road_len / 2 + 1), "#3a3a42", "Asphalt")
    for i in range(int(road_len / 2)):
        for side in (-1, 1):
            tb.box("Kerb", (1.2, 1.1, 2), (side * 8.6, 0.55, 2 + i * 2 + 1),
                   "#ff3030" if i % 2 else "#ffffff")
    for i in range(8):
        for j in range(2):
            tb.box("Checker", (2, 1.05, 2), (-7 + i * 2, 0.53, 4 + j * 2),
                   "#ffffff" if (i + j) % 2 else "#111111")
    tb.box("GateL", (1.6, 14, 1.6), (-9.5, 7, 5), "#2b2b33")
    tb.box("GateR", (1.6, 14, 1.6), (9.5, 7, 5), "#2b2b33")
    tb.box("GateTop", (21, 3.5, 2), (0, 14.5, 5), col, attrs={"Role": "Accent"})
    tb.sign("GateText", "START", (0, 14.5, 3.9), (16, 3, 0.2), col, transparent_part=True)
    tb.sign("GateTextBack", "START", (0, 14.5, 6.1), (16, 3, 0.2), col, transparent_part=True,
            rot=CF.ry(math.pi))
    # chain origin for rolled pieces: road top, facing outward
    tb.box("TrackOrigin", (1, 1, 1), (0, 1, road_len + 1), "#ffffff", transparency=1,
           collide=False, touch=False, rot=CF.ry(math.pi))
    tb.box("CarStart", (1, 1, 1), (0, 1, 3), "#ffffff", transparency=1, collide=False,
           touch=False, rot=CF.ry(math.pi))
    # default (Classic) decoration
    decor = Inst("Model", "Decor")
    m.add(decor)
    rng = random.Random(idx)
    spots = [(-36, -24), (-38, 10), (-28, 30), (36, 18), (30, 34), (40, -2), (-14, -40),
             (16, -38)]
    for k, (lx, lz) in enumerate(spots):
        wp = b.cf(lx, 0, lz).p
        tree(decor, wp, rng.uniform(0.8, 1.15), f"Tree{k}")
    # (rolled track pieces and the car are spawned by the server)
    m.add(Inst("Folder", "Track"))
    parent.add(m)
    return m


def hub(parent):
    m = Inst("Model", "Hub")
    floating_island(m, (0, TOP, 0), MAIN_R, seed=1)
    b = B(CF(0, TOP, 0), m)
    b.cyl("Plaza", 22, 0.7, (0, 0.15, 0), "#d9d4c7", "Concrete")
    b.cyl("PlazaInner", 16, 0.8, (0, 0.2, 0), "#bfb8a8", "Concrete")
    for k in range(8):
        a = k * math.tau / 8
        r = (MAIN_R / 2 + 9)
        p = part(f"Path{k}", (MAIN_R - 18, 0.66, 12),
                 CF(math.cos(a) * r, TOP + 0.17, math.sin(a) * r) * CF.ry(-a), "#d9d4c7",
                 "Cobblestone")
        m.add(p)
    b.cyl("FountainBase", 9, 2.5, (0, 1.25, 0), "#bfb8a8", "Marble")
    b.cyl("FountainWater", 8, 0.4, (0, 2.4, 0), "#4fc8ff", "Glass", transparency=0.25)
    b.cyl("FountainPillar", 2, 6, (0, 4, 0), "#bfb8a8", "Marble")
    b.cyl("FountainTop", 4.5, 1, (0, 7, 0), "#bfb8a8", "Marble")
    b.cyl("FountainTopWater", 4, 0.3, (0, 7.6, 0), "#4fc8ff", "Glass", transparency=0.25)
    spawn = Inst("SpawnLocation", "HubSpawn", {
        "Anchored": True, "Size": {"Vector3": [8, 1, 8]},
        "CFrame": CF(0, TOP + 0.3, 14).json(), "Transparency": 1, "CanCollide": False,
        "Neutral": True, "Duration": 0})
    m.add(spawn)
    # title sign in the free gap at 112.5 deg
    ta = math.radians(112.5)
    tcf = CF.look((math.cos(ta) * 45, TOP, math.sin(ta) * 45), (-math.cos(ta), 0, -math.sin(ta)))
    tb = B(tcf, m)
    tb.box("TitlePostL", (1.5, 22, 1.5), (-20, 11, 0), "#7a4a25", "Wood")
    tb.box("TitlePostR", (1.5, 22, 1.5), (20, 11, 0), "#7a4a25", "Wood")
    tb.box("TitleFrame", (46, 12, 1.0), (0, 24, 0), "#ffffff")
    tb.sign("Title", "TRACK RNG", (0, 24, -0.7), (44, 10, 0.5), "#ff3b6b")
    tb.sign("TitleBack", "TRACK RNG", (0, 24, 0.7), (44, 10, 0.5), "#ff3b6b", rot=CF.ry(math.pi))
    # shops, facing the fountain
    for k, (key, title, c1, c2, c3) in enumerate(SHOP_DEFS):
        a = math.radians(67.5 + 90 * k)
        pos = (math.cos(a) * 62, TOP, math.sin(a) * 62)
        scf = CF.look(pos, (-math.cos(a), 0, -math.sin(a)))
        shop_stall(m, key, title, c1, c2, c3, scf)
    rng = random.Random(3)
    for k in range(10):
        a = math.radians(22.5 + 90 * (k % 4)) + rng.uniform(-0.12, 0.12)
        if k % 4 == 1:
            continue  # title sign gap
        d = rng.uniform(70, 82)
        tree(m, (math.cos(a) * d, TOP, math.sin(a) * d), rng.uniform(0.9, 1.3), f"Tree{k}")
    parent.add(m)


def build():
    root = Inst("Folder", "Map")
    hub(root)
    plots = Inst("Folder", "Plots")
    root.add(plots)
    for i in range(8):
        a = i * math.tau / 8
        plot(plots, i, (math.cos(a) * RING, math.sin(a) * RING))
    bridges = Inst("Folder", "Bridges")
    root.add(bridges)
    for i in range(8):
        a = i * math.tau / 8
        u = (math.cos(a), 0, math.sin(a))
        bridge(bridges, f"HubBridge{i + 1}", mul(u, MAIN_R - 3), mul(u, RING - PLOT_R + 3))
        j = (i + 1) % 8
        c1 = mul(u, RING)
        b2 = j * math.tau / 8
        c2 = (math.cos(b2) * RING, 0, math.sin(b2) * RING)
        dv = norm(sub(c2, c1))
        bridge(bridges, f"RingBridge{i + 1}_{j + 1}", add(c1, mul(dv, PLOT_R - 3)),
               sub(c2, mul(dv, PLOT_R - 3)))
    # void catcher + ocean
    root.add(part("VoidCatcher", (2048, 4, 2048), CF(0, TOP - 140, 0), "#000000",
                  transparency=1, collide=False))
    for ix in (-1, 0, 1):
        for iz in (-1, 0, 1):
            root.add(part("Ocean", (2048, 2, 2048), CF(ix * 2048, TOP - 160, iz * 2048),
                          "#3fb7f0", "Glass", transparency=0.15, touch=False))
    return root


if __name__ == "__main__":
    write_model(build(), "Workspace/Map.model.json")
