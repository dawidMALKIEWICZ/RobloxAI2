"""Recoloured copies of the shared mesh palette for track mutations.

A mutated tile keeps its meshes and only swaps the palette texture (TextureID), so every
mutation is one 1024 px image: assets/mutations/<Mutation>.png. Run after every bake that adds
palette colours, then `python3 upload_assets.py media` and `python3 gamedata.py`.
"""
import colorsys
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "meshes", "palette.png")
PAL = os.path.join(ROOT, "assets", "meshes", "palette.json")
OUT = os.path.join(ROOT, "assets", "mutations")
GRID, CELL = 32, 32


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def ramp(stops, t):
    """Gradient map: stops = [(pos, '#hex'), ...] sorted by pos."""
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            k = (t - p0) / max(p1 - p0, 1e-6)
            a, b = hexrgb(c0), hexrgb(c1)
            return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    return hexrgb(stops[-1][1])


def lum(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# each mutation maps a swatch (rgb 0..1, its index) to a new colour
def golden(rgb, i):
    return ramp([(0, "#4a2a00"), (0.35, "#b8770a"), (0.65, "#ffc93a"), (0.9, "#fff1b0"), (1, "#ffffff")],
                lum(rgb) * 0.9 + 0.1)


def frozen(rgb, i):
    return ramp([(0, "#123a66"), (0.4, "#3b8fd1"), (0.75, "#9fe2ff"), (1, "#f4fdff")], lum(rgb) * 0.85 + 0.15)


def diamond(rgb, i):
    t = lum(rgb) * 0.7 + 0.3
    c = ramp([(0, "#2f7fa6"), (0.5, "#8fe9ff"), (0.8, "#dffaff"), (1, "#ffffff")], t)
    # faint prismatic tint so faces read as cut crystal
    h = (i * 0.137) % 1
    tint = colorsys.hsv_to_rgb(h, 0.18, 1)
    return tuple(c[k] * 0.85 + tint[k] * 0.15 for k in range(3))


def neon(rgb, i):
    t = lum(rgb)
    if t < 0.45:
        return ramp([(0, "#0b0618"), (1, "#2a1450")], t / 0.45)
    return ramp([(0, "#ff2bd6"), (0.5, "#b84dff"), (1, "#2bf6ff")], (t - 0.45) / 0.55)


def rainbow(rgb, i):
    h = (i * 0.0618 * 3) % 1
    s = 0.55 + 0.35 * (1 - lum(rgb))
    v = 0.6 + 0.4 * lum(rgb)
    return colorsys.hsv_to_rgb(h, s, v)


def void(rgb, i):
    return ramp([(0, "#030106"), (0.45, "#1e0a3a"), (0.8, "#5a1fa8"), (1, "#c58bff")], lum(rgb))


MUTATIONS = {"Golden": golden, "Frozen": frozen, "Diamond": diamond, "Neon": neon,
             "Rainbow": rainbow, "Void": void}


def main():
    os.makedirs(OUT, exist_ok=True)
    palette = json.load(open(PAL))
    for name, fn in MUTATIONS.items():
        img = Image.new("RGB", (GRID * CELL, GRID * CELL), (255, 0, 255))
        px = img.load()
        for i, h in enumerate(palette):
            col, row = i % GRID, i // GRID
            c = fn(hexrgb(h), i)
            rgb = tuple(max(0, min(255, round(v * 255))) for v in c)
            for y in range(row * CELL, (row + 1) * CELL):
                for x in range(col * CELL, (col + 1) * CELL):
                    px[x, y] = rgb
        path = os.path.join(OUT, name + ".png")
        img.save(path)
        print("wrote", path)
    # contact sheet for review
    sheet = Image.new("RGB", (len(MUTATIONS) * 256, 256))
    for k, name in enumerate(MUTATIONS):
        sheet.paste(Image.open(os.path.join(OUT, name + ".png")).resize((256, 256), Image.NEAREST), (k * 256, 0))
    sheet.save(os.path.join(ROOT, "renders", "mutation_palettes.png"))


if __name__ == "__main__":
    main()
