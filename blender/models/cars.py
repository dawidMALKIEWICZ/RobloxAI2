"""Mini cars, cartoon low-poly, rarer = shinier (1 unit = 1 stud).

Blender axes: front = +Y (Roblox -Z), Z up, wheels touch z = 0. Every car fits a 2.25 stud wide
lane (loop lanes are 2.3-2.4 wide), is at most 4.5 long and 2.6 tall.
Wheels are separate meshes ("part:WheelFL" ...) centred on their axle, so the game can spin them
about their local X axis. Run: <bpy python> cars.py [CarId ...]
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
import carkit as C  # noqa: E402
from carkit import CHROME, DARK, HEAD, TAIL, glass, neon, strip, tube  # noqa: E402

GLASS = "#9fe3ff"
WHITE = "#ffffff"
pi = math.pi


def glass_loft(sections, color=GLASS, **kw):
    o = C.loft(sections, color, **kw)
    o.data.materials.clear()
    o.data.materials.append(L.mat(color, rough=0.05, alpha=0.45))
    return glass(o)


def cabin(yr, yrt, yft, yf, zb, zt, wb, wt, body, frame=None, roof=None, glass_col=GLASS,
          bpillar=None, roof_th=0.07, pillar=0.07, roof_breaks=(), roof_paint=None, rr=0.12):
    """Glass greenhouse (rear base yr, roof from yrt to yft, front base yf) + roof and pillars."""
    frame = frame or body
    glass_loft([(yr, wb, wb * 0.97, zb - 0.02, zb + 0.03, 0.04, 0.03),
                (yrt, wb, wt, zb - 0.02, zt, 0.04, rr),
                (yft, wb, wt, zb - 0.02, zt, 0.04, rr),
                (yf, wb, wb * 0.97, zb - 0.02, zb + 0.03, 0.04, 0.03)], glass_col)
    d = 0.06
    C.loft([(yrt - d, wt + 0.03, wt - 0.03, zt - 0.03, zt + roof_th, 0.05, rr),
            (yft + d, wt + 0.03, wt - 0.03, zt - 0.03, zt + roof_th, 0.05, rr)],
           roof or body, top_breaks=roof_breaks, paint=roof_paint)
    for s in (-1, 1):
        strip((s * (wb - 0.01), yf, zb), (s * (wt + 0.0), yft, zt), pillar, pillar, frame)
        strip((s * (wb - 0.01), yr, zb), (s * (wt + 0.0), yrt, zt), pillar * 1.4, pillar, frame)
        if bpillar is not None:
            strip((s * (wb - 0.005), bpillar, zb), (s * (wt + 0.005), bpillar, zt), pillar * 1.2,
                  pillar * 0.8, frame)
        # window sill
        strip((s * (wb - 0.0), yr + 0.05, zb + 0.01), (s * (wb - 0.0), yf - 0.05, zb + 0.01),
              0.05, 0.05, frame)
    return zt + roof_th


def fenders(xw, ys, r, w, color, gap=0.04, thick=0.12):
    for x in (-xw, xw):
        for y in ys:
            C.arch(x, y, r + gap, w + 0.08, color, z=r, thick=thick)


# ------------------------------------------------------------------ 1. Dune Buggy
def buggy():
    body, cage = "#ff8a1f", "#ffd23f"
    C.wheel("WheelFL", -0.8, 1.2, 0.4, 0.3, knobs=10, style="spoke", rim="#3a3f4c", hub="#22252e",
            accent=body)
    C.wheel("WheelFR", 0.8, 1.2, 0.4, 0.3, knobs=10, style="spoke", rim="#3a3f4c", hub="#22252e",
            accent=body)
    C.wheel("WheelRL", -0.82, -1.05, 0.5, 0.4, knobs=10, style="spoke", rim="#3a3f4c",
            hub="#22252e", accent=body)
    C.wheel("WheelRR", 0.82, -1.05, 0.5, 0.4, knobs=10, style="spoke", rim="#3a3f4c",
            hub="#22252e", accent=body)
    # tub: low nose, sides with number boards
    secs = [(-1.45, 0.5, 0.48, 0.32, 0.72, 0.08, 0.1), (-0.6, 0.56, 0.54, 0.3, 0.76, 0.1, 0.12),
            (0.6, 0.56, 0.52, 0.3, 0.74, 0.1, 0.12), (1.45, 0.46, 0.4, 0.3, 0.6, 0.1, 0.12),
            (1.7, 0.36, 0.3, 0.34, 0.5, 0.08, 0.08)]
    C.loft(secs, body, side_breaks=(0.15,),
           paint=lambda u, v, y: DARK if v < 0.15 else None)
    # floor + suspension arms
    L.box((0.9, 2.6, 0.08), (0, 0.1, 0.3), DARK)
    for y in (1.2, -1.05):
        tube((-0.78, y, 0.42 if y > 0 else 0.5), (0.78, y, 0.42 if y > 0 else 0.5), 0.05, "#5b6273",
             verts=8)
    # roll cage
    r = 0.045
    hoop = [(-0.5, -0.45, 0.7), (-0.44, -0.5, 1.55), (0.44, -0.5, 1.55), (0.5, -0.45, 0.7)]
    for a, b in zip(hoop, hoop[1:]):
        tube(a, b, r, cage)
    front = [(-0.5, 0.55, 0.72), (-0.42, 0.25, 1.5), (0.42, 0.25, 1.5), (0.5, 0.55, 0.72)]
    for a, b in zip(front, front[1:]):
        tube(a, b, r, cage)
    for s in (-1, 1):
        tube((s * 0.44, -0.5, 1.55), (s * 0.42, 0.25, 1.5), r, cage)
        tube((s * 0.44, -0.5, 1.55), (s * 0.45, -1.35, 0.75), r, cage)    # rear struts
        tube((s * 0.5, 0.55, 0.72), (s * 0.3, 1.72, 0.45), r, cage)       # nose bar
    tube((-0.3, 1.72, 0.45), (0.3, 1.72, 0.45), r, cage)
    tube((-0.44, -0.5, 1.2), (0.44, -0.5, 1.2), r, cage)
    # light bar on the roof
    L.box((0.7, 0.12, 0.12), (0, 0.25, 1.6), DARK, bevel=0.02)
    for x in (-0.24, 0, 0.24):
        C.headlamp(x, 0.31, 1.6, 0.06, verts=8)
    # seat + driver (goggles)
    C.seat(0, -0.25, 0.55, w=0.52)
    C.driver(0, -0.15, 0.62, suit="#2f6bff", helmet="#2fb8ff", stripe=cage, open_face=True,
             visor="#ffcf3b", tilt=60)
    # engine at the back
    L.box((0.7, 0.55, 0.42), (0, -1.25, 0.82), "#5b6273", bevel=0.05)
    for x in (-0.18, 0.18):
        L.cyl(0.12, 0.2, (x, -1.2, 1.12), CHROME, verts=10, bevel=0.02)
    for s in (-1, 1):
        tube((s * 0.3, -1.45, 0.75), (s * 0.34, -1.62, 1.05), 0.05, CHROME, verts=8)
        L.cyl(0.065, 0.06, (s * 0.34, -1.63, 1.08), "#1a1a20", verts=8)
    # headlights + whip flag
    for s in (-1, 1):
        C.headlamp(s * 0.22, 1.71, 0.55, 0.08)
    tube((0.44, -0.5, 1.55), (0.5, -0.62, 2.35), 0.015, DARK, verts=4)
    L.prism([(0, 0), (0.0, 0.22), (-0.32, 0.11)], 0.02, (0.5, -0.66, 2.22), "#ff3b6b",
            rot=(0, 0, pi / 2))
    # number board on the nose
    L.box((0.36, 0.05, 0.22), (0, 1.66, 0.62), WHITE, rot=(math.radians(-35), 0, 0), bevel=0.02)
    C.label("3", 0.2, (0, 1.69, 0.63), DARK, rot=(math.radians(90 - 35), 0, pi), extrude=0.02)


# ------------------------------------------------------------------ 2. Go-Kart
def kart():
    body = "#ff3b3b"
    for x, y, r, w in ((-0.82, 1.15, 0.28, 0.3), (0.82, 1.15, 0.28, 0.3),
                       (-0.82, -1.05, 0.32, 0.42), (0.82, -1.05, 0.32, 0.42)):
        C.wheel(C.wheel_name(x, y, 1.15), x, y, r, w, style="dish", rim=WHITE, hub="#d0d6e0",
                accent=body)
    # chassis tubes + floor tray
    L.box((1.0, 2.5, 0.06), (0, 0.0, 0.2), "#3a3f4c")
    for s in (-1, 1):
        tube((s * 0.5, -1.25, 0.24), (s * 0.5, 1.2, 0.24), 0.04, CHROME, verts=6)
    tube((-0.82, -1.05, 0.32), (0.82, -1.05, 0.32), 0.05, "#5b6273", verts=8)   # rear axle
    tube((-0.75, 1.15, 0.28), (0.75, 1.15, 0.28), 0.035, "#5b6273", verts=6)
    # nose fairing with number plate
    C.loft([(0.75, 0.45, 0.4, 0.18, 0.42, 0.06, 0.12), (1.3, 0.5, 0.42, 0.16, 0.38, 0.06, 0.12),
            (1.62, 0.55, 0.45, 0.12, 0.3, 0.05, 0.1), (1.72, 0.5, 0.4, 0.13, 0.24, 0.04, 0.06)],
           body)
    L.box((0.42, 0.05, 0.26), (0, 0.85, 0.52), WHITE, rot=(math.radians(-20), 0, 0), bevel=0.03)
    C.label("7", 0.22, (0, 0.82, 0.53), DARK, rot=(math.radians(70), 0, pi), extrude=0.02)
    # side pods between the wheels
    for s in (-1, 1):
        C.loft([(-0.7, 0.14, 0.12, 0.16, 0.36, 0.05, 0.08), (0.75, 0.14, 0.12, 0.16, 0.36, 0.05,
                                                              0.08)],
               body, x=s * 0.66, paint=lambda u, v, y: WHITE if 0.45 < v < 0.7 else None,
               side_breaks=(0.45, 0.7))
    # rear bumper
    tube((-0.6, -1.5, 0.3), (0.6, -1.5, 0.3), 0.06, body, verts=8)
    for s in (-1, 1):
        tube((s * 0.6, -1.5, 0.3), (s * 0.45, -1.2, 0.25), 0.05, body, verts=6)
    # seat, driver, steering column
    L.box((0.5, 0.42, 0.12), (0, -0.45, 0.3), DARK, bevel=0.04)
    L.box((0.52, 0.12, 0.5), (0, -0.66, 0.55), DARK, rot=(math.radians(-18), 0, 0), bevel=0.05)
    C.driver(0, -0.38, 0.32, suit="#2b2f3a", helmet="#ffe03b", stripe=body, tilt=40,
             wheel_y=0.08, wheel_z=0.66)
    strip((0, 0.08, 0.66), (0, 0.55, 0.25), 0.05, 0.05, DARK)
    # engine on the right + exhaust
    L.box((0.32, 0.35, 0.3), (0.42, -0.9, 0.45), "#5b6273", bevel=0.04)
    L.cyl(0.11, 0.08, (0.6, -0.9, 0.45), CHROME, rot=(0, pi / 2, 0), verts=10)
    L.cyl(0.1, 0.36, (0.35, -1.25, 0.62), CHROME, rot=(pi / 2, 0, 0), verts=10)
    C.exhaust(0.35, -1.43, 0.62, r=0.05, length=0.06)
    # fuel tank + rear wing
    L.cyl(0.1, 0.28, (-0.38, -0.25, 0.42), "#ffe03b", rot=(pi / 2, 0, 0), verts=10, bevel=0.03)
    for s in (-1, 1):
        L.box((0.05, 0.12, 0.42), (s * 0.4, -1.32, 0.62), DARK)
    L.box((1.1, 0.3, 0.05), (0, -1.36, 0.85), body, bevel=0.02, rot=(math.radians(-8), 0, 0))
    for s in (-1, 1):
        L.box((0.04, 0.34, 0.16), (s * 0.56, -1.36, 0.82), WHITE)


# ------------------------------------------------------------------ 3. Hatchback
def hatch():
    body, roof = "#3ba7ff", WHITE
    C.wheels(0.86, 1.18, -1.18, 0.38, 0.3, style="disc", rim=WHITE, hub="#c7d0dc", accent=body)
    secs = [(-1.88, 0.76, 0.72, 0.26, 0.86, 0.14, 0.14), (-1.76, 0.8, 0.78, 0.22, 0.9, 0.14, 0.18),
            (1.45, 0.8, 0.78, 0.22, 0.9, 0.14, 0.2), (1.8, 0.79, 0.74, 0.22, 0.8, 0.14, 0.22),
            (1.93, 0.74, 0.66, 0.26, 0.7, 0.12, 0.18)]
    C.loft(secs, body, side_breaks=(0.15, 0.62, 0.7),
           paint=lambda u, v, y: DARK if v < 0.15 else (WHITE if 0.62 < v < 0.7 else None))
    fenders(0.86, (1.18, -1.18), 0.38, 0.3, body)
    cabin(-1.76, -1.62, 0.2, 0.92, 0.9, 1.6, 0.76, 0.64, body, frame=roof, roof=roof,
          bpillar=-0.55)
    # roof rails + spoiler lip
    for s in (-1, 1):
        L.box((0.05, 1.5, 0.05), (s * 0.5, -0.7, 1.72), DARK)
    L.box((1.2, 0.2, 0.05), (0, -1.72, 1.66), roof, rot=(math.radians(10), 0, 0), bevel=0.02)
    # face: round lights, grille, bumper
    for s in (-1, 1):
        C.headlamp(s * 0.5, 1.93, 0.6, 0.13)
        neon(L.box((0.1, 0.04, 0.06), (s * 0.7, 1.9, 0.42), "#ffb31a"))
    C.grille(0, 1.95, 0.5, 0.44, 0.16, bars=2)
    L.box((1.6, 0.16, 0.18), (0, 1.94, 0.3), DARK, bevel=0.05)
    L.box((1.6, 0.16, 0.18), (0, -1.9, 0.32), DARK, bevel=0.05)
    C.plate(-1.99, 0.42, facing=-1)
    for s in (-1, 1):
        neon(L.box((0.2, 0.05, 0.22), (s * 0.6, -1.89, 0.7), TAIL))
        C.mirror(s * 0.78, 0.86, 0.95, body, s)
        L.box((0.03, 0.12, 0.04), (s * 0.81, -0.2, 0.78), DARK)       # door handle
    C.exhaust(0.42, -1.9, 0.22, r=0.06, length=0.2)
    # interior: two seats, driver on the left
    C.seat(0.3, -0.35, 0.5)
    C.seat(-0.3, -0.35, 0.5)
    C.driver(-0.3, -0.25, 0.55, suit="#ff7b3b", helmet="#5a3a22", stripe=WHITE, open_face=True,
             visor="#22283a", wheel_y=0.15, wheel_z=0.98, tilt=70)


# ------------------------------------------------------------------ 4. Pickup
def pickup():
    body = "#4bdc5a"
    C.wheels(0.88, 1.25, -1.22, 0.44, 0.34, knobs=10, style="star", rim="#d0d6e0", hub="#3a3f4c")
    secs = [(-2.0, 0.8, 0.8, 0.36, 0.98, 0.08, 0.08), (1.88, 0.8, 0.8, 0.36, 0.98, 0.08, 0.1),
            (2.0, 0.78, 0.76, 0.38, 0.9, 0.08, 0.1)]
    C.loft(secs, body, side_breaks=(0.2, 0.72, 0.8),
           paint=lambda u, v, y: "#2f9b3c" if v < 0.2 else (WHITE if 0.72 < v < 0.8 else None))
    fenders(0.88, (1.25, -1.22), 0.44, 0.34, "#3a3f4c", thick=0.1)
    cabin(-0.62, -0.55, 0.38, 0.95, 0.98, 1.72, 0.78, 0.7, body, bpillar=None)
    # roof light bar
    L.box((1.1, 0.16, 0.08), (0, 0.15, 1.82), DARK, bevel=0.02)
    for x in (-0.38, -0.13, 0.13, 0.38):
        neon(L.box((0.16, 0.12, 0.08), (x, 0.15, 1.9), "#ffb31a"))
    # bed: floor, walls, tailgate, cargo
    L.box((1.48, 1.3, 0.04), (0, -1.3, 1.0), "#2a3a2c")
    for s in (-1, 1):
        L.box((0.09, 1.38, 0.24), (s * 0.76, -1.3, 1.1), body, bevel=0.02)
        L.box((0.11, 1.4, 0.04), (s * 0.76, -1.3, 1.23), DARK)
    L.box((1.6, 0.09, 0.24), (0, -1.97, 1.1), body, bevel=0.02)
    L.box((1.5, 0.09, 0.24), (0, -0.66, 1.1), "#2f9b3c")
    L.box((0.5, 0.45, 0.36), (0.32, -1.05, 1.2), "#c98a4b", bevel=0.04)
    L.box((0.52, 0.47, 0.05), (0.32, -1.05, 1.32), "#a8703a")
    L.box((0.44, 0.3, 0.2), (-0.35, -1.7, 1.12), "#e23b3b", bevel=0.03)
    L.cyl(0.26, 0.14, (-0.32, -1.18, 1.1), C.TIRE, verts=12, bevel=0.04)
    L.cyl(0.14, 0.16, (-0.32, -1.18, 1.1), "#d0d6e0", verts=10)
    # face: big chrome grille, round lights, bull bar
    C.grille(0, 2.01, 0.66, 0.9, 0.34, bars=4)
    for s in (-1, 1):
        C.headlamp(s * 0.62, 2.01, 0.7, 0.13)
        neon(L.box((0.12, 0.05, 0.08), (s * 0.66, 2.0, 0.48), "#ffb31a"))
        tube((s * 0.4, 2.15, 0.3), (s * 0.4, 2.15, 0.85), 0.04, DARK, verts=6)
        tube((s * 0.4, 2.04, 0.4), (s * 0.4, 2.15, 0.4), 0.035, DARK, verts=6)
    tube((-0.6, 2.15, 0.42), (0.6, 2.15, 0.42), 0.045, DARK, verts=6)
    tube((-0.4, 2.15, 0.85), (0.4, 2.15, 0.85), 0.04, DARK, verts=6)
    L.box((1.7, 0.14, 0.2), (0, 2.05, 0.36), CHROME, bevel=0.05)
    L.box((1.7, 0.14, 0.2), (0, -2.04, 0.4), CHROME, bevel=0.05)
    C.plate(-2.12, 0.42, facing=-1, band="#4bdc5a")
    for s in (-1, 1):
        neon(L.box((0.16, 0.05, 0.3), (s * 0.7, -2.02, 0.78), TAIL))
        C.mirror(s * 0.78, 0.92, 1.05, body, s)
        L.box((0.12, 1.1, 0.05), (s * 0.86, 0.0, 0.33), DARK)        # side steps
        L.box((0.26, 0.03, 0.22), (s * 0.86, -1.72, 0.22), DARK)      # mud flaps
        L.box((0.03, 0.12, 0.04), (s * 0.81, 0.3, 0.92), DARK)
    C.exhaust(0.5, -2.08, 0.28, r=0.06, length=0.2)
    C.seat(-0.3, -0.25, 0.6)
    C.seat(0.3, -0.25, 0.6)
    C.driver(-0.3, -0.15, 0.65, suit="#ff3b3b", helmet="#2b2f3a", stripe=WHITE, open_face=True,
             wheel_y=0.3, wheel_z=1.08, tilt=70)


# ------------------------------------------------------------------ 5. Muscle car
def muscle():
    body, stripe = "#ffd23f", "#1c1c24"
    for x, y, r, w in ((-0.86, 1.28, 0.4, 0.32), (0.86, 1.28, 0.4, 0.32),
                       (-0.85, -1.25, 0.44, 0.38), (0.85, -1.25, 0.44, 0.38)):
        C.wheel(C.wheel_name(x, y, 1.28), x, y, r, w, style="dish", rim=CHROME, hub="#2b2f3a",
                accent=body)
    tb = (0.1, 0.28, -0.1, -0.28)

    def paint(u, v, y):
        if v > 0.995:
            return None
        if v < 0.14:
            return DARK
        return None
    secs = [(-2.1, 0.8, 0.74, 0.26, 0.86, 0.1, 0.12), (-1.92, 0.84, 0.8, 0.24, 0.9, 0.12, 0.14),
            (1.82, 0.84, 0.8, 0.24, 0.82, 0.12, 0.14), (2.1, 0.82, 0.76, 0.26, 0.74, 0.1, 0.12)]
    o = C.loft(secs, body, top_breaks=tb, side_breaks=(0.14,), paint=paint)
    _stripe_top(o, 0.1, 0.28, stripe)
    fenders(0.86, (1.28,), 0.4, 0.32, body)
    fenders(0.85, (-1.25,), 0.44, 0.38, body)
    cabin(-1.45, -0.55, 0.15, 0.62, 0.88, 1.38, 0.76, 0.6, body, frame=stripe, roof=body,
          roof_breaks=tb, bpillar=None)
    for ob in list(bpy.context.scene.objects):
        if ob.type == "MESH" and ob.name.startswith("loft") and ob != o and ob.get("grp") is None:
            zs = [v.co.z for v in ob.data.vertices]
            if min(zs) > 1.3:
                _stripe_top(ob, 0.1, 0.28, stripe)
    # hood blower + scoop
    L.box((0.5, 0.6, 0.12), (0, 1.0, 0.88), stripe, bevel=0.04)
    L.box((0.4, 0.4, 0.14), (0, 1.0, 1.0), CHROME, bevel=0.03)
    for x in (-0.1, 0.1):
        L.cyl(0.08, 0.16, (x, 1.05, 1.13), CHROME, verts=10)
        L.cyl(0.06, 0.02, (x, 1.05, 1.21), "#1a1a20", verts=10)
    # ducktail + chrome bumpers
    L.box((1.5, 0.3, 0.08), (0, -1.98, 0.94), stripe, rot=(math.radians(14), 0, 0), bevel=0.03)
    L.box((1.72, 0.14, 0.16), (0, 2.14, 0.36), CHROME, bevel=0.05)
    L.box((1.72, 0.14, 0.16), (0, -2.14, 0.36), CHROME, bevel=0.05)
    # face: dark grille panel with quad round lights
    L.box((1.5, 0.05, 0.28), (0, 2.1, 0.58), "#1c1c24", bevel=0.02)
    for s in (-1, 1):
        for x in (0.48, 0.66):
            C.headlamp(s * x, 2.12, 0.58, 0.085, verts=10)
    for i in range(3):
        L.box((0.6, 0.06, 0.03), (0, 2.12, 0.5 + i * 0.08), CHROME)
    C.plate(-2.18, 0.52, facing=-1, band="#ff3b3b")
    for s in (-1, 1):
        neon(L.box((0.5, 0.05, 0.1), (s * 0.48, -2.1, 0.72), TAIL))
        tube((s * 0.86, -0.75, 0.2), (s * 0.86, 0.75, 0.2), 0.05, CHROME, verts=8)  # side pipes
        C.mirror(s * 0.77, 0.6, 0.9, body, s)
        L.cyl(0.18, 0.02, (s * 0.85, -0.25, 0.56), WHITE, rot=(0, pi / 2, 0), verts=14)
        C.label("7", 0.24, (s * 0.865, -0.25, 0.56), stripe, rot=(pi / 2, 0, s * pi / 2),
               extrude=0.015)
    for x in (0.38, 0.55):
        C.exhaust(x, -2.14, 0.24, r=0.055, length=0.16)
        C.exhaust(-x, -2.14, 0.24, r=0.055, length=0.16)
    C.seat(-0.3, -0.75, 0.48)
    C.seat(0.3, -0.75, 0.48)
    C.driver(-0.3, -0.65, 0.36, suit=WHITE, helmet="#ff3b3b", stripe=stripe, tilt=72, s=0.9,
             wheel_y=-0.27, wheel_z=0.8)


def _stripe_top(o, x0, x1, color):
    """Paints top faces of a loft whose centre lies between |x| in [x0, x1]."""
    me = o.data
    idx = None
    for i, m in enumerate(me.materials):
        if m.get("hex") == color:
            idx = i
    if idx is None:
        me.materials.append(L.mat(color))
        idx = len(me.materials) - 1
    for p in me.polygons:
        if p.normal.z > 0.55 and x0 - 1e-3 <= abs(p.center.x) <= x1 + 1e-3:
            xs = [me.vertices[v].co.x for v in p.vertices]
            if min(abs(x) for x in xs) >= x0 - 0.02 and max(abs(x) for x in xs) <= x1 + 0.02:
                p.material_index = idx


# ------------------------------------------------------------------ 6. Sports car
def sports():
    body, black = "#ff2d55", "#1c1c24"
    for x, y, r, w in ((-0.86, 1.3, 0.37, 0.34), (0.86, 1.3, 0.37, 0.34),
                       (-0.85, -1.25, 0.4, 0.38), (0.85, -1.25, 0.4, 0.38)):
        C.wheel(C.wheel_name(x, y, 1.3), x, y, r, w, style="star", rim="#2b2f3a", hub="#14141a",
                accent=body)
    secs = [(-2.08, 0.8, 0.72, 0.24, 0.76, 0.1, 0.12), (-1.6, 0.84, 0.78, 0.2, 0.78, 0.12, 0.16),
            (0.4, 0.84, 0.78, 0.2, 0.66, 0.12, 0.16), (1.7, 0.84, 0.76, 0.2, 0.5, 0.12, 0.14),
            (2.12, 0.76, 0.66, 0.2, 0.36, 0.08, 0.1)]
    C.loft(secs, body, side_breaks=(0.2,), top_breaks=(0.06, -0.06),
           paint=lambda u, v, y: black if v < 0.2 else (WHITE if v > 0.995 and abs(u) < 0.12
                                                       else None))
    fenders(0.86, (1.3,), 0.37, 0.34, body, thick=0.1)
    fenders(0.85, (-1.25,), 0.4, 0.38, body, thick=0.1)
    cabin(-1.15, -0.75, 0.05, 0.9, 0.7, 1.14, 0.76, 0.56, body, frame=black, roof=black,
          glass_col="#5f86c4", rr=0.1)
    # side intakes, hood vents, rear wing
    for s in (-1, 1):
        C.loft([(-0.9, 0.06, 0.05, 0.36, 0.62, 0.02, 0.03), (-0.35, 0.06, 0.05, 0.3, 0.66, 0.02,
                                                              0.03)], black, x=s * 0.82)
        L.box((0.2, 0.03, 0.04), (s * 0.25, 1.35, 0.58), black, rot=(math.radians(-12), 0, 0))
        L.box((0.2, 0.03, 0.04), (s * 0.25, 1.5, 0.55), black, rot=(math.radians(-12), 0, 0))
        L.box((0.06, 0.12, 0.36), (s * 0.55, -1.9, 0.92), black)
        L.box((0.04, 0.5, 0.26), (s * 0.84, -1.95, 1.08), body, bevel=0.02)
        C.mirror(s * 0.74, 0.7, 0.75, body, s)
    L.box((1.72, 0.48, 0.06), (0, -1.95, 1.12), black, rot=(math.radians(-8), 0, 0), bevel=0.02)
    L.box((1.68, 0.12, 0.03), (0, -2.13, 1.17), body)
    # lights: LED strips front, light bar rear
    for s in (-1, 1):
        neon(L.box((0.42, 0.05, 0.06), (s * 0.5, 2.07, 0.38), "#e6faff",
                   rot=(0, math.radians(-s * 10), math.radians(s * 12))))
        L.box((0.48, 0.06, 0.12), (s * 0.5, 2.05, 0.35), black)
    neon(L.box((1.5, 0.05, 0.06), (0, -2.09, 0.66), TAIL))
    L.box((1.3, 0.08, 0.14), (0, -2.05, 0.3), black)
    for x in (-0.15, 0.15):
        C.exhaust(x, -2.11, 0.32, r=0.055, length=0.12)
    for i in range(4):
        L.box((0.03, 0.2, 0.1), (-0.45 + i * 0.3, -2.02, 0.22), "#3a3f4c")
    L.box((1.0, 0.25, 0.08), (0, 2.08, 0.22), black)
    neon(L.box((1.4, 3.0, 0.03), (0, 0, 0.17), "#ff4f86"))   # under-glow
    C.seat(-0.28, -0.55, 0.36)
    C.seat(0.28, -0.55, 0.36)
    C.driver(-0.28, -0.45, 0.22, suit=black, helmet=WHITE, stripe=body, tilt=70, s=0.85,
             wheel_y=-0.05, wheel_z=0.6)


# ------------------------------------------------------------------ 7. Monster truck
def monster():
    body, yel = "#9b4dff", "#ffe03b"
    C.wheels(0.8, 1.08, -1.08, 0.68, 0.5, knobs=10, style="star", rim=yel, hub="#3a3f4c",
             accent="#ff3b3b")
    # chassis rails, axles, differentials, springs and shocks
    for s in (-1, 1):
        L.box((0.12, 3.2, 0.16), (s * 0.4, 0, 0.92), DARK, bevel=0.02)
    for y in (1.08, -1.08):
        tube((-0.7, y, 0.68), (0.7, y, 0.68), 0.07, "#8a8f9a", verts=8)
        L.sphere(0.17, (0, y, 0.68), "#8a8f9a", subdiv=1)
        for s in (-1, 1):
            tube((s * 0.45, y, 0.7), (s * 0.4, y, 1.1), 0.035, CHROME, verts=6)
            for k in range(2):
                C.ring(0.085, 0.022, (s * 0.45, y + 0.16 * (1 if y > 0 else -1), 0.82 + k * 0.16),
                        yel, rot=(0, 0, 0), maj=8, mnr=3)
            tube((s * 0.45, y + 0.16 * (1 if y > 0 else -1), 0.7),
                 (s * 0.42, y + 0.16 * (1 if y > 0 else -1), 1.15), 0.03, "#5b6273", verts=6)
    # body + cab
    secs = [(-1.6, 0.78, 0.76, 1.05, 1.62, 0.1, 0.12), (1.5, 0.78, 0.76, 1.05, 1.62, 0.1, 0.14),
            (1.7, 0.74, 0.7, 1.08, 1.5, 0.1, 0.12)]
    C.loft(secs, body, side_breaks=(0.15,), paint=lambda u, v, y: DARK if v < 0.15 else None)
    cabin(-0.75, -0.65, 0.25, 0.7, 1.62, 2.22, 0.74, 0.66, body, bpillar=None)
    # flames on the sides
    flame = [(0.0, 0.0), (0.9, 0.0), (0.7, 0.12), (1.15, 0.2), (0.6, 0.26), (0.95, 0.4),
             (0.35, 0.36), (0.55, 0.52), (0.0, 0.42)]
    inner = [(0.0, 0.08), (0.62, 0.08), (0.45, 0.16), (0.75, 0.22), (0.35, 0.25), (0.0, 0.3)]
    for s in (-1, 1):
        L.prism([(p[0] + 0.25, p[1] + 1.08) for p in flame], 0.02, (s * 0.785, 0, 0), "#ff7b1a",
                rot=(0, 0, pi / 2))
        L.prism([(p[0] + 0.25, p[1] + 1.08) for p in inner], 0.02, (s * 0.795, 0, 0), yel,
                rot=(0, 0, pi / 2))
        C.mirror(s * 0.76, 0.66, 1.7, body, s)
    # roof light bar, exhaust stacks, bumpers, lights
    L.box((1.1, 0.14, 0.1), (0, 0.15, 2.36), DARK, bevel=0.02)
    for x in (-0.39, -0.13, 0.13, 0.39):
        C.headlamp(x, 0.23, 2.38, 0.07, color=yel, verts=8)
    for s in (-1, 1):
        L.cyl(0.07, 0.75, (s * 0.55, -0.85, 1.95), CHROME, verts=10)
        L.cyl(0.05, 0.02, (s * 0.55, -0.85, 2.33), "#1a1a20", verts=8)
        C.headlamp(s * 0.55, 1.71, 1.4, 0.12)
        neon(L.box((0.16, 0.05, 0.22), (s * 0.6, -1.61, 1.45), TAIL))
    C.grille(0, 1.72, 1.32, 0.5, 0.22, bars=3)
    L.box((1.5, 0.16, 0.18), (0, 1.75, 1.1), DARK, bevel=0.04)
    L.box((1.5, 0.16, 0.18), (0, -1.65, 1.1), DARK, bevel=0.04)
    # small bed with a toolbox
    L.box((1.4, 0.75, 0.04), (0, -1.15, 1.63), "#3a3f4c")
    L.box((1.46, 0.2, 0.16), (0, -0.82, 1.72), DARK, bevel=0.02)
    C.seat(-0.3, -0.35, 1.2)
    C.driver(-0.3, -0.25, 1.25, suit="#2b2f3a", helmet=yel, stripe="#ff3b3b", tilt=70,
             wheel_y=0.12, wheel_z=1.68)


# ------------------------------------------------------------------ 8. Formula racer
def f1():
    red, white, black = "#e10600", WHITE, "#1c1c24"
    for x, y, r, w in ((-0.84, 1.45, 0.36, 0.36), (0.84, 1.45, 0.36, 0.36),
                       (-0.83, -1.3, 0.42, 0.44), (0.83, -1.3, 0.42, 0.44)):
        C.wheel(C.wheel_name(x, y, 1.45), x, y, r, w, style="disc", rim="#2b2f3a", hub="#14141a",
                accent=red)
        # suspension wishbones
        for dz in (-0.06, 0.08):
            strip((x * 0.25, y + 0.15, r + dz + 0.05), (x * 0.8, y, r + dz), 0.03, 0.03, black)
            strip((x * 0.25, y - 0.15, r + dz + 0.05), (x * 0.8, y, r + dz), 0.03, 0.03, black)
    # monocoque: nose -> cockpit -> engine cover
    secs = [(2.12, 0.08, 0.07, 0.2, 0.3, 0.03, 0.04), (1.4, 0.16, 0.13, 0.2, 0.48, 0.05, 0.08),
            (0.5, 0.26, 0.2, 0.18, 0.62, 0.06, 0.1), (-0.3, 0.3, 0.22, 0.18, 0.66, 0.06, 0.1),
            (-1.2, 0.26, 0.14, 0.2, 0.6, 0.06, 0.08), (-1.75, 0.16, 0.1, 0.24, 0.46, 0.04,
                                                         0.06)]
    C.loft(secs, white, top_breaks=(0.05, -0.05),
           paint=lambda u, v, y: red if (v > 0.995 and abs(u) < 0.5) or (v < 0.3 and y > 0.4)
           else None)
    # airbox + shark fin
    C.loft([(-0.05, 0.12, 0.08, 0.55, 0.95, 0.04, 0.07), (-0.35, 0.16, 0.1, 0.55, 1.0, 0.05, 0.07),
            (-1.4, 0.06, 0.04, 0.5, 0.66, 0.02, 0.02)], red)
    L.box((0.12, 0.04, 0.12), (0, -0.04, 0.9), black)
    # side pods
    for s in (-1, 1):
        C.loft([(0.45, 0.16, 0.14, 0.18, 0.46, 0.05, 0.08), (-0.2, 0.2, 0.17, 0.18, 0.5, 0.06, 0.1),
                (-1.0, 0.14, 0.1, 0.2, 0.36, 0.05, 0.06)], red, x=s * 0.44,
               paint=lambda u, v, y: white if v > 0.995 else None)
        L.box((0.26, 0.04, 0.22), (s * 0.44, 0.46, 0.32), black)
        C.mirror(s * 0.3, 0.55, 0.62, red, s)
    # front wing (2 elements + endplates)
    L.box((1.9, 0.38, 0.04), (0, 2.05, 0.12), black, bevel=0.01)
    L.box((1.8, 0.2, 0.04), (0, 1.92, 0.2), red, rot=(math.radians(18), 0, 0))
    for s in (-1, 1):
        L.box((0.04, 0.5, 0.22), (s * 0.96, 2.0, 0.2), red, bevel=0.01)
        strip((s * 0.06, 1.95, 0.22), (s * 0.12, 2.0, 0.13), 0.03, 0.03, black)
    # rear wing on a pylon + endplates + rain light
    L.box((1.7, 0.3, 0.05), (0, -1.85, 1.02), black, bevel=0.01)
    L.box((1.66, 0.18, 0.04), (0, -1.73, 1.1), red, rot=(math.radians(-25), 0, 0))
    L.box((1.5, 0.3, 0.04), (0, -1.88, 0.42), black)
    for s in (-1, 1):
        L.box((0.04, 0.5, 0.75), (s * 0.86, -1.85, 0.75), red, bevel=0.01)
    L.box((0.06, 0.3, 0.55), (0, -1.75, 0.75), black)
    neon(L.box((0.14, 0.04, 0.12), (0, -1.99, 0.38), TAIL))
    # halo + driver
    tube((-0.22, 0.05, 0.62), (-0.2, 0.3, 0.86), 0.03, black, verts=6)
    tube((0.22, 0.05, 0.62), (0.2, 0.3, 0.86), 0.03, black, verts=6)
    tube((-0.2, 0.3, 0.86), (0.2, 0.3, 0.86), 0.03, black, verts=6)
    tube((0, 0.3, 0.86), (0, 0.62, 0.6), 0.03, black, verts=6)
    C.driver(0, 0.0, 0.3, suit=red, helmet="#ffd23f", stripe=red, tilt=50, wheel_y=0.36,
             wheel_z=0.62)
    C.label("1", 0.22, (0, 1.1, 0.5), black, rot=(0, 0, pi), extrude=0.02)


# ------------------------------------------------------------------ 9. Hover car
def hover():
    body, cyan, pink = "#eef6ff", "#38d6ff", "#ff4f9a"
    secs = [(-2.05, 0.6, 0.5, 0.4, 0.82, 0.18, 0.2), (-1.6, 0.86, 0.78, 0.34, 0.92, 0.2, 0.28),
            (0.6, 0.88, 0.78, 0.34, 0.86, 0.22, 0.28), (1.6, 0.76, 0.62, 0.36, 0.7, 0.18, 0.2),
            (2.15, 0.42, 0.3, 0.42, 0.56, 0.08, 0.08)]
    C.loft(secs, body, side_breaks=(0.45, 0.55, 0.65), top_breaks=(0.16, 0.24, -0.16, -0.24),
           paint=lambda u, v, y: ("#2fb6e6" if v < 0.45 else (pink if 0.55 < v < 0.65 else None)))
    o = [ob for ob in bpy.context.scene.objects if ob.name.startswith("loft")][-1]
    _stripe_top(o, 0.16, 0.24, cyan)
    # bubble canopy + driver
    can = C.ball(0.6, (0, -0.15, 0.95), "#7ce7ff", scale=(1.0, 1.7, 0.75), seg=14, rings=8,
                 rough=0.05, alpha=0.45)
    glass(can)
    C.driver(0, -0.3, 0.45, suit="#2b2f3a", helmet="#ff4f9a", stripe=cyan, visor="#38d6ff",
             tilt=60, s=0.9, wheel_y=0.05, wheel_z=0.8)
    C.ring(0.62, 0.05, (0, -0.15, 0.93), "#c9d6e6", maj=14, mnr=4)
    # hover pads with glowing rings
    for y in (1.15, -1.25):
        for s in (-1, 1):
            L.cyl(0.36, 0.2, (s * 0.72, y, 0.33), "#3a4a60", verts=14, bevel=0.04)
            neon(L.cyl(0.26, 0.04, (s * 0.72, y, 0.22), "#7cf3ff", verts=14))
            neon(C.ring(0.33, 0.03, (s * 0.72, y, 0.25), cyan, maj=12, mnr=3))
            L.box((0.24, 0.5, 0.08), (s * 0.8, y, 0.5), body, bevel=0.03)
    # side fins, twin tail fins and thrusters
    for s in (-1, 1):
        L.prism([(-0.6, 0.0), (0.5, 0.0), (-0.2, 0.18), (-0.75, 0.2)], 0.05, (s * 0.95, 0, 0.6),
                body, rot=(0, math.radians(-s * 12), pi / 2))
        neon(L.box((0.04, 0.55, 0.04), (s * 0.99, -0.3, 0.6), cyan))
        L.prism([(0.0, 0.0), (0.45, 0.0), (0.0, 0.45), (-0.2, 0.45)], 0.05,
                (s * 0.45, -1.7, 0.85), body, rot=(0, math.radians(s * 14), pi / 2))
        neon(L.box((0.05, 0.22, 0.04), (s * 0.5, -1.85, 1.28), pink,
                   rot=(0, math.radians(s * 14), 0)))
        L.cyl(0.2, 0.4, (s * 0.38, -1.95, 0.6), "#3a4a60", rot=(pi / 2, 0, 0), verts=12,
              bevel=0.03)
        neon(L.cyl(0.14, 0.04, (s * 0.38, -2.16, 0.6), cyan, rot=(pi / 2, 0, 0), verts=12))
        neon(L.box((0.4, 0.05, 0.05), (s * 0.45, 2.0, 0.55), "#bff6ff",
                   rot=(0, 0, math.radians(s * 22))))
    neon(L.box((0.5, 0.05, 0.08), (0, -2.07, 0.75), pink))


# ------------------------------------------------------------------ 10. Rocket car
def rocket():
    body, gold, red = "#23232f", "#ffd23f", "#ff3b3b"
    C.wheels(0.86, 1.25, -1.15, 0.34, 0.3, style="dish", rim=gold, hub="#3a3a48", accent=red)
    secs = [(-1.95, 0.5, 0.4, 0.3, 0.98, 0.18, 0.2), (-1.2, 0.68, 0.56, 0.28, 1.0, 0.2, 0.24),
            (0.4, 0.66, 0.5, 0.28, 0.86, 0.2, 0.22), (1.4, 0.5, 0.36, 0.3, 0.66, 0.16, 0.16),
            (1.9, 0.24, 0.18, 0.36, 0.5, 0.06, 0.06), (2.05, 0.08, 0.06, 0.4, 0.46, 0.02, 0.02)]
    C.loft(secs, body, top_breaks=(0.12, 0.2, -0.12, -0.2), side_breaks=(0.2,),
           paint=lambda u, v, y: "#3a3a48" if v < 0.2 else None)
    o = [ob for ob in bpy.context.scene.objects if ob.name.startswith("loft")][-1]
    _stripe_top(o, 0.12, 0.2, gold)
    fenders(0.86, (1.25, -1.15), 0.34, 0.3, "#3a3a48", thick=0.08)
    # canopy
    glass_loft([(-0.6, 0.36, 0.34, 0.86, 0.9, 0.03, 0.03), (-0.35, 0.36, 0.26, 0.86, 1.22, 0.04, 0.16),
                (0.25, 0.36, 0.26, 0.86, 1.2, 0.04, 0.16), (0.8, 0.32, 0.3, 0.8, 0.84, 0.03, 0.03)],
               "#ffb31a")
    C.driver(0, -0.3, 0.36, suit=red, helmet=gold, stripe=WHITE, visor="#22283a", tilt=60,
             s=0.85, wheel_y=0.02, wheel_z=0.74)
    # swept wings with red tips, tail fin
    for s in (-1, 1):
        L.prism([(s * 0.0, -0.1), (s * 0.0, 0.75), (s * 0.4, 0.8), (s * 0.4, 0.45)], 0.05,
                (s * 0.6, 0, 0.6), gold, rot=(pi / 2, 0, 0))
        L.box((0.06, 0.4, 0.1), (s * 1.0, -0.62, 0.6), red, bevel=0.02)
        L.box((0.05, 0.6, 0.12), (s * 0.66, 0.4, 0.62), "#3a3a48")        # intakes
        neon(L.box((0.03, 0.4, 0.04), (s * 0.68, 0.4, 0.62), "#ffb31a"))
    L.prism([(-1.95, 0.0), (-1.0, 0.0), (-1.75, 0.65), (-2.05, 0.65)], 0.06, (0, 0, 0.95), body,
            rot=(0, 0, pi / 2))
    L.prism([(-1.85, 0.25), (-1.5, 0.25), (-1.95, 0.55), (-2.03, 0.55)], 0.08, (0, 0, 0.95), gold,
            rot=(0, 0, pi / 2))
    # twin rocket nozzles with flames (WorldFX adds fire at x=+-0.45, y=-2.35, z=0.8)
    for s in (-1, 1):
        L.cyl(0.26, 0.5, (s * 0.45, -1.85, 0.8), "#5b6273", rot=(pi / 2, 0, 0), verts=12,
              bevel=0.03)
        L.cyl(0.3, 0.28, (s * 0.45, -2.2, 0.8), "#8a8f9a", r2=0.24, rot=(pi / 2, 0, 0), verts=12)
        C.ring(0.27, 0.035, (s * 0.45, -2.0, 0.8), gold, rot=(pi / 2, 0, 0), maj=12, mnr=3)
        neon(L.cyl(0.24, 0.03, (s * 0.45, -2.33, 0.8), "#ff7b1a", rot=(pi / 2, 0, 0), verts=12))
        neon(L.cyl(0.18, 0.1, (s * 0.45, -2.36, 0.8), "#ffe08a", r2=0.02, rot=(pi / 2, 0, 0),
                   verts=10))
    # nose light, under-glow
    neon(L.box((0.3, 0.05, 0.04), (0, 1.92, 0.5), "#fff3b0"))
    for s in (-1, 1):
        neon(L.box((0.24, 0.05, 0.05), (s * 0.4, 1.5, 0.5), "#fff3b0",
                   rot=(0, 0, math.radians(s * 25))))
    neon(L.box((1.2, 2.8, 0.03), (0, 0, 0.2), "#ffb31a"))


CARS = {"Buggy": buggy, "GoKart": kart, "Hatchback": hatch, "Pickup": pickup, "Muscle": muscle,
        "Sports": sports, "Monster": monster, "F1": f1, "Hover": hover, "Rocket": rocket}


def check(cid):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and not o.name.startswith("_"):
            me = o.evaluated_get(dg).to_mesh()
            pts += [o.matrix_world @ v.co for v in me.vertices]
    w = max(abs(p.x) for p in pts) * 2
    ln = max(p.y for p in pts) - min(p.y for p in pts)
    h = max(p.z for p in pts)
    lo = min(p.z for p in pts)
    bad = []
    if w > 2.25:
        bad.append("TOO WIDE")
    if ln > 4.5:
        bad.append("TOO LONG")
    if h > 2.6:
        bad.append("TOO TALL")
    print(f"SIZE {cid}: width {w:.2f} length {ln:.2f} height {h:.2f} (lowest z {lo:.2f})"
          + ("  <-- " + ", ".join(bad) if bad else ""))
    return bad


def render(cid, views=((150, 22), (-35, 24))):
    L.studio(ground=True, ground_color="#d8e3ee")
    sc = bpy.context.scene
    sc.render.resolution_x = sc.render.resolution_y = 520
    sc.cycles.samples = 32
    paths = []
    for k, (azim, elev) in enumerate(views):
        cam = L.frame(lens=50, elev=elev, azim=azim, margin=1.55)
        path = os.path.join(ROOT, "renders", "cars", cid + ("" if k == 0 else "_back") + ".png")
        L.render(path)
        bpy.data.objects.remove(cam)
        paths.append(path)
    return paths


def sheet(ids):
    from PIL import Image, ImageDraw
    cell = 360
    img = Image.new("RGB", (cell * 5, (cell + 24) * 4), "#e8eef5")
    d = ImageDraw.Draw(img)
    for i, cid in enumerate(ids):
        for k, suffix in enumerate(("", "_back")):
            p = os.path.join(ROOT, "renders", "cars", cid + suffix + ".png")
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGB").resize((cell, cell))
            col, row = i % 5, (i // 5) * 2 + k
            img.paste(im, (col * cell, row * (cell + 24) + 24))
            if k == 0:
                d.text((col * cell + 8, row * (cell + 24) + 6), f"{i + 1}. {cid}", fill="#222")
    img.save(os.path.join(ROOT, "renders", "cars_sheet.png"))


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
    sheet(list(CARS))
