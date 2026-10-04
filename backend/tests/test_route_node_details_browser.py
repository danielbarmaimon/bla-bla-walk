"""Route-point details reuse route timing, forecast and supported shade results."""

from datetime import UTC, datetime, timedelta
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
          const targets=[...document.querySelectorAll(
            '.route-node-target:not([hidden])'
          )];
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
    current_hour = datetime.now(ZoneInfo("Europe/Zurich")).replace(
        minute=0, second=0, microsecond=0
    )
    page.route(
        "**/api/palette-forecast?mode=fixture",
        lambda route: route.fulfill(
            json={
                "days": {forecast_day: 8.0},
                "hours": [
                    {
                        "valid_time": (current_hour + timedelta(hours=offset))
                        .astimezone(UTC)
                        .isoformat(),
                        "temperature_c": 23.4,
                    }
                    for offset in range(24)
                ],
                "availability": "current",
            }
        ),
    )
    page.goto(page.base_url + "/?mode=fixture")
    show_route_with_points(page)

    page.locator("#map").scroll_into_view_if_needed()
    page.evaluate("window.tripFlowMap.updateSize()")
    point = route_point_pixel(page, 8)
    assert point is not None
    assert (
        page.locator(".route-node-target").first.evaluate(
            "element => getComputedStyle(element).backgroundColor"
        )
        == "rgba(0, 0, 0, 0)"
    )
    page.mouse.move(*point)
    card = page.locator(".route-node-card")
    card.wait_for(state="visible")
    assert "Temperature" in card.inner_text()
    assert card.locator("dt").first.inner_text() == "Temperature"
    assert card.locator("dd").first.inner_text() == "23.4 °C"
    assert (
        card.locator("dd").first.evaluate(
            "element => getComputedStyle(element).whiteSpace"
        )
        == "nowrap"
    )
    assert "Local segment shadow" not in card.inner_text()
    assert page.evaluate(
        """() => {
          const card=document.querySelector('.route-node-card').getBoundingClientRect();
          const controls=[...document.querySelectorAll(
            [
              '#map .ol-control',
              '#basemap-status:not([hidden])',
              '#map-pick-banner:not([hidden])'
            ].join(', ')
          )];
          return controls.every(element=>{
            const box=element.getBoundingClientRect();
            return card.right<=box.left || card.left>=box.right ||
              card.bottom<=box.top || card.top>=box.bottom;
          });
        }"""
    )

    page.mouse.move(10, 10)
    assert card.is_hidden()
    hit_point = page.evaluate(
        """point => {
          const map=document.querySelector('#map').getBoundingClientRect();
          const card=document.querySelector('.route-node-card').getBoundingClientRect();
          const targets=[...document.querySelectorAll(
            '.route-node-target:not([hidden])'
          )];
          for (const degrees of [45,135,225,315,0,90,180,270]) {
            const angle=degrees*Math.PI/180;
            const x=point[0]+48*Math.cos(angle), y=point[1]+48*Math.sin(angle);
            if (x<map.left || x>map.right || y<map.top || y>map.bottom) continue;
            if (x>=card.left && x<=card.right && y>=card.top && y<=card.bottom) {
              continue;
            }
            if (targets.some(target=>{
              const box=target.getBoundingClientRect();
              return Math.hypot(x-box.x-box.width/2,y-box.y-box.height/2)<=56;
            })) return [x,y];
          }
          return null;
        }""",
        point,
    )
    assert hit_point is not None
    page.mouse.move(*hit_point)
    card.wait_for(state="visible")
    page.mouse.click(*point)
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
          const {nearestForecastHour}=await import('/src/route-temperature-view.js');
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
          const hourlyForecast={availability:'current',hours:[
            {valid_time:'2026-10-04T10:00:00Z',temperature_c:23},
            {valid_time:'2026-10-04T11:00:00Z',temperature_c:30},
            {valid_time:'2026-10-04T23:00:00Z',temperature_c:18},
            {valid_time:'2026-10-05T00:00:00Z',temperature_c:7}
          ]};
          const forecastForArrival=date=>({
            ...nearestForecastHour(hourlyForecast,date),availability:'current'
          });
          const supported=routePointDetails(
            route,profile,evidence,0.375,'2026-10-04T10:00:00Z',forecastForArrival
          );
          const nextDay=routePointDetails(
            route,profile,evidence,0.375,'2026-10-04T22:58:00Z',forecastForArrival
          );
          const missingForecast=routePointDetails(
            route,profile,evidence,0.375,'2026-10-04T10:00:00Z',date=>({
              value:null,validTime:null,availability:'missing'
            })
          );
          const staleForecast=nearestForecastHour(
            {...hourlyForecast,availability:'stale'},new Date('2026-10-04T10:06:15Z')
          );
          const unknown=routePointDetails(route,profile,{
            ...evidence,samples:[{start_metres:25,end_metres:50,state:0}]
          },0.375);
          const stale=routePointDetails(route,profile,{
            ...evidence,shade_state:'stale'
          },0.375);
          return {
            supported:{...supported,arrivalTime:supported.arrivalTime.toISOString(),temperatureForecastTime:supported.temperatureForecastTime.toISOString()},
            nextDay:{...nextDay,arrivalTime:nextDay.arrivalTime.toISOString(),temperatureForecastTime:nextDay.temperatureForecastTime.toISOString()},
            missingForecast:{temperature:missingForecast.temperature,temperatureForecastTime:missingForecast.temperatureForecastTime},
            staleForecast,unknown,stale
          };
        }"""
    )
    assert result["supported"] == {
        "temperature": 23,
        "temperatureForecastTime": "2026-10-04T10:00:00.000Z",
        "temperatureForecastAvailability": "current",
        "arrivalTime": "2026-10-04T10:06:15.000Z",
        "remainingMetres": 62.5,
        "remainingSeconds": 625,
        "shadePercentage": 50,
    }
    assert result["unknown"]["shadePercentage"] is None
    assert result["stale"]["shadePercentage"] is None
    assert result["nextDay"]["temperature"] == 18
    assert result["nextDay"]["temperatureForecastTime"] == "2026-10-04T23:00:00.000Z"
    assert result["nextDay"]["arrivalTime"] == "2026-10-04T23:04:15.000Z"
    assert result["missingForecast"] == {
        "temperature": None,
        "temperatureForecastTime": None,
    }
    assert result["staleForecast"] is None
