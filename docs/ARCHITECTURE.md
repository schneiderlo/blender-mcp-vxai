# Agentic Blender asset factory

The factory is a durable state machine around Blender. The language model is allowed to propose a contract, choose or implement a procedural builder, and visually review diagnostic renders. It is not allowed to decide that an asset is technically valid. Blender-state inspection and deterministic validation make that decision.

The first implementation deliberately uses procedural construction. Mechanical, modular, destructible, collision-sensitive, and dimension-sensitive assets benefit from named components and reproducible topology. Neural image-to-3D generation can later be added as another builder route, but its output must enter the same inspection, validation, repair, and export stages.

Each job starts from an empty scene. The builder creates an `EXPORT` collection and a separate `PRESENTATION` collection. Only `EXPORT` is written to the GLB. This prevents lights, cameras, backdrops, and review-only helpers from leaking into the game asset.

The example builder turns the visual language of the supplied image into a parameterized kit: softened irregular blocks, modular walls, rubble, logs with visible end grain, individual planks, and a tall beam. Decorative grain is geometry in the proof-of-concept so that the GLB retains the style without a texture bake. A production version should bake that detail into base-color and normal maps, generate LODs, and replace detail geometry at distance.

## Extension points

A new asset family adds a JSON contract and a builder registered in `asset_factory/builders/__init__.py`. A neural generator can be integrated by writing its draft into Blender and then returning the same build report. Additional validators can enforce UV coverage, texel density, collider limits, rig conventions, attachment points, and engine-specific metadata.

The existing Blender MCP server remains useful for interactive inspection and bounded repair. The reproducible CLI is the production path; MCP edits should be promoted back into builder code or contract parameters before acceptance.
