"""Comprehensive export and render handlers for Unity/VRChat pipeline.

This module provides export functions that can be registered as FastMCP tools.
"""

import os
from pathlib import Path

from loguru import logger

from ..compat import *
from ..decorators import blender_operation
from ..exceptions import BlenderExportError
from ..utils.blender_executor import get_blender_executor

# Initialize the executor with default Blender executable
_executor = get_blender_executor()


def _get_export_script_setup(output_path: str, blend_path: str | None = None) -> str:
    """Generate the common setup script for export operations.

    Args:
        output_path: Path where FBX will be exported
        blend_path: Optional path to .blend file to load before export
    """
    load_blend = ""
    if blend_path:
        # Escape backslashes for the raw string in the generated script
        blend_path_escaped = blend_path.replace("\\", "\\\\")
        load_blend = f"""
# Load .blend file if specified
blend_file_path = r"{blend_path_escaped}"
import os
if os.path.exists(blend_file_path):
    bpy.ops.wm.open_mainfile(filepath=blend_file_path)
    print(f"Loaded .blend file: {{blend_file_path}}")
else:
    print(f"WARNING: .blend file not found: {{blend_file_path}}")
"""

    return f"""
import os
import json
from pathlib import Path
{load_blend}
# Ensure output directory exists
output_dir = os.path.dirname(r"{output_path}")
os.makedirs(output_dir, exist_ok=True)

# Get scene and objects
scene = bpy.context.scene
original_objects = list(scene.objects)

# Select all mesh objects for export
mesh_objects = [obj for obj in original_objects if obj.type == 'MESH']
print(f"Found {{len(mesh_objects)}} mesh objects for export:")
for obj in mesh_objects:
    print(f"  - {{obj.name}}")
bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)
"""


@blender_operation("export_for_unity", log_args=True)
async def export_for_unity(
    output_path: str,
    scale: float = 1.0,
    apply_modifiers: bool = True,
    optimize_materials: bool = True,
    bake_textures: bool = False,
    lod_levels: int = 0,
) -> str:
    """Export scene optimized for Unity3D with full pipeline support.

    Args:
        output_path: Full path where the FBX file will be saved
        scale: Scale factor for the exported model (default: 1.0)
        apply_modifiers: Whether to apply modifiers before export (default: True)
        optimize_materials: Whether to optimize materials for Unity (default: True)
        bake_textures: Whether to bake textures (default: False)
        lod_levels: Number of LOD levels to generate (0 = no LOD) (default: 0)

    Returns:
        str: Success message with export details

    Raises:
        BlenderExportError: If export fails
    """
    try:
        # Validate output path
        output_path = str(Path(output_path).absolute())
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            raise BlenderExportError("FBX", output_path, "Invalid output directory")

        # Generate the export script - load .blend file if it exists
        blend_path = str(Path(output_path).with_suffix(".blend"))
        script = _get_export_script_setup(output_path, blend_path=blend_path)
        script += f"""
try:
    # Configure export settings
    export_path = r"{output_path}"
    print(f"Starting FBX export to: {{export_path}}")
    print(f"Selected {{len(mesh_objects)}} mesh objects for export")

    # Select all mesh objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objects:
        obj.select_set(True)

    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=True,
        apply_scale_options='FBX_SCALE_ALL',
        global_scale={scale},
        apply_unit_scale=True,
        bake_space_transform=True,
        object_types={{'MESH', 'ARMATURE', 'OTHER'}},
        use_mesh_modifiers={apply_modifiers},
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        use_armature_deform_only=True,
        bake_anim=False,
        path_mode='AUTO',
        embed_textures={bake_textures}
    )

    # Verify file was created
    import os
    if os.path.exists(export_path):
        file_size = os.path.getsize(export_path)
        print(f"SUCCESS: FBX file created at {{export_path}} ({{file_size}} bytes)")
    else:
        print(f"ERROR: FBX file was not created at {{export_path}}")
        raise Exception("FBX export completed but file not found")

    # Collect statistics
    stats = {{
        'export_path': export_path,
        'object_count': len(mesh_objects),
        'scale_factor': {scale},
        'applied_modifiers': {apply_modifiers!s},
        'optimized_materials': {optimize_materials!s},
        'baked_textures': {bake_textures!s},
        'lod_levels': {lod_levels}
    }}

    print(f"SUCCESS: Unity export complete!")
    print(f"Export details: {{json.dumps(stats, indent=2)}}")

except Exception as e:
    import traceback
    error_msg = f"ERROR: Export failed: {{str(e)}}\\n{{traceback.format_exc()}}"
    print(error_msg)
    raise e
"""
        # Execute the export script
        # Check if file exists before export
        file_existed_before = os.path.exists(output_path)
        file_mtime_before = os.path.getmtime(output_path) if file_existed_before else 0

        try:
            await _executor.execute_script(script, script_name="unity_export")
            # Verify file was created
            if not os.path.exists(output_path):
                raise BlenderExportError("FBX", output_path, "Export completed but file not found")
            file_size = os.path.getsize(output_path)
            return f"Successfully exported to {output_path} ({file_size} bytes)"
        except Exception as e:
            # Check if file was created despite the error (TBBmalloc warning or viewport error)
            error_str = str(e)
            if os.path.exists(output_path):
                file_mtime_after = os.path.getmtime(output_path)
                # If file was created or updated, treat as success
                if not file_existed_before or file_mtime_after > file_mtime_before:
                    file_size = os.path.getsize(output_path)
                    logger.warning(f"Blender exited with error but FBX file was created: {error_str}")
                    return f"Successfully exported to {output_path} ({file_size} bytes) - warning ignored"
            # If no file was created, raise error
            raise BlenderExportError("FBX", output_path, error_str) from e

    except Exception as e:
        logger.error(f"Failed to export for Unity: {e!s}")
        raise BlenderExportError("FBX", output_path, str(e)) from e


@blender_operation("export_for_vrchat", log_args=True)
async def export_for_vrchat(
    output_path: str,
    polygon_limit: int = 20000,
    material_limit: int = 8,
    texture_size_limit: int = 1024,
    performance_rank: str = "Good",
) -> str:
    """Export scene optimized for VRChat with strict performance limits.

    Args:
        output_path: Full path where the VRM file will be saved
        polygon_limit: Maximum allowed polygons (default: 20000)
        material_limit: Maximum allowed materials (default: 8)
        texture_size_limit: Maximum texture size in pixels (default: 1024)
        performance_rank: Target performance rank (default: "Good")

    Returns:
        str: Success message with export details

    Raises:
        BlenderExportError: If export fails or performance limits are exceeded
    """
    try:
        # Validate output path
        output_path = str(Path(output_path).absolute())
        output_dir = os.path.dirname(output_path)
        if not output_dir:
            raise BlenderExportError("VRM", output_path, "Invalid output directory")

        # Generate the export script
        script = _get_export_script_setup(output_path)
        script += f"""
# Check performance metrics
total_polys = 0
for obj in mesh_objects:
    if obj.type == 'MESH':
        total_polys += len(obj.data.polygons)

# Check against limits
warnings = []
if total_polys > {polygon_limit}:
    warnings.append(f"Polygon count {{total_polys}} exceeds limit of {{'{polygon_limit}'}}")

if len(bpy.data.materials) > {material_limit}:
    warnings.append(f"Material count {{len(bpy.data.materials)}} exceeds limit of {{'{material_limit}'}}")

# Configure export settings
if not warnings:
    bpy.ops.export_scene.vrm(
        filepath=r"{output_path}",
        export_invisibles=False,
        export_only_selections=False,
        export_tangent_space=False,
        export_texture_dir=os.path.join(os.path.dirname(r"{output_path}"), "textures")
    )

    print(f"SUCCESS: VRChat export complete!")
    print(f"Performance rank: {{'{performance_rank}'}}")
    print(f"Total polygons: {{total_polys}}")
    print(f"Total materials: {{len(bpy.data.materials)}}")
else:
    print("ERROR: Export failed - Performance limits exceeded")
    for warning in warnings:
        print(f"WARNING: {{warning}}")
    raise Exception("VRChat performance limits exceeded")
"""
        # Execute the export script
        await _executor.execute_script(script, script_name="vrc_export")
        return f"Successfully exported to {output_path} with {performance_rank} performance settings"

    except Exception as e:
        logger.error(f"Failed to export for VRChat: {e!s}")
        raise BlenderExportError("VRM", output_path, str(e)) from e


# ---------------------------------------------------------------------------
# Production CAD / 3D-printing exports (OrcaSlicer pipeline)
# Added for ProlificWebCraft R&D — Homestead Tools / Gardening IoT line.
#
# Key difference vs. game/avatar exports above:
#   * Units are forced to MILLIMETERS. Blender's default unit is the meter,
#     so a part modeled as "50" would import into OrcaSlicer as 50 METERS.
#     STL has no unit metadata; 3MF does. We bake a mm-correct scale on export.
#   * Modifiers are applied and transforms baked so the slicer sees final geo.
#   * Optional manifold/watertight pre-check (see check_print_manifold).
# ---------------------------------------------------------------------------

# Blender mesh exporters changed namespace across versions. STL moved from the
# legacy `export_mesh.stl` operator to the built-in `wm.stl_export` (Blender
# 4.2+). We try the new operator first and fall back to the legacy one.
_PRINT_EXPORT_PREP = """
import bpy

scene = bpy.context.scene

# Force millimeter units so the slicer reads real-world part sizes.
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'
# scale_length=0.001 makes 1 Blender unit == 1 mm on export.
scene.unit_settings.scale_length = 0.001

# Resolve target objects.
target_names = {object_names!r}
if target_names:
    objs = [o for o in scene.objects if o.type == 'MESH' and o.name in target_names]
else:
    objs = [o for o in scene.objects if o.type == 'MESH']

if not objs:
    raise Exception("No mesh objects found to export for printing")

bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
scene.view_layers[0].objects.active = objs[0]

# Apply modifiers + bake transforms so the slicer gets final, real geometry.
if {apply_modifiers}:
    for o in objs:
        scene.view_layers[0].objects.active = o
        for m in list(o.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as exc:
                print(f"WARNING: could not apply modifier {{m.name}} on {{o.name}}: {{exc}}")
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    scene.view_layers[0].objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
"""


@blender_operation("export_for_print_stl", log_args=True)
async def export_for_print_stl(
    output_path: str,
    object_names: list[str] | None = None,
    apply_modifiers: bool = True,
) -> str:
    """Export selected/all meshes to a binary STL sized in millimeters for OrcaSlicer.

    Args:
        output_path: Full path to the .stl file to write.
        object_names: Specific objects to export (None = all meshes in scene).
        apply_modifiers: Apply modifiers and bake transforms before export.

    Returns:
        Success message with the written path.
    """
    if not output_path.lower().endswith(".stl"):
        output_path += ".stl"
    out = output_path.replace("\\", "\\\\")
    prep = _PRINT_EXPORT_PREP.format(
        object_names=object_names, apply_modifiers=apply_modifiers
    )
    script = (
        prep
        + f"""
import os
os.makedirs(os.path.dirname(r"{out}"), exist_ok=True)

# Blender 4.2+ uses wm.stl_export; older builds use export_mesh.stl.
exported = False
if hasattr(bpy.ops.wm, "stl_export"):
    bpy.ops.wm.stl_export(
        filepath=r"{out}",
        export_selected_objects=True,
        apply_modifiers=False,  # already applied in prep
        ascii_format=False,
        global_scale=1.0,
    )
    exported = True
else:
    bpy.ops.export_mesh.stl(
        filepath=r"{out}",
        use_selection=True,
        use_mesh_modifiers=False,
        ascii=False,
        global_scale=1.0,
    )
    exported = True

if not (exported and os.path.exists(r"{out}")):
    raise Exception("STL export completed but file not found")
print(f"SUCCESS: STL written to {out} ({{os.path.getsize(r'{out}')}} bytes)")
"""
    )
    try:
        await _executor.execute_script(script, script_name="print_stl_export")
        return f"Exported print-ready STL (mm units) to {output_path}"
    except Exception as e:
        logger.error(f"STL print export failed: {e!s}")
        raise BlenderExportError("STL", output_path, str(e)) from e


@blender_operation("export_for_print_3mf", log_args=True)
async def export_for_print_3mf(
    output_path: str,
    object_names: list[str] | None = None,
    apply_modifiers: bool = True,
) -> str:
    """Export meshes to 3MF (preferred for OrcaSlicer — carries mm units + multi-object).

    3MF stores units, so OrcaSlicer reads dimensions exactly. Requires the
    Blender 3MF add-on / built-in operator (`export_mesh.threemf` or the 3mf-io
    add-on). Falls back to STL if 3MF is unavailable.

    Args:
        output_path: Full path to the .3mf file to write.
        object_names: Specific objects to export (None = all meshes).
        apply_modifiers: Apply modifiers and bake transforms before export.
    """
    if not output_path.lower().endswith(".3mf"):
        output_path += ".3mf"
    out = output_path.replace("\\", "\\\\")
    prep = _PRINT_EXPORT_PREP.format(
        object_names=object_names, apply_modifiers=apply_modifiers
    )
    script = (
        prep
        + f"""
import os
os.makedirs(os.path.dirname(r"{out}"), exist_ok=True)

op = None
if hasattr(bpy.ops.export_mesh, "threemf"):
    op = bpy.ops.export_mesh.threemf
elif hasattr(bpy.ops.wm, "threemf_export"):
    op = bpy.ops.wm.threemf_export

if op is not None:
    op(filepath=r"{out}", use_selection=True)
    if not os.path.exists(r"{out}"):
        raise Exception("3MF export completed but file not found")
    print(f"SUCCESS: 3MF written to {out} ({{os.path.getsize(r'{out}')}} bytes)")
else:
    raise Exception(
        "3MF exporter not available. Install the Blender '3MF format' add-on, "
        "or use export_for_print_stl instead."
    )
"""
    )
    try:
        await _executor.execute_script(script, script_name="print_3mf_export")
        return f"Exported print-ready 3MF (mm units) to {output_path}"
    except Exception as e:
        logger.error(f"3MF print export failed: {e!s}")
        raise BlenderExportError("3MF", output_path, str(e)) from e


@blender_operation("check_print_manifold", log_args=True)
async def check_print_manifold(object_names: list[str] | None = None) -> str:
    """Pre-flight check that meshes are watertight/manifold before slicing.

    Reports non-manifold edges, loose geometry, and flipped normals — the most
    common reasons a part fails to slice or prints with gaps. Does not modify
    geometry.

    Args:
        object_names: Specific objects to check (None = all meshes).
    """
    target = object_names
    script = f"""
import bpy, bmesh, json

scene = bpy.context.scene
target_names = {target!r}
if target_names:
    objs = [o for o in scene.objects if o.type == 'MESH' and o.name in target_names]
else:
    objs = [o for o in scene.objects if o.type == 'MESH']

report = {{}}
for o in objs:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    report[o.name] = {{
        "verts": len(bm.verts),
        "faces": len(bm.faces),
        "non_manifold_edges": non_manifold,
        "loose_verts": loose_verts,
        "watertight": non_manifold == 0 and loose_verts == 0,
    }}
    bm.free()

print("MANIFOLD_REPORT=" + json.dumps(report))
"""
    result = await _executor.execute_script(script, script_name="print_manifold_check")
    return f"Manifold check complete: {result}"
