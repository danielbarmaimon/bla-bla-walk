"""Check the canonical API boundary and generated browser validation schema."""

import json
from pathlib import Path

import pytest
from bla_bla_walk.contract_types import typescript_contract
from bla_bla_walk.demo_fixture import fixture_snapshot
from bla_bla_walk.interfaces import MapFeature, MapSnapshot, ShadeRequest, ShadeResponse
from bla_bla_walk.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def test_api_round_trip_preserves_fixture_and_missing_values():
    response = TestClient(app).get("/api/map")
    assert response.status_code == 200
    snapshot = MapSnapshot.model_validate(response.json())
    assert len(snapshot.layers) == 2
    assert {f.availability for layer in snapshot.layers for f in layer.features} == {
        "stale",
        "missing",
        "unknown",
    }
    for layer in snapshot.layers:
        assert all(feature.provenance.fixture for feature in layer.features)
    missing = snapshot.layers[0].features[1]
    assert missing.value is None
    assert missing.provenance.observed_at is None


@pytest.mark.parametrize("coordinates", [[181, 47], [7, 91], [7], [7, 47, 2]])
def test_rejects_invalid_wgs84_positions(coordinates):
    payload = fixture_snapshot().layers[0].features[0].model_dump(mode="json")
    payload["geometry"]["coordinates"] = coordinates
    with pytest.raises(ValidationError):
        MapFeature.model_validate(payload)


def test_rejects_unknown_states_and_undeclared_fields():
    payload = fixture_snapshot().model_dump(mode="json")
    payload["layers"][0]["availability"] = "safe"
    with pytest.raises(ValidationError):
        MapSnapshot.model_validate(payload)
    payload = fixture_snapshot().model_dump(mode="json")
    payload["personal_profile"] = "unexpected"
    with pytest.raises(ValidationError):
        MapSnapshot.model_validate(payload)


def test_timestamps_require_timezones():
    payload = fixture_snapshot().model_dump(mode="json")
    payload["generated_at"] = "2026-10-03T12:00:00"
    with pytest.raises(ValidationError):
        MapSnapshot.model_validate(payload)


def test_generated_schema_matches_canonical_models():
    generated = json.loads((ROOT / "src/snapshot.schema.json").read_text())
    assert generated == MapSnapshot.model_json_schema()


def test_generated_types_and_browser_schema_match_canonical_models():
    schema = MapSnapshot.model_json_schema()
    assert (ROOT / "src/interfaces.ts").read_text() == typescript_contract(schema)
    module = (ROOT / "src/snapshot.schema.js").read_text()
    assert (
        json.loads(module.split("export const snapshotSchema = ", 1)[1][:-2]) == schema
    )


def test_generated_shade_contracts_match_canonical_models_and_coordinates():
    for model, name in ((ShadeRequest, "request"), (ShadeResponse, "response")):
        schema = json.loads((ROOT / f"src/shade-{name}.schema.json").read_text())
        assert schema == model.model_json_schema()
    declarations = (ROOT / "src/shade-interfaces.ts").read_text()
    assert "LV95 (EPSG:2056) processing metres" in declarations
    assert "WGS84" not in declarations
    for model in (ShadeRequest, ShadeResponse):
        assert f"export interface {model.__name__}" in declarations


def test_static_page_and_assets_are_served_without_a_build():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/src/main.js").status_code == 200
    assert client.get("/src/theme.css").status_code == 200
    assert client.get("/vendor/ol.js").status_code == 200


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "LineString", "coordinates": [[7.58, 47.55], [7.59, 47.56]]},
        {
            "type": "Polygon",
            "coordinates": [
                [[7.58, 47.55], [7.59, 47.55], [7.59, 47.56], [7.58, 47.55]]
            ],
        },
    ],
)
def test_contract_accepts_later_route_and_shade_geometry(geometry):
    payload = fixture_snapshot().layers[0].features[0].model_dump(mode="json")
    payload["geometry"] = geometry
    payload["kind"] = "route" if geometry["type"] == "LineString" else "shade"
    assert MapFeature.model_validate(payload).geometry.type == geometry["type"]
