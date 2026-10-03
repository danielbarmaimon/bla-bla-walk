"""Distance/time sampling, uncertainty and separation from pure preference changes."""

import base64
from datetime import UTC, datetime, timedelta

import pytest
from bla_bla_walk.adapters.routes import load_demo_routes
from bla_bla_walk.evaluation import compare_choices, load_rules
from bla_bla_walk.interfaces import ShadeResponse, ShadeState, WalkingStop
from bla_bla_walk.route_shade import calculate_walking_evidence, intervals

DEPARTURE = datetime(2026, 10, 3, 12, tzinfo=UTC)


def response(request, state=ShadeState.SHADED, **changes):
    return ShadeResponse(
        bounds=request.bounds,
        width=2,
        height=2,
        states=base64.b64encode(bytes([state] * 4)).decode(),
        counts={
            "shaded": 4 if state == 2 else 0,
            "sunlit": 4 if state == 1 else 0,
            "unknown": 4 if state == 0 else 0,
            "night": 4 if state == 3 else 0,
        },
        shade={
            "requested_time": request.requested_time,
            "effective_time": request.requested_time,
            "geometry_version": "test-geometry",
            "resolution_m": 1,
        },
        model="building-shadow-approximation",
        availability="approximate",
        explanation="Synthetic analytic sample; building approximation",
        **changes,
    )


def short_route():
    route = load_demo_routes().features[0].model_copy(deep=True)
    route.route.distance_m = 100
    route.geometry.coordinates = route.geometry.coordinates[:2]
    return route


def test_arrival_times_and_stop_boundaries_preserve_distance():
    seen = []

    def calculate(request):
        seen.append(request)
        return response(request)

    stops = [WalkingStop(at_metres=25, minutes=2)]
    evidence = calculate_walking_evidence(
        short_route(), DEPARTURE, calculate, stops=stops
    )
    assert evidence.shaded_metres == pytest.approx(100)
    assert evidence.planned_stop_minutes == 2
    assert sum(
        s.end_metres - s.start_metres for s in evidence.samples
    ) == pytest.approx(100)
    for sample in evidence.samples:
        midpoint = (sample.start_metres + sample.end_metres) / 2
        assert sample.requested_time == DEPARTURE + timedelta(
            seconds=midpoint + (120 if midpoint > 25 else 0)
        )
        assert sample.metadata.effective_time == sample.requested_time
        assert sample.end_metres - sample.start_metres <= 25
    calls = len(seen)
    for _ in range(3):
        compare_choices([evidence])
    assert len(seen) == calls
    assert compare_choices([evidence])["baseline"].status == "no_eligible_routes"


@pytest.mark.parametrize("state", list(ShadeState))
def test_full_denominator_unknown_and_night(state):
    evidence = calculate_walking_evidence(
        short_route(),
        DEPARTURE,
        lambda req: response(req, state),
        access_state="checked_open",
    )
    assert evidence.shaded_metres == (100 if state == ShadeState.SHADED else 0)
    assert evidence.unshaded_metres == (100 if state == ShadeState.SUNLIT else 0)
    assert evidence.unknown_metres == (
        100 if state in (ShadeState.UNKNOWN, ShadeState.NIGHT) else 0
    )
    assert all(s.state == state for s in evidence.samples)
    result = compare_choices([evidence])["more_shade"]
    assert result.status == (
        "insufficient_evidence"
        if state in (ShadeState.UNKNOWN, ShadeState.NIGHT)
        else "recommended"
    )


@pytest.mark.parametrize(
    "mismatch", ["time", "geometry", "unknown", "unsupported", "bytes"]
)
def test_invalid_or_unavailable_response_cannot_gain_credit(mismatch):
    def calculate(request):
        result = response(request)
        if mismatch == "time":
            result.shade.effective_time += timedelta(seconds=1)
        elif mismatch == "geometry":
            result.shade.geometry_version = "unexpected"
        elif mismatch == "bytes":
            result.states = ""
        else:
            result.availability = mismatch
        return result

    evidence = calculate_walking_evidence(
        short_route(),
        DEPARTURE,
        calculate,
        geometry_version="test-geometry",
        access_state="checked_open",
    )
    assert evidence.shaded_metres == 0 and evidence.unknown_metres == 100
    assert compare_choices([evidence])["more_shade"].winner is None


def test_stops_at_start_end_and_repeated_points():
    points = [(0, 0), (0, 0), (50, 0), (100, 0)]
    samples = list(intervals(points, 120, 25, [WalkingStop(at_metres=42, minutes=1)]))
    assert sum(b - a for a, b, _ in samples) == pytest.approx(120)
    assert any(b == 42 for a, b, _ in samples)
    route = short_route()
    evidence = calculate_walking_evidence(
        route,
        DEPARTURE,
        response,
        stops=[
            WalkingStop(at_metres=0, minutes=2),
            WalkingStop(at_metres=100, minutes=3),
        ],
    )
    assert evidence.planned_stop_minutes == 5
    assert evidence.samples[0].requested_time > DEPARTURE + timedelta(minutes=2)
    assert evidence.samples[-1].requested_time < DEPARTURE + timedelta(minutes=5)


def test_invalid_inputs_and_budget_fail_before_calculation():
    route = short_route()
    with pytest.raises(ValueError, match="aware"):
        calculate_walking_evidence(route, DEPARTURE.replace(tzinfo=None), response)
    with pytest.raises(ValueError, match="Stops"):
        calculate_walking_evidence(
            route, DEPARTURE, response, stops=[WalkingStop(at_metres=101, minutes=1)]
        )
    with pytest.raises(ValueError, match="budget"):
        calculate_walking_evidence(
            route,
            DEPARTURE,
            response,
            rules={**load_rules(), "maximum_route_samples": 1},
        )
    with pytest.raises(ValueError, match="speed"):
        calculate_walking_evidence(
            route,
            DEPARTURE,
            response,
            rules={**load_rules(), "walking_speed_m_per_s": 0},
        )


def test_missing_local_preparation_keeps_whole_route_unknown():
    def missing(request):
        raise OSError("local file absent")

    evidence = calculate_walking_evidence(short_route(), DEPARTURE, missing)
    assert evidence.unknown_metres == 100 and evidence.shade_state == "failed"
    assert not evidence.inside_calculation_coverage
    assert all(s.explanation.startswith("Prepared shade") for s in evidence.samples)


def test_mixed_distance_partition_and_speed_recalculation():
    states = [
        ShadeState.SHADED,
        ShadeState.SUNLIT,
        ShadeState.UNKNOWN,
        ShadeState.NIGHT,
    ]
    seen = []

    def calculate(request):
        state = states[len(seen) % 4]
        seen.append(request.requested_time)
        return response(request, state)

    first = calculate_walking_evidence(short_route(), DEPARTURE, calculate)
    assert (first.shaded_metres, first.unshaded_metres, first.unknown_metres) == (
        25,
        25,
        50,
    )
    result = compare_choices([first])["baseline"]
    metrics = result.metrics[first.id]
    assert metrics["shade_percentage"] == 25
    assert metrics["unknown_percentage"] == 50
    assert metrics["night_metres"] == 25
    assert metrics["samples"][0]["metadata"]["geometry_version"] == "test-geometry"
    assert metrics["water_state"] == "unknown"
    assert metrics["provenance"]["fixture"] is False
    second = calculate_walking_evidence(
        short_route(),
        DEPARTURE,
        calculate,
        rules={**load_rules(), "walking_speed_m_per_s": 2},
    )
    assert len(seen) == 8
    assert (second.samples[0].requested_time - DEPARTURE).total_seconds() == 6.25


def test_geometry_change_mid_route_withholds_shade_recommendation():
    calls = 0

    def calculate(request):
        nonlocal calls
        calls += 1
        result = response(request)
        if calls > 1:
            result.shade.geometry_version = "reprepared-geometry"
        return result

    evidence = calculate_walking_evidence(
        short_route(), DEPARTURE, calculate, access_state="checked_open"
    )
    assert not evidence.shade_geometry_matches_request
    choice = compare_choices([evidence])["more_shade"]
    assert choice.status == "insufficient_evidence" and choice.winner is None
    assert choice.contributions[evidence.id]["shade"] == 0


def test_cached_shade_cannot_be_reused_after_speed_or_stop_change():
    evidence = calculate_walking_evidence(
        short_route(), DEPARTURE, response, access_state="checked_open"
    )
    changed_speed = compare_choices(
        [evidence], rules={**load_rules(), "walking_speed_m_per_s": 2}
    )
    assert changed_speed["more_shade"].status == "insufficient_evidence"
    assert changed_speed["more_shade"].contributions[evidence.id]["shade"] == 0
    evidence.planned_stop_minutes = 2
    assert compare_choices([evidence])["more_shade"].status == "insufficient_evidence"
