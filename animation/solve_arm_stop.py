"""Solve the slider-arm end angle from the recessed front profile."""

import os

import FreeCAD as App
import Part


doc = App.openDocument(os.path.abspath("walletv2.FCStd"))
sketch = doc.getObject("Sketch005")

print(f"Sketch005 wires: {len(sketch.Shape.Wires)}")
for index, wire in enumerate(sketch.Shape.Wires):
    bounds = wire.BoundBox
    try:
        face = Part.Face(wire)
        area = face.Area
    except Exception:
        area = None
    print(
        f"wire {index}: closed={wire.isClosed()}, edges={len(wire.Edges)}, "
        f"area={area}, x=[{bounds.XMin:.4f},{bounds.XMax:.4f}], "
        f"z=[{bounds.ZMin:.4f},{bounds.ZMax:.4f}]"
    )

profile = Part.Face(sketch.Shape.Wires[0])
recess = profile.extrude(App.Vector(0.0, -3.0, 0.0))
arm_source = doc.getObject("Body004").Shape.copy()
pivot = App.Vector(50.0, 0.0, 9.7)
axis = App.Vector(0.0, 1.0, 0.0)


def outside_volume(angle):
    arm = arm_source.copy()
    arm.rotate(pivot, axis, angle)
    return max(0.0, arm.Volume - recess.common(arm).Volume)


for angle in (0.0, 62.0, 80.0, 82.0, 84.0, 86.0, 88.0, 90.0):
    print(f"angle {angle:.1f}: outside={outside_volume(angle):.8f} mm^3")

low = 62.0
high = 90.0
for _ in range(24):
    middle = (low + high) * 0.5
    if outside_volume(middle) <= 1e-5:
        low = middle
    else:
        high = middle
print(f"contact angle: {low:.6f} degrees")

App.closeDocument(doc.Name)
