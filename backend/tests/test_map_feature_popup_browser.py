"""Click actual map markers and verify compact evidence and dismissal."""

import pytest

pytestmark = pytest.mark.browser


def setup_map(page):
    """Use deterministic contract-shaped points in the real OpenLayers map."""
    page.goto(page.base_url + "/?mode=fixture")
    page.wait_for_function("!!window.ol")
    page.evaluate("""async () => {
      const NativeMap = ol.Map;
      let actual;
      ol.Map = class extends NativeMap {
        constructor(...args) { super(...args); actual = this; }
      };
      const {createMap} = await import('/src/map.js?popup-test');
      const target = document.createElement('div');
      target.id = 'popup-test-map';
      target.tabIndex = 0;
      target.style.cssText = 'width:100%;max-width:800px;height:500px';
      document.body.prepend(target);
      const selected = [];
      const api = createMap(target, f => selected.push(f.id), () => {}, () => {});
      ol.Map = NativeMap;
      const point = (id, label, kind, coordinates, value, observed_at) => ({
        id, label, kind, value, unit:'°C',
        geometry:{type:'Point',coordinates}, provenance:{observed_at}
      });
      const station = point('station', 'Sample station', 'observation',
        [7.5886,47.5596], 0, '2026-10-04T10:30:00Z');
      const missing = point('missing', 'Missing station', 'observation',
        [7.5826,47.5596], null, null);
      const fountain = point('fountain', '<b>Sample fountain</b>', 'fountain',
        [7.5946,47.5596], 99, '2026-10-04T10:30:00Z');
      const other = point('other', 'Other feature', 'shade',
        [7.5886,47.5636], null, null);
      const layers = [station,missing,fountain,other].map(f => ({
        id:f.id,kind:f.kind,features:[f]
      }));
      api.replaceLayers(layers);
      actual.renderSync();
      window.popupTest = {actual,api,target,selected,layers,station,fountain};
    }""")


def click_point(page, coordinates):
    """Click through the canvas hit detection rather than invoking a renderer."""
    # Keep separate taps outside OpenLayers' 250ms double-click interval,
    # including the preceding overlay button click.
    page.wait_for_timeout(300)
    point = page.evaluate(
        """coordinates => {
      const {actual,target} = popupTest;
      actual.renderSync();
      const pixel = actual.getPixelFromCoordinate(ol.proj.fromLonLat(coordinates));
      const box = target.getBoundingClientRect();
      return {x:box.left+pixel[0],y:box.top+pixel[1]};
    }""",
        coordinates,
    )
    page.mouse.click(point["x"], point["y"])


def test_popup_content_replacement_and_dismissal(browser_page):
    page = browser_page
    setup_map(page)
    popup = page.locator("#popup-test-map .map-stop-menu")
    click_point(page, [7.5886, 47.5596])
    popup.wait_for(state="visible")
    assert "Sample station" in popup.inner_text()
    assert "Temperature: 0 °C" in popup.inner_text()
    assert "12:30" in popup.inner_text()
    assert "Unknown" not in popup.inner_text()
    assert popup.locator("button").evaluate("e=>e===document.activeElement")
    click_point(page, [7.5826, 47.5596])
    page.wait_for_function(
        "popupTest.target.querySelector('.map-stop-menu').textContent"
        ".includes('Missing station')"
    )
    assert popup.inner_text().count("Unknown") == 2
    click_point(page, [7.5946, 47.5596])
    page.wait_for_function(
        "popupTest.target.querySelector('.map-stop-menu').textContent"
        ".includes('Sample fountain')"
    )
    assert popup.locator("strong").inner_text() == "<b>Sample fountain</b>"
    assert popup.locator("p, b").count() == 0
    assert page.evaluate("popupTest.selected") == []
    click_point(page, [7.5986, 47.5556])
    popup.wait_for(state="hidden")
    click_point(page, [7.5886, 47.5596])
    popup.wait_for(state="visible")
    page.keyboard.press("Escape")
    popup.wait_for(state="hidden")
    assert page.evaluate("document.activeElement===popupTest.target")
    click_point(page, [7.5886, 47.5596])
    popup.wait_for(state="visible")
    popup.get_by_role("button", name="Close", exact=True).click()
    popup.wait_for(state="hidden")
    click_point(page, [7.5886, 47.5636])
    page.wait_for_function("popupTest.selected.includes('other')")


def test_popup_edge_placement_and_grouped_fountains(browser_page):
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    setup_map(page)
    page.evaluate("""() => {
      const {api,fountain} = popupTest;
      api.setContextMarkers([
        {kind:'water',label:'Fountain one',coordinates:[7.5886,47.5596],
          sourceFeature:{...fountain,label:'Fountain one'}},
        {kind:'water',label:'Fountain two',coordinates:[7.5888,47.5596],
          sourceFeature:{...fountain,label:'Fountain two'}}
      ]);
    }""")
    click_point(page, [7.5886, 47.5596])
    popup = page.locator("#popup-test-map .map-stop-menu")
    popup.get_by_role("button", name="Fountain two", exact=True).click()
    assert popup.locator("strong").inner_text() == "Fountain two"
    assert page.evaluate("popupTest.actual.getOverlays().getLength()") == 1
    assert page.evaluate("popupTest.selected") == []
    page.evaluate("""() => {
      const {api,actual,station} = popupTest;
      api.setContextMarkers([]);
      const coordinates = ol.proj.toLonLat(actual.getCoordinateFromPixel([60,20]));
      station.geometry.coordinates = coordinates;
      api.replaceLayers([{id:'station',kind:'observation',features:[station]}]);
      actual.renderSync();
    }""")
    coordinates = page.evaluate("popupTest.station.geometry.coordinates")
    click_point(page, coordinates)
    popup.wait_for(state="visible")
    bounds = popup.bounding_box()
    map_bounds = page.evaluate("""() => {
      const b=popupTest.target.getBoundingClientRect();
      return {x:b.x,y:b.y,width:b.width,height:b.height};
    }""")
    assert bounds["x"] >= map_bounds["x"]
    assert bounds["y"] >= map_bounds["y"]
    assert bounds["x"] + bounds["width"] <= map_bounds["x"] + map_bounds["width"]
    zoom = page.locator("#popup-test-map .ol-zoom").bounding_box()
    assert (
        bounds["x"] >= zoom["x"] + zoom["width"]
        or bounds["y"] >= zoom["y"] + zoom["height"]
    )
    page.screenshot(path="/tmp/t33-popup-mobile.png")
    page.evaluate("popupTest.api.replaceLayers(popupTest.layers)")
    popup.wait_for(state="hidden")
    page.set_viewport_size({"width": 1280, "height": 900})
