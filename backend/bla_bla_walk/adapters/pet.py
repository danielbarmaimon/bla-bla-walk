"""Sample the Basel-Stadt historical PET classes along checked demo routes."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
from rasterio.errors import RasterioIOError
from rasterio.io import MemoryFile
from rasterio.warp import transform

from ..interfaces import MapLayer, PetRouteMetrics, Provenance

WMS_URL = "https://wms.geo.bs.ch/"
WMS_LAYER = "KL_HumanbioklimaSituation"
ATTRIBUTION = "Quelle: Geodaten Kanton Basel-Stadt"
LICENCE = "CC BY 4.0"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PET_CONFIG = json.loads(
    (PROJECT_ROOT / "config" / "pet-classes.json").read_text(encoding="utf-8")
)
CELL_SIZE_M = int(PET_CONFIG["resolution_m"])
MAX_IMAGE_BYTES = 4_000_000
MAX_IMAGE_PIXELS = 500_000
UNKNOWN_BAND = "Unknown / outside data"

PET_CLASSES = tuple(
    (item["label"], tuple(item["rgb"])) for item in PET_CONFIG["classes"]
)
SCENARIO = "Clear summer high-pressure scenario; fixed 14:00"


def add_pet_route_metrics(layer: MapLayer) -> MapLayer:
    """Attach 10 m PET-class distance estimates to every route in one WMS read."""
    routes = [feature for feature in layer.features if feature.route is not None]
    if not routes:
        return layer

    points = [point for route in routes for point in route.geometry.coordinates]
    eastings, northings = transform(
        "EPSG:4326",
        "EPSG:2056",
        [point[0] for point in points],
        [point[1] for point in points],
    )
    projected_routes: dict[str, list[tuple[float, float]]] = {}
    cursor = 0
    for route in routes:
        count = len(route.geometry.coordinates)
        projected_routes[route.id] = list(
            zip(
                eastings[cursor : cursor + count],
                northings[cursor : cursor + count],
                strict=True,
            )
        )
        cursor += count

    min_x = math.floor(min(eastings) / CELL_SIZE_M) * CELL_SIZE_M - CELL_SIZE_M
    max_x = math.ceil(max(eastings) / CELL_SIZE_M) * CELL_SIZE_M + CELL_SIZE_M
    min_y = math.floor(min(northings) / CELL_SIZE_M) * CELL_SIZE_M - CELL_SIZE_M
    max_y = math.ceil(max(northings) / CELL_SIZE_M) * CELL_SIZE_M + CELL_SIZE_M
    width = max(1, math.ceil((max_x - min_x) / CELL_SIZE_M))
    height = max(1, math.ceil((max_y - min_y) / CELL_SIZE_M))
    if width * height > MAX_IMAGE_PIXELS:
        return _with_unavailable_pet(
            layer, "unsupported", "The route area is too large to sample."
        )

    bbox = (min_x, max_y - height * CELL_SIZE_M, min_x + width * CELL_SIZE_M, max_y)
    try:
        rgba = _fetch_pet_image(bbox, width, height)
    except (OSError, ValueError, RuntimeError, RasterioIOError):
        return _with_unavailable_pet(
            layer, "missing", "The PET map service is unavailable."
        )

    annotated = []
    for route in layer.features:
        if route.id not in projected_routes:
            annotated.append(route)
            continue
        bands = {label: 0.0 for label, _ in PET_CLASSES}
        bands[UNKNOWN_BAND] = 0.0
        for (x1, y1), (x2, y2) in zip(
            projected_routes[route.id], projected_routes[route.id][1:]
        ):
            length = math.hypot(x2 - x1, y2 - y1)
            if length == 0:
                continue
            count = max(1, math.ceil(length / CELL_SIZE_M))
            sample_distance = length / count
            for index in range(count):
                fraction = (index + 0.5) / count
                x = x1 + (x2 - x1) * fraction
                y = y1 + (y2 - y1) * fraction
                column = int((x - bbox[0]) / CELL_SIZE_M)
                row = int((bbox[3] - y) / CELL_SIZE_M)
                band = _class_for_pixel(rgba[:, row, column])
                bands[band] += sample_distance

        known_distance = sum(
            value for key, value in bands.items() if key != UNKNOWN_BAND
        )
        unknown_distance = bands[UNKNOWN_BAND]
        pet = PetRouteMetrics(
            availability="current" if known_distance else "unknown",
            scenario=SCENARIO,
            resolution_m=CELL_SIZE_M,
            known_distance_m=round(known_distance, 1),
            unknown_distance_m=round(unknown_distance, 1),
            class_distances_m={
                label: round(value, 1) for label, value in bands.items() if value > 0
            },
            provenance=_provenance(),
        )
        annotated.append(route.model_copy(update={"pet": pet}))

    return layer.model_copy(
        update={
            "explanation": (
                "Route PET distances are sampled from the historical 14:00 summer "
                f"scenario at {CELL_SIZE_M} m intervals. This is not a live forecast "
                "or a personal heat-risk estimate."
            ),
            "features": annotated,
        }
    )


@lru_cache(maxsize=1)
def _fetch_pet_image(
    bbox: tuple[float, float, float, float], width: int, height: int
) -> np.ndarray:
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": WMS_LAYER,
        "STYLES": "",
        "CRS": "EPSG:2056",
        "BBOX": ",".join(f"{value:g}" for value in bbox),
        "WIDTH": str(width),
        "HEIGHT": str(height),
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE",
    }
    request = Request(
        WMS_URL + "?" + urlencode(params),
        headers={"User-Agent": "Bla-Bla-Walk/0.1 (Basel PET route comparison)"},
    )
    with urlopen(request, timeout=8) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("PET image response exceeds the configured size limit")
    with MemoryFile(data) as memory_file:
        with memory_file.open() as dataset:
            if dataset.count < 4 or dataset.width != width or dataset.height != height:
                raise ValueError("PET map response has an unexpected image format")
            return dataset.read((1, 2, 3, 4))


def _class_for_pixel(pixel: np.ndarray) -> str:
    red, green, blue, alpha = (int(value) for value in pixel)
    if alpha < 128:
        return UNKNOWN_BAND
    label, color = min(
        PET_CLASSES,
        key=lambda item: sum(
            (actual - expected) ** 2
            for actual, expected in zip((red, green, blue), item[1], strict=True)
        ),
    )
    distance_squared = sum(
        (actual - expected) ** 2
        for actual, expected in zip((red, green, blue), color, strict=True)
    )
    return (
        label
        if distance_squared <= PET_CONFIG["max_rgb_distance"] ** 2
        else UNKNOWN_BAND
    )


def _provenance() -> Provenance:
    return Provenance(
        provider="Kanton Basel-Stadt · Humanbioklimatische Situation [PET]",
        source_url=WMS_URL,
        attribution=ATTRIBUTION,
        licence=LICENCE,
        fixture=False,
        retrieved_at=datetime.now(UTC),
    )


def _with_unavailable_pet(
    layer: MapLayer, state: Literal["missing", "unsupported"], reason: str
) -> MapLayer:
    features = [
        route.model_copy(
            update={
                "pet": PetRouteMetrics(
                    availability=state,
                    scenario=SCENARIO,
                    resolution_m=CELL_SIZE_M,
                    known_distance_m=0,
                    unknown_distance_m=route.route.distance_m if route.route else 0,
                    class_distances_m={
                        UNKNOWN_BAND: route.route.distance_m if route.route else 0
                    },
                    provenance=_provenance(),
                )
            }
        )
        for route in layer.features
    ]
    return layer.model_copy(
        update={
            "explanation": f"{layer.explanation} PET metrics unavailable: {reason}",
            "features": features,
        }
    )
