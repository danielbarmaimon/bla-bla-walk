"""Windowed compact metre grids; missing halo cells stay masked as unknown."""

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from rasterio.windows import Window

from .geometry import read_heights, sha256_file


def snapped_bounds(bounds, cell):
    """Align outward to the globally anchored LV95 grid, preserving tile seams."""
    west, south, east, north = bounds
    return (
        math.floor(west / cell) * cell,
        math.floor(south / cell) * cell,
        math.ceil(east / cell) * cell,
        math.ceil(north / cell) * cell,
    )


def asset_paths(directory, manifest):
    """Reject manifest paths outside the local geometry directory."""
    paths = {}
    for name, asset in manifest["assets"].items():
        path = (directory / asset["file"]).resolve()
        if path.parent != directory.resolve():
            raise ValueError("Invalid prepared geometry path")
        paths[name] = path
    return paths


def load_metre_grids(directory: Path, manifest, bounds):
    """Read only intersecting windows, checking hashes, grid and band encoding.

    The manifest version pins source vintages. A compact equal-height cell does
    not certify a walking receiver: quantization can erase survey discrepancies.
    No gap is filled and no input is fetched from the internet.
    """
    cell = manifest["settings"]["cell_size_metres"]
    west, south, east, north = bounds
    shape = (round((north - south) / cell), round((east - west) / cell))
    surface = np.full(shape, np.nan, dtype="float32")
    terrain = np.full(shape, np.nan, dtype="float32")
    paths = asset_paths(directory, manifest)
    for name, asset in manifest["assets"].items():
        tile_west, tile_south = (int(part) * 1000 for part in asset["tile"].split("-"))
        left, bottom = max(west, tile_west), max(south, tile_south)
        right, top = min(east, tile_west + 1000), min(north, tile_south + 1000)
        path = paths[name]
        if left >= right or bottom >= top or not path.is_file():
            continue
        if sha256_file(path) != asset["sha256"]:
            raise ValueError(f"Prepared geometry checksum mismatch: {name}")
        with rasterio.open(path) as dataset:
            expected = from_origin(tile_west, tile_south + 1000, cell, cell)
            if (
                dataset.crs != rasterio.crs.CRS.from_epsg(2056)
                or not dataset.transform.almost_equals(expected)
                or dataset.scales[0] != manifest["settings"]["height_step_metres"]
                or dataset.nodata != manifest["settings"]["nodata_code"]
                or dataset.shape != tuple(asset["shape"])
            ):
                raise ValueError(f"Prepared geometry encoding mismatch: {name}")
        window = Window(
            round((left - tile_west) / cell),
            round((tile_south + 1000 - top) / cell),
            round((right - left) / cell),
            round((top - bottom) / cell),
        )
        values = read_heights(path, window).filled(np.nan)
        row, col = round((north - top) / cell), round((left - west) / cell)
        grid = surface if asset["kind"] == "surface" else terrain
        grid[row : row + values.shape[0], col : col + values.shape[1]] = values
    return surface, terrain


def city_cells(boundary, bounds, cell):
    """Select cell centres inside the admitted canton, including polygon holes."""
    west, south, east, north = bounds
    return geometry_mask(
        [boundary],
        out_shape=(round((north - south) / cell), round((east - west) / cell)),
        transform=from_origin(west, north, cell, cell),
        invert=True,
    )


def corridor_cells(request, bounds, cell):
    """Limit a request to cell centres within half the corridor's full width."""
    west, south, east, north = bounds
    shape = (round((north - south) / cell), round((east - west) / cell))
    if request.corridor is None:
        return np.ones(shape, dtype=bool)
    x = west + (np.arange(shape[1]) + 0.5) * cell
    y = north - (np.arange(shape[0]) + 0.5) * cell
    selected = np.zeros(shape, dtype=bool)
    for (ax, ay), (bx, by) in zip(request.corridor, request.corridor[1:]):
        dx, dy = bx - ax, by - ay
        denominator = dx * dx + dy * dy
        fraction = (
            np.clip(
                ((x[None, :] - ax) * dx + (y[:, None] - ay) * dy) / denominator, 0, 1
            )
            if denominator
            else np.zeros(shape)
        )
        distance = (x[None, :] - ax - fraction * dx) ** 2 + (
            y[:, None] - ay - fraction * dy
        ) ** 2
        selected |= distance <= (request.corridor_width_m / 2) ** 2
    return selected
