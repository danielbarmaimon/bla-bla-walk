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


@pytest.fixture(autouse=True)
def walking_choices_without_live_services(monkeypatch):
    """Route fixtures never add new external calls or cold city shade work."""
    monkeypatch.setattr("bla_bla_walk.adapters.walking.detour_routes", lambda *args: [])
    monkeypatch.setattr(
        "bla_bla_walk.walking_preferences.construction_sites", lambda *args: None
    )
    monkeypatch.setattr(
        "bla_bla_walk.walking_preferences.shade_fraction", lambda *args: None
    )


@pytest.fixture(autouse=True)
def dismiss_tips_in_unrelated_browser_scenarios(request):
    """The focused guide test covers the modal; other scenarios dismiss it."""
    if not request.node.get_closest_marker("browser"):
        return
    if request.node.name == "test_completion_modal_default_and_left_guide":
        return
    page = request.getfixturevalue("browser_page")
    page.add_init_script("""document.addEventListener('toggle', event => {
      if (event.target.id === 'preparation-tips' && event.newState === 'open')
        event.target.close();
    }, true);""")


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
            page = browser.new_page(
                viewport={"width": 1280, "height": 900}, timezone_id="Europe/Zurich"
            )
            page.set_default_timeout(10_000)
            page.base_url = url
            # Real basemap request is checked separately; failure is deterministic here.
            page.route("https://wmts.geo.bs.ch/**", lambda route: route.abort())
            # Basic UI tests must not start a minutes-long real shade job.
            # Journey tests override this with labelled synthetic evidence.
            page.route(
                "**/api/comparison**",
                lambda route: route.fulfill(
                    status=503,
                    json={"detail": "Shade unavailable in basic browser fixture"},
                ),
            )
            yield page
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=5)


def open_example(page, calculate=True):
    """Explicitly select the saved pair using the retained hidden fixture shortcut."""
    page.locator("#origin-input:not([disabled])").wait_for()
    page.locator("#try-example").dispatch_event("click")
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('mode')"
        " && !document.querySelector('#mode-notice').textContent.includes('Loading')"
    )
    if calculate:
        page.locator("#calculate-journey").click()
        page.locator(".comparison-card").first.wait_for(state="attached")
        page.locator("#preparation-tips").evaluate("e=>e.close()")
        page.locator("#information-sources").evaluate("e=>e.open=true")
