"""Synthesises every sound effect and the background music -> assets/audio/<name>.ogg

All sounds are made from scratch here (sine/square/saw/noise + envelopes), so there are no
licensing questions. Needs numpy and ffmpeg. Run: python3 sfx.py [name ...]
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio")
SR = 44100
rng = np.random.default_rng(7)


# ------------------------------------------------------------------ building blocks
def t_(dur):
    return np.arange(int(SR * dur)) / SR


def note(n):
    """MIDI note -> Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


def osc(freq, dur, kind="sine", phase=0.0):
    t = t_(dur)
    f = np.broadcast_to(np.asarray(freq, dtype=float), t.shape) if np.ndim(freq) else freq
    ph = 2 * np.pi * (np.cumsum(f) / SR if np.ndim(f) else f * t) + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "square":
        return np.sign(np.sin(ph)) * 0.6
    if kind == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1.0) - 1
    if kind == "tri":
        return 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1.0) - 1) - 1
    raise ValueError(kind)


def env(dur, a=0.005, d=0.1, s=0.0, r=0.05, hold=0.0):
    n = int(SR * dur)
    e = np.zeros(n)
    ia, ih, idd = int(SR * a), int(SR * hold), int(SR * d)
    k = 0
    e[k:k + ia] = np.linspace(0, 1, ia, endpoint=False)[: max(0, min(ia, n - k))]
    k += ia
    e[k:k + ih] = 1
    k += ih
    seg = np.linspace(1, s, idd, endpoint=False)
    e[k:k + idd] = seg[: max(0, min(idd, n - k))]
    k += idd
    e[k:] = s
    ir = int(SR * r)
    if ir and n > ir:
        e[-ir:] *= np.linspace(1, 0, ir)
    return e


def expdecay(dur, tau):
    return np.exp(-t_(dur) / tau)


def noise(dur):
    return rng.uniform(-1, 1, int(SR * dur))


def lowpass(x, cutoff):
    """One-pole style low-pass done in the frequency domain (fast with plain numpy)."""
    n = len(x)
    spec = np.fft.rfft(x, n * 2)
    f = np.fft.rfftfreq(n * 2, 1 / SR)
    spec /= np.sqrt(1 + (f / cutoff) ** 2)
    return np.fft.irfft(spec)[:n]


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def mix(*parts, length=None):
    n = length or max(len(p[1]) + int(p[0] * SR) for p in parts)
    out = np.zeros(n)
    for start, sig in parts:
        i = int(start * SR)
        j = min(n, i + len(sig))
        out[i:j] += sig[: j - i]
    return out


def reverb(x, wet=0.25, room=0.35):
    out = np.copy(x)
    for delay, g in ((0.0297, 0.7), (0.0371, 0.65), (0.0411, 0.6), (0.0437, 0.55)):
        d = int(delay * SR * (1 + room))
        buf = np.zeros(len(x) + d * 8)
        buf[: len(x)] += x
        for k in range(1, 8):
            buf[d * k: d * k + len(x)] += x * (g ** k)
        out = np.concatenate([out, np.zeros(len(buf) - len(out))]) if len(buf) > len(out) else out
        out[: len(buf)] += buf * wet * 0.25
    return out


def bell(freq, dur, bright=1.0):
    t = t_(dur)
    s = (np.sin(2 * np.pi * freq * t) + 0.5 * bright * np.sin(2 * np.pi * freq * 2.76 * t)
         * np.exp(-t / 0.08) + 0.25 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t / 0.04))
    return s * expdecay(dur, dur / 3.5) * env(dur, a=0.002, d=0.0, s=1, r=0.02)


def pluck(freq, dur, kind="tri"):
    return osc(freq, dur, kind) * expdecay(dur, dur / 4) * env(dur, a=0.003, d=0, s=1, r=0.02)


def sweep(f0, f1, dur, kind="sine"):
    f = np.geomspace(f0, f1, int(SR * dur))
    return osc(f, dur, kind)


def sparkle(dur, count=14, lo=2000, hi=6000, seed=1):
    r = np.random.default_rng(seed)
    parts = []
    for _ in range(count):
        st = r.uniform(0, dur * 0.8)
        parts.append((st, bell(r.uniform(lo, hi), 0.18, 0.4) * 0.25))
    return mix(*parts, length=int(SR * dur))


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


# ------------------------------------------------------------------ sounds
def s_hover():
    return norm(osc(1400, 0.05) * expdecay(0.05, 0.012), 0.5)


def s_click():
    a = osc(np.linspace(900, 1500, int(SR * 0.06)), 0.06, "tri") * expdecay(0.06, 0.018)
    c = highpass(noise(0.01), 3000) * 0.3
    return norm(mix((0, a), (0, c)), 0.8)


def s_tick():
    a = osc(2100, 0.03) * expdecay(0.03, 0.006)
    b = highpass(noise(0.02), 2500) * expdecay(0.02, 0.004) * 0.6
    return norm(mix((0, a), (0, b)), 0.7)


def s_whoosh():
    n = noise(0.32)
    e = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    x = lowpass(n * e, 1800)
    return norm(highpass(x, 200), 0.6)


def s_build_open():
    knock = lambda f: osc(f, 0.09) * expdecay(0.09, 0.02) + lowpass(noise(0.09), 900) * expdecay(0.09, 0.01) * 0.6  # noqa: E731
    up = sweep(500, 1300, 0.22, "tri") * env(0.22, a=0.02, d=0.2, s=0, r=0.0) * 0.5
    return norm(reverb(mix((0, knock(320)), (0.08, knock(420)), (0.14, up)), 0.2), 0.85)


def s_roll_start():
    notes = [72, 76, 79, 84]
    parts = [(i * 0.05, pluck(note(n), 0.25, "square") * 0.4) for i, n in enumerate(notes)]
    w = s_whoosh() * 0.6
    return norm(reverb(mix((0, w), *parts), 0.2), 0.85)


def reveal(notes, dur, step, sparkles, boom=False, pad=False, riser=0.0):
    parts = []
    if riser:
        r = sweep(200, 1800, riser, "saw") * np.linspace(0, 1, int(SR * riser)) ** 2 * 0.25
        parts.append((0, lowpass(r, 3000)))
        parts.append((0, lowpass(noise(riser), 5000) * np.linspace(0, 1, int(SR * riser)) ** 3 * 0.3))
    t0 = riser
    if boom:
        b = sweep(120, 40, 0.9) * expdecay(0.9, 0.25) * 1.2
        parts.append((t0, b))
        parts.append((t0, lowpass(noise(0.6), 1200) * expdecay(0.6, 0.15) * 0.6))
    for i, n in enumerate(notes):
        parts.append((t0 + i * step, bell(note(n), dur, 1.0) * 0.5))
        parts.append((t0 + i * step, pluck(note(n - 12), dur * 0.7, "square") * 0.18))
    if pad:
        chord = sum(osc(note(n), dur * 1.6, "saw") for n in (notes[0] - 12, notes[0] - 5, notes[0]))
        chord = lowpass(chord, 1500) * env(dur * 1.6, a=0.2, d=0.5, s=0.6, r=0.6) * 0.12
        parts.append((t0, chord))
    if sparkles:
        parts.append((t0 + step * len(notes) * 0.5, sparkle(dur * 1.4, sparkles) * 1.2))
    return norm(reverb(mix(*parts), 0.3), 0.9)


def s_common():
    return reveal([79, 84], 0.45, 0.07, 0)


def s_rare():
    return reveal([76, 79, 84], 0.6, 0.07, 6)


def s_epic():
    return reveal([72, 76, 79, 84, 88], 0.8, 0.07, 12)


def s_legendary():
    return reveal([72, 76, 79, 84, 88, 91], 1.1, 0.08, 20, boom=True, pad=True)


def s_mythical():
    return reveal([74, 78, 81, 86, 90, 93, 98], 1.3, 0.08, 28, boom=True, pad=True, riser=0.6)


def s_secret():
    return reveal([69, 73, 76, 81, 85, 88, 93, 97], 1.6, 0.09, 40, boom=True, pad=True, riser=1.2)


def s_purchase():
    a = bell(note(88), 0.5) * 0.6
    b = bell(note(93), 0.6) * 0.6
    jingle = sparkle(0.5, 10, 3000, 7000, 3)
    thunk = osc(180, 0.08) * expdecay(0.08, 0.02)
    return norm(reverb(mix((0, thunk), (0.03, a), (0.12, b), (0.1, jingle)), 0.2), 0.9)


def s_error():
    a = osc(190, 0.12, "square") * env(0.12, a=0.003, d=0.1, s=0.3, r=0.02)
    b = osc(150, 0.16, "square") * env(0.16, a=0.003, d=0.14, s=0.2, r=0.02)
    return norm(lowpass(mix((0, a), (0.13, b)), 2200), 0.7)


def s_place():
    thud = sweep(240, 90, 0.18) * expdecay(0.18, 0.05)
    clack = highpass(noise(0.03), 1500) * expdecay(0.03, 0.008) * 0.5
    pop = bell(note(84), 0.25) * 0.25
    return norm(reverb(mix((0, thud), (0, clack), (0.04, pop)), 0.15), 0.9)


def s_remove():
    a = sweep(700, 200, 0.2, "tri") * expdecay(0.2, 0.07)
    return norm(mix((0, a), (0, highpass(noise(0.05), 1200) * expdecay(0.05, 0.01) * 0.4)), 0.8)


def s_coin():
    return norm(mix((0, bell(1976, 0.18, 0.6)), (0.06, bell(2637, 0.25, 0.6))), 0.6)


def s_teleport():
    a = sweep(300, 2400, 0.5, "saw")
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 14 * t_(0.5))
    x = lowpass(a * lfo, 4000) * env(0.5, a=0.05, d=0.4, s=0, r=0.05)
    return norm(reverb(mix((0, x * 0.6), (0.3, sparkle(0.5, 8))), 0.3), 0.8)


def s_boost():
    w = s_whoosh()
    up = sweep(400, 1600, 0.35, "square") * env(0.35, a=0.01, d=0.33, s=0, r=0.02) * 0.25
    return norm(mix((0, w), (0.02, lowpass(up, 3000))), 0.8)


def s_unlock():
    notes = [72, 76, 79, 83, 86]
    parts = [(i * 0.06, bell(note(n), 0.7) * 0.5) for i, n in enumerate(notes)]
    parts.append((0.25, sparkle(0.8, 12)))
    return norm(reverb(mix(*parts), 0.35), 0.9)


def s_potion():
    parts = []
    r = np.random.default_rng(4)
    for i in range(9):
        f0 = r.uniform(300, 700)
        b = sweep(f0, f0 * 2.2, 0.06) * expdecay(0.06, 0.02)
        parts.append((i * 0.055 + r.uniform(0, 0.02), b * 0.6))
    parts.append((0.5, bell(note(86), 0.5) * 0.4))
    parts.append((0.55, sparkle(0.5, 8, seed=9)))
    return norm(reverb(mix(*parts), 0.25), 0.85)


def s_equip():
    c = highpass(noise(0.02), 2000) * expdecay(0.02, 0.005)
    chord = sum(bell(note(n), 0.4) for n in (79, 83, 86)) * 0.3
    return norm(mix((0, c), (0.02, chord)), 0.8)


def s_milestone():
    notes = [(0, 72), (0.12, 76), (0.24, 79), (0.4, 84)]
    parts = [(st, mix((0, pluck(note(n), 0.5, "square") * 0.35), (0, bell(note(n), 0.6) * 0.4)))
             for st, n in notes]
    parts.append((0.4, sum(osc(note(n), 0.8, "saw") for n in (60, 64, 67, 72)) * 0.05
                  * env(0.8, a=0.02, d=0.6, s=0.2, r=0.2)))
    parts.append((0.45, sparkle(0.8, 14)))
    return norm(reverb(mix(*parts), 0.3), 0.9)


def s_window_close():
    return norm(s_whoosh()[::-1][: int(SR * 0.22)], 0.5)


# ------------------------------------------------------------------ music
def drum_kick():
    return sweep(150, 45, 0.25) * expdecay(0.25, 0.07)


def drum_snare():
    return (highpass(noise(0.18), 1200) * expdecay(0.18, 0.05) * 0.6
            + osc(200, 0.18) * expdecay(0.18, 0.03) * 0.4)


def drum_hat():
    return highpass(noise(0.05), 6000) * expdecay(0.05, 0.012) * 0.35


def s_music():
    """Breezy 112 BPM loop: I - V - vi - IV in C, plucky lead, soft drums. ~34 s, loops."""
    bpm = 112
    beat = 60 / bpm
    bars = 16
    total = bars * 4 * beat
    prog = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]
    parts = []
    for bar in range(bars):
        root = prog[bar % 4]
        t0 = bar * 4 * beat
        # pad
        pad = sum(osc(note(n), 4 * beat, "saw") for n in root)
        pad = lowpass(pad, 900) * env(4 * beat, a=0.15, d=0.4, s=0.7, r=0.3) * 0.05
        parts.append((t0, pad))
        # bass
        for k, off in enumerate((0, 1.5, 2, 3)):
            n = root[0] - 24 + (7 if k == 2 else 0)
            parts.append((t0 + off * beat, pluck(note(n), beat * 0.9, "tri") * 0.32))
        # arpeggio
        for k in range(8):
            n = root[k % 3] + 12 + (12 if k in (3, 7) else 0)
            parts.append((t0 + k * beat / 2, pluck(note(n), beat * 0.45, "square") * 0.05))
        # drums (lighter in the first and the 9th bar for a breathing loop)
        if bar % 8 != 0:
            for k in range(4):
                parts.append((t0 + k * beat, drum_kick() * (0.3 if k % 2 == 0 else 0.0)))
                if k % 2 == 1:
                    parts.append((t0 + k * beat, drum_snare() * 0.35))
            for k in range(8):
                parts.append((t0 + k * beat / 2, drum_hat() * (0.6 if k % 2 else 0.3)))
    # lead melody (two 4-bar phrases repeated)
    phrase = [(0, 76, 1), (1, 79, 1), (2, 84, 1.5), (3.5, 83, 0.5), (4, 79, 2), (6, 74, 1),
              (7, 76, 1), (8, 76, 1), (9, 81, 1), (10, 79, 1.5), (11.5, 77, 0.5), (12, 76, 2),
              (14, 72, 2)]
    for rep in (4, 8, 12):
        for st, n, d in phrase:
            parts.append((rep * 4 * beat + st * beat,
                           mix((0, bell(note(n), d * beat * 1.2, 0.5) * 0.1),
                               (0, pluck(note(n), d * beat, "tri") * 0.07))))
    x = mix(*parts, length=int(total * SR))
    x = reverb(x, 0.25)[: int(total * SR)]
    # tiny crossfade so the loop point is seamless
    f = int(0.05 * SR)
    x[:f] *= np.linspace(0, 1, f)
    x[-f:] *= np.linspace(1, 0, f)
    return norm(x, 0.8)


SOUNDS = {name[2:]: fn for name, fn in globals().items() if name.startswith("s_")}


def write(name, x):
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, name + ".wav")
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    ogg = os.path.join(OUT, name + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis",
                    "-q:a", "5", ogg], check=True)
    os.remove(wav)
    print(f"{name}: {len(x) / SR:.2f}s")


if __name__ == "__main__":
    for name, fn in SOUNDS.items():
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        write(name, fn())
