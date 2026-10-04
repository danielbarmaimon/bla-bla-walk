"""Start-page behavior: explicit trip submission and mobile pin selection."""

import pytest
from conftest import open_example

pytestmark = pytest.mark.browser


def test_empty_start_gps_denial_and_explicit_submission(browser_page):
    page = browser_page
    page.set_viewport_size({"width": 1280, "height": 900})
    page.add_init_script("""window.gpsCalls=0;
      Object.defineProperty(navigator,'geolocation',{value:{getCurrentPosition(ok,fail){
        window.gpsCalls++; fail({code:1});}}});""")
    requests = []

    def record(request):
        if request.method == "POST":
            requests.append(request)

    page.on("request", record)
    page.goto(page.base_url)
    page.locator("#try-example:not([disabled])").wait_for()
    assert page.locator("#origin-input").input_value() == ""
    assert page.locator("#destination-input").input_value() == ""
    assert page.locator("#calculate-journey").is_disabled()
    assert page.locator("#calculate-journey").inner_text() == "Calculate"
    assert page.locator("#departure-picker").is_hidden()
    assert page.evaluate("window.gpsCalls") == 0
    assert (
        page.locator(".map-screen").bounding_box()["x"]
        > page.locator(".planner").bounding_box()["x"]
    )
    page.locator("#gps-button").click()
    assert page.evaluate("window.gpsCalls") == 1
    assert "Enter or pin" in page.locator("#origin-status").inner_text()
    open_example(page, calculate=False)
    assert not requests
    assert page.locator("#calculate-journey").is_enabled()
    page.locator("#departure-later").click()
    assert page.locator("#departure-picker").is_visible()
    page.locator("#departure-now").click()
    assert page.locator("#departure-picker").is_hidden()
    page.locator("#calculate-journey").click()
    page.locator(".comparison-card").first.wait_for()
    page.locator("#destination-input").fill("New address")
    assert page.locator("#selected-journey").is_hidden()
    assert page.locator("#calculate-journey").is_disabled()
    page.remove_listener("request", record)


def test_departure_mode_change_clears_results_without_calculating(browser_page):
    page = browser_page
    page.goto(page.base_url)
    open_example(page)
    requests = []

    def record(request):
        requests.append(request)

    page.on("request", record)
    page.locator("#departure-later").focus()
    page.keyboard.press("Enter")
    assert page.locator("#departure-picker").is_visible()
    assert page.locator("#selected-journey").is_hidden()
    assert page.locator("#route-options").inner_text() == ""
    assert page.locator("#calculate-journey").is_enabled()
    assert page.locator("#departure-time").evaluate(
        "el => el === document.activeElement"
    )
    assert not any(request.method == "POST" for request in requests)
    page.remove_listener("request", record)


def test_mobile_pin_returns_to_form_without_implicit_start(browser_page):
    page = browser_page
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(page.base_url)
    page.locator("#try-example:not([disabled])").wait_for()
    assert page.locator(".map-screen").is_hidden()
    page.locator("#pick-destination").click()
    assert page.locator(".map-screen").is_visible()
    page.locator("#map").click(position={"x": 180, "y": 240})
    page.locator(".planner").wait_for(state="visible")
    assert page.locator(".planner").is_visible()
    assert page.locator("#destination-input").input_value() == "Pinned destination"
    assert page.locator("#origin-input").input_value() == ""
    assert page.locator("#calculate-journey").is_disabled()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_pending_trip_can_cancel_and_retry_without_duplicate_requests(browser_page):
    page = browser_page
    pending = []
    page.route(
        "**/api/walking-routes",
        lambda route: (
            pending.append(route)
            if route.request.method == "POST"
            else route.continue_()
        ),
    )
    page.route(
        "**/api/addresses",
        lambda route: route.fulfill(
            json={
                "places": [
                    {
                        "id": "new-end",
                        "name": "Another Basel destination",
                        "lon": 7.606272,
                        "lat": 47.537456,
                    }
                ],
                "status": "available",
            }
        ),
    )
    page.goto(page.base_url)
    open_example(page, calculate=False)
    page.locator("#destination-input").fill("Another Basel")
    page.locator("#suggestions button").click()
    assert not pending
    with page.expect_request(
        lambda request: (
            request.method == "POST" and "/api/walking-routes" in request.url
        )
    ):
        page.locator("#calculate-journey").evaluate(
            "button=>{button.click();button.click();}"
        )
    page.wait_for_timeout(100)
    assert len(pending) == 1
    assert page.locator("#calculate-journey").is_disabled()
    page.locator("#cancel-journey").click()
    assert page.locator("#calculate-journey").is_enabled()
    assert page.locator("#selected-journey").is_hidden()
    pending.pop().fulfill(status=503, json={"detail": "Old request failure"})
    page.wait_for_timeout(100)
    assert "cancelled" in page.locator("#trip-status").inner_text()
    with page.expect_request(
        lambda request: (
            request.method == "POST" and "/api/walking-routes" in request.url
        )
    ):
        page.locator("#calculate-journey").click()
    page.wait_for_timeout(100)
    assert len(pending) == 1
    pending.pop().fulfill(status=422, json={"detail": "Outside routing coverage"})
    page.wait_for_function(
        "document.querySelector('#trip-status').textContent.includes('Basel-Stadt')"
    )
    assert page.locator("#calculate-journey").is_enabled()
    page.unroute("**/api/walking-routes")
    page.unroute("**/api/addresses")
