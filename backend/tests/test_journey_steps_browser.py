"""Focused renderer harness, with no edits to the shared app entry points."""

import pytest
from test_journey_instructions import maneuver_route

from bla_bla_walk.instructions import provider_directions

pytestmark = pytest.mark.browser


def test_route_switch_missing_and_route_ordered_prompts(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
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
    rows = page.locator("#journey-harness .walking-guide-list > li").all_text_contents()
    assert rows[0] == "Start walking on First street"
    assert not any("public fountain" in row for row in rows)
    assert "15 minutes walking" in rows[1]
    assert "30 minutes walking" in rows[-2]
    assert "selected destination" in rows[-1]
    assert page.locator("#journey-harness script").count() == 0
    page.evaluate("""() => {
      const second = structuredClone(firstRoute); second.id = 'second';
      second.directions.route_id = 'second';
      second.directions.steps[0].text = 'Start walking on Another street';
      second.directions.steps[0].street_name = 'Another street';
      second.directions.steps[1].text = 'Turn left. After Another street';
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


def test_named_references_are_near_the_maneuver_and_clear_on_route_change(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    route = maneuver_route()
    feature = {
        "id": "landmark-route",
        "geometry": route["geometry"],
        "route": {"distance_m": 2100, "duration_s": 2100},
        "directions": provider_directions(route, "landmark-route", 1).model_dump(
            mode="json"
        ),
    }
    # Synthetic named-place evidence checks matching, not real Migros coverage.
    result = page.evaluate(
        """async feature => {
      const {journeyItems} = await import('/src/journey-steps.js');
      const near = {label:'Test shop', sourceUrl:'https://example.com/mapped',
        coordinates:feature.directions.steps[1].location};
      const far = {label:'Distant church', sourceUrl:'https://example.com/mapped',
        coordinates:[7.7,47.6]};
      const unsourced = {label:'Invented Migros', coordinates:near.coordinates};
      const items = journeyItems(feature, [], [near,far,unsourced]);
      const changed = structuredClone(feature);
      changed.geometry.coordinates = [[7.7,47.6],[7.71,47.6]];
      changed.directions.steps.forEach(s => {
        s.location = changed.geometry.coordinates[0];
      });
      return {items, changed:journeyItems(changed, [], [near,far,unsourced])};
    }""",
        feature,
    )
    text = " ".join(item["text"] for item in result["items"])
    assert "by Test shop" in text
    assert "Distant church" not in text and "Invented Migros" not in text
    assert "Test shop" not in " ".join(item["text"] for item in result["changed"])
    assert "unnamed" not in text
    assert "After First street" in text


def test_short_segments_show_seconds(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    result = page.evaluate("""async () => {
      const {mountJourneySteps} = await import('/src/journey-steps.js');
      const container=document.createElement('div');
      mountJourneySteps(container).update({id:'short',geometry:{type:'LineString',
        coordinates:[[7.59,47.55],[7.591,47.55]]},
        route:{distance_m:6,duration_s:6},directions:{route_id:'short',steps:[{
          text:'Turn right on Test street',kind:'turn',location:[7.59,47.55],
          at_metres:0,distance_m:6,duration_s:6}]}});
      return container.querySelector('.walking-turn-list').textContent;
    }""")
    assert "6 sec" in result and "1 min" not in result


def test_named_saved_shops_can_be_references_but_illustrations_cannot(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    result = page.evaluate("""async () => {
      const {journeyItems} = await import('/src/journey-steps.js');
      const route = {id:'shop-route',geometry:{type:'LineString',
        coordinates:[[7.59,47.55],[7.591,47.55]]},
        route:{distance_m:75,duration_s:75},directions:{route_id:'shop-route',
          steps:[{text:'Turn left',kind:'turn',location:[7.59,47.55],
            at_metres:0,distance_m:75,duration_s:75}]}};
      const candidate = {fraction:0,feature:{label:'Test named supermarket',
        kind:'rest',rest_type:'indoor',geometry:{type:'Point',
          coordinates:[7.59,47.55]},
        provenance:{fixture:false,source_url:'https://example.com/mapped'}}};
      const real = journeyItems(route,[candidate],[])[0].text;
      candidate.feature.provenance.fixture = true;
      const fixture = journeyItems(route,[candidate],[])[0].text;
      return {real,fixture};
    }""")
    assert "by Test named supermarket" in result["real"]
    assert "by Test named supermarket" not in result["fixture"]
