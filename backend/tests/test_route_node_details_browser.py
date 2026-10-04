"""Route-point detail interactions use existing route, sensor and shade results."""

import pytest
from conftest import open_example

pytestmark = pytest.mark.browser


def expose_map(page):
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
    return capture_map


def show_route_with_points(page):
    open_example(page)
    page.locator(".comparison-secondary").first.click()
    page.wait_for_function(
        "document.querySelectorAll('.route-node-target:not([hidden])').length > 1"
    )


def route_point_pixel(page, index=0):
    return page.evaluate(
        """index => {
          const map=window.tripFlowMap;
          const targets=[...document.querySelectorAll('.route-node-target:not([hidden])')];
          const chosen=targets[index] ?? targets[0];
          if (!chosen) return null;
          const bounds=chosen.getBoundingClientRect();
          return [bounds.x+bounds.width/2,bounds.y+bounds.height/2];
        }""",
        index,
    )


def test_route_point_hover_click_keyboard_and_route_change(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    capture_map = expose_map(page)
    page.route(
        "**/api/route-temperatures?mode=fixture",
        lambda route: route.fulfill(
            json={
                "id": "missing-temperature-test",
                "label": "Temperature unavailable",
                "kind": "observation",
                "availability": "missing",
                "features": [],
                "explanation": "No supported readings in this browser test.",
            }
        ),
    )
    page.goto(page.base_url)
    show_route_with_points(page)

    page.locator("#map").scroll_into_view_if_needed()
    page.evaluate("window.tripFlowMap.updateSize()")
    point = route_point_pixel(page, 8)
    assert point is not None
    page.mouse.move(*point)
    card = page.locator(".route-node-card")
    card.wait_for(state="visible")
    assert "Temperature" in card.inner_text()
    assert "Unavailable" in card.inner_text()
    assert "Local segment shadow" not in card.inner_text()
    assert page.evaluate(
        """() => {
          const card=document.querySelector('.route-node-card').getBoundingClientRect();
          const controls=[...document.querySelectorAll('#map .ol-control, #basemap-status:not([hidden]), #map-pick-banner:not([hidden])')];
          return controls.every(element=>{
            const box=element.getBoundingClientRect();
            return card.right<=box.left || card.left>=box.right || card.bottom<=box.top || card.top>=box.bottom;
          });
        }"""
    )

    page.mouse.click(*point)
    page.mouse.move(10, 10)
    assert card.is_visible()
    page.locator("#back-to-plan").click()
    page.locator(".comparison-secondary").last.click()
    assert card.is_hidden()

    slider = page.get_by_role("slider", name="Inspect route point")
    slider.focus()
    assert card.is_visible()
    first_heading = card.locator("h3").inner_text()
    page.keyboard.press("End")
    assert card.locator("h3").inner_text() != first_heading
    page.get_by_role("button", name="Close route point details").click()
    assert card.is_hidden()
    assert not errors
    page.unroute("**/vendor/ol.js", capture_map)


def test_route_point_details_uses_only_complete_current_shade_samples(browser_page):
    page = browser_page
    page.goto(page.base_url)
    result = page.evaluate(
        """async () => {
          const {routePointDetails}=await import('/src/route-node-details.js');
          const route={route:{distance_m:100,duration_s:1000}};
          const profile={segments:Array.from({length:4},(_,index)=>({
            start:index/4,end:(index+1)/4,estimate:{value:20+index}
          }))};
          const evidence={
            shade_state:'current',shade_time_matches_request:true,
            shade_geometry_matches_request:true,
            samples:[
              {start_metres:25,end_metres:37.5,state:2},
              {start_metres:37.5,end_metres:50,state:1}
            ]
          };
          const supported=routePointDetails(route,profile,evidence,0.375);
          const unknown=routePointDetails(route,profile,{
            ...evidence,samples:[{start_metres:25,end_metres:50,state:0}]
          },0.375);
          const stale=routePointDetails(route,profile,{
            ...evidence,shade_state:'stale'
          },0.375);
          return {supported,unknown,stale};
        }"""
    )
    assert result["supported"] == {
        "temperature": 21,
        "remainingMetres": 62.5,
        "remainingSeconds": 625,
        "shadePercentage": 50,
    }
    assert result["unknown"]["shadePercentage"] is None
    assert result["stale"]["shadePercentage"] is None
