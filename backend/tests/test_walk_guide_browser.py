"""Tips open while calculation is pending; completion shows the walking guide."""

import pytest
from conftest import open_example

pytestmark = pytest.mark.browser


def test_completion_modal_default_and_left_guide(browser_page):
    page = browser_page
    pending = []
    page.route("**/api/comparison", lambda route: pending.append(route))
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    with page.expect_request("**/api/comparison"):
        page.locator("#calculate-journey").click()
    page.locator("#preparation-tips").wait_for(state="visible")
    assert page.locator("#planner-form").is_visible()
    assert "background" in page.locator("#tip-calculation-status").inner_text()
    assert page.locator("#calculate-journey").is_disabled()
    assert page.locator("#trip-tips .tip-card").count() == 4
    assert page.locator("#trip-tips img").count() == 4
    assert (
        page.locator("#trip-tips").evaluate("e=>getComputedStyle(e).listStyleType")
        == "none"
    )
    page.screenshot(path=".hack/tips-cards-desktop.png")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=".hack/tips-cards-mobile.png")
    assert page.locator("#preparation-tips").evaluate("e=>e.scrollWidth<=e.clientWidth")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.locator("#close-tips").click()
    # Closing tips must not cancel the pending calculation or reopen on completion.
    assert page.locator("#calculate-journey").is_disabled()
    pending.pop().fulfill(status=503, json={"detail": "Test comparison unavailable"})
    page.wait_for_function("!document.querySelector('#calculate-journey').disabled")
    assert page.locator("#planner-form").is_hidden()
    assert page.locator(".planner #step-list").is_visible()
    assert page.locator("#shade-mode").get_attribute("aria-pressed") == "true"
    assert page.locator("#landmark-toggle").get_attribute("aria-pressed") == "true"
    assert page.locator("#steps-summary").inner_text()
    assert page.locator("#preparation-tips").is_hidden()
    page.locator("#fast-mode").click()
    assert page.locator("#preparation-tips").is_hidden()
    page.locator("#shade-mode").click()
    assert page.locator("#preparation-tips").is_hidden()
    assert page.locator("#shade-mode").get_attribute("aria-pressed") == "true"
    page.locator("#back-to-plan").click()
    assert page.locator("#planner-form").is_visible()
    with page.expect_request("**/api/comparison"):
        page.locator("#calculate-journey").click()
    assert page.locator("#preparation-tips").is_visible()
    pending.pop().fulfill(status=503, json={"detail": "Test comparison unavailable"})
    page.wait_for_function("!document.querySelector('#calculate-journey').disabled")
    assert page.locator("#preparation-tips").is_visible()
    assert "ready" in page.locator("#tip-calculation-status").inner_text()
    page.keyboard.press("Escape")
    assert page.locator("#preparation-tips").is_hidden()
    page.unroute("**/api/comparison")


def test_rest_candidates_grouped_and_short_walk_has_none(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    result = page.evaluate("""async () => {
      const {mountJourneySteps, journeyItems} = await import('/src/journey-steps.js');
      const route = {id:'guide',geometry:{type:'LineString',
        coordinates:[[7.59,47.55],[7.63,47.55]]},
        route:{distance_m:3000,duration_s:1800}};
      const amenities = [0.49,0.5,0.51,0.1].map((fraction,i)=>({
        fraction,distance:10,feature:{kind:i===1?'fountain':'rest',
        rest_type:i===1?null:'bench',label:'Candidate '+i}}));
      const container = document.createElement('div');document.body.append(container);
      mountJourneySteps(container).update(route,{amenities});
      const result = {text:container.textContent,
        collapsed:container.querySelector('details')?.open===false,
        groups:container.querySelectorAll('details').length};
      route.route.duration_s=800;
      result.short = journeyItems(route,amenities).some(item=>item.amenities?.length);
      container.remove();return result;
    }""")
    assert result["collapsed"] and result["groups"] == 1
    assert "Candidate 0" in result["text"] and "Candidate 2" in result["text"]
    assert "Candidate 3" not in result["text"]
    assert not result["short"]
