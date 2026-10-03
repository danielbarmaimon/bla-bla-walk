"""Save sanitized OSM building footprints around the two checked demo routes."""

import argparse
import json
import re
import sys
from pathlib import Path

import httpx
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bla_bla_walk.building_acquisition import (  # noqa: E402
    acquire_buildings,
    building_queries,
    cached_buildings,
)


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


def download_buildings(endpoint, query, polygon, directory, *, refresh=False):
    """Apply the caster-only parser to resumable acquisition."""
    return acquire_buildings(
        endpoint,
        query,
        polygon,
        directory,
        sanitize=sanitized_features,
        refresh=refresh,
    )


def prepare(geometry=False, *, offline=False, refresh=False, endpoint=None):
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
    query = building_queries(
        (min(latitude), min(longitude), max(latitude), max(longitude)),
        settings["query_cell_degrees"],
    )
    directory = ROOT / ".cache/buildings"
    metadata = None if refresh else cached_buildings(directory, polygon)
    if metadata:
        print(f"Reusing verified building cache saved {metadata['retrieved_at']}")
    elif offline:
        raise ValueError(
            "No verified same-coverage building cache; prepare online first"
        )
    else:
        metadata = download_buildings(
            endpoint or settings["endpoint"], query, polygon, directory, refresh=refresh
        )
    print(
        f"Available {metadata['feature_count']} building footprints; "
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
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--geometry", action="store_true", help="Also prepare route-halo survey tiles"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Validate/reuse saved buildings without network calls",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch fresh buildings instead of reusing the saved cache",
    )
    parser.add_argument(
        "--endpoint", help="Public HTTPS Overpass mirror; recorded as provenance"
    )
    args = parser.parse_args()
    if args.offline and (args.refresh or args.geometry or args.endpoint):
        parser.error("--offline validates saved buildings only; omit download options")
    try:
        prepare(
            args.geometry,
            offline=args.offline,
            refresh=args.refresh,
            endpoint=args.endpoint,
        )
    except (httpx.HTTPError, OSError, ValueError, RuntimeError) as error:
        print(
            f"Preparation failed: {error}. Existing saved buildings were retained.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
