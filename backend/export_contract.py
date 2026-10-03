"""Export schemas and a fixture from the same canonical Python models."""

import json
from pathlib import Path

from bla_bla_walk.contract_types import typescript_contract
from bla_bla_walk.demo_fixture import fixture_snapshot
from bla_bla_walk.interfaces import (
    AddressSearchResponse,
    ComparisonJob,
    ComparisonPreferences,
    ComparisonRequest,
    MapSnapshot,
    ShadeRequest,
    ShadeResponse,
)
from bla_bla_walk.main import app

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    """Write deterministic JSON for generation and cross-language checks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    address_schema = AddressSearchResponse.model_json_schema()
    (ROOT / "src/address-interfaces.ts").write_text(
        typescript_contract(address_schema), encoding="utf-8"
    )
    schema = MapSnapshot.model_json_schema()
    write_json(ROOT / ".cache/openapi.json", app.openapi())
    write_json(ROOT / "src/snapshot.schema.json", schema)
    (ROOT / "src/snapshot.schema.js").write_text(
        "// Generated from canonical Python models. Do not edit by hand.\n"
        + "export const snapshotSchema = "
        + json.dumps(schema, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    (ROOT / "src/interfaces.ts").write_text(
        typescript_contract(schema), encoding="utf-8"
    )
    write_json(ROOT / "src/shade-request.schema.json", ShadeRequest.model_json_schema())
    shade_schema = ShadeResponse.model_json_schema()
    write_json(ROOT / "src/shade-response.schema.json", shade_schema)
    shade_client_schema = {
        **shade_schema,
        "$defs": {
            **shade_schema.get("$defs", {}),
            "ShadeRequest": ShadeRequest.model_json_schema(),
        },
    }
    (ROOT / "src/shade-interfaces.ts").write_text(
        typescript_contract(shade_client_schema, "LV95 (EPSG:2056) processing metres"),
        encoding="utf-8",
    )
    write_json(
        ROOT / ".cache/fixture-snapshot.json",
        fixture_snapshot().model_dump(mode="json"),
    )

    comparison_schema = ComparisonJob.model_json_schema()
    (ROOT / "src/comparison.schema.js").write_text(
        "// Generated from canonical Python models. Do not edit by hand.\n"
        + "export const comparisonJobSchema = "
        + json.dumps(comparison_schema, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    client_schema = {
        **comparison_schema,
        "$defs": {
            **comparison_schema.get("$defs", {}),
            **ComparisonRequest.model_json_schema().get("$defs", {}),
            "ComparisonRequest": ComparisonRequest.model_json_schema(),
            "ComparisonPreferences": ComparisonPreferences.model_json_schema(),
        },
    }
    (ROOT / "src/comparison-interfaces.ts").write_text(
        typescript_contract(client_schema),
        encoding="utf-8",
    )
