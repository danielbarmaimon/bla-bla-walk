"""Real search controls: selection, keyboard and explicit offline behaviour."""

import pytest

pytestmark = pytest.mark.browser


def test_both_fields_choose_addresses(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    payload = {
        "places": [
            {
                "id": "address-test",
                "name": "Public venue · Basel",
                "lon": 7.606272,
                "lat": 47.537456,
            }
        ],
        "status": "available",
    }
    page.route("**/api/addresses", lambda route: route.fulfill(json=payload))
    page.goto(page.base_url + "/?mode=fixture")
    origin = page.locator("#origin-input")
    origin.fill("Public venue")
    page.locator("#origin-suggestions button").wait_for()
    origin.press("ArrowDown")
    page.keyboard.press("Enter")
    assert origin.input_value() == "Public venue · Basel"
    page.locator("#destination-input").fill("Public venue")
    page.locator("#suggestions button").click()
    assert page.locator("#destination-input").input_value() == "Public venue · Basel"
    assert not errors


def test_failure_and_offline_no_address_requests(browser_page):
    page = browser_page
    page.route(
        "**/api/addresses",
        lambda route: route.fulfill(status=503, json={"detail": "down"}),
    )
    page.goto(page.base_url + "/?mode=fixture")
    page.locator("#destination-input").fill("No provider")
    page.wait_for_function(
        "document.querySelector('#destination-status').textContent.includes('unavailable')"
    )
    requests = []
    page.on(
        "request",
        lambda request: (
            requests.append(request.url) if "/api/addresses" in request.url else None
        ),
    )
    page.goto(page.base_url + "/?mode=offline")
    page.locator("#destination-input").fill("Public venue")
    page.wait_for_timeout(700)
    assert "Offline" in page.locator("#destination-status").inner_text()
    assert not requests


def test_root_page_defaults_to_online_address_search(browser_page):
    page = browser_page
    payload = page.request.get(f"{page.base_url}/api/map?mode=fixture").json()
    payload["mode"] = "online"
    page.route("**/api/map?mode=online", lambda route: route.fulfill(json=payload))
    requests = []

    def addresses(route):
        requests.append(route.request.post_data_json)
        route.fulfill(json={"places": [], "status": "available"})

    page.route("**/api/addresses", addresses)
    page.goto(f"{page.base_url}/")
    page.locator("#origin-input:not([disabled])").wait_for()
    page.locator("#origin-input").fill("Centralbahnplatz 1")
    page.wait_for_function(
        "document.querySelector('#origin-status').textContent"
        ".includes('No address or saved landmark found')"
    )
    assert requests[-1]["mode"] == "online"
    page.wait_for_function(
        "document.querySelector('#mode-notice').textContent.includes('Online mode')"
    )
    page.unroute("**/api/map?mode=online")
    page.unroute("**/api/addresses", addresses)
