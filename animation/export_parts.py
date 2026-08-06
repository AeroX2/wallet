"""Export the moving FreeCAD bodies as high-resolution STL meshes."""

import os
from pathlib import Path

import FreeCAD as App
import MeshPart


ROOT = Path(os.getcwd())
SOURCE = ROOT / "walletv2.FCStd"
OUTPUT = ROOT / "animation" / "assets"

PARTS = {
    "Body": "main_body",
    "Body001": "credit_card",
    "Body002": "slider",
    "Body003": "drive_cam",
    "Body004": "arm",
    "Body005": "door",
}


OUTPUT.mkdir(parents=True, exist_ok=True)
doc = App.openDocument(str(SOURCE))

for object_name, filename in PARTS.items():
    obj = doc.getObject(object_name)
    if obj is None or obj.Shape.isNull():
        raise RuntimeError(f"Missing solid body: {object_name}")

    mesh = MeshPart.meshFromShape(
        Shape=obj.Shape,
        LinearDeflection=0.045,
        AngularDeflection=0.0872665,
        Relative=False,
    )
    target = OUTPUT / f"{filename}.stl"
    mesh.write(str(target))
    print(
        f"{obj.Label}: {mesh.CountPoints} vertices, "
        f"{mesh.CountFacets} facets -> {target}"
    )

App.closeDocument(doc.Name)
