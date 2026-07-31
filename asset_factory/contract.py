from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ContractError(ValueError):
    """Raised when an asset contract is malformed."""


@dataclass(frozen=True)
class AssetContract:
    asset_id: str
    builder: str
    seed: int
    description: str
    style: Mapping[str, Any]
    pieces: Mapping[str, Any]
    budgets: Mapping[str, Any]
    render: Mapping[str, Any]
    raw: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "AssetContract":
        required = ("asset_id", "builder", "description", "style", "pieces", "budgets", "render")
        missing = [key for key in required if key not in data]
        if missing:
            raise ContractError(f"Missing required contract fields: {', '.join(missing)}")

        asset_id = str(data["asset_id"]).strip()
        builder = str(data["builder"]).strip()
        if not asset_id:
            raise ContractError("asset_id must not be empty")
        if not builder:
            raise ContractError("builder must not be empty")

        seed = int(data.get("seed", 0))
        budgets = _require_mapping(data["budgets"], "budgets")
        render = _require_mapping(data["render"], "render")
        style = _require_mapping(data["style"], "style")
        pieces = _require_mapping(data["pieces"], "pieces")

        max_triangles = int(budgets.get("max_triangles", 0))
        if max_triangles <= 0:
            raise ContractError("budgets.max_triangles must be a positive integer")
        width = int(render.get("width", 0))
        height = int(render.get("height", 0))
        if width < 64 or height < 64:
            raise ContractError("render width and height must both be at least 64")

        return cls(
            asset_id=asset_id,
            builder=builder,
            seed=seed,
            description=str(data["description"]).strip(),
            style=style,
            pieces=pieces,
            budgets=budgets,
            render=render,
            raw=dict(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return dict(self.raw)


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    return value


def load_contract(path: str | Path) -> AssetContract:
    contract_path = Path(path)
    try:
        data = json.loads(contract_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractError(f"Contract does not exist: {contract_path}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in {contract_path}: {exc}") from exc
    if not isinstance(data, Mapping):
        raise ContractError("The contract root must be a JSON object")
    return AssetContract.from_mapping(data)
