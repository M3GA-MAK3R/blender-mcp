# DRAFT — Part Spec: HMST-001 Soil Moisture Sensor Enclosure

> Status: **DRAFT** — pending review by Stephen.
> Line: Homestead Tools & Gardening IoT. First production part.
> Pipeline: Blender MCP (model in mm) → `check_manifold` → `export_print_3mf` → OrcaSlicer.

## Why this part first

A weatherproof enclosure for a capacitive soil-moisture sensor + microcontroller
is the ideal pilot: it exercises the **whole pipeline** (parametric body, snap
features, manifold checks, mm-accurate export), it's a real Gardening IoT need,
and it's forgiving to print in PETG/PLA. It also seeds the broader IoT product
family (battery box, sensor caps, stake mounts).

## Functional requirements

| ID | Requirement |
|---|---|
| F1 | House one capacitive soil sensor (≈98 × 23 × 1.5 mm probe) + ESP32/D1-mini board |
| F2 | Probe protrudes from bottom; electronics stay dry above grade |
| F3 | Snap-fit or single-screw lid for battery swaps — no glue |
| F4 | Cable/antenna gland or grommet slot on top face |
| F5 | Survives outdoor humidity; UV-tolerant material (PETG/ASA) |

## Print/design constraints (set targets for the model)

- **Units:** millimeters (Blender unit = 1 mm — see pipeline doc §2).
- Wall thickness: **2.0 mm** (3 perimeters @ 0.4 mm nozzle).
- Min feature: ≥ **0.8 mm**; fillet external edges ≥ 1 mm for strength.
- Tolerances: **+0.2 mm** clearance on mating/snap surfaces (FDM shrinkage).
- Orientation: print body open-side-up — no supports on the cavity.
- Layer height: 0.2 mm; infill 20–30% gyroid; PETG for outdoor use.

## Initial dimensions (v0 — iterate after fit test)

| Feature | Value |
|---|---|
| Body outer | 60 × 30 × 45 mm |
| Internal cavity | 56 × 26 × 40 mm (2 mm walls) |
| Probe slot (bottom) | 24 × 3 mm |
| Lid lip engagement | 4 mm, 0.2 mm clearance |
| Gland hole (top) | Ø6 mm |

## Build steps (Blender MCP)

1. `create_cube` → body block 60×30×45 (modeled as 60,30,45 units = mm).
2. Boolean/inset a 56×26×40 cavity; add 24×3 probe slot on -Z face.
3. Add Ø6 mm gland hole on +Z face; fillet outer vertical edges 1.5 mm.
4. Separate lid object with 4 mm lip + 0.2 mm clearance.
5. `blender_export operation=check_manifold` on `["HMST001_Body","HMST001_Lid"]`.
6. Fix any non-manifold edges / loose verts reported.
7. `blender_export operation=export_print_3mf` →
   `/parts/homestead/HMST-001.3mf`.
8. OrcaSlicer: import, confirm 60×30×45 mm on plate, slice, fit-test print.

## Acceptance / fit test

- Imported dimensions match table (±0.1 mm) without slicer scaling.
- Lid snaps and re-opens by hand; survives 5 open/close cycles.
- Sensor probe seats; board clears walls with cable routed through gland.
- No gaps in slice preview (confirms watertight geometry).

## Backlog (next parts in line)

- HMST-002 garden bed stake mount for HMST-001.
- HMST-003 rain-gauge funnel.
- HMST-004 multi-sensor hub enclosure (battery + solar).

---
*Source: pipeline doc `ORCASLICER_PRODUCTION_PIPELINE.md`; FDM design rules from
[OrcaSlicer wiki](https://github.com/SoftFever/OrcaSlicer/wiki) and the attached
OrcaSlicer beginner guide.*
