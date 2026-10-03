"""Direct-sun occlusion of supported ground receivers by surveyed height prisms.

Rows run south, columns east. Heights must be decoded metres, never int16 codes.
This calculation has no provider calls, caching, API or route scoring.
"""

import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from .interfaces import ShadeMetadata, ShadeState
from .solar import solar_position

UNKNOWN = ShadeState.UNKNOWN
SUNLIT = ShadeState.SUNLIT
SHADED = ShadeState.SHADED
NIGHT = ShadeState.NIGHT
RAY_BATCH_SIZE = 4096
SETTINGS_PATH = Path(__file__).resolve().parents[2] / "config/shade.json"


def calculate_shade(
    surface,
    terrain,
    *,
    requested_time: datetime,
    geometry_version: str,
    latitude: float,
    longitude: float,
    cell_size_m: float,
    grid_north_rotation_deg: float,
    **ray_options,
):
    """Return a uint8 state raster plus the existing canonical ShadeMetadata.

    No time buckets: effective time equals requested time. Positive grid rotation
    means grid north lies clockwise from true north; callers must resolve their
    projection's convergence. ray_options are documented by shadow_mask.
    """
    metadata = ShadeMetadata(
        requested_time=requested_time,
        effective_time=requested_time,
        geometry_version=geometry_version,
        resolution_m=cell_size_m,
    )
    if not geometry_version.strip() or not math.isfinite(grid_north_rotation_deg):
        raise ValueError("Geometry version and finite grid rotation are required")
    elevation, azimuth = solar_position(requested_time, latitude, longitude)
    settings = json.loads(SETTINGS_PATH.read_text())
    limits = {
        "minimum_elevation_deg": settings["minimum_elevation_degrees"],
        "max_distance_m": settings["maximum_ray_distance_metres"],
    }
    limits.update(ray_options)
    states = shadow_mask(
        surface,
        terrain,
        elevation_deg=elevation,
        azimuth_deg=azimuth - grid_north_rotation_deg,
        cell_size_m=cell_size_m,
        **limits,
    )
    return states, metadata


def shadow_mask(
    surface,
    terrain,
    *,
    elevation_deg: float,
    azimuth_deg: float,
    cell_size_m: float,
    max_distance_m: float,
    minimum_elevation_deg: float,
    horizon_ceiling_m: float | None = None,
    cell_flags=None,
    receivers=None,
    receiver_elevations=None,
):
    """Trace ground-to-sun rays through every intersected raster cell.

    A surface cell is a constant-height opaque prism. Native T8 flags require
    bit 1 and forbid bits 2/4; absent flags still reject surface below terrain.
    Default receivers require surface equal to terrain. For surveyed ground with
    small surface/terrain differences, callers can supply absolute metre receiver
    elevations plus an explicitly verified ground/corridor mask. Receivers below
    the surface remain unknown: these grids cannot resolve canopy interiors.

    horizon_ceiling_m is an externally VERIFIED absolute elevation bound on all
    potential blockers beyond and within this grid. Never infer it from local
    raster maxima alone. Without it, an unblocked finite ray stays UNKNOWN.
    Missing cells invalidate sunlit evidence, but a later known blocker still
    proves SHADED. NIGHT is separate from daytime shade. Low sun stays UNKNOWN.
    """
    surface = np.ma.asarray(surface, dtype="float32").filled(np.nan)
    terrain = np.ma.asarray(terrain, dtype="float32").filled(np.nan)
    _validate_inputs(
        surface,
        terrain,
        cell_size_m,
        max_distance_m,
        minimum_elevation_deg,
        elevation_deg,
        azimuth_deg,
        horizon_ceiling_m,
    )
    valid = np.isfinite(surface) & np.isfinite(terrain) & (surface >= terrain)
    if cell_flags is not None:
        flags = np.asarray(cell_flags)
        if flags.shape != surface.shape or flags.dtype.kind not in "ui":
            raise ValueError("Cell flags must be an integer grid of the same shape")
        valid &= ((flags & 1) != 0) & ((flags & 6) == 0)
    base = terrain
    selected = valid & np.isclose(surface, terrain, atol=1e-8, rtol=0)
    if receivers is not None:
        receivers = np.asarray(receivers)
        if receivers.shape != surface.shape or receivers.dtype != bool:
            raise ValueError("Receivers must be a boolean grid of the same shape")
        selected &= receivers
    if receiver_elevations is not None:
        base = np.ma.asarray(receiver_elevations, dtype="float32").filled(np.nan)
        if receivers is None or base.shape != surface.shape:
            raise ValueError(
                "Receiver elevations require a matching explicit receiver mask"
            )
        selected = valid & receivers & np.isfinite(base) & (base >= surface)
    output = np.full(surface.shape, UNKNOWN, dtype="uint8")
    if elevation_deg <= 0:
        output[selected] = NIGHT
        return output
    if elevation_deg < minimum_elevation_deg:
        return output
    if elevation_deg == 90:
        # A vertical ray stays in its known receiver column.
        output[selected] = SUNLIT
        return output
    if horizon_ceiling_m is not None and np.any(surface[valid] > horizon_ceiling_m):
        raise ValueError("Verified horizon ceiling is below a known surface")
    rows, columns = np.nonzero(selected)
    for start in range(0, len(rows), RAY_BATCH_SIZE):
        selection = slice(start, start + RAY_BATCH_SIZE)
        output[rows[selection], columns[selection]] = _trace_batch(
            surface,
            base,
            valid,
            rows[selection],
            columns[selection],
            elevation_deg,
            azimuth_deg,
            cell_size_m,
            max_distance_m,
            horizon_ceiling_m,
        )
    return output


def _validate_inputs(
    surface, terrain, cell, distance, minimum, elevation, azimuth, ceiling
):
    if surface.ndim != 2 or surface.size == 0 or terrain.shape != surface.shape:
        raise ValueError("Surface and terrain must be nonempty matching 2D grids")
    if not all(math.isfinite(x) for x in (cell, distance, minimum, elevation, azimuth)):
        raise ValueError("Ray parameters must be finite")
    if (
        cell <= 0
        or distance <= 0
        or not 0 < minimum <= 90
        or not -90 <= elevation <= 90
    ):
        raise ValueError("Invalid grid resolution, ray extent or solar elevation")
    if ceiling is not None and not math.isfinite(ceiling):
        raise ValueError("Verified horizon ceiling must be finite")


def _trace_batch(
    surface, terrain, valid, rows, columns, elevation, azimuth, cell, extent, ceiling
):
    """Vectorized grid-boundary traversal; each entry tests a whole cell prism."""
    radians = math.radians(azimuth)
    dr, dc = -math.cos(radians), math.sin(radians)
    dr = 0.0 if abs(dr) < 1e-12 else dr
    dc = 0.0 if abs(dc) < 1e-12 else dc
    row_delta = cell / abs(dr) if dr else math.inf
    col_delta = cell / abs(dc) if dc else math.inf
    next_row = np.full(len(rows), row_delta / 2)
    next_col = np.full(len(rows), col_delta / 2)
    row, col = rows.copy(), columns.copy()
    base = terrain[rows, columns]
    slope = math.tan(math.radians(elevation))
    ceiling_distance = (
        np.maximum(0, ceiling - base) / slope
        if ceiling is not None
        else np.full(len(rows), math.inf)
    )
    result = np.full(len(rows), UNKNOWN, dtype="uint8")
    active = np.ones(len(rows), dtype=bool)
    uncertain = np.zeros(len(rows), dtype=bool)
    while np.any(active):
        entry = np.minimum(next_row, next_col)
        # Crossing the ceiling within the current valid prism ends this ray.
        clear = (
            active
            & ~uncertain
            & (ceiling_distance <= entry)
            & (ceiling_distance <= extent)
        )
        result[clear] = SUNLIT
        active[clear] = False
        active &= entry <= extent
        # Treat roundoff at an exact corner as diagonal entry, not a spurious
        # intersection with a neighbouring prism of zero traversal length.
        corner = np.isclose(next_row, next_col, rtol=0, atol=1e-9)
        step_row = active & ((next_row < next_col) | corner)
        step_col = active & ((next_col < next_row) | corner)
        row[step_row] += int(np.sign(dr))
        col[step_col] += int(np.sign(dc))
        next_row[step_row] += row_delta
        next_col[step_col] += col_delta
        inside = (
            (row >= 0)
            & (row < surface.shape[0])
            & (col >= 0)
            & (col < surface.shape[1])
        )
        active &= inside
        indices = np.flatnonzero(active)
        known = valid[row[indices], col[indices]]
        uncertain[indices[~known]] = True
        blocked = known & (
            surface[row[indices], col[indices]] > base[indices] + entry[indices] * slope
        )
        result[indices[blocked]] = SHADED
        active[indices[blocked]] = False
    return result
