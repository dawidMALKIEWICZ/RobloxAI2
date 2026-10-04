"""Track tiles for the building grid -> src/ReplicatedStorage/Assets/Tiles.model.json

The visible tile is made of meshes baked by blender/models/tiles.py (one textured mesh plus a
few glowing ones). The centre lines come from trackpaths.py, so the car drives exactly on the
modelled road.
Children: MeshParts, an invisible "Hitbox", a "Path" folder of waypoints "1".."n" from A to B
(attributes Teleport, Boost) and attributes Ports ("SN" or "SE").
"""
from meshparts import mesh_parts
from rbx import CF, Inst, part, write_model
import trackpaths as T

CELL = T.CELL

# 9-tuples for gamedata.py: id, display, tier, odds, value, path fn, decor, ports, desc
TILES = [(i, d, t, o, v, fn, None, ports, desc) for i, d, t, o, v, fn, ports, desc in T.TILES]


def add_path(m, path):
    folder = Inst("Folder", "Path")
    for i, s in enumerate(path.s):
        p, r, u, f = T.frame(s)
        flags = s[4]
        attrs = {}
        if flags.get("Teleport"):
            attrs["Teleport"] = True
        if flags.get("Boost"):
            attrs["Boost"] = flags["Boost"]
        cf = CF.from_axes(p, r, u, (-f[0], -f[1], -f[2]))
        folder.add(part(str(i + 1), (0.4, 0.4, 0.4), cf, "#ffffff", transparency=1,
                        collide=False, touch=False, attrs=attrs or None))
    m.add(folder)


def build_tile(tid, display, tier, odds, value, fn, ports, desc):
    path = T.make_path(fn)
    m = Inst("Model", tid, attrs={"Tier": tier, "Odds": odds, "Value": value, "Ports": ports,
                                  "DisplayName": display, "Description": desc})
    m.add(part("Hitbox", (CELL - 0.2, 0.6, CELL - 0.2), CF(0, 0.3, 0), "#ffffff",
               transparency=1, cast_shadow=False))
    for mp in mesh_parts("Tile_" + tid):
        m.add(mp)
    add_path(m, path)
    return m


def build():
    root = Inst("Folder", "Tiles")
    for t in T.TILES + [T.START]:
        root.add(build_tile(*t))
    return root


if __name__ == "__main__":
    write_model(build(), "ReplicatedStorage/Assets/Tiles.model.json")
