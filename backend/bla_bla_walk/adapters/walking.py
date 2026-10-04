"""Ephemeral pedestrian-network geometry from the admitted FOSSGIS foot service."""

import hashlib
import json
import math
import threading
import time
from datetime import UTC, datetime

import httpx

from ..instructions import provider_directions
from ..interfaces import LineGeometry, MapFeature, MapLayer, Provenance, RouteMetrics
from ..walking_preferences import choose_routes
from .addresses import ROOT, inside_basel, search_settings

_request_lock = threading.Lock()
_last_request = float("-inf")


def reserve_request(interval):
    """Enforce one request per second across this server process."""
    global _last_request
    with _request_lock:
        now = time.monotonic()
        if now - _last_request < interval:
            raise OverflowError("Walking provider busy; retry shortly")
        _last_request = now


def fetch_routes(request, settings, waypoint=None):
    """Bound streamed replies; persist neither queries nor results."""
    coordinates = ";".join(
        ",".join(f"{coordinate:.7f}" for coordinate in point)
        for point in (
            (request.start, waypoint, request.end)
            if waypoint
            else (request.start, request.end)
        )
    )
    reserve_request(settings["minimum_request_interval_seconds"])
    with httpx.Client(
        timeout=settings["timeout_seconds"],
        headers={"User-Agent": settings["user_agent"]},
    ) as client:
        with client.stream(
            "GET",
            f"{settings['endpoint']}/{coordinates}",
            params={
                "alternatives": "true",
                "geometries": "geojson",
                "overview": "full",
                "steps": "true",
            },
        ) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > settings["max_response_bytes"]:
                    raise OSError("Walking response exceeds configured bound")
    try:
        return json.loads(content)
    except ValueError as error:
        raise OSError("Invalid walking provider reply") from error


def detour_routes(request, settings, polygons):
    """Ask the foot network for bounded alternatives, never draw links."""
    ax, ay = request.start
    bx, by = request.end
    scale = math.cos(math.radians((ay + by) / 2))
    dx, dy = (bx - ax) * scale, by - ay
    length = math.hypot(dx, dy)
    offset = min(settings["detour_offset_metres"], length * 111320 / 3) / 111320
    candidates = []
    for side in (-1, 1):
        point = (
            (ax + bx) / 2 - side * dy / length * offset / scale,
            (ay + by) / 2 + side * dx / length * offset,
        )
        if not inside_basel(*point, polygons):
            continue
        time.sleep(settings["minimum_request_interval_seconds"])
        try:
            payload = fetch_routes(request, settings, waypoint=point)
            if payload.get("code") != "Ok":
                continue
            waypoints = payload.get("waypoints", [])
            if len(waypoints) != 3 or any(
                not 0 <= float(p["distance"]) <= settings["max_snap_metres"]
                for p in waypoints
            ):
                continue
            candidates.extend(payload.get("routes", [])[:1])
        except (
            httpx.HTTPError,
            OSError,
            OverflowError,
            KeyError,
            TypeError,
            ValueError,
        ):
            continue
    return candidates


def route_feature(route, index, settings, provenance, speed):
    """Validate network lines without connecting buildings with invented paths."""
    geometry = route["geometry"]
    coords = geometry["coordinates"]
    distance = float(route["distance"])
    if (
        geometry["type"] != "LineString"
        or not 2 <= len(coords) <= settings["max_coordinates"]
    ):
        raise OSError("Invalid walking geometry")
    if not math.isfinite(distance) or distance <= 0:
        raise OSError("Invalid walking distance")
    identity = hashlib.sha256(json.dumps(coords).encode()).hexdigest()[:20]
    return MapFeature(
        id=f"walking-{identity}",
        label=f"Walking route {index + 1}",
        kind="route",
        geometry=LineGeometry(type="LineString", coordinates=coords),
        availability="unknown",
        provenance=provenance,
        route=RouteMetrics(distance_m=distance, duration_s=distance / speed),
        directions=provider_directions(route, f"walking-{identity}", speed),
        explanation=(
            f"OSM walking estimate assumes {speed:g} m/s. "
            "Endpoints snap to the pedestrian network, "
            f"up to {settings['max_snap_metres']}m. "
            "Temporary closures and local access are unverified. "
            "Building-only shade sampling is an approximation at departure; "
            "shade along the full walk is not guaranteed."
        ),
    )


def walking_routes(request):
    """Return street geometry and estimated time; access and shade stay unknown."""
    if request.mode == "offline":
        raise OSError("Offline routing graph unavailable for these endpoints")
    _, polygons = search_settings()
    if not all(
        inside_basel(*point, polygons) for point in (request.start, request.end)
    ):
        raise ValueError("Select both endpoints within Basel-Stadt")
    if request.start == request.end:
        raise ValueError("Start and destination must differ")
    settings = json.loads((ROOT / "config/walking-routing.json").read_text())
    payload = fetch_routes(request, settings)
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise OSError("No walking route found for these endpoints")
    waypoints = payload.get("waypoints", [])
    if len(waypoints) != 2 or any(
        not math.isfinite(float(point["distance"]))
        or not 0 <= float(point["distance"]) <= settings["max_snap_metres"]
        for point in waypoints
    ):
        raise OSError("Endpoint too far from the pedestrian network")
    provenance = Provenance(
        provider="FOSSGIS OpenStreetMap routing service using OSRM foot profile",
        source_url="https://routing.openstreetmap.de/about.html",
        attribution="© OpenStreetMap contributors · Routing by OSRM (FOSSGIS)",
        licence="OpenStreetMap route geometry: ODbL 1.0",
        fixture=False,
        retrieved_at=datetime.now(UTC),
    )
    speed = json.loads((ROOT / "config/routing-rules.json").read_text())[
        "walking_speed_m_per_s"
    ]
    features = [
        route_feature(route, index, settings, provenance, speed)
        for index, route in enumerate(payload["routes"][: settings["max_routes"]])
    ]
    shortest = min(f.route.distance_m for f in features)
    for route in detour_routes(request, settings, polygons):
        try:
            feature = route_feature(route, len(features), settings, provenance, speed)
        except (OSError, KeyError, TypeError, ValueError):
            continue
        if feature.route.distance_m <= shortest * settings["detour_max_ratio"]:
            features.append(feature)
    features = choose_routes(
        features, request.departure_time or datetime.now(UTC), settings
    )
    return MapLayer(
        id="selected-walking-routes",
        label="Selected walking routes",
        kind="route",
        availability="unknown",
        features=features,
        explanation="Fast and Recommended walking choices. " + features[1].explanation,
    )
