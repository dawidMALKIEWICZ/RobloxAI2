"""Main-island shops: Potions, Lucky Blocks, Cars, Island Styles.

Each builder returns a root empty; the shop's front faces local -Y.
"""
import math
from lib import box, cyl, empty, join, mat, sphere, text, torus


def _stall(name, title, c_main, c_dark, c_stripe, parent):
    """Shared stall shell: floor, back wall, pillars, counter, striped awning, sign."""
    wood = mat("Wood", "#b8773f")
    wood_d = mat("WoodDark", "#7a4a25")
    white = mat("White", "#ffffff")
    main = mat(f"{name}_main", c_main)
    dark = mat(f"{name}_dark", c_dark)
    stripe = mat(f"{name}_stripe", c_stripe)
    parts = [
        box("floor", (34, 22, 1.2), (0, 0, 0.6), wood_d, bevel=0.2),
        box("back", (34, 1.5, 16), (0, 10.25, 9.2), main, bevel=0.3),
        box("sideL", (1.5, 20, 16), (-16.25, 0, 9.2), main, bevel=0.3),
        box("sideR", (1.5, 20, 16), (16.25, 0, 9.2), main, bevel=0.3),
        box("counter", (30, 4, 4.5), (0, -7, 3.45), wood, bevel=0.3),
        box("counter_top", (31, 5, 0.8), (0, -7, 6.1), dark, bevel=0.2),
        box("pillarL", (2, 2, 18), (-16, -10, 9.6), dark, bevel=0.3),
        box("pillarR", (2, 2, 18), (16, -10, 9.6), dark, bevel=0.3),
        box("roof", (36, 24, 1.5), (0, 0, 18.6), dark, bevel=0.3),
    ]
    # slanted awning stripes over the front
    n = 9
    for i in range(n):
        w = 36 / n
        x = -18 + w * (i + 0.5)
        parts.append(box(f"awn{i}", (w, 9, 0.6), (x, -14.5, 17.2),
                         stripe if i % 2 == 0 else white, rot=(math.radians(-22), 0, 0)))
    # scalloped awning edge
    for i in range(n):
        w = 36 / n
        x = -18 + w * (i + 0.5)
        parts.append(cyl(f"scal{i}", w / 2, 0.6, (x, -18.6, 15.4),
                         stripe if i % 2 == 0 else white, verts=12, rot=(math.pi / 2, 0, 0)))
    shell = join(parts, f"{name}_Shell")
    shell.parent = parent
    # sign board on the roof
    sign = join([
        box("signbg", (26, 1.2, 7), (0, -2, 23.5), dark, bevel=0.4),
        box("signfr", (27.5, 1.0, 8.5), (0, -1.6, 23.5), white, bevel=0.4),
    ], f"{name}_SignBoard")
    sign.parent = parent
    t = text(f"{name}_SignText", title, 4.2, (0, -2.8, 23.3), white, extrude=0.3)
    t.parent = parent
    outline = text(f"{name}_SignTextShadow", title, 4.2, (0.25, -2.65, 23.05),
                   mat("Black", "#1b1b1b"), extrude=0.3)
    outline.parent = parent
    return shell


def potion(name, color, loc, s=1.0, parent=None):
    glass = mat(f"Potion_{color}", color, rough=0.15, emit=0.6)
    cork = mat("Cork", "#9c6b3c")
    x, y, z = loc
    p = join([
        sphere("body", 1.4 * s, (x, y, z + 1.4 * s), glass, subdiv=2),
        cyl("neck", 0.55 * s, 1.4 * s, (x, y, z + 3.2 * s), glass, verts=12),
        cyl("cork", 0.65 * s, 0.7 * s, (x, y, z + 4.2 * s), cork, verts=12),
    ], name)
    p.parent = parent
    return p


def lucky_block(name, loc, s=4.0, color="#ffcc1a", parent=None):
    yel = mat(f"Lucky_{color}", color, rough=0.35)
    edge = mat("LuckyEdge", "#e08a00")
    white = mat("White", "#ffffff")
    x, y, z = loc
    parts = [box("cube", (s, s, s), (x, y, z + s / 2), yel, bevel=s * 0.06)]
    for i, (dx, dy, rz) in enumerate([(0, -1, 0), (1, 0, math.pi / 2), (0, 1, math.pi),
                                      (-1, 0, -math.pi / 2)]):
        parts.append(text(f"q{i}", "?", s * 0.75,
                          (x + dx * (s / 2 + 0.02), y + dy * (s / 2 + 0.02), z + s / 2),
                          white, rot=(math.pi / 2, 0, rz), extrude=s * 0.02))
    # darker frame on edges
    t = s * 0.08
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box("e", (t, t, s * 1.01), (x + sx * s / 2, y + sy * s / 2, z + s / 2), edge))
    q = join(parts, name)
    q.parent = parent
    return q


def simple_car(name, loc, body="#e83a3a", parent=None, rz=0.0):
    bmat = mat(f"Car_{body}", body, rough=0.3)
    glass = mat("CarGlass", "#9fe6ff", rough=0.1)
    tire = mat("Tire", "#222222", rough=0.9)
    rim = mat("Rim", "#d9d9d9", metal=0.6, rough=0.3)
    x, y, z = loc
    parts = [
        box("body", (7, 13, 2.4), (x, y, z + 2.0), bmat, bevel=0.5),
        box("cab", (6, 6.5, 2.2), (x, y + 0.8, z + 4.2), glass, bevel=0.5),
        box("roof", (6.2, 5.5, 0.5), (x, y + 0.8, z + 5.4), bmat, bevel=0.2),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl("t", 1.5, 1.2, (x + sx * 3.5, y + sy * 4.2, z + 1.5), tire, verts=16,
                             rot=(0, math.pi / 2, 0)))
            parts.append(cyl("r", 0.8, 1.3, (x + sx * 3.5, y + sy * 4.2, z + 1.5), rim, verts=12,
                             rot=(0, math.pi / 2, 0)))
    c = join(parts, name)
    c.rotation_euler.z = rz
    c.parent = parent
    return c


def build_potion_shop(parent_loc=(0, 0, 0), rz=0.0):
    root = empty("Shop_Potions", parent_loc)
    root.rotation_euler.z = rz
    _stall("Potions", "POTIONS", "#9b3fe0", "#5e1f99", "#c86bff", root)
    shelf = mat("Wood", "#b8773f")
    cols = ["#ff3b3b", "#3bff6b", "#3bb8ff", "#ffd23b", "#ff6bf0", "#ff8a1f"]
    s = join([box(f"sh{i}", (28, 2.5, 0.6), (0, 8.6, 5 + i * 4.5), shelf) for i in range(3)],
             "Potions_Shelves")
    s.parent = root
    k = 0
    for row in range(3):
        for i in range(8):
            potion(f"Potion_{row}_{i}", cols[k % len(cols)], (-12 + i * 3.4, 8.6, 5.3 + row * 4.5),
                   0.65, root)
            k += 1
    for i, c in enumerate(cols[:4]):
        potion(f"PotionCounter_{i}", c, (-9 + i * 6, -7, 6.5), 1.0, root)
    return root


def build_lucky_shop(parent_loc=(0, 0, 0), rz=0.0):
    root = empty("Shop_LuckyBlocks", parent_loc)
    root.rotation_euler.z = rz
    _stall("Lucky", "LUCKY BLOCKS", "#ffb800", "#c46f00", "#ffe066", root)
    colors = ["#ffcc1a", "#3fa9ff", "#b54dff", "#ff3b6b"]
    for i, c in enumerate(colors):
        lucky_block(f"LuckyBlock_{i}", (-10.5 + i * 7, -7, 6.5), 4.5, c, root)
    for i in range(5):
        lucky_block(f"LuckyStack_{i}", (-12 + i * 6, 7, 1.2), 5, colors[i % 4], root)
    lucky_block("LuckyStackTop", (-3, 7, 6.2), 5, "#ffcc1a", root)
    lucky_block("LuckyStackTop2", (3, 7, 6.2), 5, "#ff3b6b", root)
    return root


def build_car_shop(parent_loc=(0, 0, 0), rz=0.0):
    root = empty("Shop_Cars", parent_loc)
    root.rotation_euler.z = rz
    _stall("Cars", "CAR DEALER", "#2f7dff", "#1747a8", "#7fb6ff", root)
    plat = mat("Turntable", "#e6e6e6", rough=0.3)
    stripe = mat("Cars_stripe", "#7fb6ff")
    t = join([cyl("tt", 9, 1, (0, 1, 1.7), plat, verts=40),
              torus("ring", 9, 0.35, (0, 1, 2.2), stripe, major=40, minor=8)],
             "Cars_Turntable")
    t.parent = root
    simple_car("Cars_Display", (0, 1, 2.2), "#ff2d2d", root, rz=math.radians(35))
    # small cars on the counter as "for sale" models
    m1 = simple_car("Cars_Mini1", (-12, -7, 6.5), "#33d17a", root, rz=math.radians(90))
    m1.scale = (0.35, 0.35, 0.35)
    m2 = simple_car("Cars_Mini2", (12, -7, 6.5), "#ffd23b", root, rz=math.radians(90))
    m2.scale = (0.35, 0.35, 0.35)
    return root


def build_style_shop(parent_loc=(0, 0, 0), rz=0.0):
    root = empty("Shop_IslandStyles", parent_loc)
    root.rotation_euler.z = rz
    _stall("Styles", "ISLAND STYLES", "#ff4fa3", "#b0236a", "#ff9fd0", root)
    cols = ["#ff3b3b", "#3bd16b", "#3b8bff", "#ffd23b", "#b54dff", "#ff8a1f", "#3be0e0",
            "#ffffff"]
    metal = mat("BucketMetal", "#c8c8c8", metal=0.5, rough=0.35)
    for i, c in enumerate(cols):
        x = (-13, -8.5, 8.5, 13)[i % 4] if i < 4 else -12 + (i % 4) * 8
        y = 7 if i < 4 else -7
        z = 1.2 if i < 4 else 6.5
        b = join([cyl("bucket", 2.2, 3.5, (x, y, z + 1.75), metal, verts=16, r2=2.6),
                  cyl("paint", 2.45, 0.3, (x, y, z + 3.4), mat(f"Paint_{c}", c, rough=0.2),
                      verts=16)], f"PaintBucket_{i}")
        b.parent = root
    # mini floating island preview on a pedestal
    grass = mat("Grass", "#4fc23a")
    dirt = mat("Dirt", "#8a5a2b")
    m = join([cyl("ped", 2.5, 4, (0, 7, 3.2), mat("Styles_dark", "#b0236a"), verts=16),
              cyl("g", 4, 1, (0, 7, 7.6), grass, verts=10),
              cyl("d", 4, 3, (0, 7, 5.6), dirt, verts=10, r2=1.5)], "Styles_MiniIsland")
    m.parent = root
    return root
