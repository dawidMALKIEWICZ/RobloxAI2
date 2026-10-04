"""Generates src/ReplicatedStorage/Assets/TrackPieces.model.json.

Every piece is built relative to the origin: entry at (0,0,0) heading -Z (Roblox LookVector),
road top surface at y=0. Each piece model contains:
  - road/kerb/decor parts
  - "Exit" part: the pose where the next piece attaches
  - "Path" folder: waypoint parts "1".."n" the car follows (attributes: Teleport, Boost)
The server places a piece by transforming every part with the chain CFrame.
"""
import math

from rbx import (CF, Inst, add, cross, length, mul, norm, part, sub, write_model)

ROAD_W = 16
STEP = 4.0

TIER_STYLE = {
    "Common": dict(kerb=("#ff3030", "#ffffff"), road="#3a3a42", edge="#2b2b33", neon=None),
    "Rare": dict(kerb=("#2f8bff", "#ffffff"), road="#363c4a", edge="#1f4e99", neon="#5cc8ff"),
    "Epic": dict(kerb=("#a43bff", "#ffffff"), road="#3a3448", edge="#5e1f99", neon="#c46bff"),
    "Legendary": dict(kerb=("#ffb31a", "#ffffff"), road="#3e3a32", edge="#a86a00",
                      neon="#ffcc33"),
    "Mythical": dict(kerb=("#ff3b6b", "#ffe0ea"), road="#3a2a33", edge="#a3123b",
                     neon="#ff4f86"),
    "Secret": dict(kerb=("#ffffff", "#111111"), road="#1d1d26", edge="#111111", neon="rainbow"),
}
RAINBOW = ["#ff3b3b", "#ff9f1a", "#ffe03b", "#4bdc5a", "#3bd1ff", "#3b6bff", "#b54dff"]


def smooth(t):
    return t * t * (3 - 2 * t)


class Turtle:
    """Accumulates centreline samples (pos, fwd, up, road, flags)."""

    def __init__(self):
        self.frame = CF()
        self.samples = [((0.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0), True, {})]

    def _emit(self, lp, lf, lu, road=True, flags=None):
        p = self.frame.point(lp)
        f = norm(self.frame.vector(lf))
        u = norm(self.frame.vector(lu))
        self.samples.append((p, f, u, road, dict(flags or {})))

    def _rebase(self):
        p, f, u, _, _ = self.samples[-1]
        # drop roll so following pieces stay level
        self.frame = CF.look(p, f, (0, 1, 0)) if abs(f[1]) < 0.95 else CF.look(p, f, u)

    def param(self, fn, length_est, road=True, flags=None, rebase=True, n=None):
        """fn(s) -> local pos, s in [0,1]; up via upfn or default."""
        n = n or max(2, int(math.ceil(length_est / STEP)))
        for i in range(1, n + 1):
            s = i / n
            p, up = fn(s)
            e = 1e-3
            p2, _ = fn(min(1, s + e))
            p1, _ = fn(max(0, s - e))
            f = norm(sub(p2, p1))
            self._emit(p, f, up, road, flags)
        if rebase:
            self._rebase()

    def straight(self, L, road=True, flags=None):
        self.param(lambda s: ((0, 0, -L * s), (0, 1, 0)), L, road, flags)

    def turn(self, R, deg, bank=0.0, flags=None):
        """Right turn of `deg` degrees with radius R; bank in degrees (inward roll)."""
        a = math.radians(deg)

        def fn(s):
            t = a * s
            p = (R - R * math.cos(t), 0, -R * math.sin(t))
            roll = math.radians(bank) * math.sin(math.pi * s)
            # bank inward (towards +X centre): tilt up vector to the right
            up = (math.sin(roll) * math.cos(t), math.cos(roll), math.sin(roll) * math.sin(t))
            return p, up
        self.param(fn, R * a, flags=flags)

    def teleport_to(self, local_pos):
        """Car jumps instantly from the current sample to local_pos (same heading)."""
        self.samples[-1][4]["Teleport"] = True
        p = self.frame.point(local_pos)
        self.frame = CF(*p, R=self.frame.R)
        self.samples.append((p, self.frame.look_vector, self.frame.up_vector, False, {}))


def mirror_samples(samples):
    out = []
    for p, f, u, road, flags in samples:
        out.append(((-p[0], p[1], p[2]), (-f[0], f[1], f[2]), (-u[0], u[1], u[2]), road, flags))
    return out


def frame_at(p, f, u):
    r = norm(cross(f, u))
    uu = cross(r, f)
    return CF.from_axes(p, r, uu, (-f[0], -f[1], -f[2])), r, uu


def build_road(m, samples, tier, rainbow=False):
    st = TIER_STYLE[tier]
    k = 0
    for i in range(1, len(samples)):
        p0, f0, u0, _, _ = samples[i - 1]
        p1, f1, u1, road, _ = samples[i]
        if not road:
            continue
        d = sub(p1, p0)
        L = length(d)
        if L < 1e-3:
            continue
        f = norm(d)
        u = norm(add(u0, u1))
        cf, r, uu = frame_at(mul(add(p0, p1), 0.5), f, u)
        ang = math.acos(max(-1, min(1, f0[0] * f1[0] + f0[1] * f1[1] + f0[2] * f1[2])))
        extra = ROAD_W * math.tan(ang / 2) + 0.3
        road_col = RAINBOW[i % len(RAINBOW)] if rainbow else st["road"]
        mat = "Neon" if rainbow else "Asphalt"
        m.add(part("Road", (ROAD_W, 1, L + extra), cf * CF(0, -0.5, 0), road_col, mat))
        kc = st["kerb"][k % 2]
        k += 1
        for side in (-1, 1):
            m.add(part("Kerb", (1.2, 1.2, L + extra), cf * CF(side * (ROAD_W / 2 + 0.6), -0.4, 0),
                       kc, "SmoothPlastic"))
        if st["neon"] and i % 3 == 0:
            col = RAINBOW[(i // 3) % len(RAINBOW)] if st["neon"] == "rainbow" else st["neon"]
            for side in (-1, 1):
                m.add(part("Glow", (0.4, 0.4, L + extra),
                           cf * CF(side * (ROAD_W / 2 + 1.3), -0.6, 0), col, "Neon",
                           collide=False))


def add_path(m, samples, speed_flags=None):
    folder = Inst("Folder", "Path")
    for i, (p, f, u, road, flags) in enumerate(samples):
        cf, _, _ = frame_at(p, f, u)
        attrs = {}
        if flags.get("Teleport"):
            attrs["Teleport"] = True
        if flags.get("Boost"):
            attrs["Boost"] = flags["Boost"]
        folder.add(part(str(i + 1), (1, 1, 1), cf, "#ffffff", transparency=1, collide=False,
                        touch=False, attrs=attrs or None))
    m.add(folder)


def portal(m, cf, color, r=11):
    """Ring of neon blocks standing across the road at cf."""
    n = 16
    for i in range(n):
        a = i * math.tau / n
        x, y = math.cos(a) * r, math.sin(a) * r + r - 1
        m.add(part("PortalRing", (4.6, 1.6, 1.6), cf * CF(x, y, 0) * CF.rz(a + math.pi / 2),
                   color, "Neon", collide=False))
    m.add(part("PortalFill", (r * 1.6, r * 1.6, 0.3), cf * CF(0, r - 1, 0), color, "ForceField",
               transparency=0.3, collide=False))


def finish(name, tier, odds, value, t, decor=None, rainbow=False, mirror=False, desc=""):
    samples = mirror_samples(t.samples) if mirror else t.samples
    m = Inst("Model", name, attrs={"Tier": tier, "Odds": odds, "Value": value,
                                   "Description": desc})
    build_road(m, samples, tier, rainbow)
    if decor:
        decor(m, mirror)
    p, f, u, _, _ = samples[-1]
    cf, _, _ = frame_at(p, f, u)
    m.add(part("Exit", (1, 1, 1), cf, "#ffffff", transparency=1, collide=False, touch=False))
    add_path(m, samples)
    return m


# ------------------------------------------------------------------ pieces
def p_straight():
    t = Turtle()
    t.straight(40)
    return t


def p_gentle():
    t = Turtle()
    t.turn(60, 45)
    return t


def p_sharp():
    t = Turtle()
    t.straight(4)
    t.turn(24, 90)
    t.straight(4)
    return t


def p_ramp():
    t = Turtle()
    t.param(lambda s: ((0, 16 * smooth(s), -56 * s), (0, 1, 0)), 58)
    return t


def p_hills():
    t = Turtle()
    t.param(lambda s: ((0, 5 * math.sin(3 * math.pi * s) ** 2, -84 * s), (0, 1, 0)), 90, n=36)
    return t


def p_banked():
    t = Turtle()
    t.straight(4)
    t.turn(50, 90, bank=25)
    t.straight(4)
    return t


def p_chicane():
    t = Turtle()
    t.param(lambda s: ((12 * (1 - math.cos(4 * math.pi * s)) / 2 * (1 if s < 0.5 else -1),
                        0, -100 * s), (0, 1, 0)), 104, n=36)
    return t


def p_corkscrew():
    t = Turtle()
    t.straight(10)

    def fn(s):
        ph = math.tau * smooth(s)
        return (-8 * math.sin(ph), 8 - 8 * math.cos(ph), -90 * s), (math.sin(ph), math.cos(ph), 0)
    t.param(fn, 100, n=40)
    t.straight(10)
    return t


def jump(t, rise, kick_len, gap, apex, land_drop, land_len, flags=None):
    """Kicker ramp, ballistic flight (no road), landing ramp."""
    t.param(lambda s: ((0, rise * s * s, -kick_len * s), (0, 1, 0)), kick_len, flags=flags,
            rebase=False)
    y0 = rise
    z0 = -kick_len
    y1 = rise - land_drop + land_drop  # landing ramp starts at same height as kicker top
    n = max(6, int(gap / 4))
    for i in range(1, n + 1):
        u = i / n
        y = y0 + (y1 - y0) * u + 4 * apex * u * (1 - u)
        z = z0 - gap * u
        e = 1e-3
        ya = y0 + (y1 - y0) * (u + e) + 4 * apex * (u + e) * (1 - u - e)
        f = norm((0, ya - y, -gap * e))
        t._emit((0, y, z), f, (0, 1, 0), road=False, flags=flags)
    ys = y1
    zs = z0 - gap
    t.param(lambda s: ((0, ys - land_drop * smooth(s), zs - land_len * s), (0, 1, 0)), land_len,
            flags=flags, rebase=False)
    t._rebase()


def p_jumpgap():
    t = Turtle()
    t.straight(6)
    jump(t, rise=6, kick_len=18, gap=40, apex=12, land_drop=6, land_len=20)
    t.straight(8)
    return t


def loop(t, R=20, shift=18, flags=None):
    def fn(s):
        th = math.tau * s
        x = shift * smooth(s)
        return (x, R - R * math.cos(th), -R * math.sin(th)), (0, math.cos(th), math.sin(th))
    t.param(fn, math.tau * R, flags=flags, n=40)


def p_loop():
    t = Turtle()
    t.straight(10)
    loop(t)
    t.straight(10)
    return t


def p_boost():
    t = Turtle()
    t.straight(80, flags={"Boost": 2})
    return t


def p_spiral():
    t = Turtle()
    t.straight(8)
    R, H = 30, 40

    def fn(s):
        a = 4 * math.pi * s
        roll = math.radians(15) * math.sin(math.pi * s)
        up = (math.sin(roll) * math.cos(a), math.cos(roll), math.sin(roll) * math.sin(a))
        return (R - R * math.cos(a), H * s, -R * math.sin(a)), up
    t.param(fn, 4 * math.pi * R, n=64)
    t.straight(8)
    return t


def p_wave():
    t = Turtle()

    def fn(s):
        y = -10 * (1 - math.cos(4 * math.pi * s)) / 2
        roll = math.radians(35) * math.sin(4 * math.pi * s)
        return (0, y, -120 * s), (math.sin(roll), math.cos(roll), 0)
    t.param(fn, 124, n=44)
    return t


def p_wallride():
    t = Turtle()
    t.straight(6)

    def fn(s):
        roll = math.radians(80) * math.sin(math.pi * s) ** 2
        return (-10 * math.sin(math.pi * s) ** 2, 6 * math.sin(math.pi * s) ** 2, -100 * s), \
            (math.sin(roll), math.cos(roll), 0)
    t.param(fn, 104, n=40)
    t.straight(6)
    return t


def p_teleport():
    t = Turtle()
    t.straight(18)
    t.teleport_to((0, 60, -120))
    t.straight(22)
    return t


def p_skyleap():
    t = Turtle()
    t.straight(14)
    t.teleport_to((0, 80, -110))
    t.straight(10)
    loop(t, R=22, shift=18)
    t.straight(10)
    jump(t, rise=10, kick_len=24, gap=120, apex=45, land_drop=10, land_len=30,
         flags={"Boost": 1.6})
    t.straight(10)
    return t


# ------------------------------------------------------------------ decor
def decor_boost(m, mirror):
    for i in range(5):
        z = -8 - i * 16
        cf = CF(0, 0, z)
        for k in range(9):
            a = math.pi * k / 8
            m.add(part("Arch", (4, 1.4, 1.4), cf * CF(math.cos(a) * 10, math.sin(a) * 10, 0)
                       * CF.rz(a + math.pi / 2), "#ffcc33", "Neon", collide=False))
        m.add(part("BoostPad", (8, 0.3, 6), CF(0, 0.05, z - 6), "#ff9f1a", "Neon",
                   collide=False))


def decor_spiral(m, mirror):
    x = -30 if mirror else 30
    m.add(part("Tower", (70, 10, 10), CF(x, 5, -8) * CF.rz(math.pi / 2), "#d9a521", "Metal",
               shape="Cylinder"))
    m.add(part("TowerTop", (3, 16, 16), CF(x, 41.5, -8) * CF.rz(math.pi / 2), "#ffcc33", "Neon",
               shape="Cylinder"))


def decor_teleport(m, mirror):
    portal(m, CF(0, 0, -18), "#b54dff")
    portal(m, CF(0, 60, -120), "#b54dff")


def decor_skyleap(m, mirror):
    portal(m, CF(0, 0, -14), "#ffffff")
    portal(m, CF(0, 80, -110), "#ffe03b")
    m.add(part("Star", (6, 6, 6), CF(0, 140, -250) * CF.angles(0.6, 0.6, 0), "#ffe03b", "Neon",
               collide=False))


PIECES = [
    # id, display, tier, odds (1 in N), value per pass, builder, decor, turns, description
    ("Straight", "Straight", "Common", 2, 10, p_straight, None, False, "A plain straight road."),
    ("GentleCurve", "Gentle Curve", "Common", 4, 18, p_gentle, None, True, "A soft 45° bend."),
    ("SharpTurn", "Sharp Turn", "Common", 10, 35, p_sharp, None, True, "A tight 90° corner."),
    ("Ramp", "Ramp", "Rare", 25, 80, p_ramp, None, False, "Climbs 16 studs higher."),
    ("BumpyHills", "Bumpy Hills", "Rare", 60, 160, p_hills, None, False, "Three bouncy humps."),
    ("BankedCurve", "Banked Curve", "Rare", 150, 320, p_banked, None, True,
     "A fast tilted 90° curve."),
    ("Chicane", "Chicane", "Epic", 400, 650, p_chicane, None, False, "Left-right S bends."),
    ("Corkscrew", "Corkscrew", "Epic", 1200, 1500, p_corkscrew, None, False,
     "A full barrel roll."),
    ("JumpGap", "Jump Gap", "Epic", 3000, 3200, p_jumpgap, None, False, "Fly over a 40 stud gap."),
    ("Loop", "Loop", "Legendary", 8000, 7500, p_loop, None, False, "A full vertical loop."),
    ("BoostTunnel", "Boost Tunnel", "Legendary", 20000, 15000, p_boost, decor_boost, False,
     "Neon arches double your speed."),
    ("SpiralTower", "Spiral Tower", "Legendary", 75000, 40000, p_spiral, decor_spiral, False,
     "Two spirals up a golden tower."),
    ("WaveRider", "Wave Rider", "Mythical", 250000, 120000, p_wave, None, False,
     "Swoops and rolls like a wave."),
    ("WallRide", "Wall Ride", "Mythical", 1000000, 400000, p_wallride, None, False,
     "Drive sideways on the wall!"),
    ("TeleportGate", "Teleport Gate", "Mythical", 5000000, 1500000, p_teleport, decor_teleport,
     False, "Warp to a floating road."),
    ("SkyLeap", "Sky Leap", "Secret", 19000000, 6000000, p_skyleap, decor_skyleap, False,
     "Teleport, loop, then leap over everything!"),
]


def build():
    root = Inst("Folder", "TrackPieces")
    for pid, display, tier, odds, value, builder, decor, turns, desc in PIECES:
        rainbow = tier == "Secret"
        if turns:
            for side, mirror in (("R", False), ("L", True)):
                m = finish(f"{pid}_{side}", tier, odds, value, builder(), decor, rainbow, mirror,
                           desc)
                m.attrs["PieceId"] = pid
                m.attrs["DisplayName"] = display
                root.add(m)
        else:
            m = finish(pid, tier, odds, value, builder(), decor, rainbow, False, desc)
            m.attrs["PieceId"] = pid
            m.attrs["DisplayName"] = display
            root.add(m)
    return root


if __name__ == "__main__":
    write_model(build(), "ReplicatedStorage/Assets/TrackPieces.model.json")
