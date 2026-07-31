from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from asset_factory.contract import AssetContract, ContractError, load_contract


class ContractTests(unittest.TestCase):
    def test_example_contract_loads(self) -> None:
        root = Path(__file__).resolve().parents[1]
        contract = load_contract(root / "examples" / "stylized_builder_kit" / "asset.json")
        self.assertEqual(contract.builder, "stylized_builder_kit")
        self.assertGreaterEqual(int(contract.pieces["minimum_primary_objects"]), 20)
        self.assertGreater(int(contract.budgets["max_triangles"]), 0)

    def test_missing_field_fails(self) -> None:
        with self.assertRaises(ContractError):
            AssetContract.from_mapping({"asset_id": "broken"})

    def test_invalid_dimensions_fail(self) -> None:
        data = {
            "asset_id": "broken",
            "builder": "stylized_builder_kit",
            "description": "broken",
            "style": {},
            "pieces": {},
            "budgets": {"max_triangles": 10},
            "render": {"width": 1, "height": 1}
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_contract(path)


if __name__ == "__main__":
    unittest.main()
