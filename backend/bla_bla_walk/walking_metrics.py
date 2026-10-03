"""Fixed-range benefits and auditable full-length walking metrics for T5."""

import math


def finite(value):
    return (
        isinstance(value, (float, int))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def water_benefit(water, rules):
    fresh = (
        finite(water.age_hours)
        and 0 <= water.age_hours <= rules["water_evidence_max_age_hours"]
    )
    if not fresh or not water.evidence_complete:
        return False, 0
    if water.state == "fresh_absent":
        return True, 0
    flags = (water.drinking, water.accessible, water.operational)
    if (
        water.state != "fresh_available"
        or any(v is None for v in flags)
        or not finite(water.extra_distance_metres)
        or water.extra_distance_metres < 0
        or not water.extra_distance_included
    ):
        return False, 0
    return True, int(
        all(flags)
        and water.extra_distance_metres <= rules["water_max_extra_distance_metres"]
    )


def route_metrics(route, rules, reference=None):
    walking = route.distance_metres / rules["walking_speed_m_per_s"] / 60
    duration = walking + route.planned_stop_minutes
    current = (
        route.shade_state == "current"
        and route.shade_time_matches_request
        and route.shade_geometry_matches_request
        and (
            route.sampled_speed_m_per_s is None
            or route.sampled_speed_m_per_s == rules["walking_speed_m_per_s"]
        )
        and (
            route.sampled_distance_metres is None
            or route.sampled_distance_metres == route.distance_metres
        )
        and (
            route.sampled_stop_minutes is None
            or route.sampled_stop_minutes == route.planned_stop_minutes
        )
    )
    water_complete, water = water_benefit(route.water, rules)
    known = (route.shaded_metres + route.unshaded_metres) / route.distance_metres
    low, high = rules["duration_benefit_range_minutes"]
    metrics = {
        "distance_metres": route.distance_metres,
        "shaded_metres": route.shaded_metres,
        "unshaded_metres": route.unshaded_metres,
        "unknown_metres": route.unknown_metres,
        "walking_minutes": walking,
        "stop_minutes": route.planned_stop_minutes,
        "waiting_minutes": 0,
        "ride_minutes": 0,
        "transfer_minutes": 0,
        "duration_minutes": duration,
        "shade_fraction": route.shaded_metres / route.distance_metres,
        "unshaded_fraction": route.unshaded_metres / route.distance_metres,
        "unknown_fraction": route.unknown_metres / route.distance_metres,
        "known_shade_fraction": known,
        "shade_complete": current
        and known + rules["arithmetic_tolerance"]
        >= rules["minimum_known_shade_fraction"],
        "water_complete": water_complete,
        "duration_complete": route.duration_complete,
        "benefits": {
            "shade": route.shaded_metres / route.distance_metres if current else 0,
            "duration": max(0, min(1, 1 - (duration - low) / (high - low)))
            if route.duration_complete
            else 0,
            "water": water,
        },
        "construction_caution": route.construction_caution,
        "shade_state": route.shade_state,
        "shade_time_matches_request": route.shade_time_matches_request,
        "shade_geometry_matches_request": route.shade_geometry_matches_request,
        "water_state": route.water.state,
        "water_evidence": route.water.model_dump(mode="json"),
        "provenance": route.provenance.model_dump(mode="json")
        if route.provenance
        else None,
        "samples": [sample.model_dump(mode="json") for sample in route.samples],
        "night_metres": sum(
            sample.end_metres - sample.start_metres
            for sample in route.samples
            if sample.state.name == "NIGHT"
        ),
    }
    for name in ("shade", "unshaded", "unknown"):
        metrics[name + "_percentage"] = 100 * metrics[name + "_fraction"]
    if reference is not None:
        metrics.update(
            extra_metres=max(0, route.distance_metres - reference.distance_metres),
            extra_minutes=max(
                0,
                duration
                - reference.distance_metres / rules["walking_speed_m_per_s"] / 60
                - reference.planned_stop_minutes,
            ),
            extra_distance_fraction=max(
                0, route.distance_metres / reference.distance_metres - 1
            ),
        )
    return metrics
