"""Generates src/Workspace/Map.model.json - island world in the sea.

Round hub island (market stalls around a plaza with a giant golden die) and 8 rounded player
islands, all sitting in the sea and joined by plank bridges on stone pillars. Visible geometry is
meshes baked by blender/models/world.py; invisible Parts give the ground its collision.
Plot local space: origin = island top centre, -Z points at the hub.
"""
import math
import random

from meshparts import animated, mesh_parts, set_attrs
from rbx import C3, CF, FONT, U2, V3, Inst, add, mul, norm, part, sub, text_sign, vcyl, write_model

TOP = 100.0
WATER = TOP - 8.0
CELL = 10
MAX_CELLS = 15
HUB_R = 92
RING = 380
PLOT_W, PLOT_D = 200, 220
GRID_Z = 10            # grid centre (local z)
PLOT_COLORS = ["#ff5a5a", "#ff9f1a", "#ffd83b", "#5ad65a", "#3bd1ff", "#4b7bff", "#b54dff",
               "#ff5fc8"]
GRASS_DARK = "#5fc048"
# free spots around the build grid used by island style decorations (local x, z)
DECOR_SPOTS = [(-88, -60), (-90, -20), (-88, 25), (-90, 65), (88, -60), (90, -20), (88, 25),
               (90, 65), (-55, 98), (-15, 100), (25, 98), (65, 100), (-60, -95), (60, -95)]


def collider(name, size, cf, **kw):
    return part(name, size, cf, "#ffffff", transparency=1, cast_shadow=False, **kw)


def meshes(parent, name, cf, scale=1.0, **kw):
    for mp in mesh_parts("World_" + name, base=cf, scale=scale, **kw):
        parent.add(mp)


def prop(parent, name, cf, scale=1.0, label=None):
    m = Inst("Model", label or name)
    meshes(m, name, cf, scale)
    parent.add(m)
    return m


# ------------------------------------------------------------------ hub
SHOPS = [("Cars", "CAR DEALER", "StallCars"), ("Styles", "ISLAND STYLES", "StallStyles"),
         ("Potions", "POTIONS", "StallPotions"), ("Dice", "DICE SHOP", "StallDice")]
STALL_SCALE = 1.35
STALL_DEPTH = 7.0 * STALL_SCALE


def shop(parent, key, title, mesh, cf):
    """cf: stall base, local +Z faces the plaza."""
    m = Inst("Model", f"Shop_{key}", attrs={"Shop": key})
    meshes(m, mesh, cf, STALL_SCALE)
    m.add(collider("Floor", (17.5, 0.7, 11.5), cf * CF(0, 0.35, 0)))
    m.add(collider("Back", (16.5, 11, 1.2), cf * CF(0, 5.5, -STALL_DEPTH / 2 + 0.5)))
    m.add(collider("Counter", (16, 3.6, 2.2), cf * CF(0, 1.8, STALL_DEPTH / 2 - 1.2)))
    front = STALL_DEPTH / 2
    pp = collider("PromptPart", (14, 8, 2), cf * CF(0, 4, front + 3), collide=False,
                  attrs={"Shop": key})
    pp.add(Inst("ProximityPrompt", "Prompt", {
        "ActionText": "Open", "ObjectText": title.title(), "HoldDuration": 0,
        "MaxActivationDistance": 18, "RequiresLineOfSight": False, "KeyboardKeyCode": "E"}))
    m.add(pp)
    m.add(collider(f"TP_{key}", (4, 1, 4), cf * CF(0, 1, front + 12), collide=False, touch=False))
    parent.add(m)


def hub(parent):
    m = Inst("Model", "Hub")
    base = CF(0, TOP, 0)
    meshes(m, "HubIsland", base)
    m.add(vcyl("Ground", HUB_R - 1, 6, (0, TOP - 3, 0), "#ffffff", transparency=1))
    m.add(vcyl("Beach", HUB_R + 9, 2, (0, TOP - 8.2, 0), "#ffffff", transparency=1))
    lm = Inst("Model", "Landmark")
    meshes(lm, "Landmark", base * CF(0, 0.3, 0), 1.3)
    die = Inst("Model", "Die")   # spun and bobbed by the client (WorldFX)
    meshes(die, "LandmarkDie", base * CF(0, 16.6, 0) * CF.angles(0.62, 0.5, 0.3), 1.3)
    lm.add(die)
    lm.add(vcyl("Basin", 14.3, 2.4, (0, TOP + 1.2, 0), "#ffffff", transparency=1))
    lm.add(vcyl("Pillar", 3, 16, (0, TOP + 8, 0), "#ffffff", transparency=1))
    m.add(lm)
    m.add(Inst("SpawnLocation", "HubSpawn", {
        "Anchored": True, "Size": {"Vector3": [8, 1, 8]}, "CFrame": CF(0, TOP + 0.4, 24).json(),
        "Transparency": 1, "CanCollide": False, "CanQuery": False, "Neutral": True,
        "Duration": 0}))
    # title sign facing the first bridge
    # arch over the path of the first bridge, readable from both sides
    tcf = CF.look((82, TOP, 0), (-1, 0, 0))
    for x in (-15, 15):
        m.add(part("TitlePost", (1.6, 18, 1.6), tcf * CF(x, 9, 0), "#8a5a2b"))
    m.add(part("TitleFrame", (36, 9, 1.0), tcf * CF(0, 19, 0), "#ffffff"))
    m.add(text_sign("Title", "TRACK RNG", 40, tcf * CF(0, 19, -0.7), (34, 7.4, 0.5), "#ff3b6b"))
    m.add(text_sign("TitleBack", "TRACK RNG", 40, tcf * CF(0, 19, 0.7) * CF.ry(math.pi),
                    (34, 7.4, 0.5), "#ff3b6b"))
    for k, (key, title, mesh) in enumerate(SHOPS):
        a = math.radians(22.5 + 90 * k)
        pos = (math.cos(a) * 64, TOP, math.sin(a) * 64)
        shop(m, key, title, mesh, CF.look(pos, (math.cos(a), 0, math.sin(a))))
    deco = Inst("Model", "Decor")
    rng = random.Random(3)
    for k in range(8):   # one lamp beside each path where it meets the plaza
        a = k * math.tau / 8 + 0.16
        prop(deco, "Lamp", CF(math.cos(a) * 40, TOP, math.sin(a) * 40), 1.3)
    for k in (1, 3, 5, 7):  # benches facing the flower beds
        a = (k + 0.5) * math.tau / 8
        prop(deco, "Bench", CF.look((math.cos(a) * 38, TOP, math.sin(a) * 38),
                                    (math.cos(a), 0, math.sin(a))), 1.2)
    for k in range(16):  # trees around the rim, between the paths
        a = (k + 0.5) * math.tau / 16 + rng.uniform(-0.05, 0.05)
        if k % 2 == 0 and (k // 2) % 2 == 0:
            continue
        d = rng.uniform(78, 84)
        kind = rng.choice(("TreeRound", "TreeRound", "TreePine", "TreePalm"))
        prop(deco, kind, CF(math.cos(a) * d, TOP, math.sin(a) * d) * CF.ry(rng.uniform(0, 6)),
             rng.uniform(1.6, 2.0))
        prop(deco, "Bush", CF(math.cos(a + 0.06) * (d - 6), TOP, math.sin(a + 0.06) * (d - 6))
             * CF.ry(rng.uniform(0, 6)), 1.3)
    for k in range(10):  # palms and rocks on the beach
        a = k * math.tau / 10 + 0.3
        prop(deco, "Rock" if k % 2 else "TreePalm",
             CF(math.cos(a) * (HUB_R + 6), TOP - 7.3, math.sin(a) * (HUB_R + 6))
             * CF.ry(rng.uniform(0, 6)), 1.8 if k % 2 else 1.5)
    # waterfall rock on the rim, facing the plaza
    a = math.radians(67.5)
    radial = (math.cos(a), 0, math.sin(a))
    wcf = CF.look((math.cos(a) * 85, TOP, math.sin(a) * 85), radial)
    prop(deco, "WaterfallRock", wcf, 1.25)
    m.add(collider("WaterfallRocks", (18, 20, 8), wcf * CF(0, 10, -3)))
    # harbour pier on the beach with a moored boat
    a = math.radians(157.5)
    radial = (math.cos(a), 0, math.sin(a))
    pcf = CF.look((math.cos(a) * 99, WATER + 2.6, math.sin(a) * 99), (-radial[0], 0, -radial[2]))
    prop(deco, "Pier", pcf)
    m.add(collider("PierDeck", (5.6, 1, 30), pcf * CF(0, -0.5, 14)))
    deco.add(animated("World_RowboatB", pcf * CF(-6.5, -2.6, 24) * CF.ry(0.15), "Rowboat",
                      {"Anim": "Bob", "BobHeight": 0.25, "BobSpeed": 1.4, "BobTilt": 3}))
    # floating market lanterns over the plaza
    lanterns = Inst("Model", "Lanterns")
    for k in range(12):
        a = k * math.tau / 12 + 0.26
        r = 30 if k % 2 else 22
        lanterns.add(animated("World_Lantern" + ("B" if k % 3 == 0 else ""),
                              CF(math.cos(a) * r, TOP + 19 + (k % 4) * 1.6, math.sin(a) * r)
                              * CF.ry(a), "Lantern",
                              {"Anim": "Bob", "BobHeight": 0.9, "BobSpeed": 1.1 + (k % 3) * 0.2,
                               "BobTilt": 4}, shadow=False))
    m.add(lanterns)
    m.add(deco)
    parent.add(m)


# ------------------------------------------------------------------ plot decoration
WINDMILL_AT = (-52, -90)   # front-left, beside the entrance path (replaces DECOR_SPOTS[12])


def classic_decor(cf, rng, label="Decor"):
    """Trees, rocks, bushes, flower beds, hedges and a windmill (plot local space via cf).
    Also used by tools/build_assets.py for the Classic island style."""
    def L(x, y, z):
        return cf * CF(x, y, z)
    decor = Inst("Model", label)
    for k, (x, z) in enumerate(DECOR_SPOTS):
        if k == 12:
            continue
        kind = ("TreeRound", "TreePine", "Rock")[k % 3]
        prop(decor, kind, L(x, 0, z) * CF.ry(rng.uniform(0, 6)), rng.uniform(1.5, 1.9))
        if k % 3 == 2:
            prop(decor, "Bush", L(x + 6, 0, z + 3), 1.3)
    windmill(decor, L(WINDMILL_AT[0], 0, WINDMILL_AT[1]) * CF.ry(math.pi + 0.35))
    # flower beds flanking the entrance path, hedges along the front edge
    for x in (-22, 22):
        prop(decor, "FlowerBed", L(x, 0, -84), 1.2)
    for x, z, r in ((40, -100, 0.1), (60, -96, -0.25), (-80, -97, 0.4)):
        prop(decor, "Hedge", L(x, 0, z) * CF.ry(r), 1.3)
    for x, z in ((92, 45), (-92, 45), (93, -8), (-93, -8), (-20, 101), (40, 102)):
        prop(decor, "FlowerBed" if (x + z) % 2 else "Bush", L(x, 0, z) * CF.ry(rng.uniform(0, 6)),
             1.0)
    return decor


def windmill(parent, base):
    """Windmill + spinning blades (blades hub at local (0, 14.5, 3.3) of the body)."""
    m = Inst("Model", "Windmill")
    meshes(m, "Windmill", base)
    m.add(collider("WindmillBody", (7.4, 12, 7.4), base * CF(0, 6, 0)))
    m.add(animated("World_WindmillBlades", base * CF(0, 14.5, 3.3), "Blades",
                   {"Anim": "Spin", "SpinAxis": (0, 0, 1), "SpinSpeed": 0.9}))
    parent.add(m)
    return m


def scenery(cf, idx):
    """Style-independent life around a plot: pier with a rowboat, beach sets, buoys."""
    def L(x, y, z):
        return cf * CF(x, y, z)
    m = Inst("Model", "Scenery")
    sea = WATER - TOP
    px = 40 if idx % 2 == 0 else -40
    pcf = L(px, sea + 2.6, 111)                        # pier runs outwards (+Z local)
    prop(m, "Pier", pcf)
    m.add(collider("PierDeck", (5.6, 1, 30), pcf * CF(0, -0.5, 14)))
    m.add(animated("World_Rowboat" + ("B" if idx % 3 == 0 else ""),
                   pcf * CF(6.5, -2.6, 25) * CF.ry(math.pi + 0.2), "Rowboat",
                   {"Anim": "Bob", "BobHeight": 0.25, "BobSpeed": 1.3 + idx * 0.05, "BobTilt": 3}))
    for side, z in ((1, 22), (-1, 58)):
        if (idx + (side > 0)) % 2 == 0:
            z += 12
        edge = PLOT_W / 2 * (1 - (abs(z) / (PLOT_D / 2)) ** 4.2) ** (1 / 4.2)
        prop(m, "BeachSet", L(side * (edge + 6.6), sea + 0.85, z) * CF.ry(side * math.pi / 2),
             1.0)
    for k, (x, z) in enumerate(((-35, 150), (15, 162), (70, 148))):
        m.add(animated("World_Buoy" + ("B" if k % 2 else ""), L(x, sea, z), "Buoy",
                       {"Anim": "Bob", "BobHeight": 0.35, "BobSpeed": 1.6 + k * 0.2,
                        "BobTilt": 6}))
    return m


# ------------------------------------------------------------------ sea & sky life
def sea_life(parent):
    m = Inst("Folder", "SeaLife")
    rng = random.Random(77)
    # sailboats circling in the open water between hub and plots (clear of every bridge)
    boats = ["Sailboat", "SailboatB", "Motorboat", "Sailboat"]
    for i, k in enumerate((0, 2, 4, 6)):
        a = (k + 0.5) * math.tau / 8
        c = (math.cos(a) * 200, WATER, math.sin(a) * 200)
        r = 26
        th = rng.uniform(0, math.tau)
        pos = (c[0] + math.cos(th) * r, WATER, c[2] + math.sin(th) * r)
        tangent = (-math.sin(th), 0, math.cos(th))
        m.add(animated("World_" + boats[i], CF.look(pos, (-tangent[0], 0, -tangent[2])),
                       boats[i], {"Anim": "Sail", "SailRadius": r, "SailSpeed": 0.22,
                                  "SailCenter": c}))
    # a ring of boats far out at sea, around the whole world
    for i, name in enumerate(("SailboatB", "Motorboat", "Sailboat")):
        th = i * math.tau / 3 + 0.4
        r = 570
        pos = (math.cos(th) * r, WATER, math.sin(th) * r)
        tangent = (-math.sin(th), 0, math.cos(th))
        m.add(animated("World_" + name, CF.look(pos, (-tangent[0], 0, -tangent[2])) * CF(0, 0, 0),
                       name, {"Anim": "Sail", "SailRadius": r, "SailSpeed": 0.016,
                              "SailCenter": (0, WATER, 0)}, scale=1.3))
    # lighthouse islet in one of the inner bays
    a = 1.5 * math.tau / 8
    lc = (math.cos(a) * 210, TOP, math.sin(a) * 210)
    lh = Inst("Model", "Lighthouse")
    meshes(lh, "LighthouseIsle", CF(*lc) * CF.ry(-a))
    lh.add(vcyl("Ground", 18, 6, (lc[0], TOP - 3, lc[2]), "#ffffff", transparency=1))
    lamp = animated("World_LighthouseLamp", CF(lc[0], TOP + 28.3, lc[2]), "Lamp",
                    {"Anim": "Spin", "SpinAxis": (0, 1, 0), "SpinSpeed": 0.8}, shadow=False)
    for p in lamp.children:
        if p.name == "Glow" and p.props["Size"]["Vector3"][0] > 5:
            p.props["Transparency"] = 0.55       # the light beams
    lh.add(lamp)
    m.add(lh)
    for k in range(6):
        b = a + (k - 2.5) * 0.09
        m.add(animated("World_Buoy" + ("B" if k % 2 else ""),
                       CF(math.cos(b) * 262, WATER, math.sin(b) * 262), "Buoy",
                       {"Anim": "Bob", "BobHeight": 0.35, "BobSpeed": 1.5 + k * 0.13,
                        "BobTilt": 6}))
    # channel buoys where the bridges leave the hub
    for k in range(8):
        for s in (-1, 1):
            b = k * math.tau / 8 + s * 0.13
            m.add(animated("World_Buoy" + ("B" if s > 0 else ""),
                           CF(math.cos(b) * 128, WATER, math.sin(b) * 128), "Buoy",
                           {"Anim": "Bob", "BobHeight": 0.3, "BobSpeed": 1.4 + k * 0.07,
                            "BobTilt": 5}))
    # dolphins and fish jumping (they wait under the sea between jumps)
    for k, (ang, r) in enumerate(((3.5, 215), (3.5, 228), (5.5, 205), (7.5, 220), (0.5, 550),
                                  (2.5, 560), (5.5, 545))):
        a = ang * math.tau / 8
        pos = (math.cos(a) * r, WATER, math.sin(a) * r)
        heading = rng.uniform(0, math.tau)
        m.add(animated("World_Dolphin", CF(*pos) * CF.ry(heading), "Dolphin",
                       {"Anim": "Jump", "JumpHeight": 7, "JumpLength": 18, "JumpDuration": 1.6,
                        "JumpPeriod": rng.uniform(6, 10), "AnimPhase": k * 1.7}, scale=1.2))
    for k in range(10):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(112, 150)
        if min(abs((a / (math.tau / 8)) % 1 - 0.5), 0.5) > 0.32:
            a += 0.4                          # keep them away from the bridges
        m.add(animated("World_Fish" + ("B" if k % 2 else ""),
                       CF(math.cos(a) * r, WATER, math.sin(a) * r) * CF.ry(rng.uniform(0, 6)),
                       "Fish", {"Anim": "Jump", "JumpHeight": 3, "JumpLength": 5,
                                "JumpDuration": 0.8, "JumpPeriod": rng.uniform(3.5, 7),
                                "AnimPhase": k * 0.9}, scale=1.4))
    parent.add(m)


def balloons(parent):
    m = Inst("Folder", "Balloons")
    rng = random.Random(8)
    for k, (ang, r, h) in enumerate(((0.6, 170, 58), (2.4, 300, 70), (4.3, 240, 50),
                                     (6.1, 420, 82), (7.3, 160, 64), (3.4, 470, 60))):
        a = ang * math.tau / 8
        name = ("Balloon", "BalloonB", "BalloonC")[k % 3]
        m.add(animated("World_" + name, CF(math.cos(a) * r, TOP + h, math.sin(a) * r)
                       * CF.ry(rng.uniform(0, 6)), name,
                       {"Anim": "Bob", "BobHeight": 3.5, "BobSpeed": 0.35 + k * 0.04,
                        "BobTilt": 3}, scale=1.6, shadow=False))
    parent.add(m)


# ------------------------------------------------------------------ plots
def plot(parent, idx, center):
    cx, cz = center
    col = PLOT_COLORS[idx]
    cf = CF.look((cx, TOP, cz), (-cx, 0, -cz))
    m = Inst("Model", f"Plot{idx + 1}", attrs={"PlotIndex": idx + 1, "PlotColor": col})

    def L(x, y, z):
        return cf * CF(x, y, z)
    m.add(collider("Pivot", (1, 1, 1), L(0, 0.5, 0), collide=False, touch=False))
    island = Inst("Model", "Island")
    meshes(island, "PlotIsland", cf)
    for size, pos in (((PLOT_W - 36, 6, PLOT_D), (0, -3, 0)), ((PLOT_W, 6, PLOT_D - 36), (0, -3, 0)),
                      ((PLOT_W + 18, 2, PLOT_D + 18), (0, -8.4, 0))):
        island.add(collider("Ground", size, L(*pos)))
    for x, z, w, d, h in ((-88, 98, 22, 18, 7), (88, 97, 20, 20, 9)):   # corner hills
        for kw, kh in ((1.0, 0.55), (0.66, 0.8), (0.36, 1.0)):
            island.add(collider("Hill", (w * kw, h * kh, d * kw), L(x, h * kh / 2 - 0.2, z)))
    m.add(island)
    # darker locked build area (the unlocked pad is built by the server)
    m.add(part("GridArea", (MAX_CELLS * CELL + 2, 0.3, MAX_CELLS * CELL + 2), L(0, 0.05, GRID_Z),
               GRASS_DARK, attrs={"Role": "Grass"}))
    m.add(collider("GridOrigin", (1, 1, 1), L(0, 0, GRID_Z), collide=False, touch=False))
    # respawn point (no visible pad) + owner sign arch
    m.add(collider("SpawnPoint", (2, 1, 2), L(0, 3, -92), collide=False, touch=False))
    # floating owner name over the entrance (PlotService fills in the text)
    sign = collider("OwnerSign", (1, 1, 1), L(0, 7, -100), collide=False, touch=False)
    bb = Inst("BillboardGui", "Sign", {"Size": U2(0, 360, 0, 70), "StudsOffset": V3(0, 0, 0),
                                       "MaxDistance": 260, "LightInfluence": 0,
                                       "AlwaysOnTop": False})
    lbl = Inst("TextLabel", "Text", {"Size": U2(1, 0, 1, 0), "BackgroundTransparency": 1,
                                     "Text": f"Empty Plot {idx + 1}", "TextScaled": True,
                                     "FontFace": FONT(), "TextColor3": C3("#ffffff")})
    lbl.add(Inst("UIStroke", "Stroke", {"Color": C3(col), "Thickness": 4}))
    bb.add(lbl)
    sign.add(bb)
    sign.attrs["Role"] = "Accent"
    m.add(sign)
    # default (Classic) decoration; PlotService swaps it for the owner's island style
    m.add(classic_decor(cf, random.Random(idx)))
    m.add(scenery(cf, idx))
    m.add(Inst("Folder", "Track"))
    m.add(Inst("Folder", "Pad"))
    parent.add(m)
    return cf


def exit_point(cf, w, d, direction):
    """Point on the plot rectangle edge (local half sizes) towards a world direction."""
    inv = cf.inverse()
    ld = inv.vector(direction)
    t = min((w / 2) / abs(ld[0]) if abs(ld[0]) > 1e-6 else 1e9,
            (d / 2) / abs(ld[2]) if abs(ld[2]) > 1e-6 else 1e9)
    return cf.point((ld[0] * t, 0, ld[2] * t))


def bridge(parent, name, p1, p2):
    m = Inst("Model", name)
    d = sub(p2, p1)
    length = math.hypot(d[0], d[2])
    f = norm((d[0], 0, d[2]))
    mid = ((p1[0] + p2[0]) / 2, TOP, (p1[2] + p2[2]) / 2)
    base = CF.look(mid, f)
    n = max(2, round(length / 6))
    step = length / n
    for i in range(n):
        lz = -length / 2 + step * (i + 0.5)
        meshes(m, "BridgePiece", base * CF(0, 0, lz) * CF.ry(math.pi / 2 * 0), 1.0)
    for i in range(1, max(2, int(length / 30))):
        lz = -length / 2 + length * i / max(2, int(length / 30))
        meshes(m, "BridgePillar", base * CF(0, -0.9, lz))
    m.add(collider("Deck", (13.6, 1, length + 4), base * CF(0, -0.5, 0)))
    for s in (-1, 1):
        m.add(collider("Rail", (0.6, 4, length), base * CF(s * 6.9, 1.6, 0)))
    parent.add(m)


def floating(parent):
    m = Inst("Model", "FloatingIsles")
    rng = random.Random(9)
    for k in range(6):
        a = (k + 0.5) * math.tau / 6 + rng.uniform(-0.2, 0.2)
        r = rng.uniform(610, 700)
        meshes(m, "FloatingIsle", CF(math.cos(a) * r, TOP + rng.uniform(45, 95), math.sin(a) * r)
               * CF.ry(rng.uniform(0, 6)), rng.uniform(1.6, 2.6), shadow=False)
    parent.add(m)


def sky(parent):
    """Blocky clouds, drifted slowly by the client."""
    m = Inst("Folder", "Clouds")
    rng = random.Random(21)
    for k in range(16):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(80, 950)
        meshes(m, "Cloud", CF(math.cos(a) * r, TOP + rng.uniform(110, 190), math.sin(a) * r)
               * CF.ry(rng.uniform(0, 6)), rng.uniform(1.4, 3.0), shadow=False)
    parent.add(m)


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
        bridge(bridges, f"HubBridge{i + 1}", mul(u, HUB_R - 4), add(p_plot, mul(u, 3)))
        j = (i + 1) % 8
        c1, c2 = cfs[i].p, cfs[j].p
        dv = norm(sub(c2, c1))
        e1 = exit_point(cfs[i], PLOT_W, PLOT_D, dv)
        e2 = exit_point(cfs[j], PLOT_W, PLOT_D, neg3(dv))
        bridge(bridges, f"RingBridge{i + 1}_{j + 1}", sub(e1, mul(dv, 3)), add(e2, mul(dv, 3)))
    floating(root)
    sky(root)
    sea_life(root)
    balloons(root)
    root.add(part("VoidCatcher", (2048, 4, 2048), CF(0, WATER - 30, 0), "#000000",
                  transparency=1, collide=False))
    for ix in (-1, 0, 1):
        for iz in (-1, 0, 1):
            root.add(part("Ocean", (2048, 2, 2048), CF(ix * 2048, WATER - 1, iz * 2048),
                          "#36b8f0", transparency=0.08, collide=False, touch=False,
                          reflectance=0.08, cast_shadow=False))
    return root


def neg3(v):
    return (-v[0], -v[1], -v[2])


def island_preview():
    """Tenth-scale plot island used by the style shop's 3D previews."""
    m = Inst("Model", "IslandPreview")
    meshes(m, "PlotIsland", CF(), 0.1)
    return m


if __name__ == "__main__":
    write_model(build(), "Workspace/Map.model.json")
    write_model(island_preview(), "ReplicatedStorage/Assets/IslandPreview.model.json")
