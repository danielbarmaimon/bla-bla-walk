"""Fastest effort, evidence-based recommendation and honest shared-path choices."""

import base64
import json
import math
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from shapely.geometry import LineString

from bla_bla_walk.adapters.routes import load_demo_routes
from bla_bla_walk.interfaces import ShadeState
from bla_bla_walk.walking_preferences import (
    ROOT,
    choose_routes,
    construction_sites,
    shade_fraction,
)

DEPARTURE = datetime(2026, 10, 4, 12, tzinfo=UTC)
SETTINGS = json.loads((ROOT / "config/walking-routing.json").read_text())


def choices():
    features = load_demo_routes().features
    features[0].route.duration_s = 900
    features[1].route.duration_s = 1200
    return features


def test_shadier_longer_recommendation_preserves_fast_route():
    features = choices()
    with (
        patch("bla_bla_walk.walking_preferences.construction_sites", return_value=[]),
        patch(
            "bla_bla_walk.walking_preferences.shade_fraction", side_effect=[0.1, 0.8]
        ),
    ):
        fast, recommended = choose_routes(features, DEPARTURE, SETTINGS)
    assert fast.id == features[0].id
    assert recommended.id == features[1].id
    assert recommended.route_role == "recommended"
    assert "80%" in recommended.explanation


def test_construction_caution_takes_priority_over_shade():
    features = choices()
    # A site at an exclusive point of the second candidate, away from route one.
    first_line = LineString(features[0].geometry.coordinates)
    second_line = LineString(features[1].geometry.coordinates)
    point = max(
        (second_line.interpolate(i / 100, normalized=True) for i in range(101)),
        key=lambda p: first_line.distance(p),
    )
    site = point.buffer(first_line.distance(point) / 3)
    with (
        patch(
            "bla_bla_walk.walking_preferences.construction_sites", return_value=[site]
        ),
        patch("bla_bla_walk.walking_preferences.shade_fraction", return_value=0.2),
    ):
        fast, recommended = choose_routes(features, DEPARTURE, SETTINGS)
    assert recommended.geometry == fast.geometry
    assert "share the same path" in recommended.explanation
    assert "Avoids the loaded" in recommended.explanation
    if recommended.directions:
        assert recommended.directions.route_id == recommended.id


def test_single_path_still_returns_two_honestly_labelled_choices():
    with (
        patch("bla_bla_walk.walking_preferences.construction_sites", return_value=None),
        patch("bla_bla_walk.walking_preferences.shade_fraction", return_value=None),
    ):
        fast, recommended = choose_routes(choices()[:1], DEPARTURE, SETTINGS)
    assert fast.id != recommended.id
    assert fast.geometry == recommended.geometry
    assert "provisional" in recommended.explanation
    assert "avoidance unverified" in recommended.explanation


def sample_service(first_state):
    class LocalSamples:
        def sample(self, request, points):
            west, south, east, north = request.bounds
            width, height = int(east - west), int(north - south)
            values = bytearray(width * height)
            x, y = points[0]
            values[math.floor(north - y) * width + math.floor(x - west)] = first_state
            return SimpleNamespace(
                bounds=request.bounds, width=width, states=base64.b64encode(values)
            )

    return LocalSamples


def test_sparse_positive_shade_never_credits_unknown_samples():
    route = choices()[0]
    route.geometry.coordinates = [(7.59, 47.55), (7.5905, 47.55)]
    settings = {**SETTINGS, "shade_max_samples": 2}
    with patch(
        "bla_bla_walk.walking_preferences.ShadeService",
        sample_service(ShadeState.SHADED),
    ):
        assert shade_fraction(route, DEPARTURE, settings) == 0.5
    with patch(
        "bla_bla_walk.walking_preferences.ShadeService",
        sample_service(ShadeState.NIGHT),
    ):
        assert shade_fraction(route, DEPARTURE, settings) is None


def test_missing_permit_geometry_withholds_avoidance_claim():
    projects = MagicMock()
    projects.json.return_value = {"total_count": 1, "results": [{"id": 123}]}
    permits = MagicMock()
    permits.json.return_value = {"total_count": 1, "results": [{"geo_shape": None}]}
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.side_effect = [projects, permits]
    with patch("bla_bla_walk.walking_preferences.httpx.Client", return_value=client):
        assert construction_sites(DEPARTURE, SETTINGS) is None
    assert client.get.call_args_list[0].kwargs["params"]["select"] == "id"
    assert client.get.call_args_list[1].kwargs["params"]["select"] == "geo_shape"


def test_construction_intervals_use_basel_date_near_midnight():
    projects = MagicMock()
    projects.json.return_value = {"total_count": 0, "results": []}
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.return_value = projects
    with patch("bla_bla_walk.walking_preferences.httpx.Client", return_value=client):
        assert (
            construction_sites(datetime(2026, 10, 3, 22, 30, tzinfo=UTC), SETTINGS)
            == []
        )
    assert "2026-10-04" in client.get.call_args.kwargs["params"]["where"]
