"""Building-only, flat-ground shadow approximation from dated local inputs."""

import numpy as np
from rasterio.features import geometry_mask, rasterize
from rasterio.transform import from_origin


def model_grids(surface, terrain, flags, buildings, coverage, bounds, settings):
    """Build roof prisms only within mapped footprints; missing roofs stay unknown.

    Roof height above local terrain is approximated from surveyed raster cells,
    optionally replaced by an explicit mapped metre height. Trees and terrain
    relief are excluded from casting. Receivers are plausible ground outside
    footprints, never confirmed pedestrian surfaces. No levels-to-height guess.
    """
    west, south, east, north = bounds
    cell = settings["cell_size_metres"]
    transform = from_origin(west, north, cell, cell)
    shapes = [(feature["geometry"], 1) for feature in buildings]
    footprint = (
        rasterize(shapes, out_shape=surface.shape, transform=transform, dtype="uint8")
        if shapes
        else np.zeros(surface.shape, dtype="uint8")
    )
    area = geometry_mask(
        [coverage], out_shape=surface.shape, transform=transform, invert=True
    )
    valid = np.isfinite(surface) & np.isfinite(terrain) & (flags == 1)
    difference = surface - terrain
    roofs = valid & (difference > 0)
    casters = np.zeros(surface.shape, dtype="float32")
    casters[~area] = np.nan
    casters[(footprint != 0) & ~roofs] = np.nan
    casters[(footprint != 0) & roofs] = difference[(footprint != 0) & roofs]
    known_heights = [
        (feature["geometry"], feature["height_m"])
        for feature in sorted(buildings, key=lambda item: item.get("height_m") or 0)
        if feature.get("height_m") is not None
    ]
    if known_heights:
        height_grid = rasterize(
            known_heights,
            out_shape=surface.shape,
            transform=transform,
            dtype="float32",
            fill=np.nan,
        )
        known = area & np.isfinite(height_grid)
        casters[known] = height_grid[known]
    unresolved = [
        (feature["geometry"], 1)
        for feature in buildings
        if feature.get("unresolved_geometry")
    ]
    if unresolved:
        uncertain = rasterize(
            unresolved, out_shape=surface.shape, transform=transform, dtype="uint8"
        )
        casters[uncertain != 0] = np.nan
    casters[~area] = np.nan
    receivers = (
        area
        & valid
        & (footprint == 0)
        & (difference >= 0)
        & (difference <= settings["ground_difference_metres"])
    )
    return casters, np.zeros(surface.shape, dtype="float32"), receivers
