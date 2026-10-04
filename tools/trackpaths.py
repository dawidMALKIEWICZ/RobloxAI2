"""Centre lines of every track tile (pure Python, shared by Blender and the Rojo generator).

Roblox axes: Y up. A tile fills one CELL x CELL grid cell, origin = cell centre at pad height.
Port A is the +Z edge, port B the -Z edge ("SN") or the +X edge ("SE"). The road at a port is
always centred and 2*HALF_W wide, so neighbouring tiles line up exactly.

Every sample is (pos, fwd, up, road, flags, w): w = half road width there (roads narrow into
lanes on loops so the way in and the way out never overlap), road=False marks airborne parts.
"""
import math

from rbx import add, cross, mul, norm, sub

CELL = 10.0
HALF = CELL / 2
ROAD_Y = 0.6
HALF_W = 3.0      # road half width at the ports
LANE_W = 1.2      # half width of a loop lane (cars are 2.2 studs wide)
LOOP_SHIFT = 1.65 # loops drift sideways by 2*LOOP_SHIFT so the way in never meets the way out


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


class Path:
    def __init__(self):
        self.s = [((0.0, ROAD_Y, HALF), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0), True, {}, HALF_W)]

    @property
    def end(self):
        return self.s[-1][0]

    def curve(self, fn, n, road=True, flags=None, width=None):
        """fn(t) -> (pos, up) for t in (0, 1]; width(t) -> half width (default: keep)."""
        w0 = self.s[-1][5]
        for i in range(1, n + 1):
            t = i / n
            p, up = fn(t)
            e = 1e-3
            a, _ = fn(max(0.0, t - e))
            b, _ = fn(min(1.0, t + e))
            w = width(t) if width else w0
            self.s.append((p, norm(sub(b, a)), norm(up), road, dict(flags or {}), w))

    def line(self, p1, n=2, road=True, flags=None, w1=None):
        p0 = self.end
        w0 = self.s[-1][5]
        self.curve(lambda t: (add(p0, mul(sub(p1, p0), t)), (0, 1, 0)), n, road, flags,
                   (lambda t: lerp(w0, w1, smooth(t))) if w1 is not None else None)

    def shift(self, x1, z1, n, w1=None, y1=None):
        """S-curve from the current end to (x1, z1). Narrowing happens on a straight first
        stud and widening on a straight last stud, so the wide road never turns near a port."""
        x0, y0, z0 = self.end
        w0 = self.s[-1][5]
        yy = y0 if y1 is None else y1
        dz = -1.0 if z1 < z0 else 1.0
        if w1 is not None and w1 < w0:
            self.line((x0, y0, z0 + dz), 3, w1=w1)
            z0 += dz
        zc = z1 - dz if (w1 is not None and w1 > w0) else z1
        self.curve(lambda t: ((lerp(x0, x1, smooth(t)), lerp(y0, yy, smooth(t)), lerp(z0, zc, t)),
                              (0, 1, 0)), n)
        if zc != z1:
            self.line((x1, yy, z1), 3, w1=w1)

    def loop(self, R, x1, n=28):
        """Vertical loop from the current end (heading -Z) that drifts sideways to x1."""
        x0, y0, zc = self.end

        def fn(t):
            th = math.tau * t
            return ((lerp(x0, x1, smooth(t)), y0 + R - R * math.cos(th), zc - R * math.sin(th)),
                    (0, math.cos(th), math.sin(th)))
        self.curve(fn, n)

    def teleport(self, p, w=None):
        self.s[-1][4]["Teleport"] = True
        self.s.append((p, self.s[-1][1], (0, 1, 0), False, {}, w or self.s[-1][5]))


# ------------------------------------------------------------------ tile centre lines
def t_straight(p):
    p.line((0, ROAD_Y, -HALF), 10)


def t_turn(p):
    R = HALF
    p.curve(lambda t: ((R - R * math.cos(t * math.pi / 2), ROAD_Y,
                        R - R * math.sin(t * math.pi / 2)), (0, 1, 0)), 16)


def t_bump(p):
    p.curve(lambda t: ((0, ROAD_Y + 0.8 * math.sin(math.pi * t) ** 4, HALF - CELL * t),
                       (0, 1, 0)), 14)


def t_hill(p):
    p.curve(lambda t: ((0, ROAD_Y + 2.4 * math.sin(math.pi * t) ** 2, HALF - CELL * t),
                       (0, 1, 0)), 16)


def t_banked(p):
    R = HALF

    def fn(t):
        a = t * math.pi / 2
        roll = math.radians(25) * math.sin(math.pi * t) ** 2
        up = (math.sin(roll) * math.cos(a), math.cos(roll), math.sin(roll) * math.sin(a))
        return (R - R * math.cos(a), ROAD_Y + 1.4 * math.sin(math.pi * t) ** 2,
                R - R * math.sin(a)), up
    p.curve(fn, 18)


def t_boost(p):
    p.line((0, ROAD_Y, -HALF), 10, flags={"Boost": 2})


def t_chicane(p):
    # the sin(pi t)^2 window keeps the road straight at both ports
    p.curve(lambda t: ((1.25 * math.sin(2 * math.pi * t) * math.sin(math.pi * t) ** 2, ROAD_Y,
                        HALF - CELL * t), (0, 1, 0)), 30)


JUMP_TAKEOFF = 1.4   # z where the ramp ends
JUMP_LAND = -1.6     # z where the landing ramp starts
JUMP_H = 1.5


def t_jump(p):
    p.curve(lambda t: ((0, ROAD_Y + JUMP_H * t * t, lerp(HALF, JUMP_TAKEOFF, t)), (0, 1, 0)), 6)
    y0 = ROAD_Y + JUMP_H
    for i in range(1, 6):
        u = i / 6
        y = y0 + 4 * 1.6 * u * (1 - u) - 0.2 * u
        z = lerp(JUMP_TAKEOFF, JUMP_LAND, u)
        p.s.append(((0, y, z), (0, 0, -1), (0, 1, 0), False, {}, HALF_W))
    y1 = y0 - 0.2
    p.s.append(((0, y1, JUMP_LAND), (0, -0.3, -1), (0, 1, 0), False, {}, HALF_W))
    p.curve(lambda t: ((0, y1 - (y1 - ROAD_Y) * smooth(t), lerp(JUMP_LAND, -HALF, t)),
                       (0, 1, 0)), 6)


def t_corkscrew(p):
    r = 1.6
    p.line((0, ROAD_Y, 3.6), 2, w1=LANE_W + 0.2)

    def fn(t):
        ph = math.tau * smooth(t)
        return ((-r * math.sin(ph), ROAD_Y + r - r * math.cos(ph), lerp(3.6, -3.6, t)),
                (math.sin(ph), math.cos(ph), 0))
    p.curve(fn, 28)
    p.line((0, ROAD_Y, -HALF), 2, w1=HALF_W)


def t_loop(p):
    p.shift(-LOOP_SHIFT, 0.0, 12, w1=LANE_W)
    p.loop(3.0, LOOP_SHIFT, 32)
    p.shift(0.0, -HALF, 12, w1=HALF_W)


def t_double_loop(p):
    w, s = 1.15, 3.25
    p.shift(-s, 0.0, 12, w1=w)
    p.loop(3.0, 0.0, 30)
    p.loop(3.0, s, 30)
    p.shift(0.0, -HALF, 12, w1=HALF_W)


SPIRAL_R = 2.4
SPIRAL_RISE = 5.0


def t_spiral(p):
    """Climb once around the pole, then slide down over the start of the climb."""
    lw = 1.3
    p.shift(-SPIRAL_R, 0.0, 6, w1=lw)

    def fn(t):
        ph = math.tau * t
        return ((-SPIRAL_R * math.cos(ph), ROAD_Y + SPIRAL_RISE * t, -SPIRAL_R * math.sin(ph)),
                (0, 1, 0))
    p.curve(fn, 30)
    top = p.end

    def down(t):
        # falls slowly while above the climb, then quickly once past it
        z = lerp(top[2], -HALF, t)
        k = smooth(min(1.0, t / 0.85)) ** 1.6
        return ((lerp(top[0], 0.0, smooth(t / 0.7)), top[1] - (top[1] - ROAD_Y) * k, z), (0, 1, 0))
    p.curve(down, 16, width=lambda t: lerp(lw, HALF_W, smooth((t - 0.5) * 2)))


def t_wave(p):
    def fn(t):
        win = math.sin(math.pi * t) ** 2
        roll = math.radians(32) * math.sin(2 * math.pi * t) * win
        return ((0, ROAD_Y + 2.2 * math.sin(2 * math.pi * t) ** 2 * win, HALF - CELL * t),
                (math.sin(roll), math.cos(roll), 0))
    p.curve(fn, 26)


def t_wallride(p):
    def fn(t):
        s2 = math.sin(math.pi * t) ** 4
        roll = math.radians(75) * s2
        return ((-1.2 * s2, ROAD_Y + 2.6 * s2, HALF - CELL * t),
                (math.sin(roll), math.cos(roll), 0))
    p.curve(fn, 24, width=lambda t: lerp(HALF_W, 2.2, math.sin(math.pi * t) ** 2))


TP_IN = 2.2
TP_OUT = -2.2


def t_teleport(p):
    p.line((0, ROAD_Y, TP_IN), 3)
    p.teleport((0, ROAD_Y, TP_OUT))
    p.line((0, ROAD_Y, -HALF), 3)


SKY_H = 12.0


def t_skyleap(p):
    p.line((0, ROAD_Y, 3.2), 2)
    p.teleport((-LOOP_SHIFT, ROAD_Y + SKY_H, 3.0), w=LANE_W)
    p.line((-LOOP_SHIFT, ROAD_Y + SKY_H, 2.0), 1)
    p.loop(2.4, LOOP_SHIFT, 26)
    y0 = ROAD_Y + SKY_H
    x0, _, z0 = p.end
    p.line((x0, y0, 0.6), 2)
    for i in range(1, 9):
        u = i / 8
        y = y0 + (ROAD_Y - y0) * u + 4 * 2.5 * u * (1 - u)
        p.s.append(((lerp(x0, 0, u), y, lerp(0.6, -2.6, u)), (0, 0, -1), (0, 1, 0), False,
                    {"Boost": 1.6}, HALF_W))
    p.line((0, ROAD_Y, -HALF), 3)


# ------------------------------------------------------------------ expansion tiles
def t_bridge(p):
    p.curve(lambda t: ((0, ROAD_Y + 1.3 * math.sin(math.pi * t) ** 2, HALF - CELL * t), (0, 1, 0)), 16)


def t_camel(p):
    p.curve(lambda t: ((0, ROAD_Y + 1.7 * math.sin(2 * math.pi * t) ** 2 * math.sin(math.pi * t) ** 0.5,
                        HALF - CELL * t), (0, 1, 0)), 26)


def t_halfpipe(p):
    def fn(t):
        win = math.sin(math.pi * t) ** 4
        k = math.sin(2 * math.pi * t) * win * 1.15
        roll = math.radians(45) * k
        return ((-1.0 * k, ROAD_Y + 1.9 * abs(k), HALF - CELL * t), (math.sin(roll), math.cos(roll), 0))
    p.curve(fn, 30, width=lambda t: lerp(HALF_W, 2.4, math.sin(math.pi * t) ** 2))


def t_ring_of_fire(p):
    t_jump(p)


def t_launchpad(p):
    p.curve(lambda t: ((0, ROAD_Y + 2.1 * t * t, lerp(HALF, 1.6, t)), (0, 1, 0)), 7,
            flags={"Boost": 2.5})
    y0 = ROAD_Y + 2.1
    for i in range(1, 7):
        u = i / 7
        y = y0 + 4 * 2.6 * u * (1 - u) - 0.9 * u
        p.s.append(((0, y, lerp(1.6, -2.2, u)), (0, 0, -1), (0, 1, 0), False, {"Boost": 2}, HALF_W))
    y1 = y0 - 0.9
    p.s.append(((0, y1, -2.2), (0, -0.4, -1), (0, 1, 0), False, {}, HALF_W))
    p.curve(lambda t: ((0, y1 - (y1 - ROAD_Y) * smooth(t), lerp(-2.2, -HALF, t)), (0, 1, 0)), 6)


def t_twister(p):
    r = 1.5
    p.line((0, ROAD_Y, 4.0), 2, w1=LANE_W + 0.4)

    def fn(t):
        ph = 2 * math.tau * smooth(t)
        return ((-r * math.sin(ph), ROAD_Y + r - r * math.cos(ph), lerp(4.0, -4.0, t)),
                (math.sin(ph), math.cos(ph), 0))
    p.curve(fn, 44)
    p.line((0, ROAD_Y, -HALF), 2, w1=HALF_W)


def t_rainbow(p):
    p.curve(lambda t: ((0, ROAD_Y + 0.9 * math.sin(2 * math.pi * t) ** 2, HALF - CELL * t), (0, 1, 0)),
            22, flags={"Boost": 1.4})


BH_IN = 2.6
BH_OUT = -2.6


def t_blackhole(p):
    p.curve(lambda t: ((0, ROAD_Y - 0.0 * t, lerp(HALF, BH_IN, t)), (0, 1, 0)), 4)
    p.teleport((0, ROAD_Y, BH_OUT))
    p.line((0, ROAD_Y, -HALF), 4)


# id, display, tier, odds, value, path fn, ports, desc
TILES = [
    ("Straight", "Straight", "Common", 2, 1, t_straight, "SN", "A plain piece of road."),
    ("Turn", "Turn", "Common", 3, 2, t_turn, "SE", "A 90° corner."),
    ("SpeedBump", "Speed Bump", "Common", 6, 3, t_bump, "SN", "A little bump."),
    ("Hill", "Hill", "Rare", 15, 6, t_hill, "SN", "Up and over!"),
    ("BankedTurn", "Banked Turn", "Rare", 35, 12, t_banked, "SE", "A fast tilted corner."),
    ("BoostPad", "Boost Pad", "Rare", 80, 25, t_boost, "SN", "Doubles your speed."),
    ("Chicane", "Chicane", "Epic", 250, 60, t_chicane, "SN", "Left-right wiggle."),
    ("Jump", "Jump", "Epic", 700, 150, t_jump, "SN", "Fly over a gap."),
    ("Corkscrew", "Corkscrew", "Epic", 2000, 400, t_corkscrew, "SN", "A full barrel roll."),
    ("Loop", "Loop", "Legendary", 6000, 1000, t_loop, "SN", "A vertical loop."),
    ("Spiral", "Spiral", "Legendary", 20000, 3000, t_spiral, "SN",
     "Spin up the pole, slide down."),
    ("WaveRider", "Wave Rider", "Legendary", 60000, 9000, t_wave, "SN", "Swoops and rolls."),
    ("WallRide", "Wall Ride", "Mythical", 250000, 30000, t_wallride, "SN", "Drive on the wall!"),
    ("DoubleLoop", "Double Loop", "Mythical", 1000000, 100000, t_double_loop, "SN",
     "Two loops in a row."),
    ("TeleportGate", "Teleport Gate", "Mythical", 5000000, 400000, t_teleport, "SN",
     "Warp through a portal."),
    ("SkyLeap", "Sky Leap", "Secret", 19000000, 1500000, t_skyleap, "SN",
     "Teleport, loop, leap!"),
    # expansion
    ("Tunnel", "Tunnel", "Rare", 25, 9, t_straight, "SN", "A glowing rock tunnel."),
    ("Bridge", "River Bridge", "Rare", 50, 18, t_bridge, "SN", "Hop over a little river."),
    ("IceTurn", "Ice Turn", "Rare", 120, 35, t_turn, "SE", "A slippery frozen corner."),
    ("CamelBack", "Camel Back", "Epic", 400, 100, t_camel, "SN", "Two bumps, double fun."),
    ("HalfPipe", "Half Pipe", "Epic", 1200, 250, t_halfpipe, "SN", "Ride up both walls."),
    ("NeonTurn", "Neon Turn", "Epic", 3500, 600, t_turn, "SE", "A corner lit with neon."),
    ("RingOfFire", "Ring of Fire", "Legendary", 12000, 2000, t_ring_of_fire, "SN",
     "Jump through the flames!"),
    ("LaunchPad", "Launch Pad", "Legendary", 35000, 5500, t_launchpad, "SN",
     "Boost and fly high."),
    ("Twister", "Twister", "Mythical", 500000, 60000, t_twister, "SN", "Two barrel rolls."),
    ("RainbowRoad", "Rainbow Road", "Mythical", 2500000, 220000, t_rainbow, "SN",
     "A glowing rainbow speedway."),
    ("BlackHole", "Black Hole", "Secret", 50000000, 3500000, t_blackhole, "SN",
     "Swallowed and spat out!"),
]
# order tiles by rarity so lists, the index and the reel read from common to secret
TILES.sort(key=lambda t: t[3])
START = ("Start", "Start", "Common", 1, 0, t_straight, "SN", "Start line")


def make_path(fn):
    p = Path()
    fn(p)
    # the last sample sits on a port: square its frame up exactly with the cell edge
    pos, _f, _u, road, flags, w = p.s[-1]
    f = (1.0, 0.0, 0.0) if abs(pos[0] - HALF) < 1e-3 else (0.0, 0.0, -1.0)
    p.s[-1] = (pos, f, (0.0, 1.0, 0.0), road, flags, w)
    return p


def frame(sample):
    """(pos, right, up, fwd) of a sample with an orthonormal frame."""
    p, f, u, _road, _flags, _w = sample
    r = norm(cross(f, u))
    uu = cross(r, f)
    return p, r, uu, f
