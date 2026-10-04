"""All world models, low-poly and mobile friendly (1 unit = 1 stud, Z up, fronts face -Y).

Run: <bpy python> all_models.py [name ...]
Writes assets/models/<name>.fbx/.blend and renders/models/<name>.png + renders/models_sheet.png
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mlib as L  # noqa: E402

CREAM = "#fff4e0"
WHITE = "#ffffff"
DARK = "#2b2f3a"
GLASS = "#a6e6ff"
WOOD = "#b9783f"
WOOD_D = "#8a5a2b"
LEAF = "#5cc93f"
LEAF_D = "#43a82f"


# ------------------------------------------------------------------ shared pieces
def mini_car(x, y, z, color, s=1.0):
    L.box((2.6 * s, 1.4 * s, 0.7 * s), (x, y, z + 0.6 * s), color, bevel=0.18 * s)
    L.box((1.4 * s, 1.25 * s, 0.6 * s), (x - 0.1 * s, y, z + 1.2 * s), color, bevel=0.18 * s)
    L.box((1.2 * s, 1.3 * s, 0.38 * s), (x - 0.1 * s, y, z + 1.22 * s), GLASS)
    for dx in (-0.8, 0.8):
        for dy in (-0.68, 0.68):
            L.cyl(0.32 * s, 0.25 * s, (x + dx * s, y + dy * s, z + 0.32 * s), DARK,
                  rot=(math.pi / 2, 0, 0), verts=8)


def shop_shell(main, trim, w=11.0, d=7.5, h=4.8):
    """Base slab, walls, band, door, window, flat roof with overhang."""
    L.box((w + 2, d + 2.5, 0.4), (0, 0.6, 0.2), "#e8e2d6", bevel=0.12)
    L.box((w, d, h), (0, 1, 0.4 + h / 2), main, bevel=0.15)
    L.box((w + 0.06, d + 0.06, 0.6), (0, 1, 0.7), trim, bevel=0.1)
    # window + door on the front
    fy = 1 - d / 2
    L.box((5.6, 0.3, 2.6), (1.6, fy - 0.08, 2.6), trim, bevel=0.1)
    L.box((5.1, 0.3, 2.2), (1.6, fy - 0.16, 2.6), GLASS, rough=0.1, alpha=0.45)
    L.box((2.2, 0.3, 3.2), (-3.6, fy - 0.08, 2.0), trim, bevel=0.1)
    L.box((1.7, 0.3, 2.8), (-3.6, fy - 0.16, 1.9), GLASS, rough=0.1, alpha=0.45)
    L.box((0.12, 0.2, 0.7), (-3.0, fy - 0.32, 2.0), WHITE)
    return fy


def awning(y, z, width, n, c1, c2=WHITE):
    for i in range(n):
        x = -width / 2 + width / n * (i + 0.5) + 1.6
        L.box((width / n, 1.8, 0.2), (x, y - 0.75, z), c1 if i % 2 == 0 else c2,
              rot=(math.radians(-20), 0, 0))
    L.scallops(width, n, (1.6, y - 1.6, z - 0.32), c1, c2, depth=0.2)


def sign(text, y, z, w, bg, fg, frame=WHITE):
    L.prism(L.rounded_rect(w + 0.5, 2.3, 0.6), 0.4, (0, y, z), frame)
    L.prism(L.rounded_rect(w, 1.8, 0.45), 0.45, (0, y - 0.03, z), bg)
    L.text(text, 1.25, (0, y - 0.3, z), fg, extrude=0.08)


# ------------------------------------------------------------------ market stalls
def stall(title, main, main_d, icon, goods, w=12.0, d=7.0):
    """Blocky market stall: wooden frame, striped counter, sloped striped awning, big sign."""
    wood, wood_d, plank = "#b9783f", "#8a5a2b", "#d9a066"
    hb = d / 2
    # floor
    L.box((w + 1.2, d + 1.2, 0.5), (0, 0, 0.25), "#c9a27a", bevel=0.06)
    for i in range(5):
        L.box((w + 1.0, (d + 1) / 5 - 0.12, 0.1), (0, -hb - 0.5 + (d + 1) / 5 * (i + 0.5), 0.52),
              plank if i % 2 else "#cf9658")
    # posts
    for x in (-w / 2, w / 2):
        L.box((0.8, 0.8, 7.0), (x, -hb + 0.4, 3.95), wood, bevel=0.05)
        L.box((0.8, 0.8, 8.2), (x, hb - 0.4, 4.6), wood, bevel=0.05)
    # back wall of planks
    for i in range(6):
        L.box((w - 0.6, 0.4, 1.38), (0, hb - 0.4, 1.2 + i * 1.4), wood if i % 2 else wood_d)
    # side rails
    for x in (-w / 2, w / 2):
        L.box((0.5, d - 0.8, 0.5), (x, 0, 3.0), wood_d)
    # shelves with goods
    for k, z in enumerate((3.3, 5.3)):
        L.box((w - 1.2, 1.4, 0.3), (0, hb - 1.3, z), wood_d, bevel=0.04)
        goods(z + 0.15, hb - 1.3, k)
    # counter with striped front
    L.box((w - 0.4, 1.6, 2.6), (0, -hb + 0.9, 1.8), "#ffffff")
    n = 5
    for i in range(n):
        L.box((w - 0.36, 0.1, 2.6 / n), (0, -hb + 0.06, 0.5 + 2.6 / n * (i + 0.5)),
              main if i % 2 == 0 else "#ffffff")
    L.box((w + 0.4, 2.2, 0.4), (0, -hb + 0.9, 3.3), plank, bevel=0.05)
    L.box((w + 0.6, 0.25, 0.4), (0, -hb - 0.2, 3.3), wood_d)
    # sloped striped awning (back high, front low)
    stripes = 8
    ang = math.radians(16)
    depth = d + 2.6
    for i in range(stripes):
        x = -w / 2 - 0.6 + (w + 1.2) / stripes * (i + 0.5)
        L.box(((w + 1.2) / stripes, depth, 0.45), (x, -0.6, 8.3), main if i % 2 == 0 else "#ffffff",
              rot=(ang, 0, 0))
    fz = 8.3 - math.sin(ang) * depth / 2
    fy = -0.6 - math.cos(ang) * depth / 2
    for i in range(stripes):
        x = -w / 2 - 0.6 + (w + 1.2) / stripes * (i + 0.5)
        L.box(((w + 1.2) / stripes, 0.3, 1.1), (x, fy, fz - 0.45), "#ffffff" if i % 2 == 0 else main)
    L.box((w + 1.4, 0.36, 0.3), (0, fy, fz + 0.05), main_d)
    # sign on two posts above the awning
    for x in (-3.0, 3.0):
        L.box((0.5, 0.5, 3.0), (x, 1.2, 10.0), wood_d)
    L.box((w + 0.6, 0.8, 3.6), (0, 1.0, 12.2), main_d, bevel=0.15)
    L.box((w - 0.2, 0.85, 2.9), (0, 0.98, 12.2), main, bevel=0.1)
    L.outlined_text(title, min(2.4, 12.5 / len(title)), (1.0, 0.45, 12.1), "#ffffff")
    icon(-w / 2 + 1.4, 0.45, 12.2)


def g_cars(z, y, k):
    cols = ("#ff3b3b", "#3b8bff", "#33c25a", "#ffd23b")
    for i in range(4):
        x = -4.2 + i * 2.8
        if k == 0:
            L.box((1.6, 0.9, 0.5), (x, y, z + 0.3), cols[i])
            L.box((0.9, 0.85, 0.4), (x - 0.1, y, z + 0.72), "#a6e6ff")
        else:
            L.cyl(0.55, 0.45, (x, y, z + 0.55), DARK, rot=(math.pi / 2, 0, 0), verts=8)


def g_styles(z, y, k):
    cols = ("#ff3b3b", "#3b8bff", "#33c25a", "#ffd23b", "#b54dff")
    for i in range(5):
        x = -4.4 + i * 2.2
        L.box((1.1, 1.0, 1.0), (x, y, z + 0.5), "#d0d4dc")
        L.box((1.12, 1.02, 0.25), (x, y, z + 0.9), cols[(i + k) % 5])


def g_potions(z, y, k):
    cols = ("#ff5fd2", "#7dff6b", "#5cc8ff", "#ffd23b", "#b54dff")
    for i in range(5):
        x = -4.4 + i * 2.2
        L.box((0.9, 0.9, 0.9), (x, y, z + 0.45), cols[(i + k) % 5], emit=0.3)
        L.box((0.4, 0.4, 0.4), (x, y, z + 1.1), "#e8e8ee")
        L.box((0.46, 0.46, 0.2), (x, y, z + 1.38), WOOD)


def g_dice(z, y, k):
    cols = ("#ffcc1a", "#5cc8ff", "#b54dff", "#ff3b6b", "#ffffff")
    for i in range(5):
        x = -4.4 + i * 2.2
        L.box((1.0, 1.0, 1.0), (x, y, z + 0.5), cols[(i + k) % 5], rot=(0, 0, 0.2 * (i % 2)))


def ic_car(x, y, z):
    L.box((1.7, 0.4, 0.75), (x, y, z - 0.25), "#ff3b3b")
    L.box((0.95, 0.42, 0.55), (x - 0.1, y, z + 0.35), "#ff3b3b")
    L.box((0.7, 0.44, 0.35), (x - 0.1, y - 0.01, z + 0.35), "#a6e6ff")
    for dx in (-0.55, 0.55):
        L.box((0.5, 0.45, 0.5), (x + dx, y - 0.02, z - 0.7), DARK)


def ic_brush(x, y, z):
    L.box((0.35, 0.4, 1.6), (x, y, z - 0.3), WOOD, rot=(0, math.radians(30), 0))
    L.box((0.7, 0.42, 0.7), (x + 0.45, y, z + 0.6), "#ff6fb5", rot=(0, math.radians(30), 0))


def ic_potion(x, y, z):
    L.box((1.2, 0.4, 1.2), (x, y, z - 0.25), "#7dff6b", emit=0.3)
    L.box((0.5, 0.42, 0.55), (x, y, z + 0.6), "#e8e8ee")
    L.box((0.6, 0.44, 0.25), (x, y, z + 0.95), WOOD)


def ic_dice(x, y, z):
    L.box((1.5, 0.4, 1.5), (x, y, z), "#ffffff", rot=(0, math.radians(15), 0))
    for dx, dz in ((-0.4, 0.4), (0, 0), (0.4, -0.4)):
        L.box((0.28, 0.42, 0.28), (x + dx, y - 0.02, z + dz), "#e0263c",
              rot=(0, math.radians(15), 0))


def shop_cars():
    stall("CARS", "#2f8bff", "#1d55c4", ic_car, g_cars)


def shop_styles():
    stall("STYLES", "#ff6fb5", "#c2307c", ic_brush, g_styles)


def shop_potions():
    stall("POTIONS", "#a94dff", "#6a1fc9", ic_potion, g_potions)


def shop_dice():
    stall("DICE", "#ffb81a", "#e07a00", ic_dice, g_dice)


def fountain():
    # octagon plaza
    L.cyl(12, 0.3, (0, 0, 0.15), "#efe6d2", verts=8, rot=(0, 0, math.pi / 8))
    L.cyl(9.5, 0.34, (0, 0, 0.17), "#e3d8bf", verts=8, rot=(0, 0, math.pi / 8))
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        L.box((2.4, 0.6, 0.1), (math.cos(a) * 10.8, math.sin(a) * 10.8, 0.33), "#d9ccad",
              rot=(0, 0, a + math.pi / 2))
    # basin
    L.cyl(6.2, 1.4, (0, 0, 1.0), "#c9c2b3", verts=8, rot=(0, 0, math.pi / 8), bevel=0.12)
    L.cyl(5.6, 0.2, (0, 0, 1.6), "#5fd3ff", verts=8, rot=(0, 0, math.pi / 8), rough=0.1,
          emit=0.25)
    L.cyl(0.9, 3.4, (0, 0, 3.0), "#c9c2b3", verts=8)
    L.cyl(2.6, 0.6, (0, 0, 4.6), "#c9c2b3", verts=8, r2=1.6, rot=(math.pi, 0, 0))
    L.cyl(2.3, 0.15, (0, 0, 4.88), "#5fd3ff", verts=8, rough=0.1, emit=0.25)
    # water jet
    L.cyl(0.45, 1.6, (0, 0, 5.7), "#9fe8ff", verts=6, r2=0.15, emit=0.5)
    L.sphere(0.6, (0, 0, 6.6), "#bff1ff", emit=0.6, subdiv=2)


def tree_round():
    L.box((1.2, 1.2, 4.2), (0, 0, 2.1), WOOD_D)
    blocks = [((5.2, 5.2, 3.2), (0, 0, 5.6), LEAF), ((3.7, 3.7, 2.1), (0.25, 0.15, 8.1), "#6bd94a"),
              ((2.3, 2.1, 1.7), (2.4, -0.9, 5.1), LEAF_D), ((2.1, 2.3, 1.5), (-2.3, 1.0, 6.3), LEAF_D),
              ((1.9, 1.7, 1.3), (-0.5, -2.45, 6.9), "#6bd94a")]
    for size, pos, c in blocks:
        L.box(size, pos, c)


def tree_pine():
    L.box((0.9, 0.9, 2.0), (0, 0, 1.0), WOOD_D)
    for i, (w, z) in enumerate(((5.0, 2.6), (3.8, 4.2), (2.6, 5.7), (1.4, 7.0))):
        L.box((w, w, 1.5), (0, 0, z), "#2f9e4a" if i % 2 == 0 else "#3ab456")
        L.box((w * 0.9, w * 0.9, 0.25), (0, 0, z + 0.86), "#4cc46a")


def tree_palm():
    for i in range(6):
        L.box((0.8, 0.8, 1.1), (i * i * 0.06, 0, 0.55 + i * 1.05), WOOD if i % 2 else WOOD_D,
              rot=(0, math.radians(4 * i), 0))
    tx, tz = 6 * 6 * 0.06, 6.8
    for k in range(4):
        a = k * math.pi / 2
        L.box((3.6, 1.2, 0.35), (tx + math.cos(a) * 1.8, math.sin(a) * 1.8, tz - 0.2),
              LEAF if k % 2 else LEAF_D, rot=(0, math.radians(15), a))
    L.box((1.4, 1.4, 0.6), (tx, 0, tz + 0.1), LEAF)
    for dx, dy in ((0.5, -0.4), (-0.3, 0.5)):
        L.box((0.5, 0.5, 0.5), (tx + dx, dy, tz - 0.6), "#6b4423")


def bush():
    for size, pos, c in (((2.6, 2.4, 1.8), (0, 0, 0.9), LEAF), ((1.8, 1.6, 1.4), (1.5, 0.4, 0.7), "#6bd94a"),
                         ((1.6, 1.6, 1.2), (-1.4, 0.3, 0.6), LEAF_D), ((1.3, 1.3, 1.0), (0.3, 0.2, 2.1), "#6bd94a")):
        L.box(size, pos, c)
    for x, z in ((-0.6, 1.4), (0.5, 1.6), (1.4, 1.2)):
        L.box((0.35, 0.35, 0.35), (x, -1.25, z), "#ff6fb5")


def rock():
    L.box((2.6, 2.0, 1.6), (0, 0, 0.8), "#9aa0ad", rot=(0.1, 0.05, 0.4))
    L.box((1.6, 1.4, 1.1), (1.5, 0.6, 0.55), "#868c99", rot=(0.05, 0.1, -0.3))
    L.box((1.0, 1.0, 0.8), (-1.3, -0.5, 0.4), "#a9afbb", rot=(0.1, 0, 0.8))


def bridge_segment():
    """12 studs long, 10 wide walking surface at z=0 (tile it end to end)."""
    for i in range(6):
        L.box((9.6, 1.8, 0.5), (0, -5 + i * 2 + 1, -0.25), "#d99a5b" if i % 2 else "#c9874a",
              bevel=0.08)
    for x in (-4.4, 4.4):
        L.box((0.6, 12, 0.6), (x, 0, -0.75), WOOD_D)
        for y in (-5.5, 0.5):
            L.box((0.7, 0.7, 3.4), (x * 1.1, y, 1.2), WOOD_D, bevel=0.08)
            L.box((0.9, 0.9, 0.3), (x * 1.1, y, 2.95), WHITE, bevel=0.06)
        L.box((0.4, 12, 0.4), (x * 1.1, 0, 2.3), "#f2d29b")
        L.box((0.3, 12, 0.3), (x * 1.1, 0, 1.2), "#f2d29b")


def plot_sign():
    for x in (-5.2, 5.2):
        L.box((0.8, 0.8, 8.0), (x, 0, 4.0), WOOD_D, bevel=0.1)
        L.box((1.2, 1.2, 0.4), (x, 0, 8.1), WHITE, bevel=0.08)
    L.prism(L.rounded_rect(11.4, 3.6, 0.7), 0.6, (0, 0, 6.4), WHITE)
    L.prism(L.rounded_rect(10.6, 2.9, 0.5), 0.7, (0, 0, 6.4), "#ff5a5a")


def spawn_pad():
    L.cyl(5.0, 0.5, (0, 0, 0.25), WHITE, verts=8, rot=(0, 0, math.pi / 8), bevel=0.1)
    L.cyl(3.8, 0.6, (0, 0, 0.3), "#ff5a5a", verts=8, rot=(0, 0, math.pi / 8))
    L.cyl(1.2, 0.65, (0, 0, 0.32), WHITE, verts=8, rot=(0, 0, math.pi / 8))


def lamp_post():
    L.cyl(0.6, 0.4, (0, 0, 0.2), DARK, verts=8)
    L.cyl(0.18, 5.5, (0, 0, 2.95), DARK, verts=6)
    L.box((1.4, 1.4, 0.25), (0, 0, 5.8), DARK)
    L.box((1.0, 1.0, 1.0), (0, 0, 5.2), "#fff3b0", emit=3.0)
    L.cyl(0.9, 0.6, (0, 0, 6.2), DARK, verts=4, r2=0.1, rot=(0, 0, math.pi / 4))


MODELS = {
    "shop_cars": shop_cars, "shop_styles": shop_styles, "shop_potions": shop_potions,
    "shop_dice": shop_dice, "fountain": fountain, "tree_round": tree_round,
    "tree_pine": tree_pine, "tree_palm": tree_palm, "bush": bush, "rock": rock,
    "bridge_segment": bridge_segment, "plot_sign": plot_sign, "spawn_pad": spawn_pad,
    "lamp_post": lamp_post,
}


def sheet(names):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    cols = 4
    w, h = 450, 350
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (cols * w, rows * h), (240, 246, 255))
    dr = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        p = os.path.join(L.ROOT, "renders", "models", n + ".png")
        if os.path.exists(p):
            im = Image.open(p).convert("RGB").resize((w, h))
            img.paste(im, ((i % cols) * w, (i // cols) * h))
            dr.text(((i % cols) * w + 10, (i // cols) * h + 8), n, fill=(20, 20, 30))
    img.save(os.path.join(L.ROOT, "renders", "models_sheet.png"))


if __name__ == "__main__":
    names = sys.argv[1:] or list(MODELS)
    report = []
    for n in names:
        L.reset()
        MODELS[n]()
        tris = L.export(n)
        report.append((n, tris))
        L.studio(ground_color="#8fe06a")
        if n.startswith("shop"):
            L.frame(elev=12, azim=-24, margin=1.6)
        if n == "bridge_segment":
            bpy_ground = L.bpy.data.objects.get("_ground")
            bpy_ground.location.z = -4
        if not n.startswith("shop"):
            L.frame()
        L.render(os.path.join(L.ROOT, "renders", "models", n + ".png"))
    sheet(list(MODELS))
    for n, t in report:
        print(f"TRIS {n:16s} {t}")
