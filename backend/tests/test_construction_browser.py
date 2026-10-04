"""Dated nearby site icons, independent visibility and source popups."""

import pytest
from conftest import open_example

from bla_bla_walk.adapters.routes import load_demo_routes

pytestmark = pytest.mark.browser


def test_nearby_construction_icons_date_filter_and_toggles(browser_page):
    page = browser_page
    lon, lat = load_demo_routes().features[0].geometry.coordinates[0]
    snapshot = {
        "availability": "current",
        "covers_from": "2026-10-04",
        "provenance": {
            "fixture": False,
            "retrieved_at": "2026-10-04T11:00:00Z",
            "source_url": "https://data.bs.ch/explore/dataset/100018/",
            "attribution": "Tiefbauamt",
            "licence": "CC BY 4.0",
        },
        "sites": [
            {
                "id": "near",
                "project_id": "123",
                "starts_on": "2026-10-04",
                "ends_on": "2026-10-04",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon - 0.0001, lat - 0.0001],
                            [lon + 0.0001, lat - 0.0001],
                            [lon + 0.0001, lat + 0.0001],
                            [lon - 0.0001, lat + 0.0001],
                            [lon - 0.0001, lat - 0.0001],
                        ]
                    ],
                },
            }
        ],
    }
    page.route(
        "**/api/construction-sites?**", lambda route: route.fulfill(json=snapshot)
    )

    def capture(route):
        response = route.fetch()
        route.fulfill(
            response=response,
            body=response.text()
            + """
          const NativeMap=ol.Map;
          ol.Map=class extends NativeMap {
            constructor(...args){super(...args);window.constructionMap=this;}
          };
        """,
        )

    page.route("**/vendor/ol.js", capture)
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page)
    markers = """() => window.constructionMap.getLayers().getArray()
      .flatMap(l=>l.getSource?.().getFeatures?.() ?? [])
      .filter(f=>f.get('kind')==='construction')"""
    page.wait_for_function("(" + markers + ")().length===1")
    detail = page.evaluate("(" + markers + ")()[0].get('sourceFeature').explanation")
    assert "123" in detail and "2026-10-04" in detail
    result = page.evaluate(
        """async (snapshot) => {
      const {constructionMarkers}=await import('/src/route-construction.js');
      const settings=await (await fetch('/config/construction-sites.json')).json();
      const route={geometry:{type:'LineString',
        coordinates:[[7.59,47.55],[7.60,47.55]]}};
      const site={...snapshot.sites[0],geometry:{type:'Polygon',coordinates:[[
        [7.58,47.54],[7.61,47.54],[7.61,47.56],[7.58,47.56],[7.58,47.54]]]}};
      snapshot.sites=[site];
      const crossing=constructionMarkers([route],snapshot,'2026-10-04',settings);
      const later=constructionMarkers([route],snapshot,'2026-10-05',settings);
      route.geometry.coordinates=[[8,48],[8.01,48]];
      const far=constructionMarkers([route],snapshot,'2026-10-04',settings);
      return {crossing:crossing.length,later:later.length,far:far.length};
    }""",
        snapshot,
    )
    assert result == {"crossing": 1, "later": 0, "far": 0}
    page.locator("#construction-toggle").evaluate("e=>e.click()")
    assert page.evaluate("(" + markers + ")().length") == 0
    page.locator("#construction-toggle").evaluate("e=>e.click()")
    page.locator("#fast-route-toggle").evaluate("e=>e.click()")
    page.locator("#recommended-route-toggle").evaluate("e=>e.click()")
    assert page.evaluate("(" + markers + ")().length") == 0
    page.locator("#fast-route-toggle").evaluate("e=>e.click()")
    assert page.evaluate("(" + markers + ")().length") == 1
    page.locator("#map").scroll_into_view_if_needed()
    page.wait_for_function("!window.constructionMap.getView().getAnimating()")
    page.wait_for_function("""() => {
      const map=window.constructionMap;
      map.renderSync();
      const marker=map.getLayers().getArray()
        .flatMap(l=>l.getSource?.().getFeatures?.() ?? [])
        .find(f=>f.get('kind')==='construction');
      const pixel=map.getPixelFromCoordinate(marker.getGeometry().getCoordinates());
      return map.getFeaturesAtPixel(pixel).some(f=>f.get('kind')==='construction');
    }""")
    page.evaluate("""() => {
      const map=window.constructionMap;
      const marker=map.getLayers().getArray()
        .flatMap(l=>l.getSource?.().getFeatures?.() ?? [])
        .find(f=>f.get('kind')==='construction');
      const coordinate=marker.getGeometry().getCoordinates();
      map.dispatchEvent({type:'singleclick',coordinate,
        pixel:map.getPixelFromCoordinate(coordinate)});
    }""")
    assert "Project 123" in page.locator(".map-stop-menu").inner_text()
    assert "unverified" in page.locator(".map-stop-menu").inner_text()
    page.screenshot(path=".hack/construction-icon-popup.png")
    page.unroute("**/api/construction-sites?**")
    page.unroute("**/vendor/ol.js", capture)
