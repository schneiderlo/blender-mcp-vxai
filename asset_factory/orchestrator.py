from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import bpy

from asset_factory.blender_scene import export_glb, render_still, reset_scene, save_blend
from asset_factory.builders import get_builder
from asset_factory.contract import AssetContract, load_contract
from asset_factory.validation import validate_scene, write_validation


class Stage(str, Enum):
    SPECIFY = "SPECIFY"
    PLAN = "PLAN"
    BUILD = "BUILD"
    INSPECT = "INSPECT"
    VALIDATE = "VALIDATE"
    REPAIR = "REPAIR"
    EXPORT = "EXPORT"
    ACCEPT = "ACCEPT"
    FAILED = "FAILED"


@dataclass
class EventLog:
    path: Path

    def emit(self, stage: Stage, message: str, **data: Any) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "time_unix": time.time(),
            "stage": stage.value,
            "message": message,
            "data": data,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")


def make_plan(contract: AssetContract) -> dict[str, Any]:
    return {
        "asset_id": contract.asset_id,
        "builder": contract.builder,
        "seed": contract.seed,
        "route": "procedural_blender",
        "stages": [stage.value for stage in Stage if stage not in {Stage.REPAIR, Stage.FAILED}],
        "acceptance": {
            "max_triangles": int(contract.budgets["max_triangles"]),
            "minimum_primary_objects": int(contract.pieces.get("minimum_primary_objects", 1)),
            "required_outputs": ["source.blend", "asset_kit.glb", "diagnostics/beauty.png", "validation.json"],
        },
        "agent_notes": [
            "Inspect diagnostics/beauty.png after every build.",
            "Prefer contract parameter changes over destructive edits to source.blend.",
            "Treat validation.json as authoritative for technical acceptance.",
        ],
    }


def _generic_repair(export_collection_name: str) -> list[str]:
    """Apply safe repairs that do not change the intended silhouette."""
    collection = bpy.data.collections.get(export_collection_name)
    if collection is None:
        return []
    repaired: list[str] = []
    for obj in collection.all_objects:
        if obj.type != "MESH":
            continue
        if any(abs(float(scale) - 1.0) > 1.0e-4 for scale in obj.scale):
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            repaired.append(f"applied scale on {obj.name}")
    return repaired


def run_pipeline(spec_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    events = EventLog(output / "events.jsonl")

    contract = load_contract(spec_path)
    events.emit(Stage.SPECIFY, "Loaded asset contract", asset_id=contract.asset_id, spec=str(spec_path))

    plan = make_plan(contract)
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    events.emit(Stage.PLAN, "Created deterministic production plan", builder=contract.builder)

    reset_scene()
    builder = get_builder(contract.builder)
    events.emit(Stage.BUILD, "Starting Blender construction")
    build_report = builder(contract)
    (output / "build_report.json").write_text(json.dumps(build_report, indent=2) + "\n", encoding="utf-8")
    events.emit(Stage.BUILD, "Blender construction complete", **build_report)

    camera = bpy.context.scene.camera
    if camera is not None and camera.type == "CAMERA" and "ortho_scale" in contract.render:
        camera.data.ortho_scale = float(contract.render["ortho_scale"])
        events.emit(Stage.PLAN, "Applied contract camera framing", ortho_scale=camera.data.ortho_scale)

    render_path = output / "diagnostics" / "beauty.png"
    events.emit(Stage.INSPECT, "Rendering diagnostic beauty view", path=str(render_path))
    render_still(render_path)
    events.emit(Stage.INSPECT, "Diagnostic render complete", bytes=render_path.stat().st_size)

    export_collection_name = str(build_report["export_collection"])
    events.emit(Stage.VALIDATE, "Running deterministic Blender-state validation")
    validation = validate_scene(contract, export_collection_name)
    write_validation(validation, output / "validation.json")

    if validation["status"] != "pass":
        events.emit(Stage.REPAIR, "Validation failed; applying bounded generic repair", failures=validation["failures"])
        repairs = _generic_repair(export_collection_name)
        validation = validate_scene(contract, export_collection_name)
        validation["repairs"] = repairs
        write_validation(validation, output / "validation.json")
        if validation["status"] != "pass":
            events.emit(Stage.FAILED, "Asset failed validation after repair", failures=validation["failures"])
            save_blend(output / "failed_source.blend")
            raise RuntimeError("Asset validation failed: " + "; ".join(validation["failures"]))

    events.emit(Stage.EXPORT, "Saving authoritative Blender source")
    blend_path = save_blend(output / "source.blend")
    export_collection = bpy.data.collections[export_collection_name]
    glb_path = export_glb(output / "asset_kit.glb", export_collection.all_objects)
    events.emit(
        Stage.EXPORT,
        "Export complete",
        blend_bytes=blend_path.stat().st_size,
        glb_bytes=glb_path.stat().st_size,
    )

    manifest = {
        "status": "accepted",
        "asset_id": contract.asset_id,
        "blender_version": bpy.app.version_string,
        "contract": Path(spec_path).name,
        "outputs": {
            "blend": "source.blend",
            "glb": "asset_kit.glb",
            "beauty": "diagnostics/beauty.png",
            "validation": "validation.json",
            "plan": "plan.json",
            "events": "events.jsonl",
        },
        "metrics": validation["metrics"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    events.emit(Stage.ACCEPT, "Asset accepted", metrics=validation["metrics"])
    return manifest
