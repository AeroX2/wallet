"""Solve card lift from the rotating slider's tessellated contact envelope."""

import json
import math
import os
import struct


SOURCE = os.path.abspath(os.path.join("animation", "assets", "slider.stl"))
PIVOT_X = 50.0
PIVOT_Z = 9.7
CARD_X_BOUNDS = (3.8, 57.78)
CARD_Y_BOUNDS = (5.24, 6.0)
CARD_BOTTOM_Z = 17.5
CARD_Y_OFFSETS = (-5.0, -4.0, -3.0, -2.0, -1.0)
MAX_ANGLE = 83.28244


def read_binary_stl(path):
    with open(path, "rb") as stream:
        data = stream.read()
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    triangles = []
    for index in range(triangle_count):
        values = struct.unpack_from("<12fH", data, 84 + index * 50)
        triangles.append(
            [
                [values[3], values[4], values[5]],
                [values[6], values[7], values[8]],
                [values[9], values[10], values[11]],
            ]
        )
    return triangles


def rotate_y(point, degrees):
    radians = math.radians(degrees)
    cosine = math.cos(radians)
    sine = math.sin(radians)
    dx = point[0] - PIVOT_X
    dz = point[2] - PIVOT_Z
    return [
        PIVOT_X + cosine * dx + sine * dz,
        point[1],
        PIVOT_Z - sine * dx + cosine * dz,
    ]


def clip_axis(polygon, axis, boundary, keep_greater):
    if not polygon:
        return []
    clipped = []
    previous = polygon[-1]
    previous_inside = previous[axis] >= boundary if keep_greater else previous[axis] <= boundary
    for current in polygon:
        current_inside = current[axis] >= boundary if keep_greater else current[axis] <= boundary
        if current_inside != previous_inside:
            delta = current[axis] - previous[axis]
            ratio = 0.0 if abs(delta) < 1e-9 else (boundary - previous[axis]) / delta
            clipped.append(
                [
                    previous[component] + ratio * (current[component] - previous[component])
                    for component in range(3)
                ]
            )
        if current_inside:
            clipped.append(current)
        previous = current
        previous_inside = current_inside
    return clipped


def contact_height(rotated_triangles, y_offset):
    x_min, x_max = CARD_X_BOUNDS
    y_min = CARD_Y_BOUNDS[0] + y_offset
    y_max = CARD_Y_BOUNDS[1] + y_offset
    maximum = -1e9
    for triangle in rotated_triangles:
        polygon = clip_axis(triangle, 0, x_min, True)
        polygon = clip_axis(polygon, 0, x_max, False)
        polygon = clip_axis(polygon, 1, y_min, True)
        polygon = clip_axis(polygon, 1, y_max, False)
        if polygon:
            maximum = max(maximum, max(point[2] for point in polygon))
    return maximum


triangles = read_binary_stl(SOURCE)
rises = [0.0 for _ in CARD_Y_OFFSETS]
samples = []

angles = list(range(int(math.floor(MAX_ANGLE)) + 1))
if angles[-1] != MAX_ANGLE:
    angles.append(MAX_ANGLE)

for angle in angles:
    rotated = [[rotate_y(point, angle) for point in triangle] for triangle in triangles]
    for index, y_offset in enumerate(CARD_Y_OFFSETS):
        height = contact_height(rotated, y_offset)
        rises[index] = max(rises[index], max(0.0, height - CARD_BOTTOM_Z))
    if angle % 4 == 0 or angle == MAX_ANGLE:
        samples.append(
            {
                "angle_degrees": angle,
                "card_rise_mm": [round(value, 4) for value in rises],
            }
        )

print(
    json.dumps(
        {
            "source": SOURCE,
            "pivot_mm": [PIVOT_X, 0.0, PIVOT_Z],
            "card_y_offsets_mm": list(CARD_Y_OFFSETS),
            "samples": samples,
        },
        indent=2,
    )
)
