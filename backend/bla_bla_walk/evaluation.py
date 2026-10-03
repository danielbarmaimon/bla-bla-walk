"""Eligibility and pure cached-metric rescoring using the approved T2 baseline."""

import json
import math
from pathlib import Path

from .interfaces import TripComparison, WalkingEvidence
from .walking_metrics import finite, route_metrics

RULES_PATH = Path(__file__).resolve().parents[2] / "config/routing-rules.json"
CRITERIA = ("shade", "duration", "water")


def load_rules():
    """Load the production policy; numerical acceptance fixtures remain pinned."""
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def eligibility(route, tolerance):
    lengths = (
        route.distance_metres,
        route.shaded_metres,
        route.unshaded_metres,
        route.unknown_metres,
    )
    if (
        any(not finite(v) or v < 0 for v in (*lengths, route.planned_stop_minutes))
        or route.distance_metres == 0
        or abs(sum(lengths[1:]) - lengths[0]) > tolerance
    ):
        return "invalid_data"
    if route.access_state == "confirmed_blocked":
        return "blocked"
    if route.access_state != "checked_open":
        return "needs_verification"
    if not route.inside_calculation_coverage:
        return "unsupported"
    return "eligible"


def compare_routes(
    routes: list[WalkingEvidence],
    weights=None,
    *,
    rules=None,
    extra_time_limit_minutes=None,
) -> TripComparison:
    """Rescore evidence without any shade calls; retain excluded cards and reasons.

    Optional user time limits can tighten the absolute prototype limit.
    No default five-minute preference is imposed by the pending proposal.
    """
    rules = dict(load_rules() if rules is None else rules)
    speed = rules["walking_speed_m_per_s"]
    if not finite(speed) or speed <= 0:
        raise ValueError("Walking speed must be positive and finite")
    if extra_time_limit_minutes is not None:
        if not finite(extra_time_limit_minutes) or extra_time_limit_minutes < 0:
            raise ValueError("Extra time limit must be nonnegative and finite")
        rules["max_extra_duration_minutes"] = min(
            rules["max_extra_duration_minutes"], extra_time_limit_minutes
        )
    if len({r.id for r in routes}) != len(routes):
        raise ValueError("Route IDs must be unique")
    weights = rules["default_weights"] if weights is None else weights
    statuses = {r.id: eligibility(r, rules["arithmetic_tolerance"]) for r in routes}
    result = TripComparison(status="no_eligible_routes", route_statuses=statuses)
    statuses = result.route_statuses
    candidates = [r for r in routes if statuses[r.id] == "eligible"]
    reference = min(
        candidates,
        key=lambda r: (r.distance_metres, r.planned_stop_minutes),
        default=None,
    )
    for route in routes:
        if statuses[route.id] != "invalid_data":
            result.metrics[route.id] = route_metrics(route, rules, reference)
        if statuses[route.id] == "eligible":
            metrics = result.metrics[route.id]
            if (
                metrics["extra_distance_fraction"]
                > rules["max_extra_distance_fraction"] + rules["arithmetic_tolerance"]
                or metrics["extra_minutes"]
                > rules["max_extra_duration_minutes"] + rules["arithmetic_tolerance"]
            ):
                statuses[route.id] = "detour_limit"
        result.reasons[route.id] = (
            [] if statuses[route.id] == "eligible" else [statuses[route.id]]
        )
    result.manual_choices = sorted(
        r.id for r in candidates if statuses[r.id] == "eligible"
    )
    valid = (
        isinstance(weights, dict)
        and set(weights) == set(CRITERIA)
        and all(finite(v) and v >= 0 for v in weights.values())
    )
    total = sum(weights.values()) if valid else math.nan
    if not valid or not math.isfinite(total):
        result.status = "invalid_preferences"
    elif not result.manual_choices:
        result.status = "no_eligible_routes"
    else:
        for route_id in result.manual_choices:
            metrics = result.metrics[route_id]
            contributions = {
                name: weights[name] / total * metrics["benefits"][name] if total else 0
                for name in CRITERIA
            }
            result.contributions[route_id] = contributions
            result.scores[route_id] = sum(contributions.values())
            result.reasons[route_id] = [
                "incomplete_" + name
                for name in CRITERIA
                if weights[name] > 0 and not metrics[name + "_complete"]
            ]
        if total == 0:
            result.status = "no_preferences"
        elif any(result.reasons[r] for r in result.manual_choices):
            result.status = "insufficient_evidence"
        else:
            highest = max(result.scores.values())
            winners = [
                r
                for r in result.manual_choices
                if highest - result.scores[r] <= rules["tie_tolerance"]
            ]
            result.status = "tie" if len(winners) > 1 else "recommended"
            result.winner = winners[0] if len(winners) == 1 else None
    result.explanation = explanation(result)
    return result


def explanation(result):
    if result.status == "recommended":
        return (
            f"{result.winner} has the highest fixed-range weighted benefit "
            "among eligible routes. Contributions show shade, duration and "
            "water separately; manual choice remains available."
        )
    return {
        "tie": "Eligible scores tie within tolerance; choose manually.",
        "insufficient_evidence": (
            "An eligible route lacks evidence for an active criterion; scores "
            "are incomplete lower bounds and no winner is recommended."
        ),
        "no_preferences": (
            "All weights are zero; no winner is recommended. "
            "Choose an eligible route manually."
        ),
        "invalid_preferences": (
            "Supply exactly shade, duration and water with finite nonnegative weights."
        ),
        "no_eligible_routes": (
            "No eligible route; inspect each route's reason. Manual choice "
            "cannot override access or coverage constraints."
        ),
    }[result.status]


def compare_choices(routes, *, rules=None, extra_time_limit_minutes=None):
    """Walking-only proposed modes alongside the unchanged approved baseline.

    These mode views do not admit transit or replace baseline weights. Fastest
    uses actual total minutes (no clamped duration score ties at long durations).
    """
    policy = load_rules() if rules is None else rules
    baseline = compare_routes(routes, rules=policy)
    fastest = compare_routes(
        routes, {"shade": 0, "duration": 1, "water": 0}, rules=policy
    )
    if fastest.status in ("recommended", "tie"):
        minimum = min(
            fastest.metrics[r]["duration_minutes"] for r in fastest.manual_choices
        )
        winners = [
            r
            for r in fastest.manual_choices
            if abs(fastest.metrics[r]["duration_minutes"] - minimum)
            <= policy["tie_tolerance"]
            * (
                policy["duration_benefit_range_minutes"][1]
                - policy["duration_benefit_range_minutes"][0]
            )
        ]
        fastest.status = "tie" if len(winners) > 1 else "recommended"
        fastest.winner = winners[0] if len(winners) == 1 else None
        fastest.explanation = (
            "Shortest complete total walking-plus-stop duration among eligible "
            "routes; equal durations retain manual choice. Transit data unavailable."
        )
    shade = compare_routes(
        routes,
        {"shade": 1, "duration": 0, "water": 0},
        rules=policy,
        extra_time_limit_minutes=extra_time_limit_minutes,
    )
    if shade.status == "recommended":
        shade.explanation = (
            "Highest current shaded fraction over full route length within the "
            "stated detour limits. Unknown and night earn no credit; "
            "building-model estimates are approximate."
        )
    return {"baseline": baseline, "fastest_overall": fastest, "more_shade": shade}
