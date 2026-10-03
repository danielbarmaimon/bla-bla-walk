"""Prepare sanitized saved OSM benches and park centres locally."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bla_bla_walk.adapters.addresses import inside_basel, search_settings  # noqa: E402
from bla_bla_walk.interfaces import (  # noqa: E402
    MapFeature,
    MapLayer,
    PointGeometry,
    Provenance,
)


def prepare(
    payload, retrieved_at=None, note="Saved OSM audit 2026-10-03; partial bbox coverage"
):
    """Keep only IDs, positions and enumerated amenity evidence; no raw tags."""
    _, polygons = search_settings()
    brands = json.loads((ROOT / "config/route-stops.json").read_text())[
        "supermarket_brands"
    ]
    provenance = Provenance(
        provider="OpenStreetMap via Swiss Overpass",
        source_url="https://www.openstreetmap.org/copyright",
        attribution="© OpenStreetMap contributors",
        licence="ODbL 1.0",
        fixture=False,
        retrieved_at=retrieved_at,
    )
    features = []
    for item in payload["elements"]:
        tags = item.get("tags", {})
        kind = (
            "bench"
            if tags.get("amenity") == "bench"
            else "park"
            if tags.get("leisure") == "park"
            else "indoor"
            if tags.get("shop") == "supermarket"
            else None
        )
        position = item.get("center", item)
        if not kind or not all(key in position for key in ("lon", "lat")):
            continue
        coords = (position["lon"], position["lat"])
        if not inside_basel(*coords, polygons):
            continue
        features.append(
            MapFeature(
                id=f"osm-{item['type']}-{item['id']}",
                label="Mapped bench"
                if kind == "bench"
                else "Mapped park centre"
                if kind == "park"
                else (
                    tags.get("brand")
                    if tags.get("brand") in brands
                    else "Mapped supermarket"
                ),
                kind="rest",
                rest_type=kind,
                opening_hours=tags.get("opening_hours") if kind == "indoor" else None,
                geometry=PointGeometry(type="Point", coordinates=coords),
                availability="unknown",
                provenance=provenance,
                explanation=f"{note}. Access, current condition and shade unknown. "
                + (
                    "Park centre is not a verified entrance or seating location."
                    if kind == "park"
                    else "Mapped supermarket; scheduled hours only; cooling unknown."
                    if kind == "indoor"
                    else "Mapped seating; no field verification."
                ),
            )
        )
    return MapLayer(
        id="rest-stops",
        label="Benches and rest candidates",
        kind="rest",
        availability="unknown",
        features=features,
        explanation=f"{note}. Mapped candidates, not verified accessible/cool stops.",
    )


def download(settings):
    """One bounded fixed city query; no user route or location is transmitted."""
    _, polygons = search_settings()
    points = [point for polygon in polygons for ring in polygon for point in ring]
    bbox = ",".join(
        str(v)
        for v in (
            min(p[1] for p in points),
            min(p[0] for p in points),
            max(p[1] for p in points),
            max(p[0] for p in points),
        )
    )
    query = (
        f'[out:json][timeout:40];(nwr["amenity"="bench"]({bbox});'
        f'nwr["leisure"="park"]({bbox});'
        f'nwr["shop"="supermarket"]({bbox}););out tags center;'
    )
    with httpx.Client(timeout=settings["timeout_seconds"]) as client:
        with client.stream(
            "POST", settings["endpoint"], data={"data": query}
        ) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > settings["max_response_bytes"]:
                    raise ValueError("Stop response too large")
    return json.loads(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--input", type=Path)
    sources.add_argument("--download", action="store_true")
    args = parser.parse_args()
    settings = json.loads((ROOT / "config/route-stops.json").read_text())
    if args.download:
        now = datetime.now(UTC)
        layer = prepare(
            download(settings),
            now,
            f"Saved OSM acquisition {now.isoformat()}; canton bbox queried",
        )
    else:
        layer = prepare(json.loads(args.input.read_text(encoding="utf-8")))
    target = ROOT / ".cache/rest-stops.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(layer.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(target)
    print(f"Saved {len(layer.features)} mapped candidates to {target}")
