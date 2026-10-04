"""Independent route visibility, equal tap controls and planned rest cadence."""

import pytest
from conftest import open_example

pytestmark = pytest.mark.browser


def test_badge_defaults_and_layout(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page)
    page.locator("#information-sources").evaluate("e=>e.open=false")
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Example mode')"
    )
    page.locator(".comparison-secondary").first.dispatch_event("click")
    assert page.locator(".map-controls input[type=checkbox]").count() == 0
    assert page.locator("#primary-layers [aria-pressed=true]").count() == 6
    assert not page.locator("#more-layers").evaluate("e=>e.open")
    assert not page.locator("#information-sources").evaluate("e=>e.open")
    assert page.locator("#primary-layers button").all_text_contents() == [
        "Temperature",
        "Fast route",
        "Recommended",
        "Water",
        "Bench",
        "Rest",
    ]
    dimensions = page.locator("#primary-layers button").evaluate_all(
        "buttons=>buttons.map(b=>[b.offsetWidth,b.offsetHeight])"
    )
    assert len({tuple(size) for size in dimensions}) == 1
    page.locator("#fast-route-toggle").click()
    assert page.locator("#fast-route-toggle").get_attribute("aria-pressed") == "false"
    assert (
        page.locator("#recommended-route-toggle").get_attribute("aria-pressed")
        == "true"
    )
    page.locator("#bench-stop-toggle").focus()
    page.keyboard.press("Space")
    assert page.locator("#bench-stop-toggle").get_attribute("aria-pressed") == "false"
    page.locator("#back-to-plan").click()
    page.locator("#departure-time").evaluate(
        "e=>{e.value='2026-10-04T12:00';"
        "e.dispatchEvent(new Event('input',{bubbles:true}));}"
    )
    page.locator("#calculate-journey").click()
    page.locator(".comparison-secondary").first.dispatch_event("click")
    page.locator("#more-layers").evaluate("e=>e.open=true")
    page.locator("#preparation-tips").evaluate("e=>e.close()")
    page.locator("#cool-place-toggle").click()
    assert page.locator("#interior-list-section").evaluate("e=>!e.hidden")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not errors


def test_route_roles_rest_cadence_and_schedules(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    result = page.evaluate("""async()=>{
      const {visibleRouteIds}=await import('/src/layer-badges.js');
      const {plannedRestStops}=await import('/src/route-amenities.js');
      const {routeGeometry}=await import('/src/route-planner-data.js');
      const {scheduledOpen}=await import('/src/supermarket-hours.js');
      const settings=await(await fetch('/config/route-stops.json')).json();
      const routes=[{id:'fast',route:{duration_s:1800}},
        {id:'recommended',route:{duration_s:2100}}];
      const route=routeGeometry([[7.59,47.55],[7.63,47.55]]);
      const rests=plannedRestStops(route,2701,15);
      const opening='Mo-Fr 06:00-22:00; Sa-Su 07:30-22:00; PH off';
      const check=time=>scheduledOpen(opening,new Date(time),settings.public_holidays);
      return {fast:visibleRouteIds(routes,'recommended',true,false),
        recommended:visibleRouteIds(routes,'recommended',false,true),
        withheld:visibleRouteIds(routes,null,false,true),
        restMinutes:rests.map(s=>s.walk_minutes),
        latitudes:rests.map(s=>s.coordinates[1]),
        open:check('2026-10-04T10:00:00Z'),
        closed:check('2026-10-04T21:00:00Z'),
        holiday:check('2026-12-25T10:00:00Z'),
        override:scheduledOpen('Mo-Fr 07:00-20:00; Mo 09:00-18:00',
          new Date('2026-10-05T06:00:00Z'),settings.public_holidays),
        unknown:scheduledOpen('sunrise-sunset',
          new Date('2026-10-04T10:00:00Z'),settings.public_holidays)};
    }""")
    assert result["fast"] == ["fast"]
    assert result["recommended"] == ["recommended"]
    assert result["withheld"] == []
    assert result["restMinutes"] == [15, 30, 45]
    assert result["latitudes"] == [47.55] * 3
    assert result["open"] and not result["closed"]
    assert not result["holiday"] and not result["unknown"]
    assert not result["override"]


def test_more_badges_control_all_source_points_independently(browser_page):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    snapshot = page.request.get(f"{page.base_url}/api/map?mode=fixture").json()
    stations = next(
        layer for layer in snapshot["layers"] if layer["kind"] == "observation"
    )
    fountains = next(
        layer for layer in snapshot["layers"] if layer["kind"] == "fountain"
    )
    assert stations["features"] and fountains["features"]
    page.route(
        "**/api/route-temperatures?*", lambda route: route.fulfill(json=stations)
    )
    page.route(
        "**/api/route-amenities?*",
        lambda route: route.fulfill(
            json={
                "fountains": fountains,
                "rest_stops": {"features": [], "availability": "missing"},
            }
        ),
    )

    def capture_map(route):
        response = route.fetch()
        route.fulfill(
            response=response,
            body=response.text().replace(
                "const map = new Map({", "const map = window.badgeTestMap = new Map({"
            ),
        )

    page.route("**/src/map.js", capture_map)
    page.goto(page.base_url + "/?mode=fixture")
    page.wait_for_function(
        "window.badgeTestMap && "
        "document.querySelector('#try-example').disabled === false"
    )
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Example mode')"
    )
    assert page.locator("#try-example").is_hidden()
    assert page.locator(".planner #selected-journey").count() == 0
    assert page.locator(".quick-heading").is_visible()
    page.locator("#more-layers summary").click()

    def visible_ids():
        return page.evaluate("""() => badgeTestMap.getLayers().getArray()
          .filter(layer => layer.getVisible()
            && layer.getSource() instanceof ol.source.Vector
            && !(layer.getSource() instanceof ol.source.Cluster))
          .flatMap(layer => layer.getSource().getFeatures().map(feature =>
            feature.get('sourceFeature')?.id ?? feature.getId())).filter(Boolean)""")

    station_ids = {f["id"] for f in stations["features"]}
    fountain_ids = {f["id"] for f in fountains["features"]}
    page.locator("#weather-stations-toggle").click()
    assert station_ids <= set(visible_ids())
    assert not fountain_ids.intersection(visible_ids())
    page.locator("#fountains-layer-toggle").click()
    assert station_ids | fountain_ids <= set(visible_ids())
    assert page.locator("#landmark-toggle").get_attribute("aria-pressed") == "false"
    page.locator("#landmark-toggle").click()
    assert page.locator("#landmark-toggle").get_attribute("aria-pressed") == "true"
    assert "stadtcasino" not in visible_ids()
    open_example(page)
    assert "stadtcasino" in visible_ids()
    page.locator("#weather-stations-toggle").click()
    assert not station_ids.intersection(visible_ids())
    assert fountain_ids <= set(visible_ids())
    assert "stadtcasino" in visible_ids()
    page.locator("#water-stop-toggle").click()
    assert fountain_ids <= set(visible_ids())
    page.locator("#fountains-layer-toggle").click()
    assert not fountain_ids.intersection(visible_ids())
    assert "stadtcasino" in visible_ids()
    page.locator("#landmark-toggle").click()
    assert "stadtcasino" not in visible_ids()
    assert not errors
    page.unroute("**/src/map.js", capture_map)
    page.unroute("**/api/route-temperatures?*")
    page.unroute("**/api/route-amenities?*")
