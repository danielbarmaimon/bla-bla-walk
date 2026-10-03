"""Measure actual compact-grid encoding and saved-route sample sensitivity.

Unquantized control and encoded grids use the same 1m max/nearest resampling.
Numerical upper-envelope receivers do not admit walking ground or foliage.
Finite unblocked rays stay unknown; no horizon maximum is invented.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from audit_compact_receivers import SCENES  # noqa: E402
from bla_bla_walk.geometry import (  # noqa: E402
    compact_pair_flags,
    geometry_settings,
    prepare_raster,
    read_heights,
    sha256_file,
)
from bla_bla_walk.geometry_io import normalized_sha256  # noqa: E402
from bla_bla_walk.shade import SHADED, UNKNOWN, shadow_mask  # noqa: E402
from bla_bla_walk.shade_service import solar_location  # noqa: E402
from bla_bla_walk.solar import solar_position  # noqa: E402
from prepare_geometry import download_verified, resolve_asset, write_json  # noqa: E402
from test_shade import independent_reference  # noqa: E402

TIMES = tuple(
    datetime.fromisoformat(f"2026-10-03T{h}:00:00+00:00") for h in ("08", "12", "15")
)
TILES = ("2610-1266", "2613-1269", "2612-1267", "2611-1270", "2611-1266", "2611-1267")


def download_sources(directory, inventory):
    """Fetch only six audit pairs with pinned hashes; keep sources local."""
    directory.mkdir(parents=True, exist_ok=True)
    records = {}
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for tile_id in TILES:
            tile = next(t for t in inventory["tiles"] if t["tile"] == tile_id)
            for kind in ("surface", "terrain"):
                asset = resolve_asset(tile, kind, client)
                download_verified(asset, directory / f"{tile_id}-{kind}.tif", client)
                records[f"{tile_id}-{kind}"] = asset
                print(f"Verified {tile_id} {kind}", flush=True)
    write_json(directory / "route-sources.json", records)


def control_grids(surface_path, terrain_path):
    """Resample the pinned 0.5m surface and 2m terrain without height rounding."""
    surface = read_heights(surface_path).filled(np.nan)
    terrain = read_heights(terrain_path).filled(np.nan)
    if surface.shape != (2000, 2000) or terrain.shape != (500, 500):
        raise ValueError("Expected a native 1km surface/terrain pair")
    surface = surface.reshape(1000, 2, 1000, 2).max(axis=(1, 3))
    terrain = terrain.repeat(2, axis=0).repeat(2, axis=1)
    return surface, terrain


def verified_pair(surface_path, terrain_path, tile, terrain_record, output):
    """Verify both actual source assets and prepare through production encoding."""
    surface_sha = sha256_file(surface_path)
    terrain_sha = sha256_file(terrain_path)
    if surface_sha != normalized_sha256(tile["surface"]["catalog_checksum"]):
        raise ValueError("Surface catalogue checksum mismatch")
    expected_url = tile["terrain"]["asset_url"].replace("_0.5_2056_", "_2_2056_")
    if terrain_record["url"] != expected_url or terrain_sha != terrain_record["sha256"]:
        raise ValueError("Native 2m terrain pin mismatch")
    prepared = {}
    for kind, path in (("surface", surface_path), ("terrain", terrain_path)):
        prepared[kind] = prepare_raster(
            path, output / f"{tile['tile']}-{kind}.tif", tile, kind
        )
    control = control_grids(surface_path, terrain_path)
    flags = compact_pair_flags(read_heights(surface_path), read_heights(terrain_path))
    flag_path = output / f"{tile['tile']}-flags.npy"
    np.save(flag_path, flags)
    prepared["pair_flags"] = {
        "file": flag_path.name,
        "sha256": sha256_file(flag_path),
        "bytes": flag_path.stat().st_size,
    }
    compact = tuple(
        read_heights(output / f"{tile['tile']}-{kind}.tif").filled(np.nan)
        for kind in ("surface", "terrain")
    )
    valid = np.isfinite(control[0]) & np.isfinite(control[1])
    erased = valid & (control[0] < control[1]) & (compact[0] >= compact[1])
    errors = [
        round(float(np.max(np.abs(a[valid] - b[valid]))), 6)
        for a, b in zip(control, compact)
    ]
    return (
        control,
        compact,
        flags,
        {
            "tile": tile["tile"],
            "source_sha256": {"surface": surface_sha, "terrain_2m": terrain_sha},
            "prepared": prepared,
            "valid_pairs": int(valid.sum()),
            "erased_inversions": int(erased.sum()),
            "source_subcell_inversion_cells": int(((flags & 2) != 0).sum()),
            "max_encoding_error_metres": errors,
        },
    )


def compare_window(control, compact, row, col, bounds, pair_flags, reference=False):
    """Compare the same numerical receiver on a bounded 128m local scene."""
    row0, col0 = max(0, row - 64), max(0, col - 64)
    row1, col1 = min(1000, row + 64), min(1000, col + 64)
    selection = np.s_[row0:row1, col0:col1]
    source_surface, source_terrain = (grid[selection] for grid in control)
    encoded_surface, encoded_terrain = (grid[selection] for grid in compact)
    flags = pair_flags[selection]
    receivers = np.zeros(source_surface.shape, dtype=bool)
    receivers[row - row0, col - col0] = True
    latitude, longitude, rotation = solar_location(bounds)
    result = []
    for moment in TIMES:
        elevation, azimuth = solar_position(moment, latitude, longitude)
        states = []
        for surface, terrain in (
            (source_surface, source_terrain),
            (encoded_surface, encoded_terrain),
        ):
            mask = shadow_mask(
                surface,
                terrain,
                elevation_deg=elevation,
                azimuth_deg=azimuth - rotation,
                cell_size_m=1,
                max_distance_m=1500,
                minimum_elevation_deg=10,
                receivers=receivers,
                receiver_elevations=surface,
                cell_flags=flags,
            )
            states.append(int(mask[row - row0, col - col0]))
            if reference:
                receiver_valid = (
                    flags[row - row0, col - col0] == 1
                    and np.isfinite(surface[row - row0, col - col0])
                    and np.isfinite(terrain[row - row0, col - col0])
                    and surface[row - row0, col - col0]
                    >= terrain[row - row0, col - col0]
                )
                expected = (
                    independent_reference(
                        surface,
                        row - row0,
                        col - col0,
                        azimuth - rotation,
                        elevation,
                        None,
                        cell=1,
                        receiver_height=float(surface[row - row0, col - col0]),
                        terrain=terrain,
                        flags=flags,
                        extent=1500,
                    )
                    if receiver_valid
                    else UNKNOWN
                )
                if states[-1] != expected:
                    raise AssertionError("Independent compact tracer disagrees")
        result.append(states)
    return result


def route_samples(feature):
    """Sample projected route segments every 10m with full-length denominators."""
    coordinates = feature["geometry"]["coordinates"]
    x, y = transform(
        4326, 2056, [p[0] for p in coordinates], [p[1] for p in coordinates]
    )
    samples = []
    for ax, ay, bx, by in zip(x, y, x[1:], y[1:]):
        length = float(np.hypot(bx - ax, by - ay))
        count = max(1, int(np.ceil(length / 10)))
        for fraction in (np.arange(count) + 0.5) / count:
            samples.append(
                (ax + fraction * (bx - ax), ay + fraction * (by - ay), length / count)
            )
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / ".hack/e-t10")
    parser.add_argument("--native-samples", type=Path, default=ROOT / ".hack/t0")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download six pinned pairs; default validation is offline",
    )
    args = parser.parse_args()
    inventory = json.loads((ROOT / "data/tile-inventory.json").read_text())
    if args.download:
        download_sources(args.sources, inventory)
    sources = json.loads((args.sources / "route-sources.json").read_text())
    output = args.sources / "compact"
    arrays, reports = {}, []
    names = dict(zip(("2610-1266", "2613-1269", "2612-1267", "2611-1270"), SCENES))
    for tile_id in (*names, "2611-1266", "2611-1267"):
        tile = next(t for t in inventory["tiles"] if t["tile"] == tile_id)
        surface = (
            args.native_samples / f"{names[tile_id]}-surface.tif"
            if tile_id in names
            else args.sources / f"{tile_id}-surface.tif"
        )
        if not surface.exists():
            surface = args.sources / f"{tile_id}-surface.tif"
        terrain = args.sources / f"{tile_id}-terrain.tif"
        record = sources.get(tile_id) or sources[tile_id + "-terrain"]
        control, compact, flags, report = verified_pair(
            surface, terrain, tile, record, output
        )
        arrays[tile_id] = (control, compact, tile["bounds_epsg2056"], flags)
        comparisons = [
            compare_window(
                control,
                compact,
                row,
                col,
                tile["bounds_epsg2056"],
                flags,
                reference=True,
            )
            for row, col in ((500, 500), (490, 490), (510, 510), (500, 510))
        ]
        report["numerical_scene_comparisons"] = 12
        report["receiver_policy_and_reference_matches"] = 24
        report["independent_ray_reference_matches"] = int(
            sum(
                flags[row, col] == 1
                for row, col in ((500, 500), (490, 490), (510, 510), (500, 510))
            )
            * 6
        )
        report["invalid_receiver_unknown_checks"] = (
            24 - report["independent_ray_reference_matches"]
        )
        report["changed_scene_states"] = sum(
            a != b for point in comparisons for a, b in point
        )
        reports.append(report)
    routes = []
    for feature in json.loads((ROOT / "data/routes/demo.geojson").read_text())[
        "features"
    ]:
        sums = np.zeros((3, 3), dtype=float)
        samples = route_samples(feature)
        for east, north, length in samples:
            tile_id = f"{int(east // 1000)}-{int(north // 1000)}"
            control, compact, bounds, flags = arrays[tile_id]
            row, col = int(bounds[3] - north), int(east - bounds[0])
            for i, (a, b) in enumerate(
                compare_window(control, compact, row, col, bounds, flags)
            ):
                sums[i] += [
                    length * (a == SHADED),
                    length * (b == SHADED),
                    length * (a != b),
                ]
        routes.append(
            {
                "route_id": feature["properties"]["route_id"],
                "samples": len(samples),
                "sampled_length_metres": round(sum(p[2] for p in samples), 6),
                "times": [
                    {
                        "time": moment.isoformat(),
                        "control_upper_envelope_shaded_metres": round(values[0], 6),
                        "encoded_upper_envelope_shaded_metres": round(values[1], 6),
                        "changed_state_metres": round(values[2], 6),
                    }
                    for moment, values in zip(TIMES, sums)
                ],
            }
        )
    evidence = {
        "schema_version": 1,
        "settings": geometry_settings(),
        "tiles": reports,
        "route_sensitivity": routes,
        "production_receiver_admission": False,
        "limits": (
            "Numerical upper-envelope receivers only; no walking ground or "
            "physical shade acceptance. 128m windows omit distant blockers, "
            "so unresolved rays remain unknown. Same-grid unquantized control "
            "isolates encoding. No route recommendation or horizon ceiling "
            "is admitted."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(routes, indent=2))


if __name__ == "__main__":
    main()
