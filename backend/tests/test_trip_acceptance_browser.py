"""T31 joined-flow acceptance: replayed evidence stays explicitly synthetic or saved."""

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from bla_bla_walk.adapters.walking import walking_routes
from bla_bla_walk.interfaces import WalkingRouteRequest
from conftest import open_example
from test_journey_browser import wire_calculation
from test_journey_instructions import maneuver_route
from test_walking_routing import payload

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.browser


def arbitrary_layer(start, end, first_street, second_street):
    """Build a provider-shaped, clearly synthetic layer for browser flow checks."""
    routes = []
    for index, midpoint in enumerate(((7.599, 47.541), (7.6005, 47.542))):
        route = deepcopy(maneuver_route())
        route["geometry"]["coordinates"] = [list(start), list(midpoint), list(end)]
        steps = route["legs"][0]["steps"]
        steps[0]["maneuver"]["location"] = list(start)
        steps[0]["name"] = first_street
        steps[1]["maneuver"]["location"] = list(midpoint)
        steps[1]["name"] = (
            second_street if index == 0 else f"{second_street} alternative"
        )
        steps[-1]["maneuver"]["location"] = list(end)
        routes.append(route)
    provider_reply = {**payload(), "routes": routes}
    with patch(
        "bla_bla_walk.adapters.walking.fetch_routes", return_value=provider_reply
    ):
        return walking_routes(
            WalkingRouteRequest(start=tuple(start), end=tuple(end))
        ).model_dump(mode="json")


def test_saved_pair_switching_time_and_source_status(browser_page):
    """The saved pair switches honestly, clears on time changes and exposes sources."""
    page = browser_page
    wire_calculation(page)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(page.base_url)
    open_example(page)
    assert page.locator("#route-options .comparison-secondary").count() == 2
    for card in page.locator("#route-options .comparison-secondary").all():
        card.click()
        assert "Directions unavailable" in page.locator("#step-list").inner_text()
    page.locator("#information-sources").evaluate("element => element.open = true")
    assert "avoidance unavailable" in page.locator("#construction-status").inner_text()
    assert page.locator("#tip-sources a").get_attribute("href") == (
        "https://www.bag.admin.ch/en/heat"
    )
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    if page.locator("#departure-later").is_hidden():
        page.locator("#back-to-plan").click()
    page.locator("#departure-later").click()
    page.locator("#departure-time").fill("2026-10-04T14:00")
    assert page.locator("#selected-journey").is_hidden()
    assert page.locator("#route-options").inner_text() == ""
    page.set_viewport_size({"width": 1280, "height": 900})
    page.locator("#fast-route-toggle").focus()
    page.keyboard.press("Space")
    assert page.locator("#fast-route-toggle").get_attribute("aria-pressed") == "false"


@pytest.mark.parametrize(
    "start,end,first_street,second_street",
    [
        (
            [7.6022877, 47.564373],
            [7.5940122, 47.554317],
            "Rosentalstrasse",
            "Hammerstrasse",
        ),
        (
            [7.590209, 47.548055],
            [7.606272, 47.537456],
            "Centralbahnplatz",
            "Steinenvorstadt",
        ),
    ],
)
def test_two_arbitrary_pairs_keep_route_steps_and_retry(
    browser_page, start, end, first_street, second_street
):
    """Two pairs retry once, then keep route-bound steps on selection."""
    page = browser_page
    layer = arbitrary_layer(start, end, first_street, second_street)
    requests = []

    def addresses(route):
        query = route.request.post_data_json["query"]
        place = {
            "id": "arbitrary-start" if "start" in query.lower() else "arbitrary-end",
            "name": "Checked arbitrary start"
            if "start" in query.lower()
            else "Checked arbitrary destination",
            "lon": start[0] if "start" in query.lower() else end[0],
            "lat": start[1] if "start" in query.lower() else end[1],
        }
        route.fulfill(json={"places": [place], "status": "available"})

    def walking(route):
        if route.request.method == "POST":
            requests.append(route.request.post_data_json)
            if len(requests) == 1:
                route.fulfill(status=503, json={"detail": "Synthetic provider failure"})
            else:
                route.fulfill(json=layer)
        else:
            route.continue_()

    page.route("**/api/addresses", addresses)
    page.route("**/api/walking-routes", walking)
    page.goto(page.base_url)
    page.locator("#origin-input").fill("Checked arbitrary start")
    page.locator("#origin-suggestions button").click()
    page.locator("#destination-input").fill("Checked arbitrary destination")
    page.locator("#suggestions button").click()
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#trip-status').textContent.includes('unavailable')"
    )
    page.locator("#calculate-journey").click()
    page.locator("#information-sources").evaluate("e=>e.open=true")
    page.locator("#route-options .comparison-secondary").first.wait_for()
    assert len(requests) == 2
    for feature in layer["features"]:
        page.locator(f'.comparison-secondary[data-route-id="{feature["id"]}"]').click()
        text = page.locator("#step-list").inner_text()
        assert "Directions unavailable" not in text
        assert "selected destination" in text
        assert feature["directions"]["route_id"] == feature["id"]
    if page.locator("#departure-later").is_hidden():
        page.locator("#back-to-plan").click()
    page.locator("#departure-later").click()
    page.locator("#departure-time").fill("2026-10-04T15:00")
    assert page.locator("#selected-journey").is_hidden()
    page.unroute("**/api/addresses", addresses)
    page.unroute("**/api/walking-routes", walking)


def test_saved_fallback_is_local_dated_and_has_no_external_requests(browser_page):
    """The local fallback is labelled saved and loads without any network request."""
    fallback = ROOT / ".hack" / "t31-fallback" / "index.html"
    assert fallback.exists()
    page = browser_page
    external = []
    page.on(
        "request",
        lambda request: (
            external.append(request.url) if request.url.startswith("http") else None
        ),
    )
    page.goto(fallback.as_uri())
    assert "SAVED FALLBACK" in page.locator("body").inner_text()
    assert "not live" in page.locator("body").inner_text()
    assert page.locator("tbody tr").count() == 2
    assert not external
