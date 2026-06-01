# DRAFT — Shared Math Module: ProlificManim ↔ Blender CAD

> Status: **DRAFT** — pending review by Stephen.
> Goal: derive geometry from first principles **once**, then both *animate* it
> (Manim) and *fabricate* it (Blender → OrcaSlicer) from the same source.
> First example: **6-piece burr puzzle** (rectilinear, easy fit-test + iterate).

## 1. Architecture — three layers

```
            ┌─────────────────────────────┐
            │   MATH CORE (pure Python)    │   burr_math.py
            │  voxel model → Box lists     │   no Manim, no bpy
            └──────────────┬──────────────┘
                   ┌────────┴────────┐
                   ▼                 ▼
        ┌────────────────┐   ┌──────────────────┐
        │ Manim adapter  │   │ Blender adapter  │
        │ burr_manim.py  │   │ burr_blender.py  │
        │ → explainer    │   │ → printable mesh │
        │   video        │   │   → STL/3MF      │
        └────────────────┘   └────────┬─────────┘
                                       ▼
                                 OrcaSlicer
```

The **math core has zero rendering dependencies**. It emits axis-aligned
`Box` primitives in voxel units. Each adapter is a thin consumer:

- **Manim** scales boxes to scene units, colors them, animates assembly.
- **Blender** scales boxes to **millimeters**, applies **fit clearance**,
  joins per-piece meshes, then feeds the new `export_print_3mf` path.

Guarantee: the animation and the printed part describe **identical geometry**,
because they read the same `Box` lists.

## 2. The burr math (first principles)

A 6-piece burr lives on a unit-cube grid. Each piece is a **2×2×6** stick.
Material is carved only from the central **2-voxel interlock zone** (x∈[2,4)).
A piece = a 3D occupancy grid; orthogonally-adjacent solid voxels are greedily
merged into the minimum set of clean boxes (keeps meshes watertight).

- **Key piece**: notchless (24 voxels) — slides in last, locks the puzzle.
- **5 notched pieces**: 20 voxels each (4 carved).
- Two sticks per axis × 3 axes = the interlocking cross.
- **Total material: 124 voxels** across the set (validated by tests).

Notch patterns live in `_NOTCH_PATTERNS` — swap them to generate other burr
designs or harder interlocks without touching the adapters.

## 3. Fabrication notes (Blender adapter)

| Param | Default | Meaning |
|---|---|---|
| `unit_mm` | 8.0 | voxel edge → ~48 mm finished pieces |
| `clearance_mm` | 0.2 | per-side gap so printed pieces slide (FDM 0.15–0.25) |
| `layout` | `print` | `print` = flat + spaced for the plate; `assembled` = interlocked cross |

Workflow: `build_burr()` → `check_manifold` → `export_print_3mf` per piece →
OrcaSlicer → test fit → adjust `clearance_mm` and reprint. Rectilinear geometry
makes tolerance iteration fast and unambiguous.

## 4. Files

| File | Repo | Role |
|---|---|---|
| `prolific_cad/burr_math.py` | both (mirrored) | math core — single source of truth |
| `prolific_cad/burr_blender.py` | blender-mcp | bpy mesh builder (mm + clearance) |
| `prolific_cad/test_burr.py` | blender-mcp | validates merge/volumes/clearance |
| `prolific_cad/burr_manim.py` | ProlificManim | ManimGL explainer scene |

## 5. Where game characters fit

Per the plan, the existing game/avatar exports stay — **game-character meshes
serve as physics/scale references** inside Blender scenes (drop a humanoid next
to a part to sanity-check real-world size and handling).

## 6. Open items / risks

- **Math core is mirrored** into both repos for now. *Action: promote to a tiny
  shared pip package (`prolific-cad-math`) so there's truly one copy.* Flag:
  until then, keep the two copies in sync.
- **Manim `Cube` stretch API** assumed (`set_width/height/depth(stretch=True)`);
  verify against the pinned ManimGL build.
- **Solvability** is by construction from the standard pattern set; add an
  assembly-order solver test before shipping custom notch patterns.
- Blender adapter assumes the new `export_print_*` operators from PR #1.

---
*Source: `prolific_cad/burr_math.py` and adapters; standard burr geometry
(2×2×6 sticks on a unit grid). Companion: ORCASLICER_PRODUCTION_PIPELINE.md.*
