"""Endpoint routing: actual network geometry, rate limits and unavailable cases."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bla_bla_walk.adapters.walking import reserve_request, walking_routes
from bla_bla_walk.interfaces import WalkingRouteRequest
from bla_bla_walk.main import app

START = (7.590209, 47.548055)
END = (7.606272, 47.537456)
COORDINATES = [START, (7.599, 47.541), END]


@pytest.fixture(autouse=True)
def local_evidence_only():
    with (
        patch("bla_bla_walk.adapters.walking.detour_routes", return_value=[]),
        patch("bla_bla_walk.walking_preferences.construction_sites", return_value=None),
        patch("bla_bla_walk.walking_preferences.shade_fraction", return_value=None),
    ):
        yield


def payload():
    return {
        "code": "Ok",
        "waypoints": [{"distance": 2}, {"distance": 3}],
        "routes": [
            {
                "distance": 2100,
                "geometry": {"type": "LineString", "coordinates": COORDINATES},
            }
        ],
    }


def test_network_line_and_time_preserve_unknowns():
    with patch("bla_bla_walk.adapters.walking.fetch_routes", return_value=payload()):
        layer = walking_routes(WalkingRouteRequest(start=START, end=END))
    route = layer.features[0]
    assert route.geometry.coordinates == COORDINATES
    assert route.route.distance_m == 2100
    assert route.route.duration_s == 2100
    assert route.availability == "unknown"
    assert "shade" in route.explanation
    assert not route.provenance.fixture


def test_offline_and_outside_never_call_provider():
    with patch("bla_bla_walk.adapters.walking.fetch_routes") as provider:
        with pytest.raises(OSError):
            walking_routes(WalkingRouteRequest(start=START, end=END, mode="offline"))
        with pytest.raises(ValueError):
            walking_routes(WalkingRouteRequest(start=START, end=(8.54, 47.37)))
        with pytest.raises(ValueError):
            walking_routes(WalkingRouteRequest(start=START, end=START))
    provider.assert_not_called()


@pytest.mark.parametrize("change", ["no_route", "snap", "distance", "geometry"])
def test_bad_provider_evidence_rejected(change):
    value = payload()
    if change == "no_route":
        value["code"] = "NoRoute"
    elif change == "snap":
        value["waypoints"][0]["distance"] = 1000
    elif change == "distance":
        value["routes"][0]["distance"] = -1
    else:
        value["routes"][0]["geometry"]["coordinates"] = [START]
    with patch("bla_bla_walk.adapters.walking.fetch_routes", return_value=value):
        with pytest.raises(OSError):
            walking_routes(WalkingRouteRequest(start=START, end=END))


def test_rate_limit_and_api_status():
    with (
        patch("bla_bla_walk.adapters.walking._last_request", 100),
        patch("bla_bla_walk.adapters.walking.time.monotonic", return_value=100.5),
    ):
        with pytest.raises(OverflowError):
            reserve_request(1)
    client = TestClient(app)
    with patch(
        "bla_bla_walk.main.provider_walking_routes", side_effect=OverflowError("busy")
    ):
        reply = client.post("/api/walking-routes", json={"start": START, "end": END})
    assert reply.status_code == 429
    assert reply.headers["retry-after"] == "1"
    reply = client.post(
        "/api/walking-routes", json={"start": START, "end": END, "mode": "offline"}
    )
    assert reply.status_code == 503
