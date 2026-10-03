"""Exercise the actual browser map, independent of live source availability."""

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def browser_page():
    """Start the documented server and an installed Chromium for interactions."""
    executable = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium")
    if not executable:
        pytest.skip("Browser checks need installed Chromium or CHROMIUM_PATH")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "bla_bla_walk.main:app",
            "--app-dir",
            "backend",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                with urllib.request.urlopen(url, timeout=1):
                    break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError("Test API failed to start") from None
                time.sleep(0.05)
        else:
            raise RuntimeError("Test API did not become ready")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=executable)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(10_000)
            page.base_url = url
            # Real basemap request is checked separately; failure is deterministic here.
            page.route("https://wmts.geo.bs.ch/**", lambda route: route.abort())
            yield page
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)


def open_map(page):
    """Wait for the actual API round trip and three keyboard sample controls."""
    page.goto(page.base_url)
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Example mode')"
    )
    assert page.locator("#features button").count() == 3
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
    toggle = page.get_by_role("checkbox", name="Temperature", exact=False)
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
    page.locator("#show-route").click()
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")


def test_missing_offline_tiles_explain_saved_coverage(browser_page):
    page = browser_page
    page.route("**/tiles/**", lambda route: route.fulfill(status=404))
    page.goto(page.base_url + "/?mode=offline")
    page.locator("#show-route").click()
    page.wait_for_function(
        "document.querySelector('#basemap-status').textContent"
        ".includes('not downloaded')"
    )
    page.unroute("**/tiles/**")


def test_offline_missing_resources_never_request_external_urls(browser_page):
    page = browser_page
    external = []

    def inspect(request):
        if not request.url.startswith(page.base_url + "/"):
            external.append(request.url)

    page.on("request", inspect)
    page.route("**/api/map**", lambda route: route.fulfill(status=503))
    page.route("**/tiles/**", lambda route: route.fulfill(status=404))
    try:
        page.goto(page.base_url + "/?mode=offline")
        page.wait_for_function(
            "document.querySelector('#mode-notice').textContent"
            ".includes('Map data unavailable')"
        )
        page.locator("#show-route").click()
        page.wait_for_function(
            "document.querySelector('#basemap-status').textContent"
            ".includes('not downloaded')"
        )
        assert page.locator("#pet-layer-toggle").is_disabled()
        assert page.locator("#calculate-comparison").is_disabled()
        assert not external
    finally:
        page.remove_listener("request", inspect)
        page.unroute("**/api/map**")
        page.unroute("**/tiles/**")


@pytest.mark.parametrize("mode", ["online", "offline"])
def test_comparison_controls_unknowns_failure_and_keyboard(browser_page, mode):
    """Synthetic calculation responses exercise UI only, not real shade accuracy."""
    from types import SimpleNamespace
    from unittest.mock import Mock

    from bla_bla_walk.adapters.routes import load_demo_routes
    from bla_bla_walk.evaluation import compare_choices
    from bla_bla_walk.interfaces import JourneyRequest, MapSnapshot
    from bla_bla_walk.journey import JourneyService
    from test_journey import completed
    from test_route_shade import DEPARTURE, response

    service = JourneyService(
        SimpleNamespace(
            root=ROOT,
            context=Mock(return_value=("test",)),
            respond=Mock(side_effect=lambda request: (response(request), False)),
        )
    )
    result = completed(service, JourneyRequest(mode="online", departure=DEPARTURE))
    for evidence in result.evidence:
        for sample in evidence.samples:
            sample.metadata.geometry_version = (
                "model-" + "a" * 64 + ";buildings=" + "b" * 64
            )
    service.executor.shutdown()
    snapshot = MapSnapshot(
        mode=mode, generated_at=DEPARTURE, layers=[load_demo_routes()]
    )
    page = browser_page
    calls = []
    failed = False

    def comparison(route):
        body = route.request.post_data_json
        calls.append(body)
        if failed:
            route.fulfill(status=503)
        else:
            from datetime import datetime

            value = result.model_copy(
                update={
                    "departure": datetime.fromisoformat(
                        body["departure"].replace("Z", "+00:00")
                    )
                }
            )
            route.fulfill(json=value.model_dump(mode="json"))

    page.route(
        "**/api/map**",
        lambda route: route.fulfill(json=snapshot.model_dump(mode="json")),
    )
    page.route("**/api/comparison", comparison)
    try:
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(page.base_url + f"/?mode={mode}")
        page.locator("#calculate-comparison").wait_for(state="visible")
        page.wait_for_function(
            "!document.querySelector('#calculate-comparison').disabled"
        )
        assert page.locator(".comparison-primary:disabled").count() == 2
        page.locator("#departure-time").fill("2026-10-03T12:00")
        page.locator("#calculate-comparison").focus()
        page.keyboard.press("Enter")
        page.wait_for_function(
            "document.querySelector('#route-options').textContent"
            ".includes('Locally calculated')"
        )
        assert "No eligible route" in page.locator("#route-options").inner_text()
        assert page.locator(".comparison-primary:disabled").count() == 2
        assert "Transit" in page.locator("#preference-note").inner_text()
        page.locator(".comparison-card summary").first.click()
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.locator("#shade-mode").click()
        count = len(calls)
        page.locator("#fast-mode").click()
        assert len(calls) == count
        page.locator("#shade-detour-limit").select_option("5")
        page.wait_for_function(
            "document.querySelector('#route-options').textContent"
            ".includes('Locally calculated')"
        )
        assert calls[-1]["extra_time_limit_minutes"] == 5
        # Explicit synthetic access evidence tests eligible manual actions.
        checked = [
            item.model_copy(update={"access_state": "checked_open"})
            for item in result.evidence
        ]
        result.comparison = compare_choices(checked)
        page.locator("#calculate-comparison").click()
        page.wait_for_function(
            "document.querySelectorAll('.comparison-primary:disabled').length === 0"
        )
        page.locator(".comparison-primary").last.focus()
        page.keyboard.press("Enter")
        assert (
            page.locator(".comparison-primary[aria-pressed='true']").inner_text()
            == "Chosen route"
        )
        assert page.locator(".comparison-primary[aria-pressed='true']").evaluate(
            "element => element === document.activeElement"
        )
        page.locator("#shade-layer-toggle").uncheck()
        assert not page.locator("#shade-layer-toggle").is_checked()
        failed = True
        page.locator("#departure-now").click()
        page.wait_for_function(
            "document.querySelector('#comparison-control-status').textContent.includes('unavailable')"
        )
        assert "Locally calculated" not in page.locator("#route-options").inner_text()
    finally:
        page.unroute("**/api/map**")
        page.unroute("**/api/comparison")


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
    assert page.locator("#features button").count() == 3


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
