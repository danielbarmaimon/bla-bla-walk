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

from .building_shade import model_grids
from .geometry import sha256_file
from .interfaces import ShadeCalculator, ShadeRequest, ShadeResponse, ShadeState
from .shade import calculate_shade
from .shade_cache import ShadeCache
from .shade_geometry import (
    asset_paths,
    city_cells,
    corridor_cells,
    load_metre_grids,
    load_pair_flags,
    snapped_bounds,
)

ROOT = Path(__file__).resolve().parents[2]


class ShadeService:
    """Exact-time, one-kilometre maximum requests with two bounded workers.

    The user-approved building mode is a finite, flat-ground approximation.
    The strict survey mode still requires independently admitted receivers.
    Both preserve missing/stale source evidence and keep night separate.
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
        if limits["receiver_policy"] not in (
            "unknown-until-compact-scene-validation",
            "building-shadow-approximation",
        ):
            raise ValueError("Compact receiver policy has not been admitted")
        if limits["horizon_ceiling_metres"] is not None:
            raise ValueError("A verified horizon ceiling has not been admitted")
        inventory = self._json("data/tile-inventory.json")
        paths = asset_paths(self.root / "data/geometry", manifest)
        paths.update(
            {
                f"flags-{name}": path
                for name, path in asset_paths(
                    self.root / "data/geometry",
                    {"assets": manifest.get("pair_flags", {})},
                ).items()
            }
        )
        stamps = {}
        for name, path in paths.items():
            stamps[name] = (
                (path.stat().st_size, path.stat().st_mtime_ns)
                if path.is_file()
                else None
            )
        model = None
        if limits["receiver_policy"] == "building-shadow-approximation":
            model = self._json(".cache/buildings/manifest.json")
            if Path(model["file"]).name != model["file"]:
                raise ValueError("Invalid local building geometry path")
            path = self.root / ".cache/buildings" / model["file"]
            stamps["building-footprints"] = (
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
        model_settings = self._json("config/building-shade.json") if model else None
        ray_policy = self._json("config/shade.json")
        if model_settings and (
            model_settings["cell_size_metres"] != cell
            or model_settings["maximum_ray_distance_metres"]
            != ray_policy["maximum_ray_distance_metres"]
            or halo < model_settings["maximum_ray_distance_metres"]
            or not 0 <= model_settings["ground_difference_metres"] <= 2
        ):
            raise ValueError(
                "Building model resolution, reach or ground policy mismatch"
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
            "ray_policy": ray_policy,
            "implementation": self._implementation_version(),
            "building_model": model,
            "building_settings": model_settings,
        }
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        return (
            key,
            manifest,
            inventory["boundary"]["geometry"],
            bounds,
            halo_bounds,
            identity["ray_policy"],
            model,
            identity["building_settings"],
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
            "building_shade.py",
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

    def sample(self, request: ShadeRequest, points):
        """Evaluate sparse building-model receivers without caching a partial raster.

        Ordinary respond/cache results stay complete for their requested corridor.
        This internal route-ranking path preserves the same model and input gaps.
        """
        context = self.context(request)
        if context[6] is None:
            raise ValueError("Sparse walking samples require the building model")
        return self._calculate(request, context, sample_points=points)

    def _calculate(self, request, context, sample_points=None):
        (
            _,
            manifest,
            boundary,
            bounds,
            halo_bounds,
            ray_policy,
            model,
            model_settings,
        ) = context
        cell = manifest["settings"]["cell_size_metres"]
        surface, terrain = load_metre_grids(
            self.root / "data/geometry", manifest, halo_bounds
        )
        flags = load_pair_flags(self.root / "data/geometry", manifest, halo_bounds)
        city = city_cells(boundary, bounds, cell)
        corridor = corridor_cells(request, bounds, cell)
        receivers = np.zeros(surface.shape, dtype=bool)
        west, south, east, north = bounds
        height, width = round((north - south) / cell), round((east - west) / cell)
        row = round((halo_bounds[3] - north) / cell)
        col = round((west - halo_bounds[0]) / cell)
        if model:
            city &= city_cells(model["coverage"], bounds, cell)
            path = self.root / ".cache/buildings" / model["file"]
            if sha256_file(path) != model["sha256"]:
                raise ValueError("Building footprint checksum mismatch")
            buildings = json.loads(path.read_text(encoding="utf-8"))
            surface, terrain, receivers = model_grids(
                surface,
                terrain,
                flags,
                buildings,
                model["coverage"],
                halo_bounds,
                model_settings,
                coverage_constraint=model.get("coverage_constraint"),
            )
            del buildings
            selection = np.zeros(receivers.shape, dtype=bool)
            selection[row : row + height, col : col + width] = city & corridor
            receivers &= selection
            flags = None
        if sample_points is not None:
            selection = np.zeros(receivers.shape, dtype=bool)
            for x, y in sample_points:
                sample_row = int((halo_bounds[3] - y) // cell)
                sample_col = int((x - halo_bounds[0]) // cell)
                if (
                    0 <= sample_row < selection.shape[0]
                    and 0 <= sample_col < selection.shape[1]
                ):
                    selection[sample_row, sample_col] = True
            receivers &= selection
        latitude, longitude, rotation = solar_location(bounds)
        states, metadata = self.calculator(
            surface,
            terrain,
            requested_time=request.requested_time,
            geometry_version=(
                manifest["preparation_version"] + ";buildings=" + model["sha256"]
                if model
                else manifest["preparation_version"]
            ),
            latitude=latitude,
            longitude=longitude,
            cell_size_m=cell,
            grid_north_rotation_deg=rotation,
            receivers=receivers,
            cell_flags=flags,
            finite_model=bool(model),
            minimum_elevation_deg=ray_policy["minimum_elevation_degrees"],
            max_distance_m=ray_policy["maximum_ray_distance_metres"],
        )
        result = states[row : row + height, col : col + width].copy()
        result[~(city & corridor)] = ShadeState.UNKNOWN
        supported_area = bool(np.any(city & corridor))
        approximate = bool(model) and bool(np.any(result != ShadeState.UNKNOWN))
        return ShadeResponse(
            bounds=bounds,
            width=width,
            height=height,
            states=base64.b64encode(result.tobytes()).decode("ascii"),
            counts={
                state.name.lower(): int(np.sum(result == state)) for state in ShadeState
            },
            shade=metadata,
            availability="approximate"
            if approximate
            else "unknown"
            if supported_area
            else "unsupported",
            model="building-shadow-approximation" if model else "survey-raytrace",
            explanation=(
                (
                    "Building-shadow approximation on flat ground, using "
                    "OpenStreetMap footprints "
                    + (
                        f"(source date {model['provider_timestamp']}) "
                        if model.get("provider_timestamp")
                        else "(source date unknown) "
                    )
                    + "and mapped/survey-derived roof heights. "
                    "Sunlit means no modeled building shadow within "
                    f"{model_settings['maximum_ray_distance_metres']}m. "
                    "Tree shade and terrain relief are excluded; missing heights, "
                    "uncertain ground and coverage gaps remain unknown. "
                    + model["attribution"]
                )
                if model and supported_area
                else "Compact real-scene receiver validation is unfinished; "
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
