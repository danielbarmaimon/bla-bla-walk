"""Bounded local shade API orchestration; compact acceptance stays explicit."""

import base64
import hashlib
import json
import math
from datetime import UTC
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform

from .interfaces import ShadeCalculator, ShadeRequest, ShadeResponse, ShadeState
from .shade import calculate_shade
from .shade_cache import ShadeCache
from .shade_geometry import (
    asset_paths,
    city_cells,
    corridor_cells,
    load_metre_grids,
    snapped_bounds,
)

ROOT = Path(__file__).resolve().parents[2]


class ShadeService:
    """Exact-time, one-kilometre maximum requests with two bounded workers.

    Compact receiver support has not passed E's real-scene acceptance. Thus the
    production compact path deliberately supplies no verified receivers and
    returns unknown, even where quantized surface and terrain happen to match.
    This is an integration checkpoint, not accepted city-wide walking shade.
    """

    def __init__(self, root=ROOT):
        self.root = Path(root)
        limits = self._json("config/shade-service.json")
        self.cache = ShadeCache(limits["cache_bytes"], limits["workers"])
        self.calculator: ShadeCalculator = calculate_shade

    def _json(self, path):
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def context(self, request):
        """Pin geometry, implementation, policy, bounds, support and exact time."""
        limits = self._json("config/shade-service.json")
        manifest = self._json("data/geometry/manifest.json")
        cell = manifest["settings"]["cell_size_metres"]
        if cell != 1 or manifest["settings"]["height_step_metres"] != 2:
            raise ValueError("Shade API requires the configured 1m/2m compact geometry")
        bounds = snapped_bounds(request.bounds, cell)
        west, south, east, north = bounds
        if max(east - west, north - south) > limits["maximum_viewport_side_metres"]:
            raise OverflowError("Request at most a 1000m by 1000m viewport per call")
        halo = limits["halo_metres"]
        halo_bounds = (west - halo, south - halo, east + halo, north + halo)
        cells = (east - west + 2 * halo) * (north - south + 2 * halo) / cell**2
        if cells > limits["maximum_grid_cells"]:
            raise OverflowError("Shade geometry exceeds the bounded worker grid")
        if limits["receiver_policy"] != "unknown-until-compact-scene-validation":
            raise ValueError("Compact receiver policy has not been admitted")
        if limits["horizon_ceiling_metres"] is not None:
            raise ValueError("A verified horizon ceiling has not been admitted")
        inventory = self._json("data/tile-inventory.json")
        paths = asset_paths(self.root / "data/geometry", manifest)
        stamps = {}
        for name, path in paths.items():
            stamps[name] = (
                (path.stat().st_size, path.stat().st_mtime_ns)
                if path.is_file()
                else None
            )
        identity = {
            "request": request.model_copy(
                update={"requested_time": request.requested_time.astimezone(UTC)}
            ).model_dump(mode="json"),
            "bounds": bounds,
            "manifest": manifest,
            "boundary": inventory["boundary"],
            "file_stamps": stamps,
            "limits": limits,
            "ray_policy": self._json("config/shade.json"),
            "implementation": self._implementation_version(),
        }
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        return (
            key,
            manifest,
            inventory["boundary"]["geometry"],
            bounds,
            halo_bounds,
            identity["ray_policy"],
        )

    @staticmethod
    def _implementation_version():
        digest = hashlib.sha256()
        for name in (
            "shade.py",
            "solar.py",
            "shade_geometry.py",
            "shade_service.py",
            "geometry.py",
            "interfaces.py",
        ):
            digest.update(Path(__file__).with_name(name).read_bytes())
        return digest.hexdigest()

    def respond(self, request: ShadeRequest):
        """Return a canonical response and cache status; no external calls."""
        context = self.context(request)
        value, hit = self.cache.get_or_compute(
            context[0],
            lambda: self._calculate(request, context).model_dump_json().encode(),
        )
        response = ShadeResponse.model_validate_json(value)
        # Same-instant timezone representations may share the same cache entry.
        response.shade.requested_time = request.requested_time
        return response, hit

    def _calculate(self, request, context):
        _, manifest, boundary, bounds, halo_bounds, ray_policy = context
        cell = manifest["settings"]["cell_size_metres"]
        surface, terrain = load_metre_grids(
            self.root / "data/geometry", manifest, halo_bounds
        )
        city = city_cells(boundary, bounds, cell)
        corridor = corridor_cells(request, bounds, cell)
        # Quantized equality alone cannot verify a ground receiver. Do not turn
        # erased survey disagreement or an unresolved canopy into walking shade.
        receivers = np.zeros(surface.shape, dtype=bool)
        latitude, longitude, rotation = solar_location(bounds)
        states, metadata = self.calculator(
            surface,
            terrain,
            requested_time=request.requested_time,
            geometry_version=manifest["preparation_version"],
            latitude=latitude,
            longitude=longitude,
            cell_size_m=cell,
            grid_north_rotation_deg=rotation,
            receivers=receivers,
            minimum_elevation_deg=ray_policy["minimum_elevation_degrees"],
            max_distance_m=ray_policy["maximum_ray_distance_metres"],
        )
        west, south, east, north = bounds
        height, width = round((north - south) / cell), round((east - west) / cell)
        row = round((halo_bounds[3] - north) / cell)
        col = round((west - halo_bounds[0]) / cell)
        result = states[row : row + height, col : col + width].copy()
        result[~(city & corridor)] = ShadeState.UNKNOWN
        supported_area = bool(np.any(city & corridor))
        return ShadeResponse(
            bounds=bounds,
            width=width,
            height=height,
            states=base64.b64encode(result.tobytes()).decode("ascii"),
            counts={
                state.name.lower(): int(np.sum(result == state)) for state in ShadeState
            },
            shade=metadata,
            availability="unknown" if supported_area else "unsupported",
            explanation=(
                "Compact real-scene receiver validation is unfinished; "
                "all cells remain unknown. Missing buffers, bridge/canopy "
                "receivers and the unverified "
                "horizon ceiling cannot establish sunlit walking coverage."
                if supported_area
                else "Requested cells are outside the admitted city/corridor coverage."
            ),
        )


def solar_location(bounds):
    """Resolve centre WGS84 and LV95 grid-north rotation using local PROJ data."""
    west, south, east, north = bounds
    centre_x, centre_y = (west + east) / 2, (south + north) / 2
    with rasterio.Env(PROJ_NETWORK="OFF"):
        longitudes, latitudes = transform(2056, 4326, [centre_x], [centre_y])
        longitude, latitude = longitudes[0], latitudes[0]
        x, y = transform(
            4326, 2056, [longitude, longitude], [latitude, latitude + 0.0001]
        )
    rotation = -math.degrees(math.atan2(x[1] - x[0], y[1] - y[0]))
    return latitude, longitude, rotation
