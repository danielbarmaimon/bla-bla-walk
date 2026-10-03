"""Address filtering, failures and offline no-network contract."""

from unittest.mock import patch

import httpx
import pytest
from bla_bla_walk.adapters.addresses import inside_basel, search_addresses
from bla_bla_walk.main import app
from fastapi.testclient import TestClient


def result(label, lon=7.606272, lat=47.537456, origin="address"):
    return {"attrs": {"label": label, "lon": lon, "lat": lat, "origin": origin}}


def test_boundary_holes_and_disjoint_parts():
    polygons = [
        [[[0, 0], [4, 0], [4, 4], [0, 4]], [[1, 1], [2, 1], [2, 2], [1, 2]]],
        [[[6, 6], [7, 6], [7, 7], [6, 7]]],
    ]
    assert inside_basel(3, 3, polygons)
    assert inside_basel(6.5, 6.5, polygons)
    assert not inside_basel(1.5, 1.5, polygons)
    assert not inside_basel(5, 5, polygons)


def test_real_boundary_and_plain_labels():
    payload = {
        "results": [
            result("Public venue <b>Basel</b>"),
            result("Outside", 8.54, 47.37),
            result("Not address", origin="gazetteer"),
            result("Bad", "nan"),
        ]
    }

    def handler(request):
        assert request.url.params["origins"] == "address"
        assert request.url.params["sr"] == "2056"
        assert "bbox" in request.url.params
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with patch("bla_bla_walk.adapters.addresses.httpx.Client", return_value=client):
        response = search_addresses("public venue", "online")
    assert len(response.places) == 1
    assert response.places[0].name == "Public venue Basel"
    assert response.places[0].id.startswith("address-")


def test_offline_never_constructs_http_client():
    with patch("bla_bla_walk.adapters.addresses.httpx.Client") as client:
        response = search_addresses("public venue", "offline")
    assert response.status == "unavailable"
    client.assert_not_called()


def test_api_failure_and_bounds():
    client = TestClient(app)
    assert client.post("/api/addresses", json={"query": "x"}).status_code == 422
    with patch(
        "bla_bla_walk.main.search_addresses", side_effect=httpx.ConnectError("down")
    ):
        assert client.post("/api/addresses", json={"query": "venue"}).status_code == 503
    response = client.post("/api/addresses", json={"query": "venue", "mode": "offline"})
    assert response.json()["status"] == "unavailable"
    assert response.headers["cache-control"] == "no-store"


def test_word_limit():
    with pytest.raises(ValueError):
        search_addresses("word " * 11, "online")
