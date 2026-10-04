"""Shared helpers for building Track RNG assets in Blender (bpy).

Units: 1 Blender unit = 1 Roblox stud. Z is up in Blender; FBX export
converts to Roblox's Y-up.
"""
import math
import os

import bpy
import bmesh
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
RENDERS = os.path.join(ROOT, "renders")

_mats = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()


def hexcol(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, 1.0)


def mat(name, color, rough=0.55, metal=0.0, emit=0.0, alpha=1.0):
    """Flat-colour Principled material (Roblox 'SmoothPlastic' look)."""
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    c = hexcol(color) if isinstance(color, str) else color
    b.inputs["Base Color"].default_value = c
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = c
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED"
    m.diffuse_color = c
    _mats[name] = m
    return m


def _finish(obj, material, bevel, parent):
    if material is not None:
        obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
    if parent is not None:
        obj.parent = parent
    for p in obj.data.polygons:
        p.use_smooth = False
    return obj


def box(name, size, loc=(0, 0, 0), material=None, rot=(0, 0, 0), bevel=0.0, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, material, bevel, parent)


def cyl(name, r, h, loc=(0, 0, 0), material=None, verts=24, rot=(0, 0, 0), r2=None,
        bevel=0.0, parent=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc,
                                            rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r2, depth=h,
                                        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    return _finish(o, material, bevel, parent)


def sphere(name, r, loc=(0, 0, 0), material=None, subdiv=2, scale=(1, 1, 1), parent=None):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish(o, material, 0, parent)


def torus(name, R, r, loc=(0, 0, 0), material=None, rot=(0, 0, 0), major=32, minor=12,
          parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc,
                                     rotation=rot, major_segments=major,
                                     minor_segments=minor)
    o = bpy.context.active_object
    o.name = name
    return _finish(o, material, 0, parent)


def text(name, s, size, loc, material, rot=(math.pi / 2, 0, 0), extrude=0.15,
         align="CENTER", parent=None):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.body = s
    o.data.size = size
    o.data.extrude = extrude
    o.data.align_x = align
    o.data.align_y = "CENTER"
    try:
        o.data.font = bpy.data.fonts.load("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    except Exception:
        pass
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.clear()
    return _finish(o, material, 0, parent)


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o


def mesh_from(name, verts, faces, material=None, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return _finish(o, material, 0, parent)


def sweep(name, path, profile, material=None, parent=None, closed_profile=True):
    """Sweep a 2D profile [(x, z)] along path [(pos, tangent, up)] -> mesh."""
    verts, faces = [], []
    n = len(profile)
    for pos, tan, up in path:
        tan = Vector(tan).normalized()
        up = Vector(up).normalized()
        side = tan.cross(up).normalized()
        up = side.cross(tan).normalized()
        for x, z in profile:
            verts.append(Vector(pos) + side * x + up * z)
    m = n if closed_profile else n - 1
    for i in range(len(path) - 1):
        for j in range(m):
            a = i * n + j
            b = i * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    if closed_profile:
        faces.append(tuple(reversed(range(n))))
        last = (len(path) - 1) * n
        faces.append(tuple(range(last, last + n)))
    o = mesh_from(name, [tuple(v) for v in verts], faces, material, parent)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    return o


def join(objs, name):
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_scene(sky="#8fd3ff", sun_energy=4.0, samples=48, res=(1280, 720), water=False,
                water_size=4000, water_z=-40):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = hexcol(sky)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = sun_energy
    sun_d.angle = math.radians(8)
    sun = bpy.data.objects.new("Sun", sun_d)
    sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(15), math.radians(35))
    if water:
        box("Ocean", (water_size, water_size, 1), (0, 0, water_z),
            mat("Water", "#3fb7f0", rough=0.15))


def camera(loc, target, lens=35, ortho=None):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.clip_end = 20000
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    c = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = loc
    look_at(c, target)
    bpy.context.scene.camera = c
    return c


def render(fname):
    os.makedirs(RENDERS, exist_ok=True)
    path = os.path.join(RENDERS, fname)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path)
    return path


def export_fbx(objs, fname):
    os.makedirs(os.path.dirname(os.path.join(ASSETS, fname)), exist_ok=True)
    path = os.path.join(ASSETS, fname)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        for c in o.children_recursive:
            c.select_set(True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True,
                             apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z",
                             axis_up="Y", use_mesh_modifiers=True, mesh_smooth_type="FACE",
                             object_types={"MESH", "EMPTY"})
    print("EXPORTED", path)
    return path


def save_blend(fname):
    path = os.path.join(ASSETS, fname)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    return path
