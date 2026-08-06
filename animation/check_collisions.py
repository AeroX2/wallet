"""Report mesh intersections between the wallet, the cash bundle, and the coins.

Run with:
  blender --background --factory-startup animation/output/wallet_v2_animation.blend \
      --python animation/check_collisions.py -- --start 260 --end 420
"""

import sys
from pathlib import Path

import bpy
from mathutils.bvhtree import BVHTree


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    values = {"--start": 1, "--end": 420, "--step": 1}
    for name in values:
        if name in argv:
            values[name] = int(argv[argv.index(name) + 1])
    return values["--start"], values["--end"], values["--step"]


def mesh_pieces(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    try:
        mesh = evaluated.to_mesh()
    except RuntimeError:
        return [], []
    if mesh is None:
        return [], []
    matrix = evaluated.matrix_world
    vertices = [matrix @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    evaluated.to_mesh_clear()
    return vertices, polygons


def group_tree(objects, depsgraph):
    """Build one BVH tree and one world bounding box for a group of objects."""
    vertices = []
    polygons = []
    for obj in objects:
        piece_vertices, piece_polygons = mesh_pieces(obj, depsgraph)
        offset = len(vertices)
        vertices.extend(piece_vertices)
        polygons.extend(tuple(index + offset for index in polygon) for polygon in piece_polygons)
    if not polygons:
        return None, None
    low = [min(vertex[axis] for vertex in vertices) for axis in range(3)]
    high = [max(vertex[axis] for vertex in vertices) for axis in range(3)]
    return BVHTree.FromPolygons(vertices, polygons), (low, high)


def boxes_apart(first, second, tolerance=0.0):
    low_a, high_a = first
    low_b, high_b = second
    return any(high_a[axis] + tolerance < low_b[axis] or high_b[axis] + tolerance < low_a[axis] for axis in range(3))


def visible(objects):
    return any(not obj.hide_render for obj in objects)


def collect(name_prefix):
    root = bpy.data.objects.get(name_prefix)
    if root is None:
        return []
    return [obj for obj in (root, *root.children_recursive) if obj.type == "MESH"]


scene = bpy.context.scene
start, end, step = arguments()

groups = {
    "shell": collect("Wallet shell"),
    "door": collect("Rear door"),
    "plinth": collect("Floating presentation plinth"),
    "cash": collect("Folded banknote stack"),
}
coin_names = [obj.name for obj in bpy.data.objects if obj.name.endswith("coin") or obj.name.endswith("coin body")]
for obj in bpy.data.objects:
    if obj.parent is None and "coin" in obj.name and obj.type == "EMPTY":
        groups[obj.name] = collect(obj.name)

missing = [name for name, objects in groups.items() if not objects]
if missing:
    raise SystemExit(f"Could not find mesh objects for: {', '.join(missing)}")

coins = [name for name in groups if "coin" in name]
pairs = [("cash", "shell"), ("cash", "door"), ("cash", "plinth")]
for index, coin in enumerate(coins):
    pairs.extend([(coin, "shell"), (coin, "door"), (coin, "plinth"), (coin, "cash")])
    pairs.extend((coin, other) for other in coins[index + 1 :])

static = {}
for name in ("shell", "plinth"):
    scene.frame_set(start)
    static[name] = group_tree(groups[name], bpy.context.evaluated_depsgraph_get())

failures = {}
for frame in range(start, end + 1, step):
    scene.frame_set(frame)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    trees = {}
    for name, objects in groups.items():
        if not visible(objects):
            continue
        trees[name] = static[name] if name in static else group_tree(objects, depsgraph)

    for first, second in pairs:
        if first not in trees or second not in trees:
            continue
        tree_a, box_a = trees[first]
        tree_b, box_b = trees[second]
        if tree_a is None or tree_b is None or boxes_apart(box_a, box_b):
            continue
        hits = tree_a.overlap(tree_b)
        if hits:
            record = failures.setdefault((first, second), {"frames": [], "worst": 0})
            record["frames"].append(frame)
            record["worst"] = max(record["worst"], len(hits))

print()
print(f"Checked frames {start}-{end} (step {step})")
if not failures:
    print("No intersections found.")
else:
    print(f"{len(failures)} intersecting pairs:")
    for (first, second), record in sorted(failures.items(), key=lambda item: -len(item[1]["frames"])):
        frames = record["frames"]
        print(
            f"  {first} <-> {second}: {len(frames)} frames "
            f"({frames[0]}-{frames[-1]}), worst {record['worst']} triangle pairs"
        )
    raise SystemExit(1)
