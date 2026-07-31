from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Matrix, Vector


Color = tuple[float, float, float, float]


def reset_scene() -> None:
    """Remove all scene objects and non-master collections without changing preferences."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene_root = bpy.context.scene.collection
    for collection in list(bpy.data.collections):
        if collection != scene_root:
            bpy.data.collections.remove(collection)
    for datablocks in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def create_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def activate_object(obj: bpy.types.Object) -> None:
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_transform(obj: bpy.types.Object, *, rotation: bool = False) -> None:
    activate_object(obj)
    bpy.ops.object.transform_apply(location=False, rotation=rotation, scale=True)


def set_custom_properties(obj: bpy.types.Object, *, asset_id: str, role: str, material_class: str) -> None:
    obj["asset_id"] = asset_id
    obj["asset_role"] = role
    obj["material_class"] = material_class
    obj["collision_hint"] = "box" if material_class in {"stone", "wood"} else "none"


def _principled(material: bpy.types.Material) -> tuple[bpy.types.NodeTree, bpy.types.Node, bpy.types.Node]:
    material.use_nodes = True
    material.node_tree.nodes.clear()
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    output.location = (430, 0)
    shader.location = (150, 0)
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material.node_tree, shader, output


def make_stone_material(name: str = "MAT_Stone") -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = (0.42, 0.37, 0.30, 1.0)
    tree, shader, _ = _principled(material)
    nodes = tree.nodes
    links = tree.links

    tex = nodes.new("ShaderNodeTexNoise")
    tex.location = (-520, 80)
    tex.inputs["Scale"].default_value = 2.6
    tex.inputs["Detail"].default_value = 2.2
    tex.inputs["Roughness"].default_value = 0.72
    tex.inputs["Distortion"].default_value = 0.14

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-250, 100)
    ramp.color_ramp.elements[0].position = 0.22
    ramp.color_ramp.elements[0].color = (0.16, 0.14, 0.12, 1.0)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.57, 0.51, 0.42, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-80, -110)
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.08

    shader.inputs["Roughness"].default_value = 0.78
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def make_wood_material(name: str = "MAT_Wood") -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = (0.48, 0.22, 0.075, 1.0)
    tree, shader, _ = _principled(material)
    nodes = tree.nodes
    links = tree.links

    tex = nodes.new("ShaderNodeTexNoise")
    tex.location = (-500, 70)
    tex.inputs["Scale"].default_value = 3.8
    tex.inputs["Detail"].default_value = 3.0
    tex.inputs["Roughness"].default_value = 0.70
    tex.inputs["Distortion"].default_value = 0.32

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-235, 90)
    ramp.color_ramp.elements[0].position = 0.20
    ramp.color_ramp.elements[0].color = (0.20, 0.065, 0.018, 1.0)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.73, 0.34, 0.095, 1.0)

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-70, -120)
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.055

    shader.inputs["Roughness"].default_value = 0.64
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def make_solid_material(name: str, color: Color, roughness: float = 0.7) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    _, shader, _ = _principled(material)
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Roughness"].default_value = roughness
    return material


def rounded_box(
    *,
    name: str,
    collection: bpy.types.Collection,
    location: Sequence[float],
    dimensions: Sequence[float],
    material: bpy.types.Material,
    seed: int,
    bevel: float,
    irregularity: float,
    rotation: Sequence[float] = (0.0, 0.0, 0.0),
    asset_id: str,
    role: str = "primary",
    material_class: str = "stone",
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, collection)
    obj.dimensions = tuple(float(v) for v in dimensions)
    apply_transform(obj)

    modifier = obj.modifiers.new(name="Softened silhouette", type="BEVEL")
    modifier.width = min(float(bevel), min(float(v) for v in dimensions) * 0.28)
    modifier.segments = 2
    modifier.limit_method = "ANGLE"
    activate_object(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    rng = random.Random(seed)
    mesh = obj.data
    amplitude = float(irregularity)
    for vertex in mesh.vertices:
        outward = vertex.co.normalized() if vertex.co.length_squared > 1.0e-10 else Vector((0.0, 0.0, 1.0))
        vertex.co += outward * rng.uniform(-amplitude, amplitude)
        vertex.co.x += rng.uniform(-amplitude * 0.22, amplitude * 0.22)
        vertex.co.z += rng.uniform(-amplitude * 0.16, amplitude * 0.16)
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True

    obj.data.materials.append(material)
    obj.rotation_euler = tuple(float(v) for v in rotation)
    set_custom_properties(obj, asset_id=asset_id, role=role, material_class=material_class)
    return obj


def irregular_rock(
    *,
    name: str,
    collection: bpy.types.Collection,
    location: Sequence[float],
    dimensions: Sequence[float],
    material: bpy.types.Material,
    seed: int,
    rotation: Sequence[float],
    asset_id: str,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.5, location=location)
    obj = bpy.context.object
    obj.name = name
    move_to_collection(obj, collection)
    obj.dimensions = tuple(float(v) for v in dimensions)
    apply_transform(obj)

    rng = random.Random(seed)
    for vertex in obj.data.vertices:
        radial = 1.0 + rng.uniform(-0.14, 0.12)
        vertex.co *= radial
        vertex.co.z += rng.uniform(-0.045, 0.045)
    obj.data.update()
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.materials.append(material)
    obj.rotation_euler = tuple(float(v) for v in rotation)
    set_custom_properties(obj, asset_id=asset_id, role="primary", material_class="stone")
    return obj


def _curve_mesh(
    *,
    name: str,
    collection: bpy.types.Collection,
    points: Sequence[Sequence[float]],
    material: bpy.types.Material,
    bevel_depth: float,
    parent: bpy.types.Object | None = None,
    cyclic: bool = False,
    asset_id: str,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name=f"{name}_Curve", type="CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_resolution = 1
    curve.bevel_depth = float(bevel_depth)
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coordinate in zip(spline.points, points):
        point.co = (*map(float, coordinate), 1.0)
    spline.use_cyclic_u = cyclic

    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = Matrix.Identity(4)
    activate_object(obj)
    bpy.ops.object.convert(target="MESH")
    set_custom_properties(obj, asset_id=asset_id, role="detail", material_class="painted_detail")
    obj["collision_hint"] = "none"
    return obj


def add_plank_grain(
    *,
    plank: bpy.types.Object,
    collection: bpy.types.Collection,
    dimensions: Sequence[float],
    material: bpy.types.Material,
    seed: int,
    asset_id: str,
    vertical: bool = False,
) -> list[bpy.types.Object]:
    length, depth, height = map(float, dimensions)
    rng = random.Random(seed)
    details: list[bpy.types.Object] = []
    if vertical:
        y = -depth * 0.5 - 0.012
        for index, x_offset in enumerate((-0.18, 0.16)):
            points = []
            for step in range(9):
                t = step / 8.0
                z = -height * 0.42 + t * height * 0.84
                x = x_offset * length + math.sin(t * math.tau * 1.35 + index) * length * 0.055
                points.append((x, y, z))
            details.append(
                _curve_mesh(
                    name=f"{plank.name}_grain_{index}",
                    collection=collection,
                    points=points,
                    material=material,
                    bevel_depth=max(0.008, min(length, height) * 0.012),
                    parent=plank,
                    asset_id=asset_id,
                )
            )
    else:
        y = -depth * 0.5 - 0.012
        for index, z_offset in enumerate((-0.16, 0.15)):
            phase = rng.uniform(0.0, math.tau)
            points = []
            for step in range(11):
                t = step / 10.0
                x = -length * 0.43 + t * length * 0.86
                z = z_offset * height + math.sin(t * math.tau * 1.45 + phase) * height * 0.12
                points.append((x, y, z))
            details.append(
                _curve_mesh(
                    name=f"{plank.name}_grain_{index}",
                    collection=collection,
                    points=points,
                    material=material,
                    bevel_depth=max(0.007, height * 0.035),
                    parent=plank,
                    asset_id=asset_id,
                )
            )

        knot_center = (length * rng.uniform(-0.16, 0.20), y - 0.002, height * rng.uniform(-0.12, 0.12))
        points = []
        for step in range(14):
            angle = math.tau * step / 14.0
            points.append(
                (
                    knot_center[0] + math.cos(angle) * length * 0.055,
                    knot_center[1],
                    knot_center[2] + math.sin(angle) * height * 0.15,
                )
            )
        details.append(
            _curve_mesh(
                name=f"{plank.name}_knot",
                collection=collection,
                points=points,
                material=material,
                bevel_depth=max(0.007, height * 0.03),
                parent=plank,
                cyclic=True,
                asset_id=asset_id,
            )
        )
    return details


def create_plank(
    *,
    name: str,
    collection: bpy.types.Collection,
    detail_collection: bpy.types.Collection,
    location: Sequence[float],
    dimensions: Sequence[float],
    rotation: Sequence[float],
    wood_material: bpy.types.Material,
    grain_material: bpy.types.Material,
    seed: int,
    asset_id: str,
    vertical: bool = False,
) -> bpy.types.Object:
    plank = rounded_box(
        name=name,
        collection=collection,
        location=location,
        dimensions=dimensions,
        material=wood_material,
        seed=seed,
        bevel=min(dimensions) * 0.20,
        irregularity=min(dimensions) * 0.055,
        rotation=rotation,
        asset_id=asset_id,
        role="primary",
        material_class="wood",
    )
    add_plank_grain(
        plank=plank,
        collection=detail_collection,
        dimensions=dimensions,
        material=grain_material,
        seed=seed + 13,
        asset_id=asset_id,
        vertical=vertical,
    )
    return plank


def create_log(
    *,
    name: str,
    collection: bpy.types.Collection,
    detail_collection: bpy.types.Collection,
    location: Sequence[float],
    radius: float,
    length: float,
    rotation: Sequence[float],
    bark_material: bpy.types.Material,
    end_material: bpy.types.Material,
    grain_material: bpy.types.Material,
    seed: int,
    asset_id: str,
) -> bpy.types.Object:
    rng = random.Random(seed)
    segments = 12
    rings = 5
    vertices: list[tuple[float, float, float]] = []
    phase = rng.uniform(0.0, math.tau)
    centers: list[tuple[float, float]] = []
    for ring_index in range(rings):
        t = ring_index / (rings - 1)
        y = -length * 0.5 + length * t
        wobble_x = math.sin(t * math.tau + phase) * radius * 0.055
        wobble_z = math.cos(t * math.tau * 0.75 + phase) * radius * 0.045
        centers.append((wobble_x, wobble_z))
        taper = 1.0 - 0.045 * abs(t - 0.5) * 2.0
        for segment in range(segments):
            angle = math.tau * segment / segments
            radial = radius * taper * (
                1.0
                + math.sin(angle * 3.0 + phase) * 0.035
                + rng.uniform(-0.035, 0.035)
            )
            vertices.append(
                (
                    wobble_x + math.cos(angle) * radial,
                    y,
                    wobble_z + math.sin(angle) * radial * 0.95,
                )
            )

    faces: list[tuple[int, ...]] = []
    for ring_index in range(rings - 1):
        for segment in range(segments):
            nxt = (segment + 1) % segments
            a = ring_index * segments + segment
            b = ring_index * segments + nxt
            c = (ring_index + 1) * segments + nxt
            d = (ring_index + 1) * segments + segment
            faces.append((a, b, c, d))

    front_center = len(vertices)
    vertices.append((centers[0][0], -length * 0.5, centers[0][1]))
    back_center = len(vertices)
    vertices.append((centers[-1][0], length * 0.5, centers[-1][1]))
    for segment in range(segments):
        nxt = (segment + 1) % segments
        faces.append((front_center, nxt, segment))
        a = (rings - 1) * segments + segment
        b = (rings - 1) * segments + nxt
        faces.append((back_center, a, b))

    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    log = bpy.data.objects.new(name, mesh)
    collection.objects.link(log)
    log.location = tuple(float(v) for v in location)
    log.rotation_euler = tuple(float(v) for v in rotation)
    mesh.materials.append(bark_material)
    mesh.materials.append(end_material)
    side_count = (rings - 1) * segments
    for index, polygon in enumerate(mesh.polygons):
        polygon.material_index = 0 if index < side_count else 1
        polygon.use_smooth = index < side_count

    bevel = log.modifiers.new(name="Chipped bark edge", type="BEVEL")
    bevel.width = radius * 0.055
    bevel.segments = 1
    bevel.limit_method = "ANGLE"
    activate_object(log)
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    set_custom_properties(log, asset_id=asset_id, role="primary", material_class="wood")

    front_y = -length * 0.5 - 0.012
    for ring_index, ring_radius in enumerate((radius * 0.30, radius * 0.58)):
        points = []
        for step in range(16):
            angle = math.tau * step / 16.0
            points.append((math.cos(angle) * ring_radius, front_y, math.sin(angle) * ring_radius * 0.90))
        _curve_mesh(
            name=f"{name}_end_ring_{ring_index}",
            collection=detail_collection,
            points=points,
            material=grain_material,
            bevel_depth=max(0.007, radius * 0.035),
            parent=log,
            cyclic=True,
            asset_id=asset_id,
        )
    for crack_index, angle in enumerate((0.15, 2.25, 4.4)):
        length_factor = (0.28, 0.42, 0.34)[crack_index]
        points = [
            (0.0, front_y - 0.002, 0.0),
            (
                math.cos(angle) * radius * length_factor,
                front_y - 0.002,
                math.sin(angle) * radius * length_factor,
            ),
        ]
        _curve_mesh(
            name=f"{name}_end_crack_{crack_index}",
            collection=detail_collection,
            points=points,
            material=grain_material,
            bevel_depth=max(0.006, radius * 0.026),
            parent=log,
            asset_id=asset_id,
        )
    return log


def look_at(obj: bpy.types.Object, target: Sequence[float]) -> None:
    direction = Vector(tuple(float(v) for v in target)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_area_light(
    *,
    name: str,
    collection: bpy.types.Collection,
    location: Sequence[float],
    target: Sequence[float],
    energy: float,
    size: float,
    color: Sequence[float],
) -> bpy.types.Object:
    data = bpy.data.lights.new(name=f"{name}_Data", type="AREA")
    data.energy = float(energy)
    data.shape = "DISK"
    data.size = float(size)
    data.color = tuple(float(v) for v in color)
    light = bpy.data.objects.new(name, data)
    collection.objects.link(light)
    light.location = tuple(float(v) for v in location)
    look_at(light, target)
    return light


def setup_presentation(
    *,
    collection: bpy.types.Collection,
    background_material: bpy.types.Material,
    render_width: int,
    render_height: int,
    samples: int,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 2.8, 3.5), rotation=(math.pi * 0.5, 0.0, 0.0))
    backdrop = bpy.context.object
    backdrop.name = "PRESENTATION_Backdrop"
    backdrop.scale = (9.5, 5.8, 1.0)
    apply_transform(backdrop)
    move_to_collection(backdrop, collection)
    backdrop.data.materials.append(background_material)
    backdrop["validation_skip"] = True

    camera_data = bpy.data.cameras.new("PRESENTATION_Camera_Data")
    camera = bpy.data.objects.new("PRESENTATION_Camera", camera_data)
    collection.objects.link(camera)
    camera.location = (0.0, -19.5, 5.4)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 8.55
    camera_data.lens = 70.0
    look_at(camera, (0.0, 0.0, 3.45))
    bpy.context.scene.camera = camera

    add_area_light(
        name="PRESENTATION_Key",
        collection=collection,
        location=(-4.5, -7.0, 10.0),
        target=(0.0, 0.0, 3.1),
        energy=1050.0,
        size=5.0,
        color=(1.0, 0.58, 0.30),
    )
    add_area_light(
        name="PRESENTATION_Fill",
        collection=collection,
        location=(6.5, -5.5, 6.0),
        target=(0.0, 0.0, 3.3),
        energy=520.0,
        size=6.0,
        color=(0.32, 0.48, 1.0),
    )
    add_area_light(
        name="PRESENTATION_Rim",
        collection=collection,
        location=(1.5, 2.2, 9.0),
        target=(0.0, 0.0, 3.5),
        energy=820.0,
        size=4.0,
        color=(1.0, 0.42, 0.16),
    )

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = int(render_width)
    scene.render.resolution_y = int(render_height)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True

    # Keep the Cycles settings valid as a deterministic fallback for headless runners.
    scene.cycles.samples = max(8, int(samples))
    scene.cycles.use_denoising = True

    world = bpy.data.worlds.new("PRESENTATION_World") if not scene.world else scene.world
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.018, 0.012, 0.009, 1.0)
        background.inputs["Strength"].default_value = 0.20

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = 0.65
    return camera


def render_still(output_path: str | Path) -> Path:
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.filepath = str(path)
    try:
        bpy.ops.render.render(write_still=True)
    except Exception:
        # Eevee can be unavailable in minimal headless environments. Cycles CPU is slower,
        # but it has no dependency on an interactive viewport.
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        bpy.ops.render.render(write_still=True)
    return path


def save_blend(output_path: str | Path) -> Path:
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), check_existing=False)
    return path


def export_glb(output_path: str | Path, objects: Iterable[bpy.types.Object]) -> Path:
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    selected = [obj for obj in objects if obj.type in {"MESH", "EMPTY"}]
    if not selected:
        raise RuntimeError("No exportable objects were provided")
    for obj in selected:
        obj.hide_render = False
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next((obj for obj in selected if obj.type == "MESH"), selected[0])
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )
    return path
