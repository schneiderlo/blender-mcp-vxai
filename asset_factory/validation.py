from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import bmesh
import bpy

from asset_factory.contract import AssetContract


def _is_finite_vector(values: tuple[float, ...]) -> bool:
    return all(math.isfinite(float(value)) for value in values)


def validate_scene(contract: AssetContract, export_collection_name: str) -> dict[str, Any]:
    collection = bpy.data.collections.get(export_collection_name)
    if collection is None:
        raise RuntimeError(f"Missing export collection: {export_collection_name}")

    objects = list(collection.all_objects)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    primary = [obj for obj in meshes if obj.get("asset_role") == "primary"]
    details = [obj for obj in meshes if obj.get("asset_role") == "detail"]

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    warnings: list[str] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        if not passed:
            failures.append(f"{name}: {detail}")

    min_primary = int(contract.pieces.get("minimum_primary_objects", 1))
    check(
        "minimum_primary_objects",
        len(primary) >= min_primary,
        f"found {len(primary)}, required at least {min_primary}",
    )

    names = [obj.name for obj in objects]
    check("unique_names", len(names) == len(set(names)), f"{len(names)} export objects")

    triangle_count = 0
    vertex_count = 0
    non_manifold_primary = 0
    empty_materials: list[str] = []
    invalid_bounds: list[str] = []
    invalid_scales: list[str] = []

    for obj in meshes:
        mesh = obj.data
        mesh.calc_loop_triangles()
        triangle_count += len(mesh.loop_triangles)
        vertex_count += len(mesh.vertices)
        if len(obj.material_slots) == 0:
            empty_materials.append(obj.name)
        if not _is_finite_vector(tuple(obj.dimensions)) or min(obj.dimensions) <= 1.0e-5:
            invalid_bounds.append(obj.name)
        if any(abs(float(scale) - 1.0) > 1.0e-4 for scale in obj.scale):
            invalid_scales.append(obj.name)
        if obj.get("asset_role") == "primary":
            bm = bmesh.new()
            bm.from_mesh(mesh)
            non_manifold_primary += sum(1 for edge in bm.edges if not edge.is_manifold)
            bm.free()

    max_triangles = int(contract.budgets["max_triangles"])
    check("triangle_budget", triangle_count <= max_triangles, f"{triangle_count} / {max_triangles} triangles")
    check("materials_assigned", not empty_materials, ", ".join(empty_materials) or "all mesh objects have materials")
    check("valid_bounds", not invalid_bounds, ", ".join(invalid_bounds) or "all bounds are finite and non-zero")
    check("unit_scale", not invalid_scales, ", ".join(invalid_scales) or "all object scales are applied")
    check(
        "primary_meshes_manifold",
        non_manifold_primary == 0,
        f"{non_manifold_primary} non-manifold primary edges",
    )

    if details:
        warnings.append(
            "Decorative grain is geometry in this proof-of-concept so the GLB preserves the style without a texture bake. "
            "A production pipeline should bake it into normal/base-color maps for distant LODs."
        )

    return {
        "status": "pass" if not failures else "fail",
        "asset_id": contract.asset_id,
        "blender_version": bpy.app.version_string,
        "metrics": {
            "export_objects": len(objects),
            "mesh_objects": len(meshes),
            "primary_mesh_objects": len(primary),
            "detail_mesh_objects": len(details),
            "vertices": vertex_count,
            "triangles": triangle_count,
            "materials": len({slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}),
        },
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
    }


def write_validation(report: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
