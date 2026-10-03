"""Exercise the actual browser map, independent of live source availability."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.browser


def open_map(page):
    """Wait for synthetic sources beside the saved walking pair."""
    page.goto(page.base_url)
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Example mode')"
    )
    assert page.locator("#features button").count() == 5
    for summary in page.locator("#features summary").all():
        summary.click()


def test_layers_provenance_and_missing_states(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    open_map(page)
    page.get_by_role("button", name="Sample sensor A").click()
    assert "28 °C" in page.locator("#details").inner_text()
    assert "Synthetic fixture" in page.locator("#details").inner_text()
    assert "01/10/2026" in page.locator("#details").inner_text()
    toggle = page.locator("#layers").get_by_role(
        "checkbox", name="Temperature", exact=False
    )
    toggle.uncheck()
    assert not toggle.is_checked()
    # Source inspection remains available when its map layer is hidden.
    assert "Sample sensor A" in page.locator("#details").inner_text()
    toggle.check()
    page.get_by_role("button", name="Sample sensor B").click()
    assert "Unknown / no value" in page.locator("#details").inner_text()
    page.get_by_role("button", name="Sample fountain A").focus()
    page.keyboard.press("Enter")
    assert "Drinking water" in page.locator("#details").inner_text()
    assert "unknown" in page.locator("#details").inner_text()
    page.wait_for_function(
        "document.querySelector('#basemap-status').textContent.includes('unavailable')"
    )
    assert not errors


def test_offline_mode_uses_only_same_origin_requests(browser_page):
    if (
        not (ROOT / ".cache/basemap/manifest.json").exists()
        or not (ROOT / ".cache/provider-snapshot.json").exists()
    ):
        pytest.skip("Offline browser check needs scripts/prepare_offline.py downloads")
    page = browser_page
    page.wait_for_load_state("networkidle")
    external = []
    page.on(
        "request",
        lambda request: (
            external.append(request.url) if request.url.startswith("https://") else None
        ),
    )
    page.goto(page.base_url + "/?mode=offline")
    page.wait_for_function(
        "document.querySelector('#basemap-status').textContent"
        ".includes('downloaded offline')"
    )
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Offline mode')"
    )
    page.locator("#features summary").first.click()
    page.locator("#features button").first.click()
    assert "Provider data" in page.locator("#details").inner_text()
    assert "Offline mode" in page.locator("#mode-notice").inner_text()
    assert (
        page.locator("#features").bounding_box()["height"]
        < page.viewport_size["height"]
    )
    assert not external
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_missing_offline_tiles_explain_saved_coverage(browser_page):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 900})
    page.route("**/tiles/**", lambda route: route.fulfill(status=404))
    page.goto(page.base_url + "/?mode=offline")
    page.wait_for_function(
        "document.querySelector('#basemap-status').textContent"
        ".includes('not downloaded')"
    )
    page.unroute("**/tiles/**")


def test_api_failure_and_recovery(browser_page):
    page = browser_page
    page.route(
        "**/api/map**", lambda route: route.fulfill(status=503, body="Unavailable")
    )
    page.goto(page.base_url)
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent"
        ".includes('Map data unavailable')"
    )
    assert page.locator("#features button").count() == 0
    page.unroute("**/api/map**")
    page.reload()
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Example mode')"
    )
    assert page.locator("#features button").count() == 5


def test_narrow_screen_and_browser_contract(browser_page):
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    open_map(page)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.get_by_role("button", name="Use Basel SBB").click()
    assert page.locator("#map").bounding_box()["height"] >= 400
    result = page.evaluate("""async () => {
      const {parseSnapshot} = await import('/src/api.js');
      const fixture = await (await fetch('/api/map')).json();
      parseSnapshot(fixture);
      const older = structuredClone(fixture);
      delete older.mode;
      if (parseSnapshot(older).mode !== 'fixture') return false;
      const bad = structuredClone(fixture);
      bad.layers[0].features[0].geometry.coordinates = [181, 47];
      try { parseSnapshot(bad); return false; } catch { return true; }
    }""")
    assert result
