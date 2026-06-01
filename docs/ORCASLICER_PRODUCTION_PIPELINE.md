# DRAFT — Blender MCP → OrcaSlicer Production CAD Pipeline

> Status: **DRAFT** — pending review by Stephen.
> Scope: ProlificWebCraft R&D. First product line: **Homestead Tools & Gardening IoT**.
> Owner: R&D / Hermes fleet. Source repo: `sandraschi/blender-mcp` (fork/branch).

## 1. Why this exists

The upstream `blender-mcp` exporter targets **game/avatar** pipelines
(FBX → Unity, VRM → VRChat, GLB → Godot). Those formats are wrong for
production 3D printing:

| Concern | Game pipeline | Production CAD / print |
|---|---|---|
| Format | FBX, GLB, VRM | **STL, 3MF** (OrcaSlicer native) |
| Units | arbitrary / meters | **millimeters, exact** |
| Geometry | n-gons, open meshes OK | **manifold / watertight required** |
| Modifiers | often kept live | **must be applied/baked** |

This branch adds three operations to the existing `blender_export` tool.

## 2. New operations (added to `blender_export`)

| `operation` | What it does | Output |
|---|---|---|
| `export_print_stl` | Binary STL, mm-scaled, modifiers applied | `.stl` |
| `export_print_3mf` | 3MF, mm units embedded, multi-object | `.3mf` (preferred) |
| `check_manifold` | Watertight / non-manifold pre-flight report | JSON, no file |

Common params: `output_path`, `object_names` (None = all meshes),
`use_mesh_modifiers` (maps to apply-modifiers + bake transforms).

### The unit fix (the part that bites everyone)

STL carries **no unit metadata**. Blender's default scene unit is the
**meter**. A part modeled as `50` exports as 50 — and OrcaSlicer reads that as
**50 meters**, not 50 mm. The new handler forces, on every print export:

```python
scene.unit_settings.system        = 'METRIC'
scene.unit_settings.length_unit   = 'MILLIMETERS'
scene.unit_settings.scale_length  = 0.001   # 1 Blender unit == 1 mm
```

**Convention going forward: model in Blender units = millimeters.**
A 50 mm bracket is modeled as 50 units. 3MF embeds units, so it round-trips
cleanly and is the preferred handoff; STL stays as a fallback.

> Migration risk: any existing `.blend` files modeled in "meters = 1 m" will
> come out 1000× too large. Re-scale legacy parts by 0.001 before first export,
> or re-base them in mm. **Flag before bulk-converting old assets.**

## 3. Slicer-side handoff (OrcaSlicer)

1. **File → Import → Import 3MF/STL/STEP** (or drag onto the plate).
2. If you used `export_print_3mf`, dimensions are correct on import — verify in
   the right-hand object panel.
3. If STL imported at the wrong size, it was modeled in the wrong unit — fix in
   Blender and re-export rather than scaling in the slicer (keeps the source of
   truth in CAD).
4. Use **Scale** only for intentional resizing, never to "fix units."
5. Slice → Preview → check for gaps/holes (symptom of non-manifold geometry —
   run `check_manifold` upstream).

## 4. Recommended agent workflow (Hermes)

```
create/import mesh  →  check_manifold  →  (fix if needed)  →  export_print_3mf  →  OrcaSlicer
```

Example MCP calls:

```jsonc
// 1. Pre-flight
{ "tool": "blender_export", "operation": "check_manifold",
  "object_names": ["HoseGuide_Body"] }

// 2. Export once watertight
{ "tool": "blender_export", "operation": "export_print_3mf",
  "output_path": "/parts/homestead/hose_guide.3mf",
  "object_names": ["HoseGuide_Body"], "use_mesh_modifiers": true }
```

## 5. Open items / breaking-change flags

- **3MF add-on dependency:** `export_print_3mf` needs Blender's 3MF exporter
  (`export_mesh.threemf` / `wm.threemf_export`) or the `3mf-io` add-on. If
  absent it raises with a clear message — STL fallback always works. *Action:
  bundle/enable 3MF add-on in the headless Blender image.*
- **STL operator namespace:** Blender 4.2+ uses `wm.stl_export`; older uses
  `export_mesh.stl`. Handler tries new first, falls back. Pin a Blender version
  in CI to avoid surprises.
- **No tolerance/CAD-kernel ops yet:** Blender is a mesh modeler, not a B-rep
  CAD kernel. For tight mechanical tolerances (threads, press-fits) consider the
  `freecad-mcp` STEP path noted in the upstream fleet table.

---
*Sources: repo `mcpb/src/blender_mcp/handlers/export_handler.py`,
`tools/export/export_tools.py`; OrcaSlicer beginner guide (attached);
[OrcaSlicer docs](https://github.com/SoftFever/OrcaSlicer/wiki).*
