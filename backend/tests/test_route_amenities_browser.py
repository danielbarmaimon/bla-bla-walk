"""Candidates filter to route proximity and use actual source-point markers."""

import pytest

pytestmark = pytest.mark.browser


def test_proximity_and_marker_labels(browser_page):
    page = browser_page
    page.goto(page.base_url)
    page.wait_for_function("!document.querySelector('#destination-input').disabled")
    result = page.evaluate("""async () => {
      const {routeAmenities, amenityLabel} = await import('/src/route-amenities.js');
      const {routeGeometry} = await import('/src/route-planner-data.js');
      const line = routeGeometry([[7.60,47.54],[7.61,47.54]]);
      const feature = (kind,type,latitude) => ({kind,rest_type:type,
        geometry:{type:'Point',coordinates:[7.605,latitude]}});
      const data = {fountains:{features:[feature('fountain',null,47.5401)]},
        rest_stops:{features:[feature('rest','bench',47.5402),
          feature('rest','park',47.541)]}};
      const settings = {fountain_buffer_metres:50,rest_buffer_metres:50};
      const near = routeAmenities(line,data,settings);
      const otherLine = routeGeometry([[7.60,47.55],[7.61,47.55]]);
      const changed = routeAmenities(otherLine,data,settings);
      return {labels:near.map(item=>amenityLabel(item.feature)),
        points:near.map(item=>item.feature.geometry.coordinates),
        changed:changed.length};
    }""")
    assert result["labels"] == ["WATER", "BENCH"]
    assert result["points"][1] == [7.605, 47.5402]
    assert result["changed"] == 0


def test_real_saved_candidates_visible_and_toggle(browser_page):
    page = browser_page
    page.goto(page.base_url)
    page.wait_for_function(
        "document.querySelector('#nearby-summary').textContent.includes('Route stops')"
    )
    assert "fountains" in page.locator("#nearby-summary").inner_text()
    assert "benches" in page.locator("#nearby-summary").inner_text()
    page.locator("#show-route").click()
    page.locator("#nearby-details").evaluate("element => element.open = true")
    assert (
        "Distance is geometric proximity" in page.locator("#nearby-list").inner_text()
    )
    page.locator("#nearby-list button").first.click()
    assert "Provider data" in page.locator("#map-feature-details").inner_text()
    assert "Retrieved" in page.locator("#map-feature-details").inner_text()
    assert page.locator("#map-feature-inspector").evaluate("element => element.open")
    page.locator("#route-stops-toggle").uncheck()
    assert not page.locator("#route-stops-toggle").is_checked()
