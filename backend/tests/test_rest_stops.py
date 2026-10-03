"""Sanitized saved candidates and offline source behaviour."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

from bla_bla_walk.adapters.rest_stops import rest_stops
from bla_bla_walk.main import app
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "prepare_rest_stops", ROOT / "scripts/prepare_rest_stops.py"
)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


def test_sanitize_and_boundary(tmp_path):
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lon": 7.606272,
                "lat": 47.537456,
                "tags": {
                    "amenity": "bench",
                    "name": "Do not retain",
                    "contact:email": "synthetic@example.com",
                },
            },
            {
                "type": "node",
                "id": 2,
                "lon": 8.54,
                "lat": 47.37,
                "tags": {"amenity": "bench"},
            },
            {
                "type": "way",
                "id": 3,
                "center": {"lon": 7.606272, "lat": 47.537456},
                "tags": {"leisure": "park"},
            },
        ]
    }
    layer = preparation.prepare(payload)
    assert [item.rest_type for item in layer.features] == ["bench", "park"]
    text = layer.model_dump_json()
    assert "Do not retain" not in text and "contact:email" not in text
    assert "centre" in layer.features[1].label
    path = tmp_path / "stops.json"
    path.write_text(text, encoding="utf-8")
    assert len(rest_stops(path).features) == 2
    assert rest_stops(tmp_path / "missing.json").availability == "missing"


def test_offline_and_example_stop_api_has_zero_outbound_http():
    with patch(
        "httpx.HTTPTransport.handle_request", side_effect=AssertionError("external")
    ) as transport:
        client = TestClient(app)
        for mode in ("offline", "fixture"):
            reply = client.get(f"/api/route-amenities?mode={mode}")
            assert reply.status_code == 200
            for layer in reply.json().values():
                assert all(
                    not feature["provenance"]["fixture"]
                    for feature in layer["features"]
                )
    transport.assert_not_called()
