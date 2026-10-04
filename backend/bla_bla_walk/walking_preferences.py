"""Bounded route-choice evidence from local shade and official site polygons."""

import base64
import math
from collections import defaultdict
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

import httpx
from rasterio.warp import transform
from shapely.geometry import LineString, shape

from .interfaces import ShadeRequest, ShadeState
from .shade_service import ShadeService

ROOT = Path(__file__).resolve().parents[2]
_sampling_lock = Lock()


def shade_fraction(route, departure, settings):
    """Keep sparse raster work to one route at a time across API threads."""
    if not _sampling_lock.acquire(blocking=False):
        return None
    try:
        return _sample_shade_fraction(route, departure, settings)
    finally:
        _sampling_lock.release()


def _sample_shade_fraction(route, departure, settings):
    """Sample equal route intervals at departure, never claim traversal-time shade.

    Reuse the building-only model with sparse receivers. Missing, night and
    low-sun samples never earn shade credit; positive evidence is a lower bound.
    """
    service = ShadeService()
    coords = route.geometry.coordinates
    x, y = transform(4326, 2056, [p[0] for p in coords], [p[1] for p in coords])
    line = LineString(zip(x, y))
    count = min(
        settings["shade_max_samples"],
        max(2, math.ceil(line.length / settings["shade_sample_metres"])),
    )
    tiles = defaultdict(list)
    for index in range(count):
        point = line.interpolate((index + 0.5) / count, normalized=True)
        tiles[(math.floor(point.x / 1000), math.floor(point.y / 1000))].append(
            (point.x, point.y)
        )
    if len(tiles) > settings["shade_max_tiles"]:
        return None
    known = shaded = 0
    try:
        for points in tiles.values():
            bounds = (
                math.floor(min(p[0] for p in points)),
                math.floor(min(p[1] for p in points)),
                math.floor(max(p[0] for p in points)) + 1,
                math.floor(max(p[1] for p in points)) + 1,
            )
            request = ShadeRequest(bounds=bounds, requested_time=departure)
            response = service.sample(request, points)
            states = base64.b64decode(response.states)
            for px, py in points:
                row = math.floor(response.bounds[3] - py)
                col = math.floor(px - response.bounds[0])
                value = states[row * response.width + col]
                known += value in (ShadeState.SHADED, ShadeState.SUNLIT)
                shaded += value == ShadeState.SHADED
    except (OSError, ValueError, OverflowError, KeyError):
        return None
    # Positive modeled shade can guide a provisional choice even with gaps.
    # Divide by all samples: unknown samples never earn shade credit.
    return (
        shaded / count
        if shaded or known / count >= settings["shade_min_known_fraction"]
        else None
    )


def construction_sites(departure, settings):
    """Read only dated geometry, not contact or descriptive personal fields.

    Active permits are cautions, not confirmed pedestrian closures. Incomplete
    pagination and provider failure explicitly withhold the avoidance claim.
    """
    day = departure.astimezone(ZoneInfo("Europe/Zurich")).date().isoformat()
    polygons = []
    try:
        with httpx.Client(timeout=settings["construction_timeout_seconds"]) as client:
            projects = client.get(
                settings["construction_projects_endpoint"],
                params={
                    "select": "id",
                    "where": f"datum_von <= date'{day}' AND datum_bis >= date'{day}'",
                    "limit": 100,
                },
            )
            projects.raise_for_status()
            project_data = projects.json()
            if project_data["total_count"] > 100:
                return None
            ids = [str(int(record["id"])) for record in project_data["results"]]
            if not ids:
                return []
            for offset in range(0, settings["construction_max_records"], 100):
                response = client.get(
                    settings["construction_endpoint"],
                    params={
                        "select": "geo_shape",
                        "where": (
                            f"begehrenid in ({','.join(ids)}) "
                            f"AND datum_von <= date'{day}' "
                            f"AND datum_bis >= date'{day}'"
                        ),
                        "limit": 100,
                        "offset": offset,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                for record in payload["results"]:
                    geometry = record.get("geo_shape")
                    if not geometry:
                        return None
                    polygon = shape(geometry.get("geometry", geometry))
                    if (
                        polygon.is_empty
                        or not polygon.is_valid
                        or polygon.geom_type not in ("Polygon", "MultiPolygon")
                    ):
                        return None
                    polygons.append(polygon)
                if offset + 100 >= payload["total_count"]:
                    return polygons
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        pass
    return None


def choose_routes(features, departure, settings):
    """Return exactly two labelled choices; preserve coincident-path evidence."""
    features = sorted(
        {f.id: f for f in features}.values(), key=lambda f: f.route.duration_s
    )
    fast = features[0].model_copy(deep=True)
    fast.route_role = "fast"
    fast.label = "Fast · shortest walking time"
    sites = construction_sites(departure, settings)
    candidates = features
    if sites is not None:
        clear = [
            f
            for f in features
            if not any(
                LineString(f.geometry.coordinates).intersects(site) for site in sites
            )
        ]
        candidates = clear or features
    scores = {f.id: shade_fraction(f, departure, settings) for f in candidates}
    scored = [f for f in candidates if scores[f.id] is not None]
    recommended = (
        max(scored, key=lambda f: (scores[f.id], -f.route.duration_s))
        if scored
        else next((f for f in candidates if f.id != fast.id), candidates[0])
    )
    recommended = recommended.model_copy(deep=True)
    recommended.route_role = "recommended"
    recommended.label = "Recommended"
    if sites is not None:
        recommended.provenance.attribution += (
            " · Construction context: Tiefbauamt / Geodaten Kanton Basel-Stadt "
            "(CC BY 4.0 + OpenStreetMap)"
        )
    if scored:
        recommended.provenance.attribution += (
            " · Approximate building shade: © OpenStreetMap contributors / © swisstopo"
        )
    note = (
        "Building-only shade estimate at departure: "
        f"at least {math.floor(scores[recommended.id] * 100)}% "
        "of evenly spaced samples have modeled shade; input gaps remain unknown. "
        if scored
        else "Shade ranking unavailable; this is a provisional walking choice. "
    )
    if sites is None:
        note += "Active construction geometry unavailable; avoidance unverified. "
    elif any(
        LineString(recommended.geometry.coordinates).intersects(site) for site in sites
    ):
        note += (
            "All candidates cross mapped active permit areas; "
            "inspect local diversions. "
        )
    else:
        note += (
            "Avoids the loaded active construction permit polygons; "
            "these are cautions, not confirmed closures. "
        )
    if recommended.id == fast.id:
        recommended.id += "-recommended"
        if recommended.directions:
            recommended.directions.route_id = recommended.id
        note += "Fast and Recommended share the same path. "
    recommended.explanation = note + recommended.explanation
    return [fast, recommended]
