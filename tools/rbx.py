"""Tiny helper library for generating Rojo .model.json instance trees from Python.

Roblox conventions: Y is up, a CFrame's LookVector is -Z, sizes in studs.
"""
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")


# ---------------------------------------------------------------- math
class CF:
    """Minimal CFrame: position p (tuple) + rotation R (3 rows)."""

    __slots__ = ("p", "R")

    def __init__(self, x=0.0, y=0.0, z=0.0, R=None):
        self.p = (float(x), float(y), float(z))
        self.R = R or ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    @staticmethod
    def angles(rx=0.0, ry=0.0, rz=0.0):
        """Same as Roblox CFrame.Angles (applies Z, then Y, then X)."""
        return CF.rx(rx) * CF.ry(ry) * CF.rz(rz)

    @staticmethod
    def rx(a):
        c, s = math.cos(a), math.sin(a)
        return CF(R=((1, 0, 0), (0, c, -s), (0, s, c)))

    @staticmethod
    def ry(a):
        c, s = math.cos(a), math.sin(a)
        return CF(R=((c, 0, s), (0, 1, 0), (-s, 0, c)))

    @staticmethod
    def rz(a):
        c, s = math.cos(a), math.sin(a)
        return CF(R=((c, -s, 0), (s, c, 0), (0, 0, 1)))

    @staticmethod
    def from_axes(pos, right, up, back):
        """Build from column vectors (right=X, up=Y, back=Z)."""
        R = tuple((right[i], up[i], back[i]) for i in range(3))
        return CF(*pos, R=R)

    @staticmethod
    def look(pos, forward, up=(0, 1, 0)):
        f = norm(forward)
        r = norm(cross(f, up))
        if length(r) < 1e-6:
            r = norm(cross(f, (0, 0, 1)))
        u = cross(r, f)
        return CF.from_axes(pos, r, u, neg(f))

    def __mul__(self, o):
        if isinstance(o, CF):
            R = tuple(tuple(sum(self.R[i][k] * o.R[k][j] for k in range(3)) for j in range(3))
                      for i in range(3))
            p = self.point(o.p)
            return CF(*p, R=R)
        raise TypeError

    def vector(self, v):
        return tuple(sum(self.R[i][k] * v[k] for k in range(3)) for i in range(3))

    def point(self, v):
        r = self.vector(v)
        return tuple(r[i] + self.p[i] for i in range(3))

    def inverse(self):
        Rt = tuple(tuple(self.R[j][i] for j in range(3)) for i in range(3))
        inv = CF(R=Rt)
        p = inv.vector(self.p)
        return CF(-p[0], -p[1], -p[2], R=Rt)

    @property
    def look_vector(self):
        return (-self.R[0][2], -self.R[1][2], -self.R[2][2])

    @property
    def up_vector(self):
        return (self.R[0][1], self.R[1][1], self.R[2][1])

    def json(self):
        return {"CFrame": {"position": [round(c, 4) for c in self.p],
                           "orientation": [[round(c, 6) for c in row] for row in self.R]}}


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def neg(a):
    return (-a[0], -a[1], -a[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def length(a):
    return math.sqrt(dot(a, a))


def norm(a):
    L = length(a)
    return (a[0] / L, a[1] / L, a[2] / L) if L > 1e-9 else (0.0, 0.0, 0.0)


# ---------------------------------------------------------------- value encoders
def hex3(h):
    h = h.lstrip("#")
    return [round(int(h[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)]


def C3(h):
    return {"Color3": hex3(h)}


def V3(x, y, z):
    return {"Vector3": [round(x, 4), round(y, 4), round(z, 4)]}


def V2(x, y):
    return {"Vector2": [x, y]}


def U2(xs, xo, ys, yo):
    return {"UDim2": [[xs, int(round(xo))], [ys, int(round(yo))]]}


def UD(s, o):
    return {"UDim": [s, int(round(o))]}


FONTS = {
    "Fredoka": "rbxasset://fonts/families/FredokaOne.json",
    "Luckiest": "rbxasset://fonts/families/LuckiestGuy.json",
    "Gotham": "rbxasset://fonts/families/GothamSSm.json",
    "Builder": "rbxasset://fonts/families/BuilderSans.json",
}


def FONT(name="Fredoka", weight="Bold"):
    return {"Font": {"family": FONTS[name], "weight": weight, "style": "Normal"}}


def CS(*stops):
    """ColorSequence from (time, '#hex') pairs."""
    return {"ColorSequence": {"keypoints": [{"time": t, "color": hex3(c)} for t, c in stops]}}


def NS(*stops):
    return {"NumberSequence": {"keypoints": [{"time": t, "value": v, "envelope": 0}
                                             for t, v in stops]}}


def ATTRS(d):
    out = {}
    for k, v in d.items():
        if isinstance(v, bool):
            out[k] = {"Bool": v}
        elif isinstance(v, (int, float)):
            out[k] = {"Float64": float(v)}
        else:
            out[k] = {"String": str(v)}
    return {"Attributes": out}


# ---------------------------------------------------------------- instances
class Inst:
    def __init__(self, cls, name=None, props=None, attrs=None, children=None):
        self.cls = cls
        self.name = name or cls
        self.props = dict(props or {})
        self.attrs = dict(attrs or {})
        self.children = list(children or [])

    def add(self, *children):
        for c in children:
            if c is not None:
                self.children.append(c)
        return children[0] if len(children) == 1 else children

    def json(self):
        d = {"Name": self.name, "ClassName": self.cls}
        props = dict(self.props)
        if self.attrs:
            props["Attributes"] = ATTRS(self.attrs)
        if props:
            d["Properties"] = props
        if self.children:
            d["Children"] = [c.json() for c in self.children]
        return d

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def write_model(inst, relpath):
    path = os.path.join(SRC, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = inst.json()
    d.pop("Name", None)  # the file name decides the instance name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    n = sum(1 for _ in inst.walk())
    print(f"wrote {relpath}: {n} instances")
    return path


# ---------------------------------------------------------------- 3D helpers
MATERIALS = {"SmoothPlastic", "Plastic", "Neon", "Wood", "WoodPlanks", "Marble", "Slate",
             "Concrete", "Granite", "Brick", "Pebble", "Cobblestone", "Rock", "Sandstone",
             "CorrodedMetal", "DiamondPlate", "Foil", "Metal", "Grass", "LeafyGrass", "Sand",
             "Fabric", "Snow", "Mud", "Ground", "Asphalt", "Ice", "Glass", "ForceField",
             "Glacier", "Basalt", "CrackedLava", "Limestone", "Pavement", "Salt"}


def part(name, size, cf, color="#a3a2a5", material="SmoothPlastic", shape=None,
         transparency=0.0, collide=True, anchored=True, cls="Part", attrs=None, touch=True,
         cast_shadow=True, reflectance=0.0):
    assert material in MATERIALS, material
    if isinstance(cf, tuple):
        cf = CF(*cf)
    props = {
        "Anchored": anchored,
        "Size": V3(*size),
        "CFrame": cf.json(),
        "Color": C3(color),
        "Material": material,
        "TopSurface": "Smooth",
        "BottomSurface": "Smooth",
    }
    if shape and cls == "Part":
        props["Shape"] = shape
    if transparency:
        props["Transparency"] = transparency
    if not collide:
        props["CanCollide"] = False
    if not touch:
        props["CanTouch"] = False
        props["CanQuery"] = False
    if not cast_shadow:
        props["CastShadow"] = False
    if reflectance:
        props["Reflectance"] = reflectance
    return Inst(cls, name, props, attrs)


def vcyl(name, radius, height, pos, color, material="SmoothPlastic", **kw):
    """Vertical cylinder (Roblox cylinders run along X, so rotate 90deg about Z)."""
    x, y, z = pos
    return part(name, (height, radius * 2, radius * 2), CF(x, y, z) * CF.rz(math.pi / 2), color,
                material, shape="Cylinder", **kw)


def ball(name, d, pos, color, material="SmoothPlastic", **kw):
    return part(name, (d, d, d), CF(*pos), color, material, shape="Ball", **kw)


def wedge(name, size, cf, color, material="SmoothPlastic", **kw):
    return part(name, size, cf, color, material, cls="WedgePart", **kw)


def beam_between(name, a, b, width, thick, up, color, material="SmoothPlastic", extra=0.0, **kw):
    """Box spanning from point a to point b, with given up vector."""
    d = sub(b, a)
    L = length(d)
    f = norm(d)
    r = norm(cross(f, up))
    u = cross(r, f)
    mid = mul(add(a, b), 0.5)
    cf = CF.from_axes(mid, r, u, neg(f))
    return part(name, (width, thick, L + extra), cf, color, material, **kw)


def model(name, children=None, primary=None, attrs=None):
    m = Inst("Model", name, attrs=attrs, children=children)
    return m


def folder(name, children=None):
    return Inst("Folder", name, children=children)


def text_sign(name, text, size_px, cf, part_size, bg="#ffffff", fg="#ffffff", stroke="#1b1b1b",
              face="Front", font="Fredoka", transparent_part=False, material="SmoothPlastic"):
    """A part with a SurfaceGui text label on one face."""
    p = part(name, part_size, cf, bg, material, transparency=1 if transparent_part else 0,
             collide=not transparent_part)
    sg = Inst("SurfaceGui", "Sign", {"Face": face, "SizingMode": "PixelsPerStud",
                                     "PixelsPerStud": 40, "LightInfluence": 0})
    lbl = Inst("TextLabel", "Text", {
        "Size": U2(1, 0, 1, 0), "BackgroundTransparency": 1, "Text": text,
        "TextScaled": True, "FontFace": FONT(font), "TextColor3": C3(fg),
    })
    lbl.add(Inst("UIStroke", "Stroke", {"Color": C3(stroke), "Thickness": 6}))
    lbl.add(Inst("UIPadding", "Pad", {"PaddingTop": UD(0.08, 0), "PaddingBottom": UD(0.08, 0),
                                      "PaddingLeft": UD(0.04, 0), "PaddingRight": UD(0.04, 0)}))
    sg.add(lbl)
    p.add(sg)
    return p
