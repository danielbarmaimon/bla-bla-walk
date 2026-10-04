"""Provider maneuvers stay bound to their geometry and never fill missing turns."""

from copy import deepcopy
from unittest.mock import patch

import httpx
import pytest
from bla_bla_walk.adapters.walking import fetch_routes, walking_routes
from bla_bla_walk.instructions import instruction_text, provider_directions
from bla_bla_walk.interfaces import WalkingRouteRequest
from test_walking_routing import COORDINATES, END, START, payload


def maneuver_route():
    route = payload()["routes"][0]
    route["legs"] = [
        {
            "steps": [
                {
                    "distance": 1000,
                    "name": "First street",
                    "maneuver": {"type": "depart", "location": START},
                },
                {
                    "distance": 1100,
                    "name": "",
                    "maneuver": {
                        "type": "turn",
                        "modifier": "left",
                        "location": COORDINATES[1],
                    },
                },
                {
                    "distance": 0,
                    "name": "",
                    "maneuver": {"type": "arrive", "location": END},
                },
            ]
        }
    ]
    return route


def test_order_distance_and_route_identity():
    routes = [maneuver_route(), deepcopy(maneuver_route())]
    routes[1]["geometry"]["coordinates"] = [START, (7.60, 47.54), END]
    routes[1]["legs"][0]["steps"][1]["maneuver"]["location"] = (7.60, 47.54)
    value = payload()
    value["routes"] = routes
    with patch("bla_bla_walk.adapters.walking.fetch_routes", return_value=value):
        features = walking_routes(WalkingRouteRequest(start=START, end=END)).features
    assert features[0].id != features[1].id
    for feature in features:
        assert feature.directions.route_id == feature.id
        steps = feature.directions.steps
        assert [s.kind for s in steps] == ["start", "turn", "arrive"]
        assert [s.at_metres for s in steps] == [0, 1000, 2100]
        assert sum(s.duration_s for s in steps) == feature.route.duration_s
        assert steps[1].text == (
            "Turn left. After First street; towards the selected destination"
        )
        assert "selected destination" in steps[-1].text


@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "partial",
        "wrong_geometry",
        "nan",
        "wrong_total",
        "unsupported",
        "bad_name",
        "reversed",
        "wrong_start",
        "wrong_arrival",
    ],
)
def test_unavailable_instead_of_invented_steps(change):
    route = maneuver_route()
    if change == "missing":
        route.pop("legs")
    elif change == "partial":
        route["legs"][0]["steps"].pop()
    elif change == "wrong_geometry":
        route["legs"][0]["steps"][1]["maneuver"]["location"] = (8, 48)
    elif change == "nan":
        route["legs"][0]["steps"][0]["distance"] = float("nan")
    elif change == "wrong_total":
        route["distance"] = 3000
    elif change == "bad_name":
        route["legs"][0]["steps"][1]["name"] = 123
    elif change == "wrong_start":
        route["legs"][0]["steps"][0]["maneuver"]["location"] = COORDINATES[1]
    elif change == "wrong_arrival":
        route["legs"][0]["steps"][-1]["maneuver"]["location"] = COORDINATES[1]
    elif change == "reversed":
        route["legs"][0]["steps"].insert(
            2,
            {
                "distance": 0,
                "name": "",
                "maneuver": {
                    "type": "continue",
                    "location": START,
                },
            },
        )
    else:
        route["legs"][0]["steps"][1]["maneuver"]["type"] = "future maneuver"
    assert provider_directions(route, "test-route", 1) is None


def test_roundabout_continue_and_unnamed_exit():
    assert instruction_text({"type": "continue", "modifier": "uturn"}, None) == (
        "Make a U-turn",
        "turn",
    )
    assert instruction_text({"type": "roundabout", "exit": 3}, "Ring")[0] == (
        "At the roundabout, take exit 3 on Ring"
    )
    assert instruction_text({"type": "roundabout"}, None)[0] == (
        "Follow the roundabout"
    )
    assert instruction_text({"type": "continue", "modifier": "straight"}, "Road") == (
        "Continue straight on Road",
        "continue",
    )


def test_provider_request_includes_steps():
    observed = []

    def reply(request):
        observed.append(request)
        return httpx.Response(200, json=payload())

    client = httpx.Client(transport=httpx.MockTransport(reply))
    with patch("bla_bla_walk.adapters.walking.httpx.Client", return_value=client):
        fetch_routes(
            WalkingRouteRequest(start=START, end=END),
            {
                "minimum_request_interval_seconds": 0,
                "timeout_seconds": 1,
                "user_agent": "test",
                "endpoint": "https://example.com/route",
                "max_response_bytes": 100000,
            },
        )
    assert observed[0].url.params["steps"] == "true"
    assert observed[0].url.params["overview"] == "full"


def test_missing_names_use_route_streets_without_renaming_segments():
    route = maneuver_route()
    steps = route["legs"][0]["steps"]
    steps[0]["name"] = ""
    steps[1]["name"] = "Hammerstrasse"
    result = provider_directions(route, "test", 1)
    assert result.steps[0].text == (
        "Start walking. Route continues to Hammerstrasse in 1000 m"
    )
    assert result.steps[0].street_name is None
    assert result.steps[1].street_name == "Hammerstrasse"
    assert "unnamed" not in " ".join(s.text for s in result.steps)
    assert result.steps[-1].text == "Arrive at the selected destination"


def test_provider_road_reference_is_preserved_without_guessing_a_name():
    route = maneuver_route()
    route["legs"][0]["steps"][1]["ref"] = "Mapped road reference"
    result = provider_directions(route, "test", 1)
    assert result.steps[1].street_name == "Mapped road reference"
    assert result.steps[1].text == "Turn left on Mapped road reference"
