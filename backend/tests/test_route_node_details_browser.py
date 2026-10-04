"""Route-point details reuse route timing, forecast and supported shade results."""

from datetime import datetime
from zoneinfo import ZoneInfo

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
    forecast_day = datetime.now(ZoneInfo("Europe/Zurich")).date().isoformat()
    page.route(
        "**/api/palette-forecast?mode=fixture",
        lambda route: route.fulfill(
            json={"days": {forecast_day: 23.4}, "availability": "current"}
        ),
    )
    page.goto(page.base_url)
    show_route_with_points(page)

    page.locator("#map").scroll_into_view_if_needed()
    page.evaluate("window.tripFlowMap.updateSize()")
    point = route_point_pixel(page, 8)
    assert point is not None
    assert page.locator(".route-node-target").first.evaluate(
        "element => getComputedStyle(element).backgroundColor"
    ) == "rgba(0, 0, 0, 0)"
    page.mouse.move(*point)
    card = page.locator(".route-node-card")
    card.wait_for(state="visible")
    assert "Temperature" in card.inner_text()
    assert "23.4 °C" in card.inner_text()
    assert "Basel daily mean" in card.inner_text()
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

    page.mouse.click(point[0] + 48, point[1])
    page.mouse.move(10, 10)
    assert card.is_visible()
    assert page.locator(".route-node-close").count() == 0
    page.locator("#back-to-plan").click()
    page.locator(".comparison-secondary").last.click()
    assert card.is_hidden()

    slider = page.get_by_role("slider", name="Inspect route point")
    slider.focus()
    assert card.is_visible()
    first_heading = card.locator("h3").inner_text()
    page.keyboard.press("End")
    assert card.locator("h3").inner_text() != first_heading
    page.keyboard.press("Escape")
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
          const forecastForArrival=date=>({
            day:new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Zurich',year:'numeric',month:'2-digit',day:'2-digit'}).format(date),
            value:new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Zurich',year:'numeric',month:'2-digit',day:'2-digit'}).format(date)==='2026-10-05'?18:23,
            availability:'current'
          });
          const supported=routePointDetails(route,profile,evidence,0.375,'2026-10-04T10:00:00Z',forecastForArrival);
          const nextDay=routePointDetails(route,profile,evidence,0.375,'2026-10-04T22:58:00Z',forecastForArrival);
          const missingForecast=routePointDetails(route,profile,evidence,0.375,'2026-10-04T10:00:00Z',date=>({
            day:'2026-10-04',value:null,availability:'missing'
          }));
          const unknown=routePointDetails(route,profile,{
            ...evidence,samples:[{start_metres:25,end_metres:50,state:0}]
          },0.375);
          const stale=routePointDetails(route,profile,{
            ...evidence,shade_state:'stale'
          },0.375);
          return {
            supported:{...supported,arrivalTime:supported.arrivalTime.toISOString()},
            nextDay:{...nextDay,arrivalTime:nextDay.arrivalTime.toISOString()},
            missingForecast:{temperature:missingForecast.temperature,temperatureForecastDay:missingForecast.temperatureForecastDay},
            unknown,stale
          };
        }"""
    )
    assert result["supported"] == {
        "temperature": 23,
        "temperatureForecastDay": "2026-10-04",
        "temperatureForecastAvailability": "current",
        "arrivalTime": "2026-10-04T10:06:15.000Z",
        "remainingMetres": 62.5,
        "remainingSeconds": 625,
        "shadePercentage": 50,
    }
    assert result["unknown"]["shadePercentage"] is None
    assert result["stale"]["shadePercentage"] is None
    assert result["nextDay"]["temperature"] == 18
    assert result["nextDay"]["temperatureForecastDay"] == "2026-10-05"
    assert result["nextDay"]["arrivalTime"] == "2026-10-04T23:04:15.000Z"
    assert result["missingForecast"] == {
        "temperature": None,
        "temperatureForecastDay": "2026-10-04",
    }
