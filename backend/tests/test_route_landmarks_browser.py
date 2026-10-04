"""Route-specific saved landmarks on an isolated real OpenLayers map."""

import pytest
from bla_bla_walk.adapters.routes import load_demo_routes

pytestmark = pytest.mark.browser


def initialize_harness(page):
    page.goto(page.base_url + "/?mode=fixture")
    page.wait_for_function("Boolean(window.ol)")
    page.evaluate("""async () => {
      window.landmarksModule = await import('/src/route-landmarks.js');
      document.body.replaceChildren();
      const button = document.createElement('button'); button.id = 'landmark-toggle';
      button.textContent = 'Landmarks'; button.setAttribute('aria-pressed','false');
      const status = document.createElement('p'); status.id = 'landmark-status';
      const container = document.createElement('div'); container.id = 'landmark-map';
      container.style.height = '500px';
      document.body.append(button,status,container);
      window.landmarkMap = new ol.Map({target:container,layers:[],view:new ol.View({
        center:ol.proj.fromLonLat([7.59,47.555]),zoom:16})});
      window.landmarks = landmarksModule.mountRouteLandmarks(landmarkMap,{
        onStatus:result => status.textContent = result.explanation});
      button.addEventListener('click', () => {
        const visible = button.getAttribute('aria-pressed') !== 'true';
        button.setAttribute('aria-pressed',String(visible));
        landmarks.setVisible(visible);
      });
    }""")


def test_saved_and_different_route_ids_switch_and_toggle(browser_page):
    page = browser_page
    initialize_harness(page)
    routes = load_demo_routes().model_dump(mode="json")["features"]
    result = page.evaluate("route => landmarks.update(route)", routes[0])
    assert result["availability"] == "limited"
    assert result["candidates"]
    assert all(c["routeId"] == routes[0]["id"] for c in result["candidates"])
    assert page.evaluate("landmarks.layer.getSource().getFeatures().length") == 0
    page.locator("#landmark-toggle").click()
    assert page.locator("#landmark-toggle").get_attribute("aria-pressed") == "true"
    assert page.evaluate("landmarks.layer.getSource().getFeatures().length") == len(
        result["candidates"]
    )
    for candidate in result["candidates"]:
        assert candidate["checkedAt"] == "2026-10-03"
        assert candidate["visibility"] == "unknown"
        assert candidate["familiar"] == "unknown"
    # No ID special case: identical geometry with an arbitrary provider ID works.
    renamed = {**routes[1], "id": "walking-a-different-address-pair"}
    changed = page.evaluate("route => landmarks.update(route)", renamed)
    marker_routes = page.evaluate("""landmarks.layer.getSource().getFeatures().map(
      f => f.get('landmarkCandidate').routeId)""")
    assert marker_routes == [renamed["id"]] * len(changed["candidates"])
    coordinates = page.evaluate("""landmarks.layer.getSource().getFeatures().map(
      f => ol.proj.toLonLat(f.getGeometry().getCoordinates()))""")
    for actual, candidate in zip(coordinates, changed["candidates"], strict=True):
        assert actual == pytest.approx(candidate["coordinates"])
    page.locator("#landmark-toggle").click()
    assert page.evaluate("landmarks.layer.getSource().getFeatures().length") == 0
    page.locator("#landmark-toggle").click()
    assert page.evaluate("landmarks.layer.getSource().getFeatures().length") > 0
    page.evaluate("landmarks.update(null)")
    assert page.evaluate("landmarks.layer.getSource().getFeatures().length") == 0
    assert "Select a walking route" in page.locator("#landmark-status").inner_text()
    page.evaluate("landmarks.dispose()")
    assert page.evaluate("landmarkMap.getLayers().getLength()") == 0


def test_source_locations_dates_missing_and_empty_are_preserved(browser_page):
    page = browser_page
    initialize_harness(page)
    result = page.evaluate("""() => {
      const route = {id:'another-route',geometry:{type:'LineString',
        coordinates:[[7.58,47.55],[7.60,47.55]]}};
      const feature = {id:'saved-shop',label:'Test named shop',kind:'rest',
        geometry:{type:'Point',coordinates:[7.59,47.5501]},
        provenance:{fixture:false,source_url:'https://example.com/mapped',
          retrieved_at:'2026-10-03T22:59:42.128381Z',observed_at:null}};
      const fixture = structuredClone(feature); fixture.id = 'illustrative';
      fixture.provenance.fixture = true;
      const generic = structuredClone(feature); generic.id = 'generic';
      generic.label = 'Mapped park centre';
      const evidence = landmarksModule.savedLandmarkEvidence({rest_stops:{
        features:[feature,fixture,generic]}});
      const before = JSON.stringify(evidence);
      const candidates = landmarksModule.routeLandmarkCandidates(route,evidence);
      const after = JSON.stringify(evidence);
      landmarks.setVisible(true); landmarks.update(route,evidence);
      const missing = landmarks.update(route,{availability:'missing',places:[]});
      const missingCount = landmarks.layer.getSource().getFeatures().length;
      const empty = landmarks.update({id:'far-away',geometry:{type:'LineString',
        coordinates:[[7.63,47.59],[7.64,47.59]]}},evidence);
      return {evidence,candidates,before,after,missing,missingCount,empty};
    }""")
    assert result["before"] == result["after"]
    named = next(
        c for c in result["candidates"]["candidates"] if c["id"] == "saved-shop"
    )
    assert named["coordinates"] == [7.59, 47.5501]
    assert named["retrievedAt"] == "2026-10-03T22:59:42.128381Z"
    assert named["observedAt"] is None
    assert named["sourceUrl"] == "https://example.com/mapped"
    assert {c["id"] for c in result["evidence"]["places"]}.isdisjoint(
        {"illustrative", "generic"}
    )
    assert result["missing"]["availability"] == "missing"
    assert result["missingCount"] == 0
    assert "unavailable" in result["missing"]["explanation"]
    assert result["empty"]["availability"] == "empty"
    assert not result["empty"]["candidates"]


def test_missing_configuration_does_not_invent_points(browser_page):
    page = browser_page
    page.route("**/config/landmarks.json", lambda route: route.fulfill(status=404))
    try:
        initialize_harness(page)
        result = page.evaluate("""() => landmarksModule.routeLandmarkCandidates({
          id:'missing-config',geometry:{type:'LineString',
            coordinates:[[7.58,47.55],[7.60,47.55]]}})""")
        assert result["availability"] == "missing"
        assert not result["candidates"]
    finally:
        page.unroute("**/config/landmarks.json")


def test_unusable_route_or_unsupported_evidence_clears_markers(browser_page):
    page = browser_page
    initialize_harness(page)
    route = load_demo_routes().model_dump(mode="json")["features"][0]
    page.evaluate(
        "route => {landmarks.setVisible(true); landmarks.update(route)}", route
    )
    assert page.evaluate("landmarks.layer.getSource().getFeatures().length") > 0
    for availability in ("unsupported", "failed"):
        result = page.evaluate(
            "({route,availability}) => landmarks.update(route,"
            "{...landmarksModule.savedLandmarkEvidence(),availability})",
            {"route": route, "availability": availability},
        )
        assert result["availability"] == "missing"
        assert page.evaluate("landmarks.layer.getSource().getFeatures().length") == 0
    for coordinates in ([], [[7.59, 47.55]], [[7.59, None], [7.60, 47.56]]):
        result = page.evaluate(
            "coordinates => landmarks.update({id:'broken-route',"
            "geometry:{type:'LineString',coordinates}})",
            coordinates,
        )
        assert result["availability"] == "missing"
        assert not result["candidates"]


def test_landmark_search_selects_real_endpoints_without_address_provider(browser_page):
    page = browser_page
    requests = []
    page.on(
        "request",
        lambda request: (
            requests.append(request.url) if "/api/addresses" in request.url else None
        ),
    )
    page.goto(page.base_url + "/?mode=offline")
    origin = page.locator("#origin-input")
    origin.fill("Barfusserkirche")
    page.locator("#origin-suggestions button").first.wait_for()
    assert (
        "Saved mapped landmark"
        in page.locator("#origin-suggestions button").first.inner_text()
    )
    origin.press("ArrowDown")
    page.keyboard.press("Enter")
    assert origin.input_value() == "Barfüsserkirche"
    destination = page.locator("#destination-input")
    destination.fill("Stadtcasino")
    page.locator("#suggestions button").first.click()
    assert destination.input_value() == "Stadtcasino Basel"
    assert (
        "Mapped landmark selected" in page.locator("#destination-status").inner_text()
    )
    assert page.locator("#calculate-journey").is_enabled()
    assert not requests


def test_saved_landmark_search_survives_address_failure_and_clear(browser_page):
    page = browser_page
    page.route("**/api/addresses", lambda route: route.fulfill(status=503))
    try:
        page.goto(page.base_url + "/?mode=fixture")
        field = page.locator("#destination-input")
        field.fill("Stadtcasino")
        page.wait_for_function(
            "document.querySelector('#destination-status').textContent"
            ".includes('coverage limited')"
        )
        assert "Stadtcasino Basel" in page.locator("#suggestions").inner_text()
        field.fill("No such landmark abcxyz")
        page.wait_for_function(
            "document.querySelector('#destination-status').textContent"
            ".includes('Try again')"
        )
        assert page.locator("#suggestions").is_hidden()
        field.fill("Barfu")
        page.locator("#suggestions button").first.wait_for()
        field.press("Escape")
        assert page.locator("#suggestions").is_hidden()
    finally:
        page.unroute("**/api/addresses")


def test_saved_landmark_search_preserves_shop_coordinates_and_dates(browser_page):
    page = browser_page
    initialize_harness(page)
    result = page.evaluate("""() => {
      const evidence = landmarksModule.savedLandmarkEvidence({rest_stops:{features:[{
        id:'osm-node-1',label:'Migros',geometry:{type:'Point',coordinates:[7.59,47.55]},
        provenance:{fixture:false,source_url:'https://www.openstreetmap.org/node/1',
          retrieved_at:'2026-10-03T22:59:42.128381Z'}}]}});
      return landmarksModule.searchSavedLandmarks('migros',evidence);
    }""")
    assert len(result) == 1
    assert result[0]["name"] == "Migros"
    assert (result[0]["lon"], result[0]["lat"]) == (7.59, 47.55)
    assert result[0]["landmark"]["retrievedAt"] == "2026-10-03T22:59:42.128381Z"


def test_landmark_selection_sends_source_coordinates_to_walking_router(browser_page):
    page = browser_page
    page.route(
        "**/api/addresses",
        lambda route: route.fulfill(json={"places": [], "status": "available"}),
    )
    page.route("**/api/walking-routes", lambda route: route.fulfill(status=422))
    try:
        page.goto(page.base_url + "/?mode=fixture")
        page.locator("#origin-input").fill("Barfusserkirche")
        page.locator("#origin-suggestions button").first.click()
        page.locator("#destination-input").fill("Stadtcasino")
        page.locator("#suggestions button").first.click()
        with page.expect_request(
            lambda request: (
                "/api/walking-routes" in request.url and request.method == "POST"
            )
        ) as sent:
            page.locator("#calculate-journey").click()
        assert sent.value.post_data_json["start"] == [7.5905029, 47.5544915]
        assert sent.value.post_data_json["end"] == [7.5901346, 47.5542438]
    finally:
        page.unroute("**/api/addresses")
        page.unroute("**/api/walking-routes")
