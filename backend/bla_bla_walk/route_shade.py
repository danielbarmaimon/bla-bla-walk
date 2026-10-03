"""Route-distance quadrature at exact traversal times using T10's local service."""

import base64
import math
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from rasterio.warp import transform

from .evaluation import load_rules
from .interfaces import (
    MapFeature,
    ShadeRequest,
    ShadeResponse,
    ShadeState,
    WalkingEvidence,
    WalkingShadeSample,
    WalkingStop,
    WaterEvidence,
)
from .shade_cache import ShadeBusy
from .walking_metrics import finite


def intervals(points, distance, maximum, stops):
    """Preserve source bends and split at stops; no interval exceeds maximum."""
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    if total <= 0 or not finite(total):
        raise ValueError("Route geometry must have positive finite length")
    segments = [
        (a, b, length)
        for a, b, length in zip(points, points[1:], lengths)
        if length > 0
    ]
    chainage = 0
    for index, (a, b, length) in enumerate(segments):
        end = (
            distance
            if index == len(segments) - 1
            else chainage + length / total * distance
        )
        cuts = [
            chainage,
            *sorted({s.at_metres for s in stops if chainage < s.at_metres < end}),
            end,
        ]
        for low, high in zip(cuts, cuts[1:]):
            count = math.ceil((high - low) / maximum)
            for index in range(count):
                start = low + (high - low) * index / count
                finish = low + (high - low) * (index + 1) / count
                fraction = ((start + finish) / 2 - chainage) / (end - chainage)
                yield start, finish, tuple(x + fraction * (y - x) for x, y in zip(a, b))
        chainage = end


def sample_state(response, point):
    """Read only the receiver's cell; corridor cell counts are not route metres."""
    west, south, east, north = response.bounds
    if response.width <= 0 or response.height <= 0 or west >= east or south >= north:
        raise ValueError("Invalid shade raster dimensions")
    cell = response.shade.resolution_m
    if not math.isclose(east - west, response.width * cell) or not math.isclose(
        north - south, response.height * cell
    ):
        raise ValueError("Shade grid and metadata disagree")
    states = base64.b64decode(response.states, validate=True)
    if len(states) != response.width * response.height:
        raise ValueError("Shade raster length mismatch")
    x, y = point
    row, column = math.floor((north - y) / cell), math.floor((x - west) / cell)
    if not (0 <= row < response.height and 0 <= column < response.width):
        return ShadeState.UNKNOWN
    return ShadeState(states[row * response.width + column])


def calculate_walking_evidence(
    route: MapFeature,
    departure: datetime,
    calculate: Callable[[ShadeRequest], ShadeResponse],
    *,
    access_state="unknown",
    construction_caution=False,
    stops: list[WalkingStop] | None = None,
    water: WaterEvidence | None = None,
    rules=None,
    geometry_version: str | None = None,
) -> WalkingEvidence:
    """Cache this result, then rescore with evaluation.compare_routes/choices.

    Source route distance is the full denominator. Projected segments partition
    that distance proportionally; midpoint sampling is an explicit numerical
    approximation, bounded by config. Speed/stops/departure/geometry changes
    require a new calculation. No network access or transit assumptions occur.
    A supplied geometry version is verified, otherwise the first response pins
    the version for the whole run. Every exact-time response remains auditable.
    """
    policy = load_rules() if rules is None else rules
    speed = policy["walking_speed_m_per_s"]
    maximum = policy["maximum_sample_metres"]
    if (
        not finite(speed)
        or speed <= 0
        or not finite(maximum)
        or maximum <= 0
        or departure.tzinfo is None
        or departure.utcoffset() is None
    ):
        raise ValueError("Require positive speed/sample interval and aware departure")
    if (
        route.kind != "route"
        or route.geometry.type != "LineString"
        or route.route is None
    ):
        raise ValueError("Require a canonical walking line with distance")
    distance = route.route.distance_m
    if not finite(distance) or distance <= 0:
        raise ValueError("Route distance must be positive and finite")
    stops = stops or []
    if any(s.at_metres > distance for s in stops):
        raise ValueError("Stops must lie on the route; include diversions in geometry")
    coordinates = route.geometry.coordinates
    x, y = transform(
        4326, 2056, [p[0] for p in coordinates], [p[1] for p in coordinates]
    )
    segments = list(intervals(list(zip(x, y)), distance, maximum, stops))
    if len(segments) > policy["maximum_route_samples"]:
        raise ValueError("Route exceeds sampling budget; use a bounded route")
    samples = []
    supported, matches, succeeded = True, True, True
    model = None
    for start, end, point in segments:
        midpoint = (start + end) / 2
        pause = sum(s.minutes for s in stops if s.at_metres <= midpoint)
        moment = departure.astimezone(UTC) + timedelta(
            seconds=midpoint / speed + pause * 60
        )
        request = ShadeRequest(
            bounds=(point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1),
            requested_time=moment,
        )
        sample = WalkingShadeSample(
            start_metres=start,
            end_metres=end,
            requested_time=moment,
            explanation="Shade calculation unavailable",
        )
        try:
            response = calculate(request)
            sample.metadata = response.shade
            sample.model = response.model
            sample.explanation = response.explanation
            geometry_version = geometry_version or response.shade.geometry_version
            model = model or response.model
            matching = (
                response.shade.requested_time == moment
                and response.shade.effective_time == moment
                and response.shade.geometry_version == geometry_version
                and response.model == model
            )
            matches &= matching
            supported &= response.availability != "unsupported"
            # Unknown responses cannot earn credit even with contradictory bytes.
            if matching and response.availability == "approximate":
                sample.state = sample_state(response, point)
            elif not matching:
                sample.explanation = "Time, geometry or model mismatch; no shade credit"
        except (OSError, ValueError, KeyError, OverflowError, ShadeBusy):
            succeeded = False
            supported = False
            sample.explanation = (
                "Prepared shade calculation failed; unknown distance retained"
            )
        samples.append(sample)
    totals = {state: 0.0 for state in ShadeState}
    for sample in samples:
        totals[sample.state] += sample.end_metres - sample.start_metres
    return WalkingEvidence(
        id=route.id,
        distance_metres=distance,
        shaded_metres=totals[ShadeState.SHADED],
        unshaded_metres=totals[ShadeState.SUNLIT],
        unknown_metres=max(
            0, distance - totals[ShadeState.SHADED] - totals[ShadeState.SUNLIT]
        ),
        planned_stop_minutes=sum(s.minutes for s in stops),
        access_state=access_state,
        construction_caution=construction_caution,
        inside_calculation_coverage=supported,
        shade_state="current" if succeeded else "failed",
        shade_time_matches_request=matches,
        shade_geometry_matches_request=matches,
        water=water or WaterEvidence(),
        provenance=route.provenance,
        samples=samples,
        sampled_speed_m_per_s=speed,
        sampled_distance_metres=distance,
        sampled_stop_minutes=sum(s.minutes for s in stops),
    )
