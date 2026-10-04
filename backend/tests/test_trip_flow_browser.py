"""T30 role selection and truthful pending/unavailable states; synthetic UI jobs."""

from datetime import UTC, datetime

import pytest
from bla_bla_walk.adapters.routes import load_demo_routes
from bla_bla_walk.interfaces import MapSnapshot
from conftest import open_example
from test_journey_browser import wire_calculation

pytestmark = pytest.mark.browser


def test_supported_roles_open_map_and_keep_steps_below(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))

    def capture_map(route):
        response = route.fetch()
        route.fulfill(
            response=response,
            body=response.text()
            + """
          const NativeMap=ol.Map;
          ol.Map=class extends NativeMap {
            constructor(...args){super(...args);window.tripFlowMap=this;}
          };
        """,
        )

    page.route("**/vendor/ol.js", capture_map)
    _, requests = wire_calculation(page)
    layer = load_demo_routes().model_copy(deep=True)
    layer.features[1].route.duration_s = layer.features[0].route.duration_s + 600
    snapshot = MapSnapshot(
        mode="fixture", generated_at=datetime.now(UTC), layers=[layer]
    )
    page.route(
        "**/api/map?mode=fixture",
        lambda route: route.fulfill(json=snapshot.model_dump(mode="json")),
    )
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page)
    page.wait_for_function("!document.querySelector('#shade-mode').disabled")
    assert page.locator("#fast-mode").inner_text() == "Fast"
    assert (
        page.locator("#fast-mode img").get_attribute("src").endswith("fast-forward.svg")
    )
    assert "distinct routes" in page.locator("#route-role-status").inner_text()
    assert (
        page.locator(".comparison-card.is-selected h3").inner_text()
        == layer.features[0].label
    )
    page.locator("#shade-mode").click()
    assert page.locator(".map-screen").is_visible()
    assert page.locator("#shade-mode").get_attribute("aria-pressed") == "true"
    drawn = page.evaluate("""() => {
      const map=window.tripFlowMap;
      const ids=[];
      let inside=true;
      const size=map.getSize();
      map.getLayers().forEach(layer=>{
        layer.getSource()?.getFeatures?.().forEach(feature=>{
          if (!['demo-route-a','demo-route-b'].includes(feature.getId())) return;
          if (!layer.getStyleFunction()(feature)) return;
          ids.push(feature.getId());
          if (feature.getId()==='demo-route-b')
            feature.getGeometry().getCoordinates().forEach(c=>{
            const p=map.getPixelFromCoordinate(c);
            inside=inside && p[0]>=0 && p[0]<=size[0] && p[1]>=0 && p[1]<=size[1];
          });
        });
      });
      return {ids,inside};
    }""")
    assert set(drawn["ids"]) == {"demo-route-a", "demo-route-b"}
    assert drawn["inside"]
    assert "unavailable" in page.locator("#step-list").inner_text()
    assert page.locator(".steps").bounding_box()["y"] >= (
        page.locator(".map-wrap").bounding_box()["y"]
        + page.locator(".map-wrap").bounding_box()["height"]
    )
    assert page.locator("#basemap-status").is_visible()  # actual tile failure retained
    page.locator("#back-to-plan").click()
    page.locator("#fast-mode").click()
    assert page.locator("#fast-mode").get_attribute("aria-pressed") == "true"
    assert (
        sum(
            method == "POST" and not url.endswith("/rescore")
            for method, url in requests
        )
        == 1
    )
    badge = page.locator("#fast-route-toggle")
    badge.focus()
    assert badge.evaluate("e=>getComputedStyle(e).textDecorationLine") == "none"
    assert badge.evaluate("e=>getComputedStyle(e).textAlign") == "center"
    page.keyboard.press("Space")
    assert badge.get_attribute("aria-pressed") == "false"
    assert not errors
    page.unroute("**/api/comparison**")
    page.unroute("**/api/map?mode=fixture")
    page.unroute("**/vendor/ol.js", capture_map)


def test_real_counts_tips_and_cancel_clear_evidence(browser_page):
    page = browser_page
    wire_calculation(page)
    # Hold the poll so the test observes the API's running state, not a timer guess.
    pending = []
    page.route(
        "**/api/comparison/synthetic-browser-validation",
        lambda route: (
            route.fulfill(status=204)
            if route.request.method == "DELETE"
            else pending.append(route)
        ),
    )
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page)
    page.wait_for_function(
        "document.querySelector('#trip-status').textContent.includes('0 of')"
    )
    assert "0 of" in page.locator("#trip-status").inner_text()
    assert page.locator("#preparation-tips").is_visible()
    assert page.locator("#trip-tips li").count() == 4
    page.locator("#cancel-journey").click()
    assert page.locator("#preparation-tips").is_hidden()
    assert page.locator("#comparison-evidence").inner_text() == ""
    assert page.locator("#calculate-journey").is_enabled()
    for route in pending:
        route.fulfill(status=503, json={"detail": "Cancelled test poll"})
    page.unroute("**/api/comparison/synthetic-browser-validation")
    page.unroute("**/api/comparison**")


def test_missing_shade_withholds_recommended_and_allows_manual_map(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page)
    assert page.locator("#shade-mode").is_disabled()
    assert "Recommended unavailable" in page.locator("#route-role-status").inner_text()
    page.locator(".comparison-secondary").last.click()
    assert page.locator(".map-screen").is_visible()
    assert "unavailable" in page.locator("#step-list").inner_text()
    page.locator("#information-sources").evaluate("e=>e.open=true")
    assert (
        page.locator("#tip-sources a").get_attribute("href")
        == "https://www.bag.admin.ch/en/heat"
    )
    assert "avoidance unavailable" in page.locator("#construction-status").inner_text()
    page.screenshot(path="/tmp/t30-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path="/tmp/t30-mobile.png", full_page=True)


@pytest.mark.parametrize("supported", [False, True])
def test_one_route_and_same_route_roles_are_explicit(browser_page, supported):
    page = browser_page
    if supported:
        wire_calculation(page)
    else:
        page.route(
            "**/api/comparison**",
            lambda route: route.fulfill(
                status=503, json={"detail": "Missing prepared inputs"}
            ),
        )
    layer = load_demo_routes().model_copy(deep=True)
    layer.features = layer.features[1:]
    snapshot = MapSnapshot(
        mode="fixture", generated_at=datetime.now(UTC), layers=[layer]
    )
    page.route(
        "**/api/map?mode=fixture",
        lambda route: route.fulfill(json=snapshot.model_dump(mode="json")),
    )
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page)
    if supported:
        page.wait_for_function("!document.querySelector('#shade-mode').disabled")
        assert (
            page.locator("#route-role-status").inner_text()
            == "Fast and Recommended use the same route."
        )
    else:
        assert (
            "One walking route available"
            in page.locator("#route-role-status").inner_text()
        )
        assert page.locator("#shade-mode").is_disabled()
    assert page.locator(".comparison-card").count() == 1
    page.unroute("**/api/map?mode=fixture")
    page.unroute("**/api/comparison**")


@pytest.mark.parametrize("pair_index", [0, 1])
def test_dated_real_provider_payload_in_joined_screen(browser_page, pair_index):
    """Replay freshly checked local API replies; never treat saved output as live."""
    import json
    from pathlib import Path

    path = Path(".cache/t30-checked-payloads.json")
    if not path.exists():
        pytest.skip("Needs local checked T30 provider replies; see handoff/T30.md")
    layer = json.loads(path.read_text())[pair_index]
    endpoints = [
        ([7.590209, 47.548055], [7.588921, 47.558082]),
        (
            [7.602287769317627, 47.56437301635742],
            [7.594012260437012, 47.554317474365234],
        ),
    ][pair_index]
    page = browser_page
    requests = []

    def addresses(route):
        is_start = route.request.post_data_json["query"] == "Checked public start"
        point = endpoints[0 if is_start else 1]
        route.fulfill(
            json={
                "places": [
                    {
                        "id": "checked-start" if is_start else "checked-end",
                        "name": "Checked public start"
                        if is_start
                        else "Checked public destination",
                        "lon": point[0],
                        "lat": point[1],
                    }
                ],
                "status": "available",
            }
        )

    def walking(route):
        if route.request.method != "POST":
            route.continue_()
            return
        requests.append(route.request.post_data_json)
        route.fulfill(json=layer)

    page.route("**/api/addresses", addresses)
    page.route("**/api/walking-routes", walking)
    page.goto(page.base_url + "/?mode=fixture")
    page.locator("#origin-input:not([disabled])").wait_for()
    page.locator("#origin-input").fill("Checked public start")
    page.locator("#origin-suggestions button").click()
    page.locator("#destination-input").fill("Checked public destination")
    page.locator("#suggestions button").click()
    page.locator("#calculate-journey").click()
    page.locator("#information-sources").evaluate("e=>e.open=true")
    page.locator(".comparison-secondary").first.wait_for()
    assert requests[0]["start"] == endpoints[0]
    assert requests[0]["end"] == endpoints[1]
    assert page.locator("#shade-mode").is_disabled()
    for feature in layer["features"]:
        page.locator(f'.comparison-secondary[data-route-id="{feature["id"]}"]').click()
        instructions = page.locator("#step-list").inner_text()
        assert "Directions unavailable" not in instructions
        for step in feature["directions"]["steps"]:
            assert step["text"] in instructions
        assert feature["directions"]["route_id"] == feature["id"]
        assert "selected destination" in instructions
        page.locator("#back-to-plan").click()
    assert len(requests) == 1
    page.locator("#departure-later").click()
    assert page.locator("#step-list").inner_text() == ""
    page.unroute("**/api/addresses", addresses)
    page.unroute("**/api/walking-routes", walking)
