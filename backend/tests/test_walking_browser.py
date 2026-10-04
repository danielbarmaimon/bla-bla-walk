"""Changed endpoint routes replace the example line and draw network geometry."""

from unittest.mock import patch

import pytest
from bla_bla_walk.adapters.walking import walking_routes
from bla_bla_walk.interfaces import WalkingRouteRequest
from conftest import open_example
from test_walking_routing import COORDINATES, END, START, payload

pytestmark = pytest.mark.browser


def test_address_route_drawn_and_replaced(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    with patch("bla_bla_walk.adapters.walking.fetch_routes", return_value=payload()):
        layer = walking_routes(WalkingRouteRequest(start=START, end=END)).model_dump(
            mode="json"
        )
    page.route(
        "**/api/addresses",
        lambda route: route.fulfill(
            json={
                "places": [
                    {
                        "id": "address-test",
                        "name": "Public venue · Basel",
                        "lon": END[0],
                        "lat": END[1],
                    }
                ],
                "status": "available",
            }
        ),
    )
    requests = []

    def provider(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json=layer)

    page.route(
        "**/api/walking-routes",
        lambda route: (
            provider(route) if route.request.method == "POST" else route.continue_()
        ),
    )
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.wait_for_function(
        "window.ol && document.querySelector('#mode-notice')"
        ".textContent.includes('Example mode')"
    )
    page.evaluate("""() => {
      const original = window.ol.Map.prototype.addLayer;
      window.ol.Map.prototype.addLayer = function(layer) {
        const features = layer.getSource?.()?.getFeatures?.();
        const lines = features?.filter(
          f=>f.getGeometry().getType()==='LineString');
        if (lines?.length) window.drawnRoutes=lines.map(
          f=>f.getGeometry().getCoordinates().map(c=>window.ol.proj.toLonLat(c)));
        return original.call(this,layer);
      };
    }""")
    page.locator("#destination-input").fill("Public venue")
    page.locator("#suggestions button").click()
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#journey-summary').textContent.includes('street-following')"
    )
    assert requests[-1]["end"] == list(END)
    drawn = page.evaluate("window.drawnRoutes[0]")
    assert len(drawn) == len(COORDINATES)
    assert drawn[-1] == pytest.approx(END)
    page.locator("#information-sources").evaluate("e=>e.open=true")
    assert "2,100" in page.locator("#route-options").inner_text()
    assert page.locator("#calculate-journey").is_enabled()
    page.locator("#try-example").dispatch_event("click")
    page.locator("#calculate-journey").click()
    assert (
        "checked walking alternatives" in page.locator("#journey-summary").inner_text()
    )
    assert "Public venue" not in page.locator("#route-options").inner_text()
    assert not errors


def test_failed_new_route_has_no_demo_line(browser_page):
    page = browser_page
    page.route(
        "**/api/addresses",
        lambda route: route.fulfill(
            json={
                "places": [
                    {
                        "id": "address-test",
                        "name": "Public venue",
                        "lon": END[0],
                        "lat": END[1],
                    }
                ],
                "status": "available",
            }
        ),
    )
    page.route(
        "**/api/walking-routes",
        lambda route: (
            route.fulfill(status=503, json={"detail": "unavailable"})
            if route.request.method == "POST"
            else route.continue_()
        ),
    )
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.locator("#destination-input").fill("Public venue")
    page.locator("#suggestions button").click()
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#journey-summary')"
        ".textContent.includes('Walking route unavailable')"
    )
    assert page.locator("#route-options").inner_text() == ""
    assert page.locator("#calculate-journey").is_enabled()


def test_late_response_and_offline_never_overwrite_current_route(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#nearby-summary').textContent.includes('Route stops')"
        " && document.querySelector('#mode-notice')"
        ".textContent.includes('Example mode')"
    )
    page.wait_for_load_state("networkidle")
    result = page.evaluate("""async () => {
      const {walkingRouting} = await import('/src/walking-routing.js');
      const original = window.fetch;
      const pending = [];
      const received = [];
      window.fetch = () => new Promise(resolve => pending.push(resolve));
      const wait = () => new Promise(resolve => setTimeout(resolve,20));
      const loader = walkingRouting('online',{debounce_ms:0},
        layer => {if(layer) received.push(layer.id);});
      loader.start([7.59,47.54],[7.60,47.55]); await wait();
      loader.start([7.59,47.54],[7.61,47.56]); await wait();
      pending[1](new Response(JSON.stringify({id:'new',features:[]})));
      await wait();
      pending[0](new Response(JSON.stringify({id:'old',features:[]})));
      await wait();
      const count = pending.length;
      const offline = walkingRouting('offline',{debounce_ms:0},()=>{});
      offline.start([7.59,47.54],[7.61,47.56]); await wait();
      window.fetch = original;
      return {received, noOfflineRequest:pending.length===count};
    }""")
    assert result == {"received": ["new"], "noOfflineRequest": True}
