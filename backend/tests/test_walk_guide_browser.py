"""Route completion replaces the form, and rest candidates stay at pauses."""

import pytest
from conftest import open_example

pytestmark = pytest.mark.browser


def test_completion_modal_default_and_left_guide(browser_page):
    page = browser_page
    page.goto(page.base_url + "/?mode=fixture")
    open_example(page, calculate=False)
    page.locator("#calculate-journey").click()
    page.locator("#preparation-tips").wait_for(state="visible")
    assert page.locator("#planner-form").is_hidden()
    assert page.locator(".planner #step-list").is_visible()
    assert page.locator("#shade-mode").get_attribute("aria-pressed") == "true"
    assert page.locator("#landmark-toggle").get_attribute("aria-pressed") == "true"
    assert page.locator("#steps-summary").inner_text()
    page.locator("#close-tips").click()
    page.locator("#fast-mode").click()
    assert page.locator("#preparation-tips").is_hidden()
    page.locator("#shade-mode").click()
    assert page.locator("#preparation-tips").is_hidden()
    assert page.locator("#shade-mode").get_attribute("aria-pressed") == "true"
    page.locator("#back-to-plan").click()
    assert page.locator("#planner-form").is_visible()


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
