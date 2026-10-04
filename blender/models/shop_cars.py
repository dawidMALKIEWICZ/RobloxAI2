"""Model 1: Car Dealer - small cartoon showroom (~16 x 11 studs). Front faces -Y."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mlib as L  # noqa: E402

BLUE = "#2f7dff"
BLUE_D = "#1d55c4"
CREAM = "#fff4e0"
GLASS = "#9fe3ff"
YELLOW = "#ffd23b"
RED = "#ff3b3b"
DARK = "#2b2f3a"


def cartoon_car(x, y, z, s=1.0, color=RED, rotz=0.0):
    parts = []
    parts.append(L.box((3.2 * s, 1.7 * s, 0.9 * s), (x, y, z + 0.75 * s), color, bevel=0.35 * s,
                       segs=3, smooth=True))
    parts.append(L.box((1.8 * s, 1.5 * s, 0.85 * s), (x - 0.15 * s, y, z + 1.45 * s), color,
                       bevel=0.35 * s, segs=3, smooth=True))
    parts.append(L.box((1.55 * s, 1.55 * s, 0.55 * s), (x - 0.15 * s, y, z + 1.5 * s), GLASS,
                       bevel=0.2 * s, segs=3, smooth=True, rough=0.1))
    for dx in (-1.0, 1.0):
        for dy in (-0.82, 0.82):
            parts.append(L.cyl(0.42 * s, 0.32 * s, (x + dx * s, y + dy * s, z + 0.42 * s), DARK,
                               rot=(math.pi / 2, 0, 0), bevel=0.08 * s))
            parts.append(L.cyl(0.2 * s, 0.34 * s, (x + dx * s, y + dy * s, z + 0.42 * s), "#e8e8ee",
                               rot=(math.pi / 2, 0, 0), bevel=0.04 * s))
    for dy in (-0.5, 0.5):
        parts.append(L.sphere(0.16 * s, (x - 1.58 * s, y + dy * s, z + 0.9 * s), "#fff7b0",
                              emit=2.0))
    for o in parts:
        o.rotation_euler.z += rotz
        if rotz:
            # rotate around the car centre
            import mathutils
            rel = o.location - mathutils.Vector((x, y, z))
            rel.rotate(mathutils.Euler((0, 0, rotz)))
            o.location = mathutils.Vector((x, y, z)) + rel
    return parts


def build():
    L.reset()
    # base platform with a step
    L.box((18, 13, 0.6), (0, 0.5, 0.3), "#e9e4da", bevel=0.25)
    L.box((8, 1.6, 0.3), (0, -6.6, 0.15), "#d9d3c7", bevel=0.12)
    # main body
    L.box((15, 9.5, 6.2), (0, 1.5, 3.7), CREAM, bevel=0.45, segs=3)
    L.box((15.1, 9.6, 1.0), (0, 1.5, 1.1), BLUE, bevel=0.3)
    # roof slab + parapet
    L.box((16.4, 10.8, 0.9), (0, 1.5, 7.2), BLUE, bevel=0.35, segs=3)
    L.box((16.0, 10.4, 0.5), (0, 1.5, 7.85), BLUE_D, bevel=0.2)
    # big showroom window (front) with frame and mullions
    L.box((11.4, 0.5, 4.2), (0, -3.15, 4.2), BLUE_D, bevel=0.25)
    L.box((10.8, 0.4, 3.7), (0, -3.32, 4.2), GLASS, bevel=0.15, rough=0.05, alpha=0.35)
    for x in (-3.6, 3.6):
        L.box((0.35, 0.55, 3.7), (x, -3.3, 4.2), BLUE_D, bevel=0.1)
    # door (left side of the front) - glass with handle
    L.box((2.6, 0.5, 4.0), (-6.0, -3.15, 3.6), BLUE_D, bevel=0.2)
    L.box((2.1, 0.4, 3.5), (-6.0, -3.3, 3.55), GLASS, bevel=0.12, rough=0.05, alpha=0.35)
    L.box((0.15, 0.3, 0.9), (-5.3, -3.55, 3.5), "#e8e8ee", bevel=0.05)
    # car inside the showroom
    cartoon_car(0.6, 0.6, 1.6, s=1.1, color=YELLOW, rotz=math.radians(-20))
    L.cyl(2.4, 0.25, (0.6, 0.6, 1.5), "#e8e8ee", bevel=0.08)
    # striped awning over the window
    n = 8
    w = 12.0
    for i in range(n):
        x = -w / 2 + w / n * (i + 0.5)
        L.box((w / n, 2.4, 0.3), (x, -4.25, 6.35), BLUE if i % 2 == 0 else "#ffffff",
              rot=(math.radians(-22), 0, 0), bevel=0.05)
    L.scallops(w, n, (0, -5.35, 5.95), BLUE, "#ffffff", depth=0.3)
    # sign on the roof
    sign = L.rounded_rect(11, 3.2, 0.8)
    L.prism(sign, 0.6, (0, 0.2, 10.0), BLUE_D, bevel=0.12)
    L.prism(L.rounded_rect(10.2, 2.5, 0.6), 0.65, (0, 0.17, 10.0), BLUE, bevel=0.08)
    L.text("CARS", 2.0, (0, -0.35, 10.0), YELLOW, extrude=0.15)
    for x in (-3.5, 3.5):
        L.box((0.4, 0.4, 1.4), (x, 0.4, 8.5), DARK, bevel=0.1)
    # hero car on the roof
    cartoon_car(5.6, -2.0, 8.1, s=1.0, color=RED, rotz=math.radians(25))
    # tyre stack + potted bushes
    for i in range(3):
        L.torus(0.65, 0.3, (7.6, -4.7, 0.9 + i * 0.6), DARK)
    for x in (-9.0, 8.8):
        L.cyl(0.8, 1.2, (x, -5.4 if x < 0 else 4.0, 1.2), "#c9874a", r2=0.65, bevel=0.1)
        L.sphere(1.0, (x, -5.4 if x < 0 else 4.0, 2.3), "#4cc23a", ico=True, subdiv=1, smooth=False)


if __name__ == "__main__":
    build()
    L.export("shop_cars")
    L.studio()
    L.camera((0, 0.5, 4.5), 38, elev=24, azim=-32, lens=50)
    L.render(os.path.join(L.ROOT, "renders", "models", "shop_cars.png"))
