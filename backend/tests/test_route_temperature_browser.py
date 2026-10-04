"""Temporal/coverage boundaries, sensor estimates and exact user palettes."""

import pytest
from conftest import open_example

pytestmark = pytest.mark.browser


def test_estimates_palettes_and_unknowns(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    result = page.evaluate("""async () => {
      const {sensorCohort,estimateTemperature,temperatureProfile,temperatureColour,
        validateSensorInterpolation}=await import('/src/route-temperature.js');
      const {chooseTemperaturePalette}=await import('/src/route-temperature-view.js');
      const {routeGeometry}=await import('/src/route-planner-data.js');
      const settings=await (await fetch('/config/route-temperature.json')).json();
      const now=Date.parse('2026-10-04T12:00:00Z');
      const sensor=(id,lon,value,time='2026-10-04T11:55:00Z')=>({id,label:id,
        kind:'observation',geometry:{type:'Point',coordinates:[lon,47.55]},
        value,unit:'°C',availability:'current',provenance:{fixture:false,observed_at:time}});
      const sensors=[sensor('a',7.59,20),sensor('b',7.60,24),
        sensor('old',7.595,90,'2026-10-04T09:00:00Z'),
        sensor('missing',7.595,null)];
      const cohort=sensorCohort(sensors,settings,now);
      const route=routeGeometry([[7.592,47.55],[7.598,47.55]]);
      const profile=temperatureProfile(route,{features:sensors},settings,now);
      const mean=estimateTemperature([7.595,47.55],cohort,settings).value;
      const far=temperatureProfile(routeGeometry([[8,47.55],[8.01,47.55]]),
        {features:sensors},settings,now);
      const flat=temperatureProfile(route,{features:[sensor('a',7.59,20),
        sensor('b',7.60,20)]},settings,now);
      const summer=['#86efac','#fbbf24','#e11d48'];
      const winter=['#a5f3fc','#4338ca'];
      const colours=[temperatureColour(20,20,24,summer),
        temperatureColour(22,20,24,summer),temperatureColour(24,20,24,summer),
        temperatureColour(0,0,4,winter),temperatureColour(4,0,4,winter)];
      const forecast={days:{'2026-10-04':5},availability:'current'};
      const pick=p=>chooseTemperaturePalette(p,forecast,settings,'2026-10-04',
        'auto','2026-10-04').name;
      const stale=temperatureProfile(route,{features:sensors},settings,
        now+86400000);
      const validation=validateSensorInterpolation({features:[
        sensor('a',7.59,20),sensor('b',7.595,20),sensor('c',7.60,20)]},settings,now);
      return {ids:cohort.map(s=>s.id),mean,coverage:profile.coverage,
        far:far.coverage,flatSpan:flat.high-flat.low,colours,
        current:pick(profile),fallback:pick(stale),missing:pick({coverage:0}),
        stale:stale.stale,validation};
    }""")
    assert result["ids"] == ["a", "b"]
    assert result["mean"] == pytest.approx(22)
    assert result["coverage"] == 1 and result["far"] == 0
    assert result["flatSpan"] == 2
    assert result["colours"] == ["#86efac", "#fbbf24", "#e11d48", "#a5f3fc", "#4338ca"]
    assert result["current"] == "summer"
    assert result["fallback"] == result["missing"] == "winter"
    assert result["stale"]
    assert result["validation"]["count"] == 3
    assert result["validation"]["meanAbsoluteError"] == 0


def test_real_saved_route_gradient_and_switches(browser_page):
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
            constructor(...args){super(...args);window.temperatureTestMap=this;}
          };
        """,
        )

    page.route("**/vendor/ol.js", capture_map)
    page.goto(page.base_url + "/?mode=offline")
    open_example(page)
    page.unroute("**/vendor/ol.js", capture_map)
    page.wait_for_function(
        "document.querySelector('#temperature-legend')"
        ".textContent.includes('sensor-based estimate')"
    )
    page.locator("#information-sources").evaluate("e=>e.open=true")
    assert "SAVED / STALE" in page.locator("#temperature-legend").inner_text()
    assert "°C" in page.locator("#temperature-legend").inner_text()
    page.locator(".comparison-secondary[data-route-id=demo-route-b]").click()
    page.locator("#map").scroll_into_view_if_needed()
    page.wait_for_function("!window.temperatureTestMap.getView().getAnimating()")
    drawn = page.evaluate("""() => {
      const map=window.temperatureTestMap;
      map.renderSync();
      const layer=map.getLayers().getArray().find(l=>l.getZIndex()===6);
      const features=layer.getSource().getFeatures();
      const known=features.filter(f=>f.get('temperatureSample'));
          const free=known.find(feature=>{
            const c=feature.getGeometry().getCoordinates();
            const pixel=map.getPixelFromCoordinate([(c[0][0]+c.at(-1)[0])/2,
              (c[0][1]+c.at(-1)[1])/2]);
            return map.getFeaturesAtPixel(pixel)[0]?.get('temperatureSample');
          });
          const point=free.getGeometry().getCoordinates();
      return {colours:[...new Set(known.map(f=>f.get('temperatureColour')))],
        pixel:map.getPixelFromCoordinate([(point[0][0]+point.at(-1)[0])/2,
          (point[0][1]+point.at(-1)[1])/2])};
    }""")
    assert len(drawn["colours"]) > 1
    page.locator("#map").click(
        position={"x": drawn["pixel"][0], "y": drawn["pixel"][1]}
    )
    page.wait_for_function(
        "document.querySelector('#temperature-sample')"
        ".textContent.includes('Estimated air temperature here')"
    )
    assert (
        "Estimated air temperature here"
        in page.locator("#temperature-sample").inner_text()
    )
    page.locator("#temperature-palette").select_option("summer")
    ramp = page.locator(".temperature-ramp").evaluate("e=>e.style.background")
    assert "134, 239, 172" in ramp and "225, 29, 72" in ramp
    page.locator("#temperature-palette").select_option("winter")
    ramp = page.locator(".temperature-ramp").evaluate("e=>e.style.background")
    assert "165, 243, 252" in ramp and "67, 56, 202" in ramp
    page.locator("#temperature-route-toggle").click()
    assert (
        page.locator("#temperature-route-toggle").get_attribute("aria-pressed")
        == "false"
    )
    assert not page.evaluate(
        "window.temperatureTestMap.getLayers().getArray()"
        ".find(l=>l.getZIndex()===6).getVisible()"
    )
    assert not errors
