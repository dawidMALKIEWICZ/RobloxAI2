"""Minimal reader for Roblox binary place/model files (.rbxl/.rbxm).

Decodes instances, names, scripts and the most common property types so a place can be
inspected without Studio. Usage: python rbxl_reader.py <file.rbxl> <out_dir>
"""
import json
import os
import struct
import sys


def lz4_block(src, size):
    dst = bytearray()
    i = 0
    n = len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        dst += src[i:i + lit]
        i += lit
        if i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        ml = token & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(dst) - off
        for k in range(ml):
            dst.append(dst[start + k])
    return bytes(dst[:size])


def decompress(comp, size, data):
    if comp == 0:
        return data
    if data[:4] == b"\x28\xb5\x2f\xfd":
        import zstandard
        return zstandard.ZstdDecompressor().decompress(data, max_output_size=size)
    return lz4_block(data, size)


class R:
    def __init__(self, b):
        self.b = b
        self.i = 0

    def u8(self):
        v = self.b[self.i]
        self.i += 1
        return v

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.i)[0]
        self.i += 4
        return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.i)[0]
        self.i += 4
        return v

    def f32(self):
        v = struct.unpack_from("<f", self.b, self.i)[0]
        self.i += 4
        return v

    def f64(self):
        v = struct.unpack_from("<d", self.b, self.i)[0]
        self.i += 8
        return v

    def string(self):
        n = self.u32()
        s = self.b[self.i:self.i + n]
        self.i += n
        return s

    def raw(self, n):
        s = self.b[self.i:self.i + n]
        self.i += n
        return s

    def interleaved(self, count, width):
        data = self.raw(count * width)
        out = []
        for k in range(count):
            out.append(bytes(data[j * count + k] for j in range(width)))
        return out

    def ints(self, count):
        out = []
        for bs in self.interleaved(count, 4):
            v = struct.unpack(">I", bs)[0]
            out.append((v >> 1) ^ -(v & 1))
        return out

    def uints(self, count):
        return [struct.unpack(">I", bs)[0] for bs in self.interleaved(count, 4)]

    def floats(self, count):
        out = []
        for bs in self.interleaved(count, 4):
            v = struct.unpack(">I", bs)[0]
            v = ((v >> 1) | ((v & 1) << 31)) & 0xFFFFFFFF
            out.append(struct.unpack(">f", struct.pack(">I", v))[0])
        return out

    def refs(self, count):
        vals = self.ints(count)
        acc = 0
        out = []
        for v in vals:
            acc += v
            out.append(acc)
        return out

    def int64s(self, count):
        out = []
        for bs in self.interleaved(count, 8):
            v = struct.unpack(">Q", bs)[0]
            out.append((v >> 1) ^ -(v & 1))
        return out


def _rot_table():
    """Rotation ids of the binary format: 6 * xAxisIndex + yAxisIndex + 2."""
    axes = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1)]
    tbl = {}
    for xi, x in enumerate(axes):
        for yi, y in enumerate(axes):
            if sum(abs(p * q) for p, q in zip(x, y)) != 0:
                continue
            z = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0])
            tbl[6 * xi + yi + 2] = (x, y, z)
    return tbl


def read_prop(r, typ, count):
    if typ == 0x01:
        return [r.string() for _ in range(count)]
    if typ == 0x02:
        return [bool(r.u8()) for _ in range(count)]
    if typ == 0x03:
        return r.ints(count)
    if typ == 0x04:
        return r.floats(count)
    if typ == 0x05:
        return [r.f64() for _ in range(count)]
    if typ == 0x06:
        s = r.floats(count)
        o = r.ints(count)
        return list(zip(s, o))
    if typ == 0x07:
        xs, ys = r.floats(count), r.floats(count)
        xo, yo = r.ints(count), r.ints(count)
        return [((xs[k], xo[k]), (ys[k], yo[k])) for k in range(count)]
    if typ == 0x0C:
        r_, g, b = r.floats(count), r.floats(count), r.floats(count)
        return list(zip(r_, g, b))
    if typ == 0x0D:
        x, y = r.floats(count), r.floats(count)
        return list(zip(x, y))
    if typ == 0x0E:
        x, y, z = r.floats(count), r.floats(count), r.floats(count)
        return list(zip(x, y, z))
    if typ == 0x10:
        rots = []
        tbl = _rot_table()
        for _ in range(count):
            rid = r.u8()
            if rid == 0:
                rots.append([r.f32() for _ in range(9)])
            else:
                x, y, z = tbl.get(rid, ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
                rots.append([x[0], y[0], z[0], x[1], y[1], z[1], x[2], y[2], z[2]])
        px, py, pz = r.floats(count), r.floats(count), r.floats(count)
        return [{"pos": (px[k], py[k], pz[k]), "rot": rots[k]} for k in range(count)]
    if typ == 0x12:
        return r.uints(count)
    if typ == 0x13:
        return r.refs(count)
    if typ == 0x1A:
        rs = r.raw(count)
        gs = r.raw(count)
        bs = r.raw(count)
        return list(zip(rs, gs, bs))
    if typ == 0x1B:
        return r.int64s(count)
    if typ == 0x1C:
        return r.uints(count)
    return None


def load(path):
    b = open(path, "rb").read()
    assert b[:8] == b"<roblox!", "not a binary roblox file"
    r = R(b)
    r.i = 14
    _ver = struct.unpack_from("<H", b, r.i)[0]
    r.i = 16
    _ntypes = r.u32()
    _ninst = r.u32()
    r.i += 8
    classes = {}
    inst = {}
    shared = []
    while r.i < len(b):
        name = r.raw(4)
        comp = r.u32()
        size = r.u32()
        r.raw(4)
        data = decompress(comp, size, r.raw(comp if comp else size))
        c = R(data)
        if name == b"INST":
            cid = c.u32()
            cname = c.string().decode()
            _service = c.u8()
            n = c.u32()
            ids = c.refs(n)
            classes[cid] = (cname, ids)
            for rid in ids:
                inst[rid] = {"class": cname, "props": {}, "children": [], "parent": None}
        elif name == b"SSTR":
            c.u32()
            n = c.u32()
            for _ in range(n):
                c.raw(16)
                shared.append(c.string())
        elif name == b"PROP":
            cid = c.u32()
            pname = c.string().decode()
            typ = c.u8()
            cname, ids = classes[cid]
            try:
                vals = read_prop(c, typ, len(ids))
            except Exception:
                vals = None
            if vals is not None:
                for rid, v in zip(ids, vals):
                    if typ == 0x1C and shared:
                        v = shared[v] if v < len(shared) else v
                    inst[rid]["props"][pname] = v
        elif name == b"PRNT":
            c.u8()
            n = c.u32()
            kids = c.refs(n)
            parents = c.refs(n)
            for k, p in zip(kids, parents):
                inst[k]["parent"] = p
                if p in inst:
                    inst[p]["children"].append(k)
        elif name == b"END\x00":
            break
    roots = [k for k, v in inst.items() if v["parent"] is None or v["parent"] not in inst]
    return inst, roots


def name_of(node):
    n = node["props"].get("Name", b"?")
    return n.decode(errors="replace") if isinstance(n, bytes) else str(n)


def dump(path, out):
    inst, roots = load(path)
    os.makedirs(out, exist_ok=True)
    lines = []

    def walk(rid, depth, p):
        node = inst[rid]
        nm = name_of(node)
        cls = node["class"]
        is_script = cls in ("Script", "LocalScript", "ModuleScript")
        if depth <= 5 or is_script:
            lines.append("  " * depth + f"{cls} {nm} ({len(node['children'])})")
        if is_script:
            src = node["props"].get("Source", b"")
            fn = (p + "." + nm).strip(".").replace("/", "_").replace(" ", "_")
            with open(os.path.join(out, fn + "." + cls + ".luau"), "wb") as f:
                f.write(src if isinstance(src, bytes) else str(src).encode())
        for k in node["children"]:
            walk(k, depth + 1, p + "." + nm)

    for r in roots:
        walk(r, 0, "")
    with open(os.path.join(out, "tree.txt"), "w") as f:
        f.write("\n".join(lines))
    print("instances", len(inst), "lines", len(lines))
    return inst, roots


if __name__ == "__main__":
    dump(sys.argv[1], sys.argv[2])
