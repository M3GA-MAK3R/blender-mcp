"""Burr puzzle math core — pure Python, no Manim or bpy dependencies.

This is the single source of truth for interlocking-block puzzle geometry.
Both the Manim renderer and the Blender mesh builder consume the box lists
produced here, so the math is derived once, from first principles, and reused.

Coordinate model
----------------
A 6-piece burr lives on a unit-cube voxel grid. Each piece is a stick that is
2 voxels x 2 voxels in cross-section and 6 voxels long. Material is removed
from the central 2-voxel-long region to create the interlocking notches.

A piece is described by a 3D occupancy grid (1 = solid, 0 = removed). The
"key piece" (no notches) is what makes the standard burr solvable: it slides
in last. We merge orthogonally-adjacent solid voxels into the minimum set of
axis-aligned boxes so downstream meshes stay clean and watertight.

Units
-----
`unit_mm` is the physical size of one voxel edge in millimeters. `clearance_mm`
is subtracted from every box on all sides during *fabrication* (the Blender
adapter), giving printed pieces room to slide. Manim renders nominal geometry
(no clearance) for clarity.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --- Primitive box (axis-aligned, in voxel units) --------------------------
@dataclass(frozen=True)
class Box:
    """Axis-aligned box in voxel coordinates: [x0,x1) x [y0,y1) x [z0,z1)."""

    x0: int
    y0: int
    z0: int
    x1: int
    y1: int
    z1: int

    def to_mm(self, unit_mm: float, clearance_mm: float = 0.0):
        """Return (center_xyz_mm, size_xyz_mm) shrunk by clearance per side."""
        cx = (self.x0 + self.x1) / 2.0 * unit_mm
        cy = (self.y0 + self.y1) / 2.0 * unit_mm
        cz = (self.z0 + self.z1) / 2.0 * unit_mm
        sx = (self.x1 - self.x0) * unit_mm - 2 * clearance_mm
        sy = (self.y1 - self.y0) * unit_mm - 2 * clearance_mm
        sz = (self.z1 - self.z0) * unit_mm - 2 * clearance_mm
        return (cx, cy, cz), (sx, sy, sz)


@dataclass
class Piece:
    name: str
    boxes: list[Box]
    # axis the stick runs along: 'x', 'y', or 'z'
    axis: str = "x"
    color: tuple[float, float, float] = (0.8, 0.8, 0.8)


# --- Notch patterns for the standard solvable 6-piece burr -----------------
# Each pattern describes which of the 6 unit-cells in the central 2x2x2
# interlock region are SOLID (1) for that piece. The grid is the central
# notch zone, indexed [a][b] over the 2x2 cross-section, for each of the two
# central length-slices. Index order chosen to make the standard "Burr #1"
# solvable, with one notchless key piece.
#
# Layout of the central interlock zone (cross-section 2x2, two slices deep):
#   slice 0:  [c00 c01 / c10 c11]    slice 1: [c20 c21 / c30 c31]
# 1 = keep material, 0 = carve out.
_NOTCH_PATTERNS: dict[str, list[int]] = {
    # key piece: fully solid (slides in last, locks the assembly)
    "key":    [1, 1, 1, 1, 1, 1, 1, 1],
    # standard notched pieces (8 central cells each: [c00,c01,c10,c11,c20,c21,c30,c31])
    "P1":     [1, 0, 1, 0, 1, 0, 1, 0],
    "P2":     [0, 1, 0, 1, 0, 1, 0, 1],
    "P3":     [1, 1, 0, 0, 0, 0, 1, 1],
    "P4":     [0, 0, 1, 1, 1, 1, 0, 0],
    "P5":     [1, 0, 0, 1, 1, 0, 0, 1],
}


def _merge_boxes(voxels: set[tuple[int, int, int]]) -> list[Box]:
    """Greedily merge a set of unit voxels into fewer axis-aligned boxes.

    Strategy: extend each unclaimed voxel as far as possible along +x, then
    +y, then +z while the whole growing box stays fully occupied. Simple,
    deterministic, and produces clean watertight slabs for the burr geometry.
    """
    remaining = set(voxels)
    boxes: list[Box] = []
    while remaining:
        x0, y0, z0 = min(remaining)
        # grow x
        x1 = x0
        while (x1, y0, z0) in remaining:
            x1 += 1
        # grow y while full row present
        y1 = y0
        while all((x, y1, z0) in remaining for x in range(x0, x1)):
            y1 += 1
        # grow z while full slab present
        z1 = z0
        while all(
            (x, y, z1) in remaining
            for x in range(x0, x1)
            for y in range(y0, y1)
        ):
            z1 += 1
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    remaining.discard((x, y, z))
        boxes.append(Box(x0, y0, z0, x1, y1, z1))
    return boxes


def _make_stick(pattern: list[int], name: str) -> Piece:
    """Build one x-running stick: 2x2 cross-section, length 6, central notches.

    Cross-section spans y,z in {0,1}. Length spans x in [0,6). The interlock
    zone is x in [2,4) (two central voxel-slices). Outside that zone the stick
    is always solid.
    """
    voxels: set[tuple[int, int, int]] = set()
    for x in range(6):
        for y in range(2):
            for z in range(2):
                if 2 <= x < 4:
                    # central interlock zone -> consult pattern
                    slice_idx = x - 2          # 0 or 1
                    cell = (slice_idx * 4) + (y * 2 + z)
                    if pattern[cell]:
                        voxels.add((x, y, z))
                else:
                    voxels.add((x, y, z))
    return Piece(name=name, boxes=_merge_boxes(voxels), axis="x")


def standard_six_piece_burr() -> list[Piece]:
    """Return the 6 pieces of a standard solvable burr in voxel coordinates.

    All pieces are generated as x-running sticks here; the assembly/adapter
    layer rotates them onto the three orthogonal axes (two per axis) to form
    the interlocking cross. Geometry derivation stays axis-agnostic.
    """
    names = ["key", "P1", "P2", "P3", "P4", "P5"]
    palette = [
        (0.85, 0.30, 0.30), (0.30, 0.60, 0.85), (0.40, 0.75, 0.40),
        (0.90, 0.75, 0.25), (0.65, 0.45, 0.80), (0.55, 0.55, 0.55),
    ]
    pieces = []
    for n, col in zip(names, palette):
        p = _make_stick(_NOTCH_PATTERNS[n], n)
        p.color = col
        pieces.append(p)
    return pieces


def piece_volume_voxels(piece: Piece) -> int:
    return sum(
        (b.x1 - b.x0) * (b.y1 - b.y0) * (b.z1 - b.z0) for b in piece.boxes
    )


if __name__ == "__main__":
    for p in standard_six_piece_burr():
        print(f"{p.name:5s} axis={p.axis} boxes={len(p.boxes):2d} "
              f"vol={piece_volume_voxels(p):2d} voxels")
