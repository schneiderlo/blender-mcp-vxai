# Agent operating contract

This repository treats Blender as an authoritative asset runtime, not as a canvas for untracked one-off edits.

When creating or revising an asset, an agent must first edit an asset contract under `examples/` or create a new contract. It must then run the pipeline, inspect the generated diagnostic render, read `validation.json`, and change either the contract or the procedural builder. It must not manually patch `source.blend` and call the result reproducible.

The required loop is:

```text
SPECIFY -> PLAN -> BUILD -> INSPECT -> VALIDATE -> REPAIR -> EXPORT -> ACCEPT
```

`validation.json` is authoritative for technical acceptance. The diagnostic image is authoritative for the visual review. A visual reviewer should report one dominant discrepancy at a time and name the affected object family. A builder should make the smallest parameter or code change that addresses that discrepancy, then regenerate the entire job from an empty scene.

The supplied example can be built with:

```bash
python -m asset_factory.cli build \
  examples/stylized_builder_kit/asset.json \
  --output out/stylized_builder_kit
```

The process must leave behind the contract, plan, event log, Blender source, render, validation report, and game-engine export. These files are the manufacturing record for the asset.
