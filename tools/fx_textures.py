"""Small textures for particles and the animated sea -> assets/fx/*.png (run with Pillow + numpy)."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fx")


def water():
    """Tileable soft wave highlights (white on transparent) for the ocean surface."""
    n = 512
    y, x = np.mgrid[0:n, 0:n] / n * 2 * math.pi
    v = (np.sin(x * 3 + np.sin(y * 2) * 1.5) + np.sin(y * 4 + np.sin(x * 3) * 1.2)
         + 0.6 * np.sin((x + y) * 5 + np.sin(x * 2)))
    a = np.clip((v - 1.6) * 0.9, 0, 1) ** 1.5
    img = np.zeros((n, n, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (a * 200).astype(np.uint8)
    Image.fromarray(img).filter(ImageFilter.GaussianBlur(1.2)).save(os.path.join(OUT, "water.png"))


def leaf():
    im = Image.new("RGBA", (128, 128))
    d = ImageDraw.Draw(im)
    d.ellipse((24, 40, 104, 88), fill=(255, 255, 255, 255))
    d.polygon([(20, 64), (36, 52), (36, 76)], fill=(255, 255, 255, 255))
    d.line((30, 64, 100, 64), fill=(200, 200, 200, 255), width=3)
    im.rotate(35, resample=Image.BICUBIC).save(os.path.join(OUT, "leaf.png"))


def star():
    n = 256
    y, x = (np.mgrid[0:n, 0:n] - n / 2) / (n / 2)
    r = np.hypot(x, y) + 1e-6
    cross = np.exp(-np.abs(x) * 28) * np.exp(-np.abs(y) * 2.2) + np.exp(-np.abs(y) * 28) * np.exp(-np.abs(x) * 2.2)
    glow = np.exp(-r * 6)
    a = np.clip(cross + glow, 0, 1)
    img = np.zeros((n, n, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(img).save(os.path.join(OUT, "star.png"))


def streak():
    n = 256
    y, x = (np.mgrid[0:n, 0:n] - n / 2) / (n / 2)
    a = np.exp(-np.abs(y) * 14) * np.clip(1 - np.abs(x), 0, 1) ** 0.7
    img = np.zeros((n, n, 4), np.uint8)
    img[..., :3] = 255
    img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img).save(os.path.join(OUT, "streak.png"))


def butterfly():
    im = Image.new("RGBA", (128, 128))
    d = ImageDraw.Draw(im)
    for s in (-1, 1):
        d.ellipse((64 + s * 4 - (44 if s < 0 else 0), 22, 64 + s * 4 + (44 if s > 0 else 0), 66),
                  fill=(255, 255, 255, 255))
        d.ellipse((64 + s * 4 - (32 if s < 0 else 0), 60, 64 + s * 4 + (32 if s > 0 else 0), 100),
                  fill=(235, 235, 235, 255))
    d.rectangle((61, 30, 67, 98), fill=(60, 50, 60, 255))
    im.save(os.path.join(OUT, "butterfly.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for fn in (water, leaf, star, streak, butterfly):
        fn()
        print("wrote", fn.__name__)
