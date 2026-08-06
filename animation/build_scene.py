"""Build and render the Wallet V2 product-animation scene in Blender.

Run with:
  blender --background --factory-startup --python animation/build_scene.py -- --preview
  blender --background --factory-startup --python animation/build_scene.py -- --video
"""

import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(os.getcwd())
ASSETS = ROOT / "animation" / "assets"
OUTPUT = ROOT / "animation" / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)

SCALE = 0.01
CENTER_MM = Vector((30.75, 6.75, 51.68515))
FPS = 30
FRAME_END = 420
LINKAGE_MAX_ANGLE = 83.28244

# Card rise in millimetres, solved from the exact slider mesh at four-degree
# intervals. Each row corresponds to the five one-millimetre card lanes.
LINKAGE_SAMPLES = (
    (0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0, 0.0, 0.2345),
    (0.0, 0.0, 0.0, 0.0113, 0.8483),
    (0.0, 0.0, 0.0, 0.4394, 1.7747),
    (0.0, 0.0, 0.0, 1.2029, 3.0554),
    (0.0, 0.0, 0.3452, 2.2538, 4.6329),
    (0.0, 0.0, 1.0868, 3.5973, 6.5302),
    (0.0, 0.0, 2.0866, 5.2506, 8.7330),
    (0.0, 0.2178, 3.3749, 7.1696, 11.2050),
    (0.0, 0.9928, 4.9171, 9.3714, 13.9030),
    (0.0, 2.0151, 6.7008, 11.5981, 16.4954),
    (0.0, 3.2520, 8.4911, 13.7303, 18.9695),
    (0.0, 4.6467, 10.2021, 15.7576, 21.3131),
    (0.2146, 5.9807, 11.8255, 17.6702, 23.5149),
    (1.1422, 7.2477, 13.3531, 19.4586, 25.5641),
    (2.1048, 8.4413, 14.7778, 21.1143, 27.4508),
    (3.0191, 9.5558, 16.0924, 22.6291, 29.1657),
    (3.8808, 10.5857, 17.2907, 23.9956, 30.7006),
    (4.6855, 11.5261, 18.3667, 25.2073, 32.0478),
    (5.4294, 12.3723, 19.3152, 26.2581, 33.2010),
    (6.1088, 13.1202, 20.1316, 27.1430, 34.1544),
    (6.7205, 13.7662, 20.8119, 27.8576, 34.9034),
    (7.2615, 14.3072, 21.3529, 28.3986, 35.4443),
    (7.7290, 14.7404, 21.7518, 28.7632, 35.7746),
)


def srgb_channel(value):
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def color(hex_value, alpha=1.0):
    value = hex_value.lstrip("#")
    return tuple(srgb_channel(int(value[index : index + 2], 16)) for index in (0, 2, 4)) + (alpha,)


def socket(node, name):
    return node.inputs.get(name)


def set_principled(node, **values):
    for name, value in values.items():
        target = socket(node, name)
        if target is not None:
            target.default_value = value


def material_principled(name, base, metallic=0.0, roughness=0.35, coat=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    set_principled(
        principled,
        **{
            "Base Color": color(base),
            "Metallic": metallic,
            "Roughness": roughness,
            "Coat Weight": coat,
            "Coat Roughness": 0.18,
        },
    )
    return material


def material_printed_plastic(name, base, accent=False):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    set_principled(
        principled,
        **{
            "Base Color": color(base),
            "Metallic": 0.38 if accent else 0.04,
            "Roughness": 0.23 if accent else 0.31,
            "Coat Weight": 0.38 if accent else 0.22,
            "Coat Roughness": 0.16,
        },
    )

    texture = nodes.new("ShaderNodeTexCoord")
    wave = nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "Z"
    wave.inputs["Scale"].default_value = 245.0
    wave.inputs["Distortion"].default_value = 2.4
    wave.inputs["Detail"].default_value = 2.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.075 if accent else 0.105
    bump.inputs["Distance"].default_value = 0.0018
    links.new(texture.outputs["Generated"], wave.inputs["Vector"])
    links.new(wave.outputs["Color"], bump.inputs["Height"])
    if socket(principled, "Normal") is not None:
        links.new(bump.outputs["Normal"], principled.inputs["Normal"])

    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 42.0
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    low = 0.18 if accent else 0.26
    high = 0.29 if accent else 0.39
    ramp.color_ramp.elements[0].color = (low, low, low, 1.0)
    ramp.color_ramp.elements[1].color = (high, high, high, 1.0)
    links.new(texture.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], principled.inputs["Roughness"])
    return material


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def import_stl(filename, name, material, bevel=0.0012):
    bpy.ops.wm.stl_import(filepath=str(ASSETS / filename))
    obj = bpy.context.object
    obj.name = name
    for vertex in obj.data.vertices:
        vertex.co = (vertex.co - CENTER_MM) * SCALE
    obj.data.update()
    obj.data.materials.append(material)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    try:
        bpy.ops.object.shade_smooth_by_angle()
    except Exception:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True

    modifier = obj.modifiers.new("Micro edge highlights", "BEVEL")
    modifier.width = bevel
    modifier.segments = 2
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = math.radians(27.0)
    obj.select_set(False)
    return obj


def set_origin(obj, world_pivot):
    pivot = Vector(world_pivot)
    for vertex in obj.data.vertices:
        vertex.co -= pivot
    obj.location = pivot


def add_beveled_cube(name, location, dimensions, material, bevel=0.01):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    modifier = obj.modifiers.new("Soft edges", "BEVEL")
    modifier.width = bevel
    modifier.segments = 4
    return obj


def add_coin(name, radius, material, inset_material, vertices=96, thickness=0.022):
    rig = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(rig)
    rig.empty_display_type = "CIRCLE"
    rig.empty_display_size = radius

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=thickness,
        location=(0.0, 0.0, 0.0),
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    body = bpy.context.object
    body.name = f"{name} body"
    body.data.materials.append(material)
    body.parent = rig
    rim = body.modifiers.new("Rounded milled rim", "BEVEL")
    rim.width = 0.0030
    rim.segments = 3

    # The stamped relief finishes flush with the face. The compartment leaves
    # only 0.2 mm behind the topmost coin, so it must not stand proud.
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius * 0.76,
        depth=0.0012,
        location=(0.0, thickness * 0.5 - 0.0002, 0.0),
        rotation=(math.radians(90.0), 0.0, 0.0),
    )
    inset = bpy.context.object
    inset.name = f"{name} inset"
    inset.data.materials.append(inset_material)
    inset.parent = rig
    inset_bevel = inset.modifiers.new("Coin face relief", "BEVEL")
    inset_bevel.width = 0.0008
    inset_bevel.segments = 2
    return rig


def key_visibility_tree(root, frame, visible):
    for obj in (root, *root.children_recursive):
        obj.hide_render = not visible
        obj.keyframe_insert(data_path="hide_render", frame=frame)


def add_area_light(name, location, energy, size, tint, target=(0.0, 0.0, 0.05)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color(tint)[:3]
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return obj


def key_location(obj, frame, value):
    obj.location = value
    obj.keyframe_insert(data_path="location", frame=frame)


def key_rotation(obj, frame, value):
    obj.rotation_euler = value
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def key_scale(obj, frame, value):
    obj.scale = value
    obj.keyframe_insert(data_path="scale", frame=frame)


def smooth_animation(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    # Blender 5.x uses layered/slotted actions and already creates Bezier keys
    # with automatic handles. Older versions expose fcurves directly.
    if not hasattr(action, "fcurves"):
        return
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def linkage_rises(angle_degrees):
    position = max(0.0, min(LINKAGE_MAX_ANGLE, angle_degrees)) / 4.0
    lower = int(math.floor(position))
    upper = min(lower + 1, len(LINKAGE_SAMPLES) - 1)
    mix = position - lower
    return tuple(
        (LINKAGE_SAMPLES[lower][index] * (1.0 - mix) + LINKAGE_SAMPLES[upper][index] * mix) * SCALE
        for index in range(5)
    )


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    if hasattr(scene.render, "use_motion_blur"):
        scene.render.use_motion_blur = True
    if hasattr(scene.render, "motion_blur_shutter"):
        scene.render.motion_blur_shutter = 0.38
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 48
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.35

    world = bpy.data.worlds.new("Midnight studio")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = color("07101B")
    background.inputs["Strength"].default_value = 0.18
    scene.world = world
    return scene


clean_scene()
scene = setup_render()

mat_shell = material_printed_plastic("Carbon black printed polymer", "080A0C")
mat_shell_edge = material_printed_plastic("Soft black rear shell", "0D1013")
mat_accent = material_printed_plastic("Graphite mechanism", "353A40", accent=True)
mat_accent_dark = material_principled("Dark titanium cam", "20252A", metallic=0.74, roughness=0.24, coat=0.34)
mat_gold = material_principled("Warm gold contacts", "D5A642", metallic=0.92, roughness=0.20, coat=0.28)
mat_coin_gold = material_principled("Australian coin gold", "C69A3D", metallic=0.94, roughness=0.22, coat=0.24)
mat_coin_silver = material_principled("Australian coin silver", "ADB6BC", metallic=0.96, roughness=0.19, coat=0.22)
mat_coin_copper = material_principled("Warm coin relief", "7D512D", metallic=0.88, roughness=0.25, coat=0.18)
mat_note_gold = material_principled("Ochre banknote paper", "D7A93C", metallic=0.02, roughness=0.48, coat=0.05)
mat_note_plum = material_principled("Plum banknote paper", "70526F", metallic=0.01, roughness=0.50, coat=0.04)
mat_note_blue = material_principled("Blue banknote paper", "506E8A", metallic=0.01, roughness=0.50, coat=0.04)
mat_note_red = material_principled("Red banknote paper", "914F54", metallic=0.01, roughness=0.50, coat=0.04)
mat_note_green = material_principled("Green banknote paper", "557566", metallic=0.01, roughness=0.50, coat=0.04)
mat_note_ink = material_principled("Banknote green ink", "244F43", metallic=0.02, roughness=0.43, coat=0.06)
mat_note_window = material_principled("Banknote security window", "B6C8C4", metallic=0.42, roughness=0.17, coat=0.48)
mat_floor = material_principled("Studio floor", "071019", metallic=0.18, roughness=0.26, coat=0.32)
mat_plinth = material_principled("Black glass plinth", "101B25", metallic=0.42, roughness=0.19, coat=0.55)

main_body = import_stl("main_body.stl", "Wallet shell", mat_shell, bevel=0.0010)
slider = import_stl("slider.stl", "Internal slider", mat_accent, bevel=0.0010)
drive_cam = import_stl("drive_cam.stl", "Drive cam", mat_accent_dark, bevel=0.0012)
arm = import_stl("arm.stl", "Swing arm", mat_accent, bevel=0.0014)
door = import_stl("door.stl", "Rear door", mat_shell_edge, bevel=0.0012)
card_source = import_stl("credit_card.stl", "Card template", mat_gold, bevel=0.0006)

# True mechanical pivots inferred from the designed hinge and drive-cam geometry.
arm_pivot = (Vector((50.0, 0.0, 9.7)) - CENTER_MM) * SCALE
door_pivot = (Vector((1.75, 12.5, 51.5)) - CENTER_MM) * SCALE
set_origin(arm, arm_pivot)
set_origin(drive_cam, arm_pivot)
set_origin(slider, arm_pivot)
set_origin(door, door_pivot)

cards = []
card_palette = ["303338", "77746E", "223047", "293831", "4A292D"]
card_names = ["Charcoal", "Warm Grey", "Navy", "Forest", "Oxblood"]
for index, (hex_value, card_name) in enumerate(zip(card_palette, card_names)):
    if index == 0:
        card = card_source
        card.name = f"Card {index + 1} - {card_name}"
        card.data.materials.clear()
    else:
        card = card_source.copy()
        card.data = card_source.data.copy()
        bpy.context.collection.objects.link(card)
        card.name = f"Card {index + 1} - {card_name}"
        card.data.materials.clear()
    card_mat = material_principled(
        f"{card_name} card",
        hex_value,
        metallic=0.08,
        roughness=0.23,
        coat=0.42,
    )
    card.data.materials.append(card_mat)
    card.location.y = -0.018 + index * 0.009
    cards.append(card)

# A physical gold contact chip makes the front card read instantly as a card.
chip = add_beveled_cube(
    "Gold contact chip",
    location=(-0.115, -0.0347, 0.145),
    dimensions=(0.115, 0.0024, 0.083),
    material=mat_gold,
    bevel=0.009,
)
chip.parent = cards[0]
chip.matrix_parent_inverse = cards[0].matrix_world.inverted()

# Fine chip contact grooves.
groove_mat = material_principled("Chip grooves", "5C421C", metallic=0.78, roughness=0.28)
for offset in (-0.028, 0.0, 0.028):
    groove = add_beveled_cube(
        f"Chip groove {offset:+.3f}",
        location=(-0.115 + offset, -0.0361, 0.145),
        dimensions=(0.0022, 0.0008, 0.068),
        material=groove_mat,
        bevel=0.0006,
    )
    groove.parent = cards[0]
    groove.matrix_parent_inverse = cards[0].matrix_world.inverted()

# Five folded notes form a believable 48 x 24 mm cash bundle. The coin
# diameters match Australian currency at the scene's 1 unit = 100 mm scale.
cash_rig = bpy.data.objects.new("Folded banknote stack", None)
bpy.context.collection.objects.link(cash_rig)
cash_rig.empty_display_type = "CUBE"
cash_rig.empty_display_size = 0.12

note_layers = (
    ("Green folded banknote", (-0.010, -0.0120, 0.018), (0.455, 0.0030, 0.225), mat_note_green, -4.0),
    ("Red folded banknote", (0.012, -0.0090, 0.012), (0.462, 0.0030, 0.228), mat_note_red, 3.2),
    ("Blue folded banknote", (-0.008, -0.0060, 0.008), (0.468, 0.0030, 0.232), mat_note_blue, -2.0),
    ("Plum folded banknote", (0.006, -0.0030, 0.004), (0.474, 0.0030, 0.236), mat_note_plum, 1.2),
)
for note_name, note_location, note_dimensions, note_material, note_angle in note_layers:
    note = add_beveled_cube(
        note_name,
        location=note_location,
        dimensions=note_dimensions,
        material=note_material,
        bevel=0.011,
    )
    note.rotation_euler.z = math.radians(note_angle)
    note.parent = cash_rig

note_front = add_beveled_cube(
    "Ochre folded banknote",
    location=(0.0, 0.0, 0.0),
    dimensions=(0.480, 0.0034, 0.240),
    material=mat_note_gold,
    bevel=0.012,
)
note_front.parent = cash_rig

note_panel = add_beveled_cube(
    "Banknote printed panel",
    location=(0.078, 0.00215, 0.0),
    dimensions=(0.198, 0.0010, 0.168),
    material=mat_note_ink,
    bevel=0.012,
)
note_panel.parent = cash_rig

note_window = add_beveled_cube(
    "Banknote security strip",
    location=(-0.095, 0.00225, 0.0),
    dimensions=(0.020, 0.0011, 0.194),
    material=mat_note_window,
    bevel=0.003,
)
note_window.parent = cash_rig

bpy.ops.mesh.primitive_cylinder_add(
    vertices=64,
    radius=0.050,
    depth=0.0012,
    location=(0.110, 0.0028, 0.0),
    rotation=(math.radians(90.0), 0.0, 0.0),
)
note_medallion = bpy.context.object
note_medallion.name = "Banknote portrait medallion"
note_medallion.data.materials.append(mat_note_gold)
note_medallion.parent = cash_rig

coins = [
    add_coin("Gold dollar coin", 0.1250, mat_coin_gold, mat_coin_copper, vertices=96, thickness=0.025),
    add_coin("Silver fifty-cent coin", 0.15825, mat_coin_silver, mat_coin_gold, vertices=12, thickness=0.020),
    add_coin("Silver twenty-cent coin", 0.14260, mat_coin_silver, mat_coin_copper, vertices=96, thickness=0.025),
    add_coin("Gold two-dollar coin", 0.10250, mat_coin_gold, mat_coin_copper, vertices=96, thickness=0.029),
    add_coin("Silver ten-cent coin", 0.1180, mat_coin_silver, mat_coin_gold, vertices=96, thickness=0.020),
]

# Hero platform and an infinite-feeling studio floor.
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=0.92, depth=0.055, location=(0.0, 0.0, -0.554))
plinth = bpy.context.object
plinth.name = "Floating presentation plinth"
plinth.data.materials.append(mat_plinth)
plinth_bevel = plinth.modifiers.new("Rounded plinth rim", "BEVEL")
plinth_bevel.width = 0.025
plinth_bevel.segments = 5

bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, -0.585))
floor = bpy.context.object
floor.name = "Studio floor"
floor.data.materials.append(mat_floor)

# Controlled four-point studio lighting: neutral key, cool rim, and warm counter-rim.
add_area_light("Large soft key", (-2.35, -2.7, 3.1), 980.0, 2.4, "F2F4F5", target=(0.0, 0.0, 0.18))
add_area_light("Front fill", (2.7, -1.9, 1.25), 580.0, 2.1, "DDE7EF", target=(0.0, 0.0, 0.05))
add_area_light("Cool steel edge", (1.5, 2.4, 2.25), 900.0, 1.35, "BFD7E5", target=(0.0, 0.0, 0.20))
add_area_light("Warm neutral edge", (-2.2, 1.45, 1.2), 650.0, 1.45, "E6C7A8", target=(0.0, 0.0, 0.08))
add_area_light("Top strip", (0.0, 0.0, 4.2), 720.0, 1.6, "EEF7FF", target=(0.0, 0.0, 0.0))

# Camera tracks an animated focus target so framing rises with the card cascade.
target = bpy.data.objects.new("Camera focus", None)
bpy.context.collection.objects.link(target)
target.empty_display_type = "SPHERE"
target.empty_display_size = 0.05

camera_data = bpy.data.cameras.new("Product camera")
camera = bpy.data.objects.new("Product camera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera_data.lens = 58.0
camera_data.sensor_width = 36.0
camera_data.dof.use_dof = True
camera_data.dof.focus_object = target
camera_data.dof.aperture_fstop = 3.8
camera_data.dof.aperture_blades = 7
camera.data.display_size = 0.2
track = camera.constraints.new(type="TRACK_TO")
track.target = target
track.track_axis = "TRACK_NEGATIVE_Z"
track.up_axis = "UP_Y"

camera_keys = {
    1: (1.55, -2.75, 0.88),
    45: (1.08, -2.38, 0.68),
    115: (0.72, -2.74, 1.03),
    165: (-0.78, -2.72, 0.98),
    205: (-2.08, -0.82, 0.94),
    228: (-2.24, 1.42, 0.88),
    252: (0.82, 2.86, 0.82),
    275: (1.34, 2.68, 0.72),
    335: (1.18, 2.78, 0.72),
    365: (1.08, 2.82, 0.76),
    420: (1.55, -2.75, 0.88),
}
for frame, location in camera_keys.items():
    key_location(camera, frame, location)

target_keys = {
    1: (0.0, 0.0, 0.02),
    50: (0.0, 0.0, 0.04),
    115: (0.0, 0.0, 0.15),
    175: (0.0, 0.0, 0.12),
    210: (0.0, 0.0, 0.07),
    252: (-0.05, 0.02, 0.04),
    365: (-0.04, 0.02, 0.02),
    420: (0.0, 0.0, 0.02),
}
for frame, location in target_keys.items():
    key_location(target, frame, location)

# The arm, drive cam, and internal five-step slider are one rigid rotating chain.
# Card Z is sampled from the slider contact envelope at every rendered frame.
card_rest_locations = [card.location.copy() for card in cards]


def key_linkage(frame, angle_degrees):
    rotation = (0.0, math.radians(angle_degrees), 0.0)
    for part in (arm, drive_cam, slider):
        key_rotation(part, frame, rotation)
    rises = linkage_rises(angle_degrees)
    for index, card in enumerate(cards):
        location = card_rest_locations[index].copy()
        location.z += rises[index]
        key_location(card, frame, location)


key_linkage(1, 0.0)
key_linkage(48, 0.0)
for frame in range(49, 106):
    progress = smoothstep((frame - 48) / (105 - 48))
    key_linkage(frame, LINKAGE_MAX_ANGLE * progress)
key_linkage(160, LINKAGE_MAX_ANGLE)
for frame in range(161, 203):
    progress = smoothstep((frame - 160) / (202 - 160))
    key_linkage(frame, LINKAGE_MAX_ANGLE * (1.0 - progress))

# Rear door remains shut for the front reveal, then swings outward on its real
# hinge line. It stays open for loading before closing ahead of the loop orbit.
key_rotation(door, 1, (0.0, 0.0, 0.0))
key_rotation(door, 218, (0.0, 0.0, 0.0))
key_rotation(door, 266, (0.0, 0.0, math.radians(114.0)))
key_rotation(door, 281, (0.0, 0.0, math.radians(108.0)))
key_rotation(door, 338, (0.0, 0.0, math.radians(108.0)))
key_rotation(door, 365, (0.0, 0.0, 0.0))
key_rotation(door, 420, (0.0, 0.0, 0.0))

# Resting places solved against the compartment cavity measured from the
# FreeCAD solid: x [-0.2715, 0.2731], z [-0.4946, 0.4932], and only 0.0445 of
# depth between the inner face at 0.0130 and the closed door at 0.0575. That
# depth holds a single layer of coins, so four lie flat with at least 0.75 mm
# of clearance from each other and from the walls. Each note is tilted about Z,
# which leans its 48 mm length into the depth axis and makes the bundle 3.48 mm
# thick, so the cash claims most of the depth in the band above the coins. The
# 2.0 mm ten-cent piece is the one coin thin enough to rest on another and
# still clear the shut door, so it sits on the fifty. Swung open, the door lies
# across the left edge of the mouth out to x=-0.2466, so the whole load is
# packed clear of that side rather than centred in the cavity.
DRIFT_Y = 0.42
STAGING_Y = 0.145

CASH_REST = (0.0132, 0.0439, 0.3587)

COIN_REST = (
    (0.1364, 0.0265, -0.1267),   # one dollar, 25.00 mm
    (-0.0767, 0.0240, -0.3246),  # fifty cents, 31.65 mm
    (-0.0923, 0.0265, 0.0411),   # twenty cents, 28.52 mm
    (0.1589, 0.0285, 0.1100),    # two dollars, 20.50 mm
    (-0.0835, 0.0450, -0.3058),  # ten cents, 23.60 mm, resting on the fifty
)


def key_flight(rig, rest, timing, start, tumble, spin, squash):
    """Fly an item in, square it up well clear of the shell, then drop it in.

    An item tumbles freely only on the opening leg, which stays out beyond
    DRIFT_Y. By the drift key it is already lined up over its own resting
    place and flat, and everything after that moves along -Y alone while
    spinning about its own axis. A descent that never travels sideways cannot
    sweep through the shell rim, the open door, or anything already settled,
    and because the resting footprints do not overlap, neither do the columns
    the items come down in.
    """
    reveal, square_up, touchdown, settle = timing
    rest_x, rest_y, rest_z = rest

    key_visibility_tree(rig, 1, False)
    key_visibility_tree(rig, reveal - 1, False)
    key_visibility_tree(rig, reveal, True)

    key_location(rig, reveal, start)
    key_rotation(rig, reveal, tuple(math.radians(value) for value in tumble))
    key_scale(rig, reveal, (1.0, 1.0, 1.0))

    drift = (reveal + square_up) // 2
    key_location(rig, drift, (rest_x, DRIFT_Y, rest_z))
    key_rotation(rig, drift, (0.0, math.radians(spin * 0.55), 0.0))

    key_location(rig, square_up, (rest_x, STAGING_Y, rest_z))
    key_rotation(rig, square_up, (0.0, math.radians(spin * 0.72), 0.0))
    key_scale(rig, square_up, (1.0, 1.0, 1.0))

    # Contact squashes the item along its own thickness only. Widening it in
    # the compartment plane would eat the millimetre of clearance next door.
    key_location(rig, touchdown, (rest_x, rest_y, rest_z))
    key_rotation(rig, touchdown, (0.0, math.radians(spin * 0.94), 0.0))
    key_scale(rig, touchdown, (1.0, squash, 1.0))

    key_location(rig, settle, (rest_x, rest_y, rest_z))
    key_rotation(rig, settle, (0.0, math.radians(spin), 0.0))
    key_scale(rig, settle, (1.0, 1.0, 1.0))

    key_visibility_tree(rig, 365, True)
    key_visibility_tree(rig, 366, False)
    key_visibility_tree(rig, FRAME_END, False)


# Arrivals are spaced seven frames apart so only one item is ever working its
# way down the funnel; the rest are already below it in their own columns.
key_flight(
    cash_rig,
    CASH_REST,
    (266, 282, 290, 296),
    (1.30, 0.62, 0.98),
    (26.0, -18.0, -24.0),
    0.0,
    0.90,
)

coin_flight = (
    # reveal, square-up, touchdown, settle; entry start; tumble; settled spin
    ((273, 289, 297, 303), (1.44, 0.56, 0.34), (38.0, -24.0, -80.0), -524.0),
    ((280, 296, 304, 310), (0.92, 0.68, 1.18), (-28.0, 34.0, 95.0), 486.0),
    ((287, 303, 311, 317), (1.50, 0.58, -0.60), (46.0, 20.0, -120.0), -612.0),
    ((294, 310, 318, 324), (1.16, 0.72, 1.06), (-34.0, 28.0, 105.0), 448.0),
    # The ten lands last, after the fifty it comes to rest on has settled.
    ((301, 317, 325, 331), (1.54, 0.64, 0.58), (42.0, -30.0, -92.0), -566.0),
)
for coin, rest, (timing, start, tumble, spin) in zip(coins, COIN_REST, coin_flight):
    key_flight(coin, rest, timing, start, tumble, spin, 0.88)

for animated in [camera, target, arm, drive_cam, slider, door, cash_rig, *coins, *cards]:
    smooth_animation(animated)

scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "wallet_v2_animation.blend"))

arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else ["--preview"]
if "--video" in arguments:
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    # This Blender build lists FFMPEG among the image formats but rejects it at
    # assignment, so movie output is unavailable. Render a lossless sequence and
    # encode it externally with the command in README.md.
    frames = OUTPUT / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(frames / "frame_")
    bpy.ops.render.render(animation=True)
else:
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for preview_frame in (1, 112, 292, 315, 336, 365, 420):
        scene.frame_set(preview_frame)
        scene.render.filepath = str(OUTPUT / f"preview_{preview_frame:03d}.png")
        bpy.ops.render.render(write_still=True)
