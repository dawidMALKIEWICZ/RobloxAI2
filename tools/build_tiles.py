"""Mini track tiles for the building grid -> src/ReplicatedStorage/Assets/Tiles.model.json

Every tile fills one CELL x CELL grid cell, origin = cell centre at pad height (y = 0).
Port A is the +Z edge (0, ROAD_Y, +5), port B is the -Z edge (straight tiles) or the +X edge
(turn tiles). The car may drive a tile in either direction.
Children: base/road/decor parts, a "Path" folder of waypoints "1".."n" from A to B
(attributes Teleport, Boost) and attributes Ports ("SN" or "SE").
"""
import math

from rbx import CF, Inst, add, cross, length, mul, norm, part, sub, write_model

CELL = 10.0
ROAD_W = 6.0
ROAD_Y = 0.6          # road top above the pad
HALF = CELL / 2

TIER_STYLE = {
    "Common": dict(base="#d9dde6", kerb=("#ff4d4d", "#ffffff"), road="#4a4f5c", glow=None),
    "Rare": dict(base="#bfe3ff", kerb=("#2f8bff", "#ffffff"), road="#45506a", glow="#5cc8ff"),
    "Epic": dict(base="#e3c9ff", kerb=("#a43bff", "#ffffff"), road="#4a4060", glow="#c46bff"),
    "Legendary": dict(base="#ffe6a8", kerb=("#ffb31a", "#ffffff"), road="#57503f",
                      glow="#ffcc33"),
    "Mythical": dict(base="#ffc2d4", kerb=("#ff3b6b", "#ffffff"), road="#55384a",
                     glow="#ff4f86"),
    "Secret": dict(base="#2b2b38", kerb=("#ffffff", "#111111"), road="#1d1d26", glow="rainbow"),
}
RAINBOW = ["#ff3b3b", "#ff9f1a", "#ffe03b", "#4bdc5a", "#3bd1ff", "#3b6bff", "#b54dff"]


def smooth(t):
    return t * t * (3 - 2 * t)


class Path:
    """Sample list of (pos, fwd, up, road, flags) starting at port A heading -Z."""

    def __init__(self):
        self.s = [((0.0, ROAD_Y, HALF), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0), True, {})]

    @property
    def end(self):
        return self.s[-1][0]

    def curve(self, fn, n, road=True, flags=None):
        """fn(t)->(pos, up) for t in (0,1]; tangent estimated numerically."""
        for i in range(1, n + 1):
            t = i / n
            p, up = fn(t)
            e = 1e-3
            a, _ = fn(max(0, t - e))
            b, _ = fn(min(1, t + e))
            self.s.append((p, norm(sub(b, a)), up, road, dict(flags or {})))

    def line(self, p1, n=2, road=True, flags=None):
        p0 = self.end
        self.curve(lambda t: (add(p0, mul(sub(p1, p0), t)), (0, 1, 0)), n, road, flags)

    def teleport(self, p):
        self.s[-1][4]["Teleport"] = True
        f = self.s[-1][1]
        self.s.append((p, f, (0, 1, 0), False, {}))


def frame_at(p, f, u):
    r = norm(cross(f, u))
    uu = cross(r, f)
    return CF.from_axes(p, r, uu, (-f[0], -f[1], -f[2]))


def build_road(m, path, tier, rainbow=False):
    st = TIER_STYLE[tier]
    s = path.s
    k = 0
    for i in range(1, len(s)):
        p0, f0, u0, _, _ = s[i - 1]
        p1, f1, u1, road, _ = s[i]
        if not road:
            continue
        d = sub(p1, p0)
        L = length(d)
        if L < 1e-3:
            continue
        f = norm(d)
        u = norm(add(u0, u1))
        cf = frame_at(mul(add(p0, p1), 0.5), f, u)
        dot = max(-1, min(1, sum(f0[j] * f1[j] for j in range(3))))
        extra = ROAD_W * math.tan(math.acos(dot) / 2) + 0.12
        col = RAINBOW[i % len(RAINBOW)] if rainbow else st["road"]
        lift = 0.03 * (i % 2)  # alternate heights so overlapping segments never z-fight
        m.add(part("Road", (ROAD_W, 0.5, L + extra), cf * CF(0, -0.25 + lift, 0), col,
                   "Neon" if rainbow else "SmoothPlastic"))
        kc = st["kerb"][k % 2]
        k += 1
        for side in (-1, 1):
            m.add(part("Kerb", (0.6, 0.7, L + extra), cf * CF(side * (ROAD_W / 2 + 0.3), -0.15 + lift, 0),
                       kc))


def add_path(m, path):
    folder = Inst("Folder", "Path")
    for i, (p, f, u, _road, flags) in enumerate(path.s):
        attrs = {}
        if flags.get("Teleport"):
            attrs["Teleport"] = True
        if flags.get("Boost"):
            attrs["Boost"] = flags["Boost"]
        folder.add(part(str(i + 1), (0.4, 0.4, 0.4), frame_at(p, f, u), "#ffffff",
                        transparency=1, collide=False, touch=False, attrs=attrs or None))
    m.add(folder)


def base(m, tier, color=None):
    st = TIER_STYLE[tier]
    m.add(part("Base", (CELL - 0.2, 0.4, CELL - 0.2), CF(0, 0.2, 0), color or st["base"]))


def ring(m, center_cf, r, color, n=12, thick=0.6, mat="Neon"):
    for i in range(n):
        a = i * math.tau / n
        m.add(part("Ring", (thick, 2 * math.pi * r / n + 0.15, thick),
                   center_cf * CF(math.cos(a) * r, math.sin(a) * r, 0) * CF.rz(a), color, mat,
                   collide=False))


# ------------------------------------------------------------------ tile paths
def t_straight(p):
    p.line((0, ROAD_Y, -HALF), 4)


def t_turn(p):
    R = HALF
    p.curve(lambda t: ((R - R * math.cos(t * math.pi / 2), ROAD_Y, R - R * math.sin(t * math.pi / 2)),
                       (0, 1, 0)), 24)


def t_bump(p):
    p.curve(lambda t: ((0, ROAD_Y + 0.9 * math.sin(math.pi * t) ** 4, HALF - CELL * t), (0, 1, 0)), 8)


def t_hill(p):
    p.curve(lambda t: ((0, ROAD_Y + 2.6 * math.sin(math.pi * t) ** 2, HALF - CELL * t), (0, 1, 0)),
            10)


def t_banked(p):
    R = HALF

    def fn(t):
        a = t * math.pi / 2
        roll = math.radians(30) * math.sin(math.pi * t)
        up = (math.sin(roll) * math.cos(a), math.cos(roll), math.sin(roll) * math.sin(a))
        return (R - R * math.cos(a), ROAD_Y + 0.6 * math.sin(math.pi * t), R - R * math.sin(a)), up
    p.curve(fn, 24)


def t_boost(p):
    p.line((0, ROAD_Y, -HALF), 4, flags={"Boost": 2})


def t_chicane(p):
    p.curve(lambda t: ((1.4 * math.sin(2 * math.pi * t), ROAD_Y, HALF - CELL * t), (0, 1, 0)), 12)


def t_jump(p):
    p.curve(lambda t: ((0, ROAD_Y + 1.4 * t * t, HALF - 3.2 * t), (0, 1, 0)), 4)
    y0, z0 = ROAD_Y + 1.4, HALF - 3.2
    y1, z1 = ROAD_Y + 1.4, HALF - 6.6
    for i in range(1, 6):
        u = i / 6
        y = y0 + (y1 - y0) * u + 4 * 1.8 * u * (1 - u)
        z = z0 + (z1 - z0) * u
        p.s.append(((0, y, z), (0, 0, -1), (0, 1, 0), False, {}))
    p.s.append(((0, y1, z1), (0, -0.3, -1), (0, 1, 0), False, {}))
    p.curve(lambda t: ((0, y1 - 1.4 * smooth(t), z1 - 3.4 * t), (0, 1, 0)), 4)


def t_corkscrew(p):
    r = 1.8

    def fn(t):
        ph = math.tau * smooth(t)
        return ((-r * math.sin(ph), ROAD_Y + r - r * math.cos(ph), HALF - CELL * t),
                (math.sin(ph), math.cos(ph), 0))
    p.curve(fn, 18)


def loop_at(p, zc, R, y0=ROAD_Y, n=20):
    """Vertical loop starting at current end (x=0, z=zc)."""
    def fn(t):
        th = math.tau * t
        return (0, y0 + R - R * math.cos(th), zc - R * math.sin(th)), (0, math.cos(th), math.sin(th))
    p.curve(fn, n)


def t_loop(p):
    p.line((0, ROAD_Y, 1.5), 2)
    loop_at(p, 1.5, 3.2)
    p.line((0, ROAD_Y, -HALF), 3)


def t_spiral(p):
    p.line((0, ROAD_Y, 2.8), 1)
    R = 2.2

    def fn(t):
        a = math.tau * t
        return (R - R * math.cos(a), ROAD_Y + 4.5 * t, 2.8 - R * math.sin(a)), (0, 1, 0)
    p.curve(fn, 22)
    top = p.end
    p.curve(lambda t: ((0, top[1] - 4.5 * smooth(t), top[2] + (-HALF - top[2]) * t), (0, 1, 0)), 8)


def t_wave(p):
    def fn(t):
        roll = math.radians(35) * math.sin(2 * math.pi * t)
        return ((0, ROAD_Y + 2.2 * math.sin(2 * math.pi * t) ** 2, HALF - CELL * t),
                (math.sin(roll), math.cos(roll), 0))
    p.curve(fn, 16)


def t_wallride(p):
    def fn(t):
        s2 = math.sin(math.pi * t) ** 2
        roll = math.radians(80) * s2
        return ((-1.6 * s2, ROAD_Y + 1.8 * s2, HALF - CELL * t), (math.sin(roll), math.cos(roll), 0))
    p.curve(fn, 14)


def t_double_loop(p):
    p.line((0, ROAD_Y, 3.2), 1)
    loop_at(p, 3.2, 2.4, n=16)
    p.line((0, ROAD_Y, -1.4), 2)
    loop_at(p, -1.4, 2.4, n=16)
    p.line((0, ROAD_Y, -HALF), 2)


def t_teleport(p):
    p.line((0, ROAD_Y, 2.2), 2)
    p.teleport((0, ROAD_Y, -2.2))
    p.line((0, ROAD_Y, -HALF), 2)


def t_skyleap(p):
    p.line((0, ROAD_Y, 3.0), 2)
    p.teleport((0, ROAD_Y + 12, 3.5))
    p.line((0, ROAD_Y + 12, 2.0), 1)
    loop_at(p, 2.0, 2.4, y0=ROAD_Y + 12, n=16)
    # leap: dive from the sky platform onto the exit
    y0 = ROAD_Y + 12
    for i in range(1, 9):
        u = i / 8
        y = y0 + (ROAD_Y - y0) * u + 4 * 3.0 * u * (1 - u)
        z = 2.0 + (-3.0 - 2.0) * u
        p.s.append(((0, y, z), (0, 0, -1), (0, 1, 0), False, {"Boost": 1.6}))
    p.line((0, ROAD_Y, -HALF), 2)


# ------------------------------------------------------------------ decor
def d_cones(m, path):
    for x, z in ((-4.2, 3.8), (4.2, -3.8)):
        m.add(part("Cone", (0.8, 0.9, 0.8), CF(x, 0.85, z), "#ff8a1f"))
        m.add(part("ConeTip", (0.5, 0.5, 0.5), CF(x, 1.5, z), "#ffffff"))


def d_boost(m, path):
    for z in (2.5, -1.0):
        for side in (-1, 1):
            m.add(part("Arrow", (0.6, 0.12, 2.4), CF(side * 0.8, ROAD_Y + 0.02, z)
                       * CF.ry(side * math.radians(35)), "#ff9f1a", "Neon", collide=False))
    m.add(part("ArchL", (0.6, 4, 0.6), CF(-3.6, 2.4, 0), "#ffcc33"))
    m.add(part("ArchR", (0.6, 4, 0.6), CF(3.6, 2.4, 0), "#ffcc33"))
    m.add(part("ArchTop", (7.8, 0.6, 0.6), CF(0, 4.4, 0), "#ffcc33", "Neon"))


def d_banked(m, path):
    R = HALF
    for i in range(6):
        a = (i + 0.5) / 6 * math.pi / 2
        x, z = R - (R + 3.6) * math.cos(a), R - (R + 3.6) * math.sin(a)
        m.add(part("Wall", (0.5, 1.8, 2.6), CF(x, 1.3, z) * CF.ry(-a), "#ffffff"))


def d_jump(m, path):
    for side in (-1, 1):
        m.add(part("Flag", (0.2, 3, 0.2), CF(side * 4, 1.9, -1.6), "#ffffff"))
        m.add(part("FlagCloth", (0.1, 0.8, 1.2), CF(side * 4, 3.0, -1.0), "#ff3b3b"))


def d_spiral(m, path):
    m.add(part("Pole", (6, 1.2, 1.2), CF(2.2, 3.2, 2.8) * CF.rz(math.pi / 2), "#ffcc33",
               shape="Cylinder"))


def d_teleport(m, path):
    ring(m, CF(0, ROAD_Y + 2.6, 2.2), 2.6, "#b54dff")
    ring(m, CF(0, ROAD_Y + 2.6, -2.2), 2.6, "#b54dff")
    m.add(part("Swirl", (4.4, 4.4, 0.2), CF(0, ROAD_Y + 2.6, 2.2), "#d9a3ff", "ForceField",
               collide=False))
    m.add(part("Swirl2", (4.4, 4.4, 0.2), CF(0, ROAD_Y + 2.6, -2.2), "#d9a3ff", "ForceField",
               collide=False))


def d_skyleap(m, path):
    ring(m, CF(0, ROAD_Y + 2.6, 3.0), 2.6, "#ffffff")
    for i, x in enumerate((-3.6, 3.6)):
        m.add(part("Pillar", (0.6, 12, 0.6), CF(x, 6.4, 3.0), RAINBOW[i * 3], "Neon"))
    m.add(part("Star", (1.4, 1.4, 1.4), CF(0, 19, 1.0) * CF.angles(0.6, 0.6, 0), "#ffe03b",
               "Neon", collide=False))


def d_loop_supports(m, path):
    m.add(part("Support", (0.5, 1.2, 0.5), CF(-3.6, 1.0, 0), "#9aa3b5"))
    m.add(part("Support2", (0.5, 1.2, 0.5), CF(3.6, 1.0, 0), "#9aa3b5"))


def d_start(m, path):
    for i in range(6):
        for j in range(2):
            m.add(part("Checker", (1.0, 0.06, 1.0), CF(-2.5 + i, ROAD_Y + 0.02, -0.5 + j),
                       "#ffffff" if (i + j) % 2 else "#111111", collide=False))
    m.add(part("GateL", (0.6, 5, 0.6), CF(-3.7, 2.9, 0), "#2b2b33"))
    m.add(part("GateR", (0.6, 5, 0.6), CF(3.7, 2.9, 0), "#2b2b33"))
    m.add(part("GateTop", (8.2, 1.2, 0.8), CF(0, 5.6, 0), "#ff3b6b"))


TILES = [
    # id, display, tier, odds, value, path fn, decor, ports, desc
    ("Straight", "Straight", "Common", 2, 1, t_straight, None, "SN", "A plain piece of road."),
    ("Turn", "Turn", "Common", 3, 2, t_turn, None, "SE", "A 90° corner."),
    ("SpeedBump", "Speed Bump", "Common", 6, 3, t_bump, d_cones, "SN", "A little bump."),
    ("Hill", "Hill", "Rare", 15, 6, t_hill, None, "SN", "Up and over!"),
    ("BankedTurn", "Banked Turn", "Rare", 35, 12, t_banked, d_banked, "SE", "A fast tilted corner."),
    ("BoostPad", "Boost Pad", "Rare", 80, 25, t_boost, d_boost, "SN", "Doubles your speed."),
    ("Chicane", "Chicane", "Epic", 250, 60, t_chicane, d_cones, "SN", "Left-right wiggle."),
    ("Jump", "Jump", "Epic", 700, 150, t_jump, d_jump, "SN", "Fly over a gap."),
    ("Corkscrew", "Corkscrew", "Epic", 2000, 400, t_corkscrew, None, "SN", "A full barrel roll."),
    ("Loop", "Loop", "Legendary", 6000, 1000, t_loop, d_loop_supports, "SN", "A vertical loop."),
    ("Spiral", "Spiral", "Legendary", 20000, 3000, t_spiral, d_spiral, "SN",
     "Spin up the pole, slide down."),
    ("WaveRider", "Wave Rider", "Legendary", 60000, 9000, t_wave, None, "SN",
     "Swoops and rolls."),
    ("WallRide", "Wall Ride", "Mythical", 250000, 30000, t_wallride, None, "SN",
     "Drive on the wall!"),
    ("DoubleLoop", "Double Loop", "Mythical", 1000000, 100000, t_double_loop, d_loop_supports,
     "SN", "Two loops in a row."),
    ("TeleportGate", "Teleport Gate", "Mythical", 5000000, 400000, t_teleport, d_teleport, "SN",
     "Warp through a portal."),
    ("SkyLeap", "Sky Leap", "Secret", 19000000, 1500000, t_skyleap, d_skyleap, "SN",
     "Teleport, loop, leap!"),
]


def build_tile(tid, display, tier, odds, value, fn, decor, ports, desc, base_col=None):
    p = Path()
    fn(p)
    m = Inst("Model", tid, attrs={"Tier": tier, "Odds": odds, "Value": value, "Ports": ports,
                                  "DisplayName": display, "Description": desc})
    base(m, tier, base_col)
    build_road(m, p, tier, rainbow=tier == "Secret")
    if decor:
        decor(m, p)
    add_path(m, p)
    return m


def build():
    root = Inst("Folder", "Tiles")
    for t in TILES:
        root.add(build_tile(*t))
    start = build_tile("Start", "Start", "Common", 1, 0, t_straight, d_start, "SN", "Start line",
                       base_col="#ffffff")
    root.add(start)
    return root


if __name__ == "__main__":
    write_model(build(), "ReplicatedStorage/Assets/Tiles.model.json")
