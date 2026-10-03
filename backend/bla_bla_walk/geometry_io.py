"""Bounded raster acquisition and native-grid geometry preparation."""

from __future__ import annotations

import hashlib
import http.client
import math
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

PAIR_VALID = 1
SURFACE_BELOW_TERRAIN = 2
SURFACE_BELOW_TERRAIN_BY_MORE_THAN_1M = 4
NODATA = -9999.0
READ_ROWS = 256


def sha256_path(path: Path) -> str:
    """Return a streaming SHA-256 for one local artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_verified(url: str, checksum: str, destination: Path) -> dict[str, Any]:
    """Download one asset atomically and reject bytes outside the inventory."""
    expected = normalized_sha256(checksum)
    if destination.exists() and sha256_path(destination) == expected:
        return _download_record(destination, expected, 0.0, True, 0)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    started = time.monotonic()
    for attempt in range(1, 33):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "bla-bla-walk-t8/1"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                if offset and response.status != 206:
                    partial.unlink(missing_ok=True)
                    continue
                if response.status not in (200, 206):
                    raise ValueError(f"asset returned HTTP {response.status}: {url}")
                server_hash = response.headers.get("X-Amz-Meta-Sha256")
                if server_hash and normalized_sha256(server_hash) != expected:
                    raise ValueError(
                        f"server checksum no longer matches inventory: {url}"
                    )
                total = _response_total(response, offset)
                mode = "ab" if response.status == 206 else "wb"
                with partial.open(mode) as handle:
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        handle.write(block)
        except (
            http.client.IncompleteRead,
            OSError,
            TimeoutError,
            urllib.error.URLError,
        ):
            time.sleep(min(attempt * 0.25, 2.0))
            continue
        size = partial.stat().st_size
        if size < total:
            time.sleep(min(attempt * 0.25, 2.0))
            continue
        if size > total:
            partial.unlink(missing_ok=True)
            raise ValueError(f"asset exceeded advertised length {total}: {url}")
        actual = sha256_path(partial)
        if actual != expected:
            partial.unlink(missing_ok=True)
            raise ValueError(f"checksum mismatch for {url}: {actual} != {expected}")
        os.replace(partial, destination)
        return _download_record(
            destination, actual, time.monotonic() - started, False, attempt
        )
    raise OSError(f"asset remained incomplete after 32 ranged attempts: {url}")


def _response_total(response: Any, offset: int) -> int:
    """Return and validate the complete byte length for a 200/206 response."""
    if response.status == 206:
        content_range = response.headers.get("Content-Range", "")
        unit_range, separator, total = content_range.partition("/")
        start = unit_range.removeprefix("bytes ").partition("-")[0]
        if not separator or int(start) != offset:
            raise ValueError(f"invalid Content-Range: {content_range}")
        return int(total)
    content_length = response.headers.get("Content-Length")
    if content_length is None:
        raise ValueError("asset response omitted Content-Length")
    return int(content_length)


def normalized_sha256(checksum: str) -> str:
    """Accept raw SHA-256 or the STAC multihash 0x12/0x20 prefix."""
    value = checksum.lower()
    if len(value) == 68 and value.startswith("1220"):
        value = value[4:]
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError(f"unsupported SHA-256 encoding: {checksum}")
    return value


def _download_record(
    path: Path, checksum: str, seconds: float, reused: bool, attempts: int
) -> dict[str, Any]:
    return {
        "bytes": path.stat().st_size,
        "sha256": checksum,
        "catalog_checksum_verified": True,
        "download_seconds": round(seconds, 6),
        "http_attempts": attempts,
        "source_cache_reused": reused,
    }


def decode_native_grid(
    source: Path, destination: Path, tile: dict[str, Any]
) -> dict[str, Any]:
    """Validate and decode a GeoTIFF by windows into an atomic float32 NPY."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    started = time.monotonic()
    with rasterio.open(source) as dataset:
        grid = validate_grid(dataset, tile)
        output = np.lib.format.open_memmap(
            partial, mode="w+", dtype="float32", shape=dataset.shape
        )
        minimum, maximum, valid_cells = math.inf, -math.inf, 0
        for row in range(0, dataset.height, READ_ROWS):
            height = min(READ_ROWS, dataset.height - row)
            window = rasterio.windows.Window(0, row, dataset.width, height)
            values = dataset.read(1, window=window, out_dtype="float32")
            output[row : row + height] = values
            valid = np.isfinite(values) & (values != NODATA)
            if valid.any():
                minimum = min(minimum, float(values[valid].min()))
                maximum = max(maximum, float(values[valid].max()))
                valid_cells += int(valid.sum())
        output.flush()
        del output
    os.replace(partial, destination)
    cells = grid["shape"][0] * grid["shape"][1]
    return {
        "path": destination.as_posix(),
        "sha256": sha256_path(destination),
        "bytes": destination.stat().st_size,
        "dtype": "float32",
        "valid_cells": valid_cells,
        "nodata_cells": cells - valid_cells,
        "minimum_metres": minimum if valid_cells else None,
        "maximum_metres": maximum if valid_cells else None,
        "decode_seconds": round(time.monotonic() - started, 6),
        **grid,
    }


def validate_grid(dataset: rasterio.io.DatasetReader, tile: dict[str, Any]) -> dict:
    """Return canonical grid metadata or reject a misaligned source."""
    expected_bounds = tuple(float(value) for value in tile["bounds_epsg2056"])
    actual_bounds = tuple(float(value) for value in dataset.bounds)
    failures = []
    if dataset.crs is None or dataset.crs.to_epsg() != 2056:
        failures.append(f"CRS {dataset.crs}")
    if dataset.shape != (2000, 2000):
        failures.append(f"shape {dataset.shape}")
    if dataset.dtypes != ("float32",):
        failures.append(f"dtype {dataset.dtypes}")
    if dataset.nodata != NODATA:
        failures.append(f"NoData {dataset.nodata}")
    if not np.allclose(actual_bounds, expected_bounds, atol=1e-6, rtol=0):
        failures.append(f"bounds {actual_bounds}")
    if dataset.transform.a != 0.5 or dataset.transform.e != -0.5:
        failures.append(f"resolution {dataset.res}")
    if failures:
        raise ValueError(f"{tile['tile']} grid mismatch: {', '.join(failures)}")
    return {
        "shape": [dataset.height, dataset.width],
        "resolution_metres": 0.5,
        "bounds_epsg2056": list(actual_bounds),
        "transform": list(dataset.transform)[:6],
        "horizontal_crs": "EPSG:2056",
        "vertical_reference": "LN02 / EPSG:5728",
        "nodata": NODATA,
    }


def build_pair_flags(
    surface_path: Path, terrain_path: Path, destination: Path
) -> dict[str, Any]:
    """Flag pair validity and impossible cross-survey height ordering."""
    surface = np.load(surface_path, mmap_mode="r")
    terrain = np.load(terrain_path, mmap_mode="r")
    if surface.shape != terrain.shape:
        raise ValueError(f"pair shape mismatch: {surface.shape} != {terrain.shape}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    flags = np.lib.format.open_memmap(
        partial, mode="w+", dtype="uint8", shape=surface.shape
    )
    counts = {"pair_valid": 0, "surface_below_terrain": 0, "below_by_gt_1m": 0}
    for row in range(0, surface.shape[0], READ_ROWS):
        stop = min(row + READ_ROWS, surface.shape[0])
        surface_rows = surface[row:stop]
        terrain_rows = terrain[row:stop]
        valid = (
            np.isfinite(surface_rows)
            & np.isfinite(terrain_rows)
            & (surface_rows != NODATA)
            & (terrain_rows != NODATA)
        )
        below = valid & (surface_rows < terrain_rows)
        severe = valid & (surface_rows < terrain_rows - 1.0)
        row_flags = valid.astype("uint8") * PAIR_VALID
        row_flags[below] |= SURFACE_BELOW_TERRAIN
        row_flags[severe] |= SURFACE_BELOW_TERRAIN_BY_MORE_THAN_1M
        flags[row:stop] = row_flags
        counts["pair_valid"] += int(valid.sum())
        counts["surface_below_terrain"] += int(below.sum())
        counts["below_by_gt_1m"] += int(severe.sum())
    flags.flush()
    del flags
    os.replace(partial, destination)
    return {
        "path": destination.as_posix(),
        "sha256": sha256_path(destination),
        "bytes": destination.stat().st_size,
        "dtype": "uint8",
        "counts": counts,
    }


def edge_statistics(first: Path, second: Path, orientation: str) -> dict[str, Any]:
    """Measure adjacent edge continuity without assuming equal elevations."""
    left = np.load(first, mmap_mode="r")
    right = np.load(second, mmap_mode="r")
    if orientation == "east":
        first_edge, second_edge = left[:, -1], right[:, 0]
    elif orientation == "north":
        first_edge, second_edge = left[0, :], right[-1, :]
    else:
        raise ValueError(f"unsupported seam orientation: {orientation}")
    valid = (
        np.isfinite(first_edge)
        & np.isfinite(second_edge)
        & (first_edge != NODATA)
        & (second_edge != NODATA)
    )
    differences = np.abs(first_edge[valid] - second_edge[valid])
    return {
        "valid_cell_pairs": int(valid.sum()),
        "unknown_cell_pairs": int(valid.size - valid.sum()),
        "absolute_delta_metres": {
            "median": float(np.median(differences)) if differences.size else None,
            "p95": float(np.quantile(differences, 0.95)) if differences.size else None,
            "maximum": float(differences.max()) if differences.size else None,
        },
    }
