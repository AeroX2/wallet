"""Report arm-to-shell overlap at candidate end-stop angles."""

import os

import FreeCAD as App


doc = App.openDocument(os.path.abspath("walletv2.FCStd"))
shell = doc.getObject("Body").Shape.copy()
arm_source = doc.getObject("Body004").Shape.copy()
pivot = App.Vector(50.0, 0.0, 9.7)
axis = App.Vector(0.0, 1.0, 0.0)

for angle in (62.0, 84.0, 90.0, 96.0):
    arm = arm_source.copy()
    arm.rotate(pivot, axis, angle)
    overlap = shell.common(arm).Volume
    bounds = arm.BoundBox
    print(
        f"{angle:.0f} degrees: overlap={overlap:.6f} mm^3, "
        f"x=[{bounds.XMin:.3f}, {bounds.XMax:.3f}], "
        f"z=[{bounds.ZMin:.3f}, {bounds.ZMax:.3f}]"
    )

App.closeDocument(doc.Name)
