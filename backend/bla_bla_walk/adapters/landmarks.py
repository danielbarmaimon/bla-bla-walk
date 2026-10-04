"""Daily citywide named OSM landmarks; raw tags are never persisted."""

import json
from datetime import UTC, datetime

import httpx

from ..daily_cache import daily_snapshot
from ..interfaces import MapFeature, MapLayer, PointGeometry, Provenance
from .addresses import ROOT, inside_basel, search_settings

SETTINGS = json.loads((ROOT / "config/landmarks.json").read_text())
PATH = ROOT / ".cache/landmarks.sqlite3"


def empty_landmarks():
    return MapLayer(
        id="city-landmarks",
        label="City landmarks",
        kind="landmark",
        availability="missing",
        explanation="Saved landmark data unavailable.",
        features=[],
    )


def fetch_landmarks(now):
    _, polygons = search_settings()
    points = [point for polygon in polygons for ring in polygon for point in ring]
    bounds = (
        min(p[1] for p in points),
        min(p[0] for p in points),
        max(p[1] for p in points),
        max(p[0] for p in points),
    )
    bbox = ",".join(str(value) for value in bounds)
    query = f"""[out:json][timeout:25];(
      nwr["historic"]["name"]({bbox});
      nwr["tourism"~"^(museum|attraction|artwork)$"]["name"]({bbox});
      nwr["amenity"~"^(place_of_worship|police|townhall)$"]["name"]({bbox});
      nwr["leisure"="park"]["name"]({bbox});
    );out center tags;"""
    with httpx.Client(timeout=SETTINGS["timeout_seconds"]) as client:
        with client.stream(
            "POST", SETTINGS["endpoint"], data={"data": query}
        ) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > SETTINGS["max_response_bytes"]:
                    raise ValueError("Landmark response too large")
    payload = json.loads(content)
    if payload.get("remark") or len(payload["elements"]) > SETTINGS["max_records"]:
        raise ValueError("Incomplete landmark acquisition")
    features = {}
    for item in payload["elements"]:
        tags = item.get("tags", {})
        name = tags.get("name", "").strip()
        position = item.get("center", item)
        if (
            not name
            or len(name) > 180
            or not all(key in position for key in ("lon", "lat"))
        ):
            continue
        lon, lat = position["lon"], position["lat"]
        if not inside_basel(lon, lat, polygons):
            continue
        category = (
            tags.get("amenity")
            or tags.get("tourism")
            or tags.get("leisure")
            or "historic"
        )
        if item["type"] not in {"node", "way", "relation"}:
            raise ValueError("Invalid landmark identity")
        identity = f"osm-{item['type']}-{int(item['id'])}"
        features[identity] = MapFeature(
            id=identity,
            label=name,
            kind="landmark",
            geometry=PointGeometry(type="Point", coordinates=(lon, lat)),
            availability="current",
            explanation=(
                f"Mapped {category.replace('_', ' ')} centre; "
                "visibility and access are unverified."
            ),
            provenance=Provenance(
                provider="OpenStreetMap via Swiss Overpass",
                source_url=f"https://www.openstreetmap.org/{item['type']}/{int(item['id'])}",
                attribution="© OpenStreetMap contributors",
                licence="ODbL 1.0",
                fixture=False,
                retrieved_at=now,
            ),
        )
    return MapLayer(
        id="city-landmarks",
        label="City landmarks",
        kind="landmark",
        availability="current",
        explanation=(
            "Daily named landmarks across Basel-Stadt, including "
            "Riehen and Bettingen. Mapped centres are not verified entrances."
        ),
        features=list(features.values()),
    )


def landmarks(mode="online", path=PATH, now=None):
    layer = daily_snapshot(
        mode, path, fetch_landmarks, MapLayer, empty_landmarks, now or datetime.now(UTC)
    )
    for feature in layer.features:
        feature.availability = layer.availability
    return layer
