# Tested example: stylized modular builder kit

The example is designed from the visual properties of the supplied reference rather than by tracing or embedding the source image. It includes two stone wall arrangements, a stacked column, loose rubble, an exposed-end log bundle, a mixed log-and-plank bundle, a tall timber beam, and eight reusable plank variants.

The automated job produces:

- `source.blend`, the authoritative editable scene;
- `asset_kit.glb`, containing only exportable asset geometry;
- `diagnostics/beauty.png`, the visual-review view;
- `validation.json`, containing mesh counts, triangle counts, manifold checks, scale checks, and material checks;
- `events.jsonl`, a complete state-transition log;
- `manifest.json`, the accepted output inventory.

The GitHub Actions workflow installs the official Blender Python module, constructs the scene in a clean process, renders it, validates it, exports it, and uploads the complete output directory as an artifact. This is a real Blender execution test rather than a static script check.
