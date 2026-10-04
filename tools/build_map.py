"""Generates src/Workspace/Map.model.json - island world in the sea.

Round hub island (market stalls around a plaza with a giant golden die) and 8 rounded player
islands, all sitting in the sea and joined by plank bridges on stone pillars. Visible geometry is
meshes baked by blender/models/world.py; invisible Parts give the ground its collision.
Plot local space: origin = island top centre, -Z points at the hub.
"""
import math
import random

from meshparts import mesh_parts
from rbx import CF, Inst, add, mul, norm, part, sub, text_sign, vcyl, write_model

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
    m.add(deco)
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
    meshes(m, "SignArch", L(0, 0, -104))
    for x in (-9, 9):
        m.add(collider("SignPost", (1.4, 13, 1.4), L(x, 6.5, -104)))
    s = text_sign("OwnerSign", f"Empty Plot {idx + 1}", 40, L(0, 10.5, -104.45), (18, 5.6, 0.2),
                  col)
    s.attrs["Role"] = "Accent"
    m.add(s)
    m.add(text_sign("OwnerSignBack", f"PLOT {idx + 1}", 40, L(0, 10.5, -103.55) * CF.ry(math.pi),
                    (18, 5.6, 0.2), col))
    # plot-coloured flags either side of the entrance
    for x in (-14, 14):
        m.add(part("FlagPole", (0.5, 12, 0.5), L(x, 6, -100), "#ffffff"))
        m.add(part("Flag", (0.2, 3, 4.5), L(x, 10.2, -102.3), col, attrs={"Role": "Accent"}))
    decor = Inst("Model", "Decor")
    rng = random.Random(idx)
    for k, (x, z) in enumerate(DECOR_SPOTS):
        kind = ("TreeRound", "TreePine", "Rock")[k % 3]
        prop(decor, kind, L(x, 0, z) * CF.ry(rng.uniform(0, 6)), rng.uniform(1.5, 1.9))
        if k % 3 == 2:
            prop(decor, "Bush", L(x + 6, 0, z + 3), 1.3)
    m.add(decor)
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
