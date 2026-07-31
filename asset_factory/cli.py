from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blender-asset-factory",
        description="Build, render, validate, and export reproducible Blender assets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Run an asset contract through the Blender pipeline")
    build.add_argument("spec", type=Path, help="Path to an asset contract JSON file")
    build.add_argument("--output", type=Path, required=True, help="Output job directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        from asset_factory.orchestrator import run_pipeline

        manifest = run_pipeline(args.spec, args.output)
        print(json.dumps(manifest, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
