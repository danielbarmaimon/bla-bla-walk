"""Bounded official address lookup; queries and selections are never persisted."""

import hashlib
import html
import json
import math
import re
from functools import lru_cache
from pathlib import Path

import httpx
from rasterio.warp import transform_geom

from ..interfaces import AddressPlace, AddressSearchResponse

ROOT = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def search_settings():
    """Reuse static settings and the admitted canton polygon, never queries."""
    settings = json.loads((ROOT / "config/address-search.json").read_text())
    boundary = json.loads((ROOT / "data/tile-inventory.json").read_text())["boundary"]
    geometry = transform_geom(boundary["crs"], "EPSG:4326", boundary["geometry"])
    polygons = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        polygons = [polygons]
    coordinates = (
        [
            point
            for polygon in boundary["geometry"]["coordinates"]
            for ring in polygon
            for point in ring
        ]
        if boundary["geometry"]["type"] == "MultiPolygon"
        else [point for ring in boundary["geometry"]["coordinates"] for point in ring]
    )
    settings["bbox"] = ",".join(
        str(v)
        for v in (
            min(p[0] for p in coordinates),
            min(p[1] for p in coordinates),
            max(p[0] for p in coordinates),
            max(p[1] for p in coordinates),
        )
    )
    return settings, polygons


def in_ring(lon, lat, ring):
    """Ray-crossing containment for a WGS84 ring."""
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > lat) != (b[1] > lat):
            crossing = (b[0] - a[0]) * (lat - a[1]) / (b[1] - a[1]) + a[0]
            if lon < crossing:
                inside = not inside
    return inside


def inside_basel(lon, lat, polygons):
    """Respect exterior rings and holes, including Riehen and Bettingen."""
    return any(
        in_ring(lon, lat, polygon[0])
        and not any(in_ring(lon, lat, hole) for hole in polygon[1:])
        for polygon in polygons
    )


def search_addresses(query, mode):
    """Search addresses only; offline returns before any provider access."""
    if mode == "offline":
        return AddressSearchResponse(status="unavailable")
    query = " ".join(query.split())
    if len(query) < 3 or len(query.split()) > 10:
        raise ValueError("Use 3–120 characters and at most ten words")
    settings, polygons = search_settings()
    params = {
        "searchText": query,
        "type": "locations",
        "origins": "address",
        "sr": 2056,
        "bbox": settings["bbox"],
        "limit": settings["provider_limit"],
    }
    with httpx.Client(timeout=settings["timeout_seconds"]) as client:
        with client.stream("GET", settings["endpoint"], params=params) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > settings["max_response_bytes"]:
                    raise OSError("Address response too large")
    try:
        payload = json.loads(content)
    except ValueError as error:
        raise OSError("Invalid address provider response") from error
    places = []
    seen = set()
    for result in payload["results"]:
        try:
            attrs = result["attrs"]
            lon, lat = float(attrs["lon"]), float(attrs["lat"])
            if attrs["origin"] != "address" or not all(map(math.isfinite, (lon, lat))):
                continue
            if not inside_basel(lon, lat, polygons):
                continue
            name = html.unescape(re.sub(r"<[^>]*>", "", attrs["label"]))[:240]
            identity = hashlib.sha256(f"{name}|{lon}|{lat}".encode()).hexdigest()[:20]
            if not name.strip() or identity in seen:
                continue
            seen.add(identity)
            places.append(
                AddressPlace(id=f"address-{identity}", name=name, lon=lon, lat=lat)
            )
        except (KeyError, TypeError, ValueError):
            continue
        if len(places) == settings["result_limit"]:
            break
    return AddressSearchResponse(places=places)
