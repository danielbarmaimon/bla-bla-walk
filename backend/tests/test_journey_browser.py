"""Exercise T6 UI with labelled synthetic calculation responses, never live claims."""

from datetime import UTC, datetime

import pytest
from bla_bla_walk.adapters.routes import load_demo_routes
from bla_bla_walk.evaluation import compare_choices, compare_routes
from bla_bla_walk.interfaces import ComparisonJob, MapSnapshot
from bla_bla_walk.route_shade import calculate_walking_evidence
from conftest import open_example
from test_comparison_api import LocalShade

pytestmark = pytest.mark.browser


def wire_calculation(page):
    routes = load_demo_routes()
    departure = datetime(2026, 10, 3, 12, tzinfo=UTC)
    shade = LocalShade()
    evidence = [
        calculate_walking_evidence(
            route,
            departure,
            lambda request: shade.respond(request)[0],
            access_state="checked_open" if index else "unknown",
        )
        for index, route in enumerate(routes.features)
    ]
    for route_evidence in evidence:
        for sample in route_evidence.samples:
            if sample.metadata:
                sample.metadata.geometry_version = (
                    "model-" + "a" * 64 + ";buildings=" + "b" * 64
                )
    job = ComparisonJob(
        id="synthetic-browser-validation",
        status="ready",
        departure_time=departure,
        completed_samples=len(shade.calls),
        total_samples=len(shade.calls),
        evidence=evidence,
        choices=compare_choices(evidence),
        explanation="Synthetic browser validation only; not real route evidence.",
    )
    requests = []

    def api(route):
        requests.append((route.request.method, route.request.url))
        result = job.model_copy(deep=True)
        if route.request.method == "DELETE":
            route.fulfill(status=204)
            return
        if route.request.url.endswith("/rescore"):
            preferences = route.request.post_data_json
            result.choices = compare_choices(
                evidence,
                extra_time_limit_minutes=preferences.get("extra_time_limit_minutes"),
            )
            result.choices["baseline"] = compare_routes(
                evidence, preferences.get("weights")
            )
        elif route.request.method == "POST":
            result.status = "running"
            result.choices = {}
            result.evidence = []
            result.completed_samples = 0
            result.explanation = "Synthetic calculation running"
        route.fulfill(
            status=202 if result.status == "running" else 200,
            json=result.model_dump(mode="json"),
        )

    page.route("**/api/comparison**", api)
    return job, requests


def test_journey_polling_eligibility_preferences_and_time_invalidation(browser_page):
    page = browser_page
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _, requests = wire_calculation(page)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.locator("#departure-later").click()
    page.locator("#departure-time").fill("2026-10-03T14:00")
    page.locator("#calculate-journey").focus()
    page.keyboard.press("Enter")
    page.wait_for_function(
        "document.querySelector('#comparison-control-status').textContent"
        ".includes('Synthetic browser validation')"
    )
    page.locator("#information-sources").evaluate("e=>e.open=true")
    assert page.locator(".comparison-primary:disabled").count() == 1
    assert (
        "needs verification"
        in page.locator(".comparison-card").first.inner_text().lower()
    )
    assert "Recommended" in page.locator(".comparison-card").last.inner_text()
    page.locator(".comparison-primary:not(:disabled)").click()
    assert (
        page.get_by_role("button", name="Chosen route", exact=True).get_attribute(
            "aria-pressed"
        )
        == "true"
    )
    assert page.evaluate("document.activeElement.textContent") == "Chosen route"
    page.locator("#information-sources").evaluate("e=>e.open=true")
    page.locator("#comparison-evidence summary").first.click()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#shade-mode").click()
    page.locator("#back-to-plan").click()
    page.locator("#information-sources").evaluate("e=>e.open=true")
    page.get_by_text("Advanced comparison settings", exact=True).click()
    page.locator("#shade-detour-limit").select_option("5")
    page.wait_for_function(
        "document.querySelector('#preference-note').textContent"
        ".includes('Highest current shaded fraction')"
    )
    page.locator("#balanced-mode").click()
    page.locator(".weight-controls summary").click()
    for name in ("shade", "duration", "water"):
        page.locator(f"#weight-{name}").evaluate(
            "input => { input.value = '0'; input.dispatchEvent(new Event('change')); }"
        )
    page.wait_for_function(
        "document.querySelector('#preference-note').textContent"
        ".includes('All weights are zero')"
    )
    assert (
        sum(
            method == "POST" and not url.endswith("/rescore")
            for method, url in requests
        )
        == 1
    )
    page.locator("#departure-time").fill("2026-10-03T15:00")
    assert page.locator("#selected-journey").is_hidden()
    assert page.locator("#calculate-journey").is_enabled()
    assert not errors
    page.unroute("**/api/comparison**")


def test_offline_journey_uses_only_same_origin_even_with_missing_tiles(browser_page):
    page = browser_page
    _, requests = wire_calculation(page)
    external = []
    snapshot = MapSnapshot(
        mode="offline", generated_at=datetime.now(UTC), layers=[load_demo_routes()]
    )
    page.route(
        "**/api/map?mode=offline",
        lambda route: route.fulfill(json=snapshot.model_dump(mode="json")),
    )
    page.route("**/tiles/**", lambda route: route.fulfill(status=404))

    def record(request):
        if not request.url.startswith(page.base_url):
            external.append(request.url)

    page.on("request", record)
    page.goto(page.base_url + "/?mode=offline")
    open_example(page, calculate=False)
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#comparison-control-status').textContent"
        ".includes('Synthetic browser validation')"
    )
    page.locator("#information-sources").evaluate("e=>e.open=true")
    page.locator(".comparison-secondary").last.click()
    page.wait_for_function(
        "document.querySelector('#basemap-status').textContent"
        ".includes('not downloaded')"
    )
    assert not external
    assert requests
    page.remove_listener("request", record)
    page.unroute("**/api/map?mode=offline")
    page.unroute("**/tiles/**")
    page.unroute("**/api/comparison**")


def test_missing_preparation_and_unsupported_pair_are_visible(browser_page):
    page = browser_page
    page.route(
        "**/api/addresses",
        lambda route: route.fulfill(json={"places": [], "status": "available"}),
    )
    page.route(
        "**/api/walking-routes",
        lambda route: (
            route.fulfill(status=503, json={"detail": "unavailable"})
            if route.request.method == "POST"
            else route.continue_()
        ),
    )
    page.route(
        "**/api/comparison",
        lambda route: route.fulfill(
            status=503,
            json={
                "detail": (
                    "Prepared shade inputs unavailable; "
                    "run local geometry and building preparation"
                )
            },
        ),
    )
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#comparison-control-status').textContent"
        ".includes('Prepared shade inputs unavailable')"
    )
    assert page.locator(".comparison-primary:disabled").count() == 2
    page.locator("#destination-input").fill("Museum")
    page.wait_for_selector("#suggestions button")
    page.locator("#suggestions button").first.click()
    assert page.locator("#calculate-journey").is_enabled()
    assert page.locator("#selected-journey").is_hidden()
    page.locator("#calculate-journey").click()
    page.wait_for_function(
        "document.querySelector('#trip-status').textContent.includes('unavailable')"
    )
    page.unroute("**/api/comparison")


def test_departure_change_discards_and_cancels_late_start_response(browser_page):
    page = browser_page
    pending = []
    cancelled = []

    def hold(route):
        if route.request.method == "DELETE":
            cancelled.append(route.request.url)
            route.fulfill(status=204)
        else:
            pending.append(route)

    page.route("**/api/comparison**", hold)
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.locator("#calculate-journey").click()
    page.locator("#departure-later").click()
    page.locator("#departure-time").fill("2026-10-04T14:00")
    assert pending
    job = ComparisonJob(
        id="late-synthetic-validation",
        status="running",
        departure_time=datetime(2026, 10, 3, 12, tzinfo=UTC),
        explanation="This old departure must never be displayed",
    )
    pending.pop().fulfill(status=202, json=job.model_dump(mode="json"))
    page.wait_for_timeout(150)
    assert cancelled
    assert (
        "Choose a departure"
        in page.locator("#comparison-control-status").text_content()
    )
    assert page.locator("#selected-journey").is_hidden()
    assert page.locator("#calculate-journey").is_enabled()
    page.unroute("**/api/comparison**")
