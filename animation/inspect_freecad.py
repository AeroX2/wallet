"""Print a compact inventory of a FreeCAD assembly for animation setup."""

import json
import os

import FreeCAD as App


SOURCE = os.path.abspath("walletv2.FCStd")


def vector(value):
    return [round(value.x, 5), round(value.y, 5), round(value.z, 5)]


doc = App.openDocument(SOURCE)
objects = []

for obj in doc.Objects:
    if obj.TypeId not in {
        "App::Part",
        "Mesh::Feature",
        "Part::Feature",
        "PartDesign::Body",
        "PartDesign::Feature",
    }:
        continue

    entry = {
        "name": obj.Name,
        "label": obj.Label,
        "type": obj.TypeId,
        "visibility": getattr(getattr(obj, "ViewObject", None), "Visibility", None),
    }

    if hasattr(obj, "Placement"):
        entry["placement"] = {
            "base": vector(obj.Placement.Base),
            "quaternion": [round(component, 7) for component in obj.Placement.Rotation.Q],
        }

    shape = getattr(obj, "Shape", None)
    if shape is not None and not shape.isNull():
        bounds = shape.BoundBox
        entry["shape"] = {
            "solids": len(shape.Solids),
            "faces": len(shape.Faces),
            "volume": round(shape.Volume, 5),
            "bounds": {
                "min": [round(bounds.XMin, 5), round(bounds.YMin, 5), round(bounds.ZMin, 5)],
                "max": [round(bounds.XMax, 5), round(bounds.YMax, 5), round(bounds.ZMax, 5)],
                "size": [round(bounds.XLength, 5), round(bounds.YLength, 5), round(bounds.ZLength, 5)],
            },
        }

    mesh = getattr(obj, "Mesh", None)
    if mesh is not None and mesh.CountPoints:
        bounds = mesh.BoundBox
        entry["mesh"] = {
            "points": mesh.CountPoints,
            "facets": mesh.CountFacets,
            "bounds": {
                "min": [round(bounds.XMin, 5), round(bounds.YMin, 5), round(bounds.ZMin, 5)],
                "max": [round(bounds.XMax, 5), round(bounds.YMax, 5), round(bounds.ZMax, 5)],
                "size": [round(bounds.XLength, 5), round(bounds.YLength, 5), round(bounds.ZLength, 5)],
            },
        }

    group = getattr(obj, "Group", None)
    if group:
        entry["group"] = [child.Name for child in group]

    for prop in ("Tip", "BaseFeature", "Support"):
        if hasattr(obj, prop):
            value = getattr(obj, prop)
            if value:
                if isinstance(value, tuple):
                    entry[prop.lower()] = [getattr(value[0], "Name", str(value[0])), list(value[1])]
                else:
                    entry[prop.lower()] = getattr(value, "Name", str(value))

    objects.append(entry)

print(json.dumps({"source": SOURCE, "label": doc.Label, "objects": objects}, indent=2))

App.closeDocument(doc.Name)
