from __future__ import annotations

import math
import random
from typing import Any

import bpy

from asset_factory.blender_scene import (
    create_collection,
    create_log,
    create_plank,
    irregular_rock,
    make_solid_material,
    make_stone_material,
    make_wood_material,
    rounded_box,
    setup_presentation,
)
from asset_factory.contract import AssetContract


def _stone_block(
    *,
    contract: AssetContract,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    name: str,
    location: tuple[float, float, float],
    dimensions: tuple[float, float, float],
    seed: int,
    rotation_z: float = 0.0,
) -> bpy.types.Object:
    return rounded_box(
        name=name,
        collection=collection,
        location=location,
        dimensions=dimensions,
        material=material,
        seed=seed,
        bevel=min(dimensions) * 0.18,
        irregularity=min(dimensions) * 0.055,
        rotation=(0.0, 0.0, rotation_z),
        asset_id=contract.asset_id,
        material_class="stone",
    )


def _build_wall(
    *,
    contract: AssetContract,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    prefix: str,
    origin_x: float,
    origin_z: float,
    rows: list[list[float]],
    block_height: float,
    seed: int,
) -> list[bpy.types.Object]:
    rng = random.Random(seed)
    objects: list[bpy.types.Object] = []
    for row_index, widths in enumerate(rows):
        total = sum(widths) + 0.055 * (len(widths) - 1)
        cursor = origin_x - total * 0.5
        for column_index, width in enumerate(widths):
            height = block_height * rng.uniform(0.94, 1.06)
            depth = rng.uniform(0.52, 0.68)
            x = cursor + width * 0.5
            z = origin_z + row_index * (block_height * 0.96) + height * 0.5
            obj = _stone_block(
                contract=contract,
                collection=collection,
                material=material,
                name=f"{prefix}_r{row_index}_c{column_index}",
                location=(x, rng.uniform(-0.035, 0.035), z),
                dimensions=(width, depth, height),
                seed=seed + row_index * 101 + column_index * 17,
                rotation_z=rng.uniform(-0.018, 0.018),
            )
            objects.append(obj)
            cursor += width + 0.055
    return objects


def build(contract: AssetContract) -> dict[str, Any]:
    export_root = create_collection("EXPORT")
    stone_collection = create_collection("EXPORT_STONE", export_root)
    wood_collection = create_collection("EXPORT_WOOD", export_root)
    detail_collection = create_collection("EXPORT_DETAILS", export_root)
    presentation = create_collection("PRESENTATION")

    stone = make_stone_material()
    wood = make_wood_material()
    wood_end = make_solid_material("MAT_Wood_End", (0.64, 0.29, 0.075, 1.0), roughness=0.72)
    grain = make_solid_material("MAT_Wood_Grain", (0.085, 0.022, 0.008, 1.0), roughness=0.86)
    background = make_solid_material("MAT_Background", (0.025, 0.014, 0.010, 1.0), roughness=0.92)

    seed = contract.seed
    rng = random.Random(seed)
    primary: list[bpy.types.Object] = []

    # Top-left stacked stone column.
    primary.append(
        _stone_block(
            contract=contract,
            collection=stone_collection,
            material=stone,
            name="ASSET_Stone_Column_Lower",
            location=(-6.45, 0.0, 4.28),
            dimensions=(1.04, 0.66, 1.35),
            seed=seed + 1,
            rotation_z=-0.015,
        )
    )
    primary.append(
        _stone_block(
            contract=contract,
            collection=stone_collection,
            material=stone,
            name="ASSET_Stone_Column_Upper",
            location=(-6.44, 0.0, 5.53),
            dimensions=(1.00, 0.65, 1.08),
            seed=seed + 2,
            rotation_z=0.025,
        )
    )

    # Small modular wall and larger lower wall.
    primary.extend(
        _build_wall(
            contract=contract,
            collection=stone_collection,
            material=stone,
            prefix="ASSET_Stone_ShortWall",
            origin_x=-4.22,
            origin_z=4.06,
            rows=[[1.15, 0.78, 0.82], [0.82, 1.15, 0.78]],
            block_height=0.92,
            seed=seed + 20,
        )
    )
    primary.extend(
        _build_wall(
            contract=contract,
            collection=stone_collection,
            material=stone,
            prefix="ASSET_Stone_LongWall",
            origin_x=-4.17,
            origin_z=0.55,
            rows=[[1.20, 1.10, 1.18, 0.78], [0.98, 1.24, 1.08, 0.95]],
            block_height=1.00,
            seed=seed + 80,
        )
    )

    # Loose rocks as a reusable rubble mini-kit.
    rock_specs = [
        ((-1.78, 0.02, 5.12), (0.86, 0.54, 0.62), 0.10),
        ((-2.62, 0.01, 4.62), (0.48, 0.38, 0.50), -0.16),
        ((-1.90, -0.02, 4.16), (0.60, 0.44, 0.54), 0.20),
        ((-1.05, 0.02, 4.56), (0.75, 0.48, 0.62), -0.10),
        ((-1.08, -0.01, 5.68), (0.52, 0.38, 0.42), 0.28),
    ]
    for index, (location, dimensions, rotation_z) in enumerate(rock_specs):
        primary.append(
            irregular_rock(
                name=f"ASSET_Stone_Rubble_{index}",
                collection=stone_collection,
                location=location,
                dimensions=dimensions,
                material=stone,
                seed=seed + 150 + index,
                rotation=(rng.uniform(-0.15, 0.15), rng.uniform(-0.12, 0.12), rotation_z),
                asset_id=contract.asset_id,
            )
        )

    # Log bundle. The local log axis tilts away from the camera so both its side and end grain read.
    log_specs = [
        ((1.05, 0.10, 4.42), 0.34, 1.24, (math.radians(54), 0.0, math.radians(-7))),
        ((1.78, 0.16, 4.34), 0.38, 1.35, (math.radians(58), 0.0, math.radians(5))),
        ((2.47, 0.12, 4.44), 0.35, 1.28, (math.radians(52), 0.0, math.radians(-4))),
        ((1.85, -0.02, 5.00), 0.36, 1.50, (math.radians(56), math.radians(8), math.radians(-32))),
    ]
    for index, (location, radius, length, rotation) in enumerate(log_specs):
        primary.append(
            create_log(
                name=f"ASSET_Wood_Log_{index}",
                collection=wood_collection,
                detail_collection=detail_collection,
                location=location,
                radius=radius,
                length=length,
                rotation=rotation,
                bark_material=wood,
                end_material=wood_end,
                grain_material=grain,
                seed=seed + 230 + index,
                asset_id=contract.asset_id,
            )
        )

    # Mixed small bundle with a diagonal plank.
    mixed_logs = [
        ((3.82, 0.12, 4.34), 0.31, 1.18, (math.radians(52), 0.0, math.radians(-4))),
        ((4.50, 0.10, 4.30), 0.31, 1.12, (math.radians(58), 0.0, math.radians(5))),
    ]
    for index, (location, radius, length, rotation) in enumerate(mixed_logs):
        primary.append(
            create_log(
                name=f"ASSET_Wood_MixedLog_{index}",
                collection=wood_collection,
                detail_collection=detail_collection,
                location=location,
                radius=radius,
                length=length,
                rotation=rotation,
                bark_material=wood,
                end_material=wood_end,
                grain_material=grain,
                seed=seed + 280 + index,
                asset_id=contract.asset_id,
            )
        )
    primary.append(
        create_plank(
            name="ASSET_Wood_DiagonalPlank",
            collection=wood_collection,
            detail_collection=detail_collection,
            location=(4.17, -0.10, 4.97),
            dimensions=(2.08, 0.40, 0.39),
            rotation=(math.radians(-3), math.radians(7), math.radians(-28)),
            wood_material=wood,
            grain_material=grain,
            seed=seed + 300,
            asset_id=contract.asset_id,
        )
    )

    # Tall hero beam at the right edge.
    primary.append(
        create_plank(
            name="ASSET_Wood_TallBeam",
            collection=wood_collection,
            detail_collection=detail_collection,
            location=(6.45, 0.0, 3.34),
            dimensions=(0.82, 0.58, 5.50),
            rotation=(0.0, 0.0, math.radians(1.7)),
            wood_material=wood,
            grain_material=grain,
            seed=seed + 330,
            asset_id=contract.asset_id,
            vertical=True,
        )
    )

    # Bottom plank palette: independently reusable lengths and proportions.
    plank_specs = [
        ((0.18, 0.0, 2.22), (1.62, 0.34, 0.36), 0.02),
        ((1.96, 0.0, 2.20), (1.40, 0.34, 0.36), -0.01),
        ((3.45, 0.0, 2.19), (1.05, 0.34, 0.34), 0.01),
        ((0.24, 0.0, 1.52), (1.66, 0.34, 0.38), -0.012),
        ((1.94, 0.0, 1.50), (1.10, 0.34, 0.38), 0.018),
        ((3.22, 0.0, 1.50), (1.52, 0.34, 0.38), -0.006),
        ((0.58, 0.0, 0.82), (2.30, 0.35, 0.40), 0.008),
        ((2.95, 0.0, 0.82), (1.48, 0.35, 0.40), -0.01),
    ]
    for index, (location, dimensions, rotation_z) in enumerate(plank_specs):
        primary.append(
            create_plank(
                name=f"ASSET_Wood_Plank_{index}",
                collection=wood_collection,
                detail_collection=detail_collection,
                location=location,
                dimensions=dimensions,
                rotation=(0.0, 0.0, rotation_z),
                wood_material=wood,
                grain_material=grain,
                seed=seed + 400 + index,
                asset_id=contract.asset_id,
            )
        )

    setup_presentation(
        collection=presentation,
        background_material=background,
        render_width=int(contract.render["width"]),
        render_height=int(contract.render["height"]),
        samples=int(contract.render.get("samples", 24)),
    )

    return {
        "asset_id": contract.asset_id,
        "export_collection": export_root.name,
        "presentation_collection": presentation.name,
        "primary_object_count": len(primary),
        "primary_object_names": [obj.name for obj in primary],
    }
