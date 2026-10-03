"""Save sanitized OSM building footprints around the two checked demo routes."""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]


def height_metres(value):
    """Accept explicit positive metre heights only, never infer floor heights."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:m)?\s*", value or "")
    height = float(match[1]) if match else None
    return height if height and height <= 1000 else None


def join_rings(lines):
    """Join relation way segments; fail closed when a ring cannot be assembled."""
    remaining = [list(line) for line in lines if len(line) >= 2]
    rings = []
    while remaining:
        ring = remaining.pop()
        while ring[0] != ring[-1]:
            for i, segment in enumerate(remaining):
                if segment[0] == ring[-1]:
                    ring += segment[1:]
                    remaining.pop(i)
                    break
                if segment[-1] == ring[-1]:
                    ring += list(reversed(segment))[1:]
                    remaining.pop(i)
                    break
            else:
                return None
        if len(ring) < 4:
            return None
        rings.append(ring)
    return rings


def inside(point, ring):
    x, y = point
    found = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:]):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            found = not found
    return found


def footprint(element):
    """Keep polygon geometry only; unresolved relation extents stay unknown."""

    def line(points):
        return [(point["lon"], point["lat"]) for point in points]

    if element["type"] == "way":
        ring = line(element.get("geometry", []))
        if len(ring) < 4 or ring[0] != ring[-1]:
            return None, True
        polygons = [[ring]]
    else:
        members = element.get("members", [])
        outers = join_rings(
            [
                line(m.get("geometry", []))
                for m in members
                if m.get("role") in ("outer", "")
            ]
        )
        inners = join_rings(
            [line(m.get("geometry", [])) for m in members if m.get("role") == "inner"]
        )
        if not outers or inners is None:
            points = [p for m in members for p in line(m.get("geometry", []))]
            if not points:
                return None, True
            west, south = min(p[0] for p in points), min(p[1] for p in points)
            east, north = max(p[0] for p in points), max(p[1] for p in points)
            polygons = [
                [
                    [
                        (west, south),
                        (east, south),
                        (east, north),
                        (west, north),
                        (west, south),
                    ]
                ]
            ]
            unresolved = True
        else:
            polygons = [
                [outer, *[inner for inner in inners if inside(inner[0], outer)]]
                for outer in outers
            ]
            unresolved = False
    if element["type"] == "way":
        unresolved = False
    projected = []
    for polygon in polygons:
        rings = []
        for ring in polygon:
            x, y = transform(4326, 2056, [p[0] for p in ring], [p[1] for p in ring])
            rings.append([[round(a, 6), round(b, 6)] for a, b in zip(x, y)])
        projected.append(rings)
    return {"type": "MultiPolygon", "coordinates": projected}, unresolved


def sanitized_features(elements):
    """Keep caster fields only; fail closed on unlocatable building geometry."""
    features = []
    for element in elements:
        tags = element.get("tags", {})
        if tags.get("building") == "no" or tags.get("building:part") == "no":
            continue
        geometry, unresolved = footprint(element)
        if geometry is None:
            raise ValueError("Unlocatable building geometries prevent bounded coverage")
        features.append(
            {
                "id": f"{element['type']}/{element['id']}",
                "geometry": geometry,
                "height_m": None if unresolved else height_metres(tags.get("height")),
                "unresolved_geometry": unresolved,
            }
        )
    return features


def prepare(geometry=False):
    settings = json.loads((ROOT / "config/building-shade.json").read_text())
    routes = json.loads((ROOT / "data/routes/demo.geojson").read_text())
    points = [p for f in routes["features"] for p in f["geometry"]["coordinates"]]
    x, y = transform(4326, 2056, [p[0] for p in points], [p[1] for p in points])
    halo = settings["maximum_ray_distance_metres"]
    bounds = [min(x) - halo, min(y) - halo, max(x) + halo, max(y) + halo]
    west, south, east, north = bounds
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }
    longitude, latitude = transform(
        2056, 4326, [west, east, east, west], [south, south, north, north]
    )
    bbox = f"{min(latitude)},{min(longitude)},{max(latitude)},{max(longitude)}"
    query = (
        f'[out:json][timeout:90];(way["building"]({bbox});'
        f'relation["building"]({bbox});way["building:part"]({bbox});'
        f'relation["building:part"]({bbox}););out geom;'
    )
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.post(settings["endpoint"], data={"data": query})
        response.raise_for_status()
        data = response.json()
    if data.get("remark") or "elements" not in data:
        raise ValueError("Building query was incomplete")
    features = sanitized_features(data["elements"])
    directory = ROOT / ".cache/buildings"
    directory.mkdir(parents=True, exist_ok=True)
    content = json.dumps(features, separators=(",", ":")).encode()
    (directory / "buildings.json").write_bytes(content)
    metadata = {
        "version": hashlib.sha256(content).hexdigest(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "file": "buildings.json",
        "coverage": polygon,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "provider_timestamp": data.get("osm3s", {}).get("timestamp_osm_base"),
        "attribution": (
            "© OpenStreetMap contributors · ODbL 1.0; roof heights © swisstopo"
        ),
        "endpoint": settings["endpoint"],
        "feature_count": len(features),
        "unresolved_geometries": sum(f["unresolved_geometry"] for f in features),
        "scope": (
            "Building-only flat-ground approximation; no tree shadows, terrain "
            "relief, measured cooling or verified walking ground"
        ),
    }
    (directory / "manifest.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Saved {len(features)} building footprints; "
        f"{metadata['unresolved_geometries']} unresolved extents stay unknown"
    )
    inventory = json.loads((ROOT / "data/tile-inventory.json").read_text())
    tiles = [
        tile["tile"]
        for tile in inventory["tiles"]
        if tile["bounds_epsg2056"][0] < east
        and tile["bounds_epsg2056"][2] > west
        and tile["bounds_epsg2056"][1] < north
        and tile["bounds_epsg2056"][3] > south
    ]
    (directory / "tiles.json").write_text(json.dumps(tiles))
    print("Geometry tiles: " + ",".join(tiles))
    if geometry:
        from prepare_geometry import prepare_geometry

        if not prepare_geometry(workers=2, tiles=set(tiles)):
            raise RuntimeError("Route geometry preparation did not complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geometry", action="store_true", help="Also prepare route-halo survey tiles"
    )
    prepare(parser.parse_args().geometry)
