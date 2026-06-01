"""Blender adapter: build printable burr-puzzle meshes from the math core.

Run *inside* Blender (headless via blender-mcp's executor, or `blender -P`).
Consumes Box lists from burr_math.py and emits one mesh object per piece,
sized in millimeters with fabrication clearance applied so the printed pieces
actually slide together.

Assembly transforms place the 6 sticks onto 3 orthogonal axes (2 per axis),
forming the interlocking cross. For printing you usually want pieces laid out
flat and separated (see `layout='print'`).
"""

from __future__ import annotations

import math

import bpy  # type: ignore  # only available inside Blender

# Requires the shared math package:  pip install prolific-cad-math
# (or: pip install git+https://github.com/M3GA-MAK3R/prolific-cad-math.git)
# Install it into the SAME Python that runs Blender's bpy.
from prolific_cad_math import Piece, standard_six_piece_burr


# Orientation per piece index: (euler_rotation, assembled_offset_in_units)
# Two sticks per axis, offset so notches interlock at the center.
_ASSEMBLY = [
    ((0, 0, 0),               (0, 0, 0)),   # key  - X axis
    ((0, 0, 0),               (0, 2, 2)),   # P1   - X axis, shifted
    ((0, 0, math.pi / 2),     (2, 0, 0)),   # P2   - Y axis
    ((0, 0, math.pi / 2),     (0, 0, 2)),   # P3   - Y axis
    ((0, math.pi / 2, 0),     (2, 0, 0)),   # P4   - Z axis
    ((0, math.pi / 2, 0),     (0, 2, 0)),   # P5   - Z axis
]


def _add_box(center_mm, size_mm, name):
    bpy.ops.mesh.primitive_cube_add(location=center_mm)
    obj = bpy.context.active_object
    obj.scale = (size_mm[0] / 2.0, size_mm[1] / 2.0, size_mm[2] / 2.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.name = name
    return obj


def build_piece(piece: Piece, unit_mm: float, clearance_mm: float):
    """Build one piece as a single joined mesh from its boxes."""
    parts = []
    for i, b in enumerate(piece.boxes):
        c, s = b.to_mm(unit_mm, clearance_mm)
        parts.append(_add_box(c, s, f"{piece.name}_b{i}"))
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = f"Burr_{piece.name}"
    # color via a simple material for viewport/render clarity
    mat = bpy.data.materials.new(f"mat_{piece.name}")
    mat.diffuse_color = (*piece.color, 1.0)
    obj.data.materials.append(mat)
    return obj


def build_burr(unit_mm: float = 8.0, clearance_mm: float = 0.2,
               layout: str = "print"):
    """Build the full 6-piece set.

    Args:
        unit_mm: physical size of one voxel edge (8 mm -> ~48 mm pieces).
        clearance_mm: per-side gap for printed fit (0.15-0.25 typical FDM).
        layout: 'assembled' interlocks the cross; 'print' lays pieces flat,
                spaced apart on the plate for slicing.
    """
    # clear scene
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    pieces = standard_six_piece_burr()
    objs = []
    for idx, p in enumerate(pieces):
        obj = build_piece(p, unit_mm, clearance_mm)
        if layout == "assembled":
            rot, off = _ASSEMBLY[idx]
            obj.rotation_euler = rot
            obj.location = (off[0] * unit_mm, off[1] * unit_mm, off[2] * unit_mm)
        else:  # print: spread along x, all flat
            obj.location = (idx * 7 * unit_mm, 0, 0)
        objs.append(obj)
    bpy.context.view_layer.update()
    return objs


if __name__ == "__main__":
    build_burr()
    print("Burr puzzle built. Export each Burr_* with "
          "blender_export operation=export_print_3mf.")
