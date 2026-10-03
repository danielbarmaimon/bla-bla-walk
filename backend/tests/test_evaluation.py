"""Production parity with all approved T2 cases and conservative proposed modes."""

import json
from pathlib import Path

import pytest
from bla_bla_walk.evaluation import compare_choices, compare_routes, load_rules
from bla_bla_walk.interfaces import WalkingEvidence

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "data/scenarios.json").read_text())


def routes_for(case):
    routes = []
    for base in FIXTURE["base_routes"]:
        patch = case.get("route_patches", {}).get(base["id"], {})
        routes.append(
            WalkingEvidence.model_validate(
                {
                    **base,
                    **patch,
                    "water": {**base["water"], **patch.get("water", {})},
                }
            )
        )
    return routes


def check_numbers(actual, expected):
    for key, value in expected.items():
        if isinstance(value, dict):
            check_numbers(actual[key], value)
        else:
            assert actual[key] == pytest.approx(
                value, abs=FIXTURE["rules"]["arithmetic_tolerance"]
            )


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda c: c["id"])
def test_approved_examples_in_production(case):
    routes = routes_for(case)
    result = compare_routes(routes, case.get("weights"))
    expected = case["expected"]
    assert result.status == expected["status"]
    assert result.winner == expected["winner"]
    assert result.route_statuses == expected["route_statuses"]
    assert set(result.scores) == set(expected["scores"])
    check_numbers(result.scores, expected["scores"])
    for key in ("metrics", "contributions", "detour"):
        if key in expected:
            check_numbers(
                result.metrics if key == "detour" else getattr(result, key),
                expected[key],
            )
    reverse = compare_routes(list(reversed(routes)), case.get("weights"))
    assert reverse == result
    assert result.model_validate_json(result.model_dump_json()) == result
    assert result.manual_choices == sorted(
        r for r, status in result.route_statuses.items() if status == "eligible"
    )


def test_production_config_preserves_pinned_policy():
    rules = load_rules()
    assert {k: rules[k] for k in FIXTURE["rules"]} == FIXTURE["rules"]


def test_proposed_modes_preserve_baseline_and_require_evidence():
    routes = routes_for({})
    modes = compare_choices(routes)
    assert modes["baseline"] == compare_routes(routes)
    assert modes["fastest_overall"].winner == "A"
    assert modes["more_shade"].winner == "B"
    routes[1].shade_time_matches_request = False
    modes = compare_choices(routes)
    assert modes["more_shade"].status == "insufficient_evidence"
    assert modes["fastest_overall"].winner == "A"
    assert all(m.transit_status == "unavailable" for m in modes.values())


def test_fastest_uses_total_duration_beyond_normalization_range():
    routes = routes_for({})
    for r in routes:
        r.planned_stop_minutes = 30
    assert (
        compare_routes(routes, {"shade": 0, "duration": 1, "water": 0}).status == "tie"
    )
    assert compare_choices(routes)["fastest_overall"].winner == "A"
    routes[0].duration_complete = False
    assert compare_choices(routes)["fastest_overall"].status == "insufficient_evidence"


def test_optional_user_limit_only_tightens_absolute_limit():
    routes = routes_for({})
    routes[1].planned_stop_minutes = 1
    assert compare_choices(routes)["more_shade"].winner == "B"
    assert (
        compare_choices(routes, extra_time_limit_minutes=5)["more_shade"].winner == "A"
    )
    assert (
        compare_choices(routes, extra_time_limit_minutes=100)["more_shade"].winner
        == "B"
    )
    with pytest.raises(ValueError):
        compare_choices(routes, extra_time_limit_minutes=-1)


@pytest.mark.parametrize(
    "weights",
    [
        None,
        [],
        {"shade": True, "duration": 0, "water": 0},
        {"shade": float("inf"), "duration": 0, "water": 0},
    ],
)
def test_invalid_preferences_and_defaults(weights):
    assert compare_routes(routes_for({}), weights).status == (
        "recommended" if weights is None else "invalid_preferences"
    )


def test_duplicate_ids_cannot_overwrite_evidence():
    routes = routes_for({})
    routes[1].id = routes[0].id
    with pytest.raises(ValueError, match="unique"):
        compare_routes(routes)


def test_excluded_routes_retain_metrics_and_cautions():
    routes = routes_for({})
    routes[0].access_state = "confirmed_blocked"
    routes[0].construction_caution = True
    routes[1].access_state = "unknown"
    result = compare_routes(routes)
    assert result.manual_choices == []
    assert result.metrics["A"]["construction_caution"]
    assert result.metrics["B"]["unknown_percentage"] == 0
    assert result.reasons == {"A": ["blocked"], "B": ["needs_verification"]}
