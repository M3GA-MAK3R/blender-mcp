"""Self-test for the burr math core — no Blender/Manim needed.

Validates:
  1. Each piece's merged boxes reconstruct its original voxel set exactly
     (merge is lossless and non-overlapping).
  2. The key piece is notchless (volume 24); notched pieces are volume 20.
  3. to_mm clearance shrinks each box by 2*clearance per axis.
"""
import math
from burr_math import (
    Box,
    standard_six_piece_burr,
    piece_volume_voxels,
    _make_stick,
    _NOTCH_PATTERNS,
)


def voxels_from_boxes(boxes):
    s = set()
    for b in boxes:
        for x in range(b.x0, b.x1):
            for y in range(b.y0, b.y1):
                for z in range(b.z0, b.z1):
                    assert (x, y, z) not in s, "overlap detected in merged boxes"
                    s.add((x, y, z))
    return s


def expected_voxels(pattern):
    s = set()
    for x in range(6):
        for y in range(2):
            for z in range(2):
                if 2 <= x < 4:
                    cell = (x - 2) * 4 + (y * 2 + z)
                    if pattern[cell]:
                        s.add((x, y, z))
                else:
                    s.add((x, y, z))
    return s


def test_merge_lossless():
    for name, pat in _NOTCH_PATTERNS.items():
        p = _make_stick(pat, name)
        got = voxels_from_boxes(p.boxes)
        exp = expected_voxels(pat)
        assert got == exp, f"{name}: merge mismatch"
    print("PASS: box merge is lossless and non-overlapping for all pieces")


def test_volumes():
    pieces = {p.name: p for p in standard_six_piece_burr()}
    assert piece_volume_voxels(pieces["key"]) == 24, "key must be solid (24)"
    for n in ["P1", "P2", "P3", "P4", "P5"]:
        v = piece_volume_voxels(pieces[n])
        assert v == 20, f"{n} expected 20 voxels, got {v}"
    print("PASS: key=24 solid, 5 notched pieces=20 each (4 voxels carved)")


def test_clearance():
    b = Box(0, 0, 0, 2, 2, 6)
    (cx, cy, cz), (sx, sy, sz) = b.to_mm(unit_mm=8.0, clearance_mm=0.2)
    assert math.isclose(sx, 2 * 8.0 - 0.4), sx
    assert math.isclose(sz, 6 * 8.0 - 0.4), sz
    assert math.isclose(cx, 8.0) and math.isclose(cz, 24.0)
    print("PASS: clearance shrinks each box by 2*clearance; center preserved")


def test_total_volume():
    total = sum(piece_volume_voxels(p) for p in standard_six_piece_burr())
    # 24 + 5*20 = 124 voxels of material across the set
    assert total == 124, total
    print(f"PASS: total material = {total} voxels across 6 pieces")


if __name__ == "__main__":
    test_merge_lossless()
    test_volumes()
    test_clearance()
    test_total_volume()
    print("\nALL TESTS PASSED")
