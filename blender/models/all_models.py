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


# ------------------------------------------------------------------ models
def shop_cars():
    blue, blue_d = "#2f7dff", "#1d55c4"
    fy = shop_shell(CREAM, blue)
    L.box((12.0, 8.6, 0.5), (0, 1, 5.45), blue, bevel=0.15)
    awning(fy, 4.6, 6.4, 4, blue)
    sign("CARS", 1.0, 7.0, 7.5, blue_d, "#ffd23b")
    for x in (-2.6, 2.6):
        L.box((0.3, 0.3, 0.9), (x, 1.2, 6.0), DARK)
    mini_car(3.6, 3.0, 5.7, "#ff3b3b", s=1.0)
    for i in range(3):
        L.torus(0.5, 0.22, (6.4, -2.6, 0.62 + i * 0.44), DARK)


def shop_styles():
    pink, pink_d = "#ff6fb5", "#c2307c"
    fy = shop_shell(CREAM, pink)
    # gable roof
    L.prism([(-6.2, 0), (6.2, 0), (0, 3.0)], 8.8, (0, 1, 5.2), pink, rot=(0, 0, 0))
    L.prism([(-6.5, -0.2), (6.5, -0.2), (0, 3.25)], 0.3, (0, 1 - 4.5, 5.2), WHITE)
    awning(fy, 4.6, 6.4, 4, pink)
    sign("STYLES", -4.2, 6.6, 7.5, pink_d, WHITE)
    # palette on the roof side
    L.cyl(1.6, 0.25, (4.2, 2.5, 8.0), "#f2d29b", rot=(math.radians(70), 0, 0), verts=10)
    for i, c in enumerate(("#ff3b3b", "#ffd23b", "#3bd16b", "#3b8bff")):
        a = math.radians(30 + i * 60)
        L.sphere(0.32, (4.2 + math.cos(a) * 0.9, 2.3, 8.0 + math.sin(a) * 0.9), c)
    for i, c in enumerate(("#3b8bff", "#ffd23b")):
        x = 5.8 + i * 1.4
        L.cyl(0.55, 0.9, (x, -3.0, 0.85), "#d0d4dc", verts=8)
        L.cyl(0.5, 0.1, (x, -3.0, 1.32), c, verts=8)


def shop_potions():
    purple, purple_d = "#a94dff", "#6a1fc9"
    L.cyl(6.2, 0.4, (0, 0.5, 0.2), "#e8e2d6", verts=10)
    L.cyl(4.6, 5.0, (0, 1, 2.9), "#f3e6ff", verts=10)
    L.cyl(4.65, 0.6, (0, 1, 0.7), purple, verts=10)
    # witch-hat roof
    L.cyl(5.6, 0.5, (0, 1, 5.6), purple_d, verts=10)
    L.cyl(4.6, 4.6, (0, 1, 8.1), purple, r2=0.6, verts=10)
    L.cyl(0.7, 1.4, (0.6, 1.2, 10.9), purple, r2=0.2, verts=6, rot=(0, math.radians(25), 0))
    L.cyl(4.7, 0.5, (0, 1, 6.4), "#ffd23b", r2=4.4, verts=10)
    # door + window
    L.box((2.0, 0.6, 3.0), (-1.4, -3.5, 1.9), purple_d)
    L.box((1.6, 0.6, 2.6), (-1.4, -3.65, 1.8), "#7a3b1f")
    L.cyl(0.85, 0.5, (2.0, -3.4, 3.0), "#b2f5ff", rot=(math.pi / 2, 0, 0), verts=10,
          alpha=0.5)
    sign("POTIONS", -4.6, 5.5, 6.4, purple_d, "#7dff6b")
    # big potion on the side + cauldron with glowing brew
    L.sphere(1.2, (4.6, -2.6, 1.6), "#ff5fd2", emit=0.6)
    L.cyl(0.4, 0.8, (4.6, -2.6, 3.0), "#ffb3ef", verts=8)
    L.cyl(0.5, 0.4, (4.6, -2.6, 3.55), WOOD, verts=8)
    L.cyl(1.2, 1.2, (-5.2, -2.4, 1.0), DARK, r2=1.4, verts=10)
    L.cyl(1.1, 0.15, (-5.2, -2.4, 1.62), "#7dff6b", verts=10, emit=1.5)


def shop_dice():
    yel, yel_d = "#ffc61a", "#e58a00"
    fy = shop_shell(CREAM, yel_d)
    L.box((12.0, 8.6, 0.5), (0, 1, 5.45), yel, bevel=0.15)
    awning(fy, 4.6, 6.4, 4, yel)
    sign("DICE", fy - 0.6, 7.0, 6.5, yel_d, WHITE)
    # giant dice on the roof
    import mathutils
    rot = mathutils.Euler((math.radians(15), math.radians(-10), math.radians(30)))
    c = mathutils.Vector((2.4, 2.6, 7.9))
    L.box((3.6, 3.6, 3.6), tuple(c), WHITE, rot=tuple(rot), bevel=0.45)
    m = rot.to_matrix()
    for p in [(0, -1.81, 0), (-0.9, -1.81, 0.9), (0.9, -1.81, -0.9), (1.81, 0.8, 0.8),
              (1.81, -0.8, -0.8), (0, 0, 1.81)]:
        v = c + m @ mathutils.Vector(p)
        L.sphere(0.32, tuple(v), "#e0263c")
    for i, col in enumerate(("#3fa9ff", "#b54dff")):
        L.box((1.2, 1.2, 1.2), (5.8, -2.6 + i * 1.5, 1.0), col, bevel=0.2, rot=(0, 0, 0.3 * i))


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
    L.cyl(0.55, 4.0, (0, 0, 2.0), WOOD_D, verts=6, r2=0.35)
    L.sphere(2.6, (0, 0, 5.2), LEAF, scale=(1, 1, 0.9), subdiv=2)
    L.sphere(1.8, (1.3, 0.5, 6.5), "#6bd94a", subdiv=2)
    L.sphere(1.6, (-1.2, -0.4, 6.1), LEAF_D, subdiv=2)


def tree_pine():
    L.cyl(0.45, 2.0, (0, 0, 1.0), WOOD_D, verts=6)
    for i, (r, h, z) in enumerate(((3.0, 3.0, 3.2), (2.3, 2.6, 5.0), (1.5, 2.2, 6.6))):
        L.cyl(r, h, (0, 0, z), "#2f9e4a" if i % 2 == 0 else "#3ab456", r2=0.15, verts=7,
              rot=(0, 0, i * 0.4))


def tree_palm():
    import mathutils
    pts = []
    for i in range(5):
        p = mathutils.Vector((0.25 * i * i * 0.18, 0, 1.1 * i + 0.6))
        pts.append(p)
        L.cyl(0.42 - i * 0.04, 1.5, tuple(p), WOOD if i % 2 else WOOD_D, verts=6,
              r2=0.34 - i * 0.04, rot=(0, math.radians(8 * i), 0))
    top = pts[-1] + mathutils.Vector((0.2, 0, 0.7))
    for k in range(6):
        a = k * math.tau / 6
        L.box((3.2, 0.9, 0.15), (top.x + math.cos(a) * 1.5, top.y + math.sin(a) * 1.5, top.z - 0.3),
              LEAF if k % 2 else LEAF_D, rot=(0, math.radians(18), a))
    L.sphere(0.35, (top.x + 0.3, top.y - 0.3, top.z - 0.4), "#6b4423")


def bush():
    L.sphere(1.3, (0, 0, 0.9), LEAF, scale=(1.2, 1, 0.85), subdiv=2)
    L.sphere(0.9, (1.1, 0.5, 0.9), "#6bd94a", subdiv=2)
    L.sphere(0.8, (-1.0, 0.3, 0.7), LEAF_D, subdiv=2)
    for x, z in ((-0.6, 1.5), (0.4, 1.6), (1.2, 1.3)):
        L.sphere(0.2, (x, -0.95, z), "#ff6fb5")


def rock():
    import random
    rng = random.Random(4)
    for o in (L.sphere(1.5, (0, 0, 0.8), "#9aa0ad", scale=(1.3, 1, 0.8), subdiv=2),
              L.sphere(0.9, (1.4, 0.5, 0.5), "#868c99", scale=(1, 1, 0.8), subdiv=2)):
        for v in o.data.vertices:
            v.co *= rng.uniform(0.88, 1.1)


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
        if n == "bridge_segment":
            bpy_ground = L.bpy.data.objects.get("_ground")
            bpy_ground.location.z = -4
        L.frame()
        L.render(os.path.join(L.ROOT, "renders", "models", n + ".png"))
    sheet(list(MODELS))
    for n, t in report:
        print(f"TRIS {n:16s} {t}")
