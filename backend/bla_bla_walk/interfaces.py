"""Canonical wire models and server processing contracts.

Coordinates are WGS84 longitude/latitude (GeoJSON), not LV95 processing metres.
Unknown values stay null. Source times are distinct from calculation times.
Feature tasks extend these models with a decision line before regeneration.
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import ArrayLike, NDArray

Longitude = Annotated[float, Field(ge=-180, le=180)]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Position = tuple[Longitude, Latitude]
Availability = Literal["current", "stale", "missing", "unknown", "unsupported"]
LayerKind = Literal["observation", "fountain", "shade", "route"]


class ContractModel(BaseModel):
    """Reject undeclared fields so producers cannot silently drift."""

    model_config = ConfigDict(extra="forbid")


class PointGeometry(ContractModel):
    """A known point location, even when its measured value is missing."""

    type: Literal["Point"]
    coordinates: Position


class LineGeometry(ContractModel):
    """A walking line in display coordinates; does not imply eligibility."""

    type: Literal["LineString"]
    coordinates: Annotated[list[Position], Field(min_length=2)]


class PolygonGeometry(ContractModel):
    """GeoJSON rings for later calculated shade coverage."""

    type: Literal["Polygon"]
    coordinates: list[Annotated[list[Position], Field(min_length=4)]]


class Provenance(ContractModel):
    """Provider, reuse terms and distinct observation/retrieval timestamps."""

    provider: str
    source_url: str | None = None
    attribution: str
    licence: str
    fixture: bool
    observed_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime | None = None


class ShadeMetadata(ContractModel):
    """Calculation context, independent of sensor observations."""

    requested_time: AwareDatetime
    effective_time: AwareDatetime
    geometry_version: str
    resolution_m: Annotated[float, Field(gt=0)]


class ShadeState(IntEnum):
    """Server raster values; night must never count as daytime shaded metres."""

    UNKNOWN = 0
    SUNLIT = 1
    SHADED = 2
    NIGHT = 3


class ShadeCalculator(Protocol):
    """Slot E/F processing boundary; metre grids enter, states and metadata leave.

    Arrays are server processing data, not JSON/browser payloads. Result states
    follow ShadeState. Exact requested time is retained as effective time until
    a later explicitly validated policy introduces temporal approximation.
    """

    def __call__(
        self,
        surface: ArrayLike,
        terrain: ArrayLike,
        *,
        requested_time: datetime,
        geometry_version: str,
        latitude: float,
        longitude: float,
        cell_size_m: float,
        grid_north_rotation_deg: float,
        **ray_options: Any,
    ) -> tuple[NDArray[np.uint8], ShadeMetadata]: ...


class ShadeRequest(ContractModel):
    """LV95 viewport, optionally limited to a walking corridor; exact aware time.

    Bounds are west/south/east/north in metres. Corridor points also use LV95,
    unlike the map's GeoJSON. Responses snap bounds outward to the stored grid.
    """

    bounds: tuple[float, float, float, float]
    requested_time: AwareDatetime
    corridor: (
        Annotated[list[tuple[float, float]], Field(min_length=2, max_length=128)] | None
    ) = None
    corridor_width_m: Annotated[float, Field(gt=0, le=100)] = 10

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_bounds(self):
        west, south, east, north = self.bounds
        if west >= east or south >= north:
            raise ValueError("Bounds must have positive width and height")
        if self.corridor and any(
            not (west <= x <= east and south <= y <= north) for x, y in self.corridor
        ):
            raise ValueError("Corridor points must lie within the requested bounds")
        return self


class ShadeCounts(ContractModel):
    """Disjoint raster cell counts; unknown and night never earn shade credit."""

    unknown: Annotated[int, Field(ge=0)]
    sunlit: Annotated[int, Field(ge=0)]
    shaded: Annotated[int, Field(ge=0)]
    night: Annotated[int, Field(ge=0)]


class ShadeResponse(ContractModel):
    """North-first row-major uint8 raster encoded as base64, with ShadeState codes.

    Unknown includes unsupported receivers and geometry gaps. Night is distinct
    from shaded. Model and availability distinguish the finite building approximation
    from strict survey rays. This is not observed physical-scene evidence.
    The API serves local geometry in both operating modes; no provider calls.
    """

    bounds: tuple[float, float, float, float]
    crs: Literal["EPSG:2056"] = "EPSG:2056"
    width: int
    height: int
    encoding: Literal["base64-uint8-row-major-north-first"] = (
        "base64-uint8-row-major-north-first"
    )
    states: str
    counts: ShadeCounts
    shade: ShadeMetadata
    availability: Literal["approximate", "unknown", "unsupported"]
    model: Literal["survey-raytrace", "building-shadow-approximation"] = (
        "survey-raytrace"
    )
    explanation: str


class RouteMetrics(ContractModel):
    """Basic walking effort; comparison rules and scoring come from T2/T5."""

    distance_m: Annotated[float, Field(ge=0)]
    duration_s: Annotated[float, Field(ge=0)]


class MapFeature(ContractModel):
    """One display feature, with explicit evidence and unknown values."""

    id: str
    label: str
    kind: LayerKind
    geometry: Annotated[
        PointGeometry | LineGeometry | PolygonGeometry, Field(discriminator="type")
    ]
    availability: Availability
    explanation: str
    provenance: Provenance
    value: float | None = None
    unit: str | None = None
    drinking_water: Literal["yes", "no", "unknown"] | None = None
    shade: ShadeMetadata | None = None
    route: RouteMetrics | None = None


class MapLayer(ContractModel):
    """Independently toggleable layer; empty is distinct from a failed layer."""

    id: str
    label: str
    kind: LayerKind
    availability: Availability
    explanation: str
    features: list[MapFeature]


class MapSnapshot(ContractModel):
    """API envelope shared by observations, fountains, shade and route layers."""

    generated_at: AwareDatetime
    layers: list[MapLayer]
    mode: Literal["fixture", "online", "offline"] = "fixture"
