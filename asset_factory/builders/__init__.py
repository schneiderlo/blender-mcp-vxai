from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asset_factory.contract import AssetContract

Builder = Callable[[AssetContract], dict[str, Any]]


def get_builder(name: str) -> Builder:
    if name == "stylized_builder_kit":
        from .stylized_builder_kit import build

        return build
    raise KeyError(f"Unknown asset builder: {name}")
