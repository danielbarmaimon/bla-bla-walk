"""Focused renderer harness, with no edits to the shared app entry points."""

import pytest
from bla_bla_walk.instructions import provider_directions
from test_journey_instructions import maneuver_route

pytestmark = pytest.mark.browser


def test_route_switch_missing_and_route_ordered_prompts(browser_page):
    page = browser_page
    page.goto(page.base_url)
    route = maneuver_route()
    feature = {
        "id": "first",
        "geometry": route["geometry"],
        "route": {"distance_m": 2100, "duration_s": 2100},
        "directions": provider_directions(route, "first", 1).model_dump(mode="json"),
    }
    page.evaluate(
        """async feature => {
      const {mountJourneySteps} = await import('/src/journey-steps.js');
      const container = document.createElement('section');
      container.id = 'journey-harness'; document.body.append(container);
      window.steps = mountJourneySteps(container);
      window.firstRoute = feature;
      steps.update(feature, {amenities: [{fraction:0.25, feature:{
        kind:'fountain', label:'<script>public fountain</script>'}}]});
    }""",
        feature,
    )
    rows = page.locator("#journey-harness li").all_text_contents()
    assert rows[0].startswith("Start walking on First street. Walk 1000 m")
    assert "water candidate" in rows[1]
    assert "15 minutes walking" in rows[2]
    assert "30 minutes walking" in rows[-2]
    assert "selected destination" in rows[-1]
    assert page.locator("#journey-harness script").count() == 0
    page.evaluate("""() => {
      const second = structuredClone(firstRoute); second.id = 'second';
      second.directions.route_id = 'second';
      second.directions.steps[0].text = 'Start walking on Another street';
      steps.update(second);
    }""")
    text = page.locator("#journey-harness").inner_text()
    assert "Another street" in text and "First street" not in text
    assert "SBB" not in text and "Marktplatz" not in text
    # A directions object for another ID is never shown.
    page.evaluate("steps.update({...firstRoute, id:'saved-route'})")
    text = page.locator("#journey-harness").inner_text()
    assert "Directions unavailable" in text and "First street" not in text
    page.evaluate("steps.update({...firstRoute, directions:null})")
    assert "Directions unavailable" in page.locator("#journey-harness").inner_text()
    page.evaluate(
        "steps.update({...firstRoute, route:{distance_m:2100,duration_s:1800}})"
    )
    assert page.locator("#journey-harness [data-kind=prompt]").count() == 1
    page.evaluate("steps.dispose()")
    assert page.locator("#journey-harness").inner_text() == ""
