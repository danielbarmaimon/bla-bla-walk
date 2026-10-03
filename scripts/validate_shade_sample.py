"""Compare a local real raster window with the independent test ray tracer.

This is a numerical spot check, not validation of actual pedestrian shade.
Inputs must be the checksum-pinned native Basel centre pair in the inventory.
"""

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from bla_bla_walk.geometry import read_heights, sha256_file  # noqa: E402
from bla_bla_walk.geometry_io import normalized_sha256  # noqa: E402
from bla_bla_walk.shade import SHADED, UNKNOWN, shadow_mask  # noqa: E402
from bla_bla_walk.solar import solar_position  # noqa: E402
from test_shade import independent_reference  # noqa: E402


def validate_sample(surface_path: Path, terrain_path: Path) -> dict:
    """Validate 48 deterministic receiver/time combinations on pinned heights."""
    inventory = json.loads((ROOT / "data/tile-inventory.json").read_text())
    tile = next(row for row in inventory["tiles"] if row["tile"] == "2610-1266")
    inputs = {}
    for kind, path in (("surface", surface_path), ("terrain", terrain_path)):
        inputs[kind] = sha256_file(path)
        if inputs[kind] != normalized_sha256(tile[kind]["catalog_checksum"]):
            raise ValueError(f"{kind} input differs from the pinned source")
        with rasterio.open(path) as dataset:
            if dataset.res != (0.5, 0.5) or dataset.crs.to_epsg() != 2056:
                raise ValueError("Expected native LV95 0.5m source grids")
            if list(dataset.bounds) != tile["bounds_epsg2056"]:
                raise ValueError("Source grid does not align with the selected tile")
    window = Window(970, 970, 64, 64)
    surface = read_heights(surface_path, window).filled(np.nan)
    terrain = read_heights(terrain_path, window).filled(np.nan)
    valid = np.isfinite(surface) & np.isfinite(terrain)
    flags = valid.astype("uint8")
    flags[valid & (surface < terrain)] |= 2
    flags[valid & (surface < terrain - 1)] |= 4
    # Only numerical comparison candidates: this does not verify walkability.
    candidates = np.argwhere((flags == 1) & (surface - terrain <= 0.1))
    if len(candidates) < 16:
        raise ValueError("Window has fewer than 16 ground-envelope candidates")
    candidates = candidates[np.linspace(0, len(candidates) - 1, 16, dtype=int)]
    receivers = np.zeros(surface.shape, dtype=bool)
    receivers[candidates[:, 0], candidates[:, 1]] = True
    longitude, latitude = transform(
        "EPSG:2056", "EPSG:4326", [2610500.25], [1266499.75]
    )
    east, north = transform(
        "EPSG:4326",
        "EPSG:2056",
        [longitude[0]] * 2,
        [latitude[0], latitude[0] + 0.0001],
    )
    grid_rotation = -math.degrees(math.atan2(east[1] - east[0], north[1] - north[0]))
    checks = []
    for hour in (8, 12, 15):
        moment = datetime.fromisoformat(f"2026-10-03T{hour:02}:00:00+00:00")
        elevation, azimuth = solar_position(moment, latitude[0], longitude[0])
        states = shadow_mask(
            surface,
            terrain,
            elevation_deg=elevation,
            azimuth_deg=azimuth - grid_rotation,
            cell_size_m=0.5,
            max_distance_m=1500,
            minimum_elevation_deg=10,
            cell_flags=flags,
            receivers=receivers,
            receiver_elevations=surface,
        )
        compared = []
        for row, col in candidates:
            expected = independent_reference(
                surface,
                row,
                col,
                azimuth - grid_rotation,
                elevation,
                None,
                cell=0.5,
                receiver_height=float(surface[row, col]),
                terrain=terrain,
                flags=flags,
                extent=1500,
            )
            if int(states[row, col]) != expected:
                raise AssertionError(f"Independent tracer disagrees at {row},{col}")
            compared.append({"row": int(row), "column": int(col), "state": expected})
        checks.append(
            {
                "time": moment.isoformat(),
                "elevation_degrees": elevation,
                "azimuth_degrees": azimuth,
                "receivers": compared,
            }
        )
    return {
        "schema_version": 1,
        "scope": "independent numerical real-raster spot check",
        "tile": tile["tile"],
        "source_sha256": inputs,
        "attribution": "© swisstopo",
        "window": [970, 970, 64, 64],
        "cell_size_m": 0.5,
        "grid_north_rotation_degrees": grid_rotation,
        "comparisons": sum(len(check["receivers"]) for check in checks),
        "shaded": sum(
            point["state"] == SHADED for check in checks for point in check["receivers"]
        ),
        "unknown": sum(
            point["state"] == UNKNOWN
            for check in checks
            for point in check["receivers"]
        ),
        "checks": checks,
        "limits": (
            "No physical ground/foliage validation or horizon ceiling is claimed. "
            "Unblocked finite rays remain unknown. Compact-grid real-scene accuracy, "
            "score sensitivity and city-scale performance remain open."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--terrain", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = validate_sample(args.surface, args.terrain)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        f"{evidence['comparisons']} reference matches; "
        f"{evidence['shaded']} shaded, {evidence['unknown']} unknown"
    )


if __name__ == "__main__":
    main()
