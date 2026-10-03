"""Prepare compact surveyed heights; this module does not calculate shade."""

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]


def geometry_settings() -> dict:
    """Read the versioned preparation settings shared by ingestion and consumers."""
    return json.loads((ROOT / "config/geometry.json").read_text())


def sha256_file(path: Path) -> str:
    """Hash files incrementally without holding source rasters in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compact_heights(values, kind: str, source_cell: float, settings: dict):
    """Resample with conservative missingness, then encode nearest height steps.

    Surface maxima retain potential casters but can enlarge them. Terrain nearest
    repeats native 2m values without inventing detail or interpolating tile seams.
    Any missing surface sample makes its aggregated output cell unknown.
    """
    cell = settings["cell_size_metres"]
    masked = np.ma.masked_invalid(values)
    data = masked.filled(0)
    unknown = np.ma.getmaskarray(masked)
    if source_cell < cell:
        ratio = cell / source_cell
        factor = int(ratio)
        if ratio != factor or any(size % factor for size in data.shape):
            raise ValueError("Source grid cannot align with the requested cell size")
        shape = (data.shape[0] // factor, factor, data.shape[1] // factor, factor)
        if kind != "surface":
            raise ValueError("Only surface max aggregation is supported")
        # Unknown blocks remain unknown even if another sample has a valid height.
        data = np.where(unknown, -np.inf, data).reshape(shape).max(axis=(1, 3))
        unknown = unknown.reshape(shape).any(axis=(1, 3))
    elif source_cell > cell:
        ratio = source_cell / cell
        factor = int(ratio)
        if ratio != factor or kind != "terrain":
            raise ValueError("Only integer terrain nearest upsampling is supported")
        data = data.repeat(factor, axis=0).repeat(factor, axis=1)
        unknown = unknown.repeat(factor, axis=0).repeat(factor, axis=1)
    step = settings["height_step_metres"]
    codes = np.floor(np.where(unknown, 0, data) / step + 0.5)
    valid = codes[~unknown]
    if np.any(valid <= -32768) or np.any(valid > 32767):
        raise ValueError("Heights exceed the int16 encoding range")
    result = codes.astype("int16")
    result[unknown] = settings["nodata_code"]
    return result


def prepare_raster(source: Path, target: Path, tile: dict, kind: str) -> dict:
    """Check source alignment and write one bounded, compressed height-code tile."""
    settings = geometry_settings()
    bounds = tile["bounds_epsg2056"]
    with rasterio.open(source) as dataset:
        if dataset.crs != rasterio.crs.CRS.from_epsg(2056):
            raise ValueError("Unexpected horizontal CRS")
        if list(dataset.bounds) != bounds or dataset.count != 1:
            raise ValueError("Source bounds or band count do not match the inventory")
        expected = 0.5 if kind == "surface" else 2.0
        if dataset.res != (expected, expected) or dataset.nodata != -9999:
            raise ValueError("Unexpected native resolution or NoData")
        codes = compact_heights(dataset.read(1, masked=True), kind, expected, settings)
    cell = settings["cell_size_metres"]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.tif")
    with rasterio.open(
        temporary,
        "w",
        driver="GTiff",
        height=codes.shape[0],
        width=codes.shape[1],
        count=1,
        dtype="int16",
        crs="EPSG:2056",
        transform=from_origin(bounds[0], bounds[3], cell, cell),
        nodata=settings["nodata_code"],
        tiled=True,
        blockxsize=256,
        blockysize=256,
        compress="DEFLATE",
        predictor=2,
    ) as output:
        output.write(codes, 1)
        output.scales = (settings["height_step_metres"],)
        output.offsets = (0,)
        output.set_band_unit(1, "metre")
        output.update_tags(
            vertical_reference=settings["vertical_reference"],
            kind=kind,
            source_cell_metres=str(expected),
            resampling=settings[f"{kind}_resampling"],
            height_encoding="height_metres = code * band_scale; mask NoData first",
        )
    temporary.replace(target)
    return {
        "file": target.name,
        "sha256": sha256_file(target),
        "bytes": target.stat().st_size,
        "shape": list(codes.shape),
        "unknown_cells": int(np.count_nonzero(codes == settings["nodata_code"])),
        "source_cell_size_metres": expected,
    }


def compact_pair_flags(surface, terrain):
    """Preserve source subcell inconsistencies before pooling and quantization.

    Inputs are aligned 0.5m surface and 2m terrain metre arrays. The 1m output
    uses native flag bits: all samples must be valid; any inverted subcell
    invalidates support even if max pooling or rounding hides it. Flags alone
    do not establish a walking receiver.
    """
    surface = np.ma.masked_invalid(surface)
    terrain = np.ma.masked_invalid(terrain)
    if (
        surface.ndim != 2
        or terrain.ndim != 2
        or surface.size == 0
        or surface.shape != tuple(size * 4 for size in terrain.shape)
    ):
        raise ValueError("Expected aligned 0.5m surface and 2m terrain grids")
    terrain = terrain.repeat(4, axis=0).repeat(4, axis=1)
    valid = ~(np.ma.getmaskarray(surface) | np.ma.getmaskarray(terrain))
    difference = surface.filled(0) - terrain.filled(0)
    shape = (surface.shape[0] // 2, 2, surface.shape[1] // 2, 2)
    flags = valid.reshape(shape).all(axis=(1, 3)).astype("uint8")
    flags[(valid & (difference < 0)).reshape(shape).any(axis=(1, 3))] |= 2
    flags[(valid & (difference < -1)).reshape(shape).any(axis=(1, 3))] |= 4
    return flags


def read_heights(path: Path, window=None):
    """Return masked elevation metres; raw stored codes are not metre heights."""
    with rasterio.open(path) as dataset:
        return (
            dataset.read(1, window=window, masked=True).astype("float32")
            * (dataset.scales[0])
            + dataset.offsets[0]
        )
