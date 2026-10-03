"""Audit information lost by 2m height encoding on pinned native raster pairs.

This isolates vertical encoding at native resolution. It does not validate the
1m resampling pipeline, physical receivers, route scores or horizon coverage.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from bla_bla_walk.geometry import (  # noqa: E402
    compact_heights,
    geometry_settings,
    read_heights,
    sha256_file,
)
from bla_bla_walk.geometry_io import normalized_sha256  # noqa: E402

SCENES = (
    "urban_centre",
    "vegetation_lange_erlen",
    "tall_building_roche",
    "border_kleinhuningen",
)


def audit_heights(surface, terrain, step: float) -> dict:
    """Count false equality and erased inversion evidence on aligned metre grids."""
    if surface.shape != terrain.shape or surface.ndim != 2 or surface.size == 0:
        raise ValueError("Expected matching nonempty two-dimensional height grids")
    if not np.isfinite(step) or step <= 0:
        raise ValueError("Height step must be positive and finite")
    surface = np.ma.masked_invalid(surface)
    terrain = np.ma.masked_invalid(terrain)
    valid = ~(np.ma.getmaskarray(surface) | np.ma.getmaskarray(terrain))
    settings = {
        "cell_size_metres": 0.5,
        "height_step_metres": step,
        "nodata_code": -32768,
    }
    # Same source/output spacing deliberately isolates vertical information loss.
    encoded_surface = compact_heights(surface, "surface", 0.5, settings)
    encoded_terrain = compact_heights(terrain, "terrain", 0.5, settings)
    equal = valid & (encoded_surface == encoded_terrain)
    below = valid & (surface.filled(0) < terrain.filled(0))
    unequal = valid & (surface.filled(0) != terrain.filled(0))
    errors = []
    for values, codes in ((surface, encoded_surface), (terrain, encoded_terrain)):
        error = np.abs(codes[valid] * step - values.filled(0)[valid])
        errors.append(round(float(error.max()), 6) if error.size else None)
    return {
        "cells": int(surface.size),
        "valid_pairs": int(valid.sum()),
        "missing_pairs": int((~valid).sum()),
        "source_below_terrain": int(below.sum()),
        "encoded_equal_pairs": int(equal.sum()),
        "encoded_equal_but_source_unequal": int((equal & unequal).sum()),
        "erased_below_terrain": int((equal & below).sum()),
        "surface_max_encoding_error_metres": errors[0],
        "terrain_max_encoding_error_metres": errors[1],
    }


def audit_scene(directory: Path, scene: str, tiles: list, step: float) -> dict:
    """Verify catalogue checksums and alignment before auditing one source pair."""
    paths = {kind: directory / f"{scene}-{kind}.tif" for kind in ("surface", "terrain")}
    checksums = {kind: sha256_file(path) for kind, path in paths.items()}
    tile = next(
        (
            row
            for row in tiles
            if all(
                row.get(kind, {}).get("catalog_checksum")
                and normalized_sha256(row[kind]["catalog_checksum"]) == checksums[kind]
                for kind in paths
            )
        ),
        None,
    )
    if tile is None:
        raise ValueError(f"{scene}: pair differs from the pinned inventory")
    with (
        rasterio.open(paths["surface"]) as surface_ds,
        rasterio.open(paths["terrain"]) as terrain_ds,
    ):
        for dataset in (surface_ds, terrain_ds):
            if (
                dataset.crs.to_epsg() != 2056
                or dataset.res != (0.5, 0.5)
                or list(dataset.bounds) != tile["bounds_epsg2056"]
                or dataset.count != 1
            ):
                raise ValueError(f"{scene}: expected pinned native LV95 grid")
        if (
            surface_ds.transform != terrain_ds.transform
            or surface_ds.shape != terrain_ds.shape
        ):
            raise ValueError(f"{scene}: grids do not align")
    return {
        "scene": scene,
        "tile": tile["tile"],
        "source_sha256": checksums,
        "source_cell_metres": 0.5,
        **audit_heights(
            read_heights(paths["surface"]), read_heights(paths["terrain"]), step
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads((ROOT / "data/tile-inventory.json").read_text())
    step = geometry_settings()["height_step_metres"]
    scenes = [
        audit_scene(args.source_directory, scene, inventory["tiles"], step)
        for scene in SCENES
    ]
    evidence = {
        "schema_version": 1,
        "scope": "vertical encoding information-loss audit at native 0.5m spacing",
        "attribution": "© swisstopo",
        "height_step_metres": step,
        "scenes": scenes,
        "production_receiver_admission": False,
        "limits": (
            "No horizontal resampling, physical receiver, horizon, route or "
            "city-performance acceptance. Native 2m terrain and actual compact "
            "assets must be checked separately. Equal encoded heights cannot "
            "establish supported receivers; preserve source inversion flags."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    for scene in scenes:
        print(
            f"{scene['scene']}: {scene['erased_below_terrain']} erased inversion "
            f"flags; {scene['encoded_equal_but_source_unequal']} false equal pairs"
        )


if __name__ == "__main__":
    main()
