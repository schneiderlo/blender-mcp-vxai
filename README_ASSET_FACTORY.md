# Blender asset factory MVP

This directory is a working, agent-oriented Blender production loop. It builds assets from machine-readable contracts, renders a diagnostic view, validates the actual Blender scene, saves the authoritative `.blend`, and exports a GLB.

The first real example recreates the design language of the supplied stylized construction-kit image: chunky taupe masonry, warm carved wood, modular walls, loose stones, logs, planks, and a tall beam. It is generated procedurally and reproducibly from `examples/stylized_builder_kit/asset.json`.

Run it with Python 3.13 and Blender's official Python module:

```bash
python -m pip install bpy==5.2.0
python -m asset_factory.cli build \
  examples/stylized_builder_kit/asset.json \
  --output out/stylized_builder_kit
```

The GitHub Actions workflow performs the same build in a clean Ubuntu runner and uploads the complete job directory.
