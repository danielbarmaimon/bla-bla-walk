"""Canonical wire models and server processing contracts.

Coordinates are WGS84 longitude/latitude (GeoJSON), not LV95 processing metres.
Unknown values stay null. Source times are distinct from calculation times.
Feature tasks extend these models with a decision line before regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class CompactReceiverEvidence:
    """Server evidence recorded before quantization; never a browser payload.

    Flags use native T8 bits 1/2/4, aggregated conservatively across each compact
    cell. ground_candidates requires all source samples within the explicitly
    supplied numerical ground-envelope tolerance; it does not prove walkability.
    surface_elevations retains unrounded source maxima in absolute metres.
    Slot F must intersect candidates with verified receiver support and retain
    source checksums, grid alignment and evidence version in preparation/cache keys.
    """

    cell_flags: NDArray[np.uint8]
    ground_candidates: NDArray[np.bool_]
    surface_elevations: NDArray[np.float32]
    maximum_surface_gap_m: float


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


class PetRouteMetrics(ContractModel):
    """Route length sampled by the provider's fixed historical PET classes."""

    availability: Availability
    scenario: str
    resolution_m: Annotated[float, Field(gt=0)]
    known_distance_m: Annotated[float, Field(ge=0)]
    unknown_distance_m: Annotated[float, Field(ge=0)]
    class_distances_m: dict[str, Annotated[float, Field(ge=0)]]
    provenance: Provenance


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
    pet: PetRouteMetrics | None = None


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


class WaterEvidence(ContractModel):
    """Verified network diversion and physical evidence, never point proximity."""

    state: str = "unknown"
    evidence_complete: bool = False
    age_hours: float | None = None
    drinking: bool | None = None
    accessible: bool | None = None
    operational: bool | None = None
    extra_distance_metres: float | None = None
    extra_distance_included: bool = False
    provenance: Provenance | None = None


class WalkingEvidence(ContractModel):
    """Cached T5 route distances; invalid metrics remain displayable with reasons.

    Sampling approximation, requested/effective times and model limits live in
    samples. Unknown includes night for scoring, with night separately recorded.
    Flags must come from evidence, never from the mere existence of a polyline.
    """

    id: str
    distance_metres: float
    shaded_metres: float
    unshaded_metres: float
    unknown_metres: float
    planned_stop_minutes: float = 0
    access_state: Literal["checked_open", "confirmed_blocked", "unknown"] = "unknown"
    inside_calculation_coverage: bool = False
    construction_caution: bool = False
    shade_state: Literal["current", "stale", "failed", "unknown"] = "unknown"
    shade_time_matches_request: bool = False
    shade_geometry_matches_request: bool = False
    duration_complete: bool = True
    water: WaterEvidence = Field(default_factory=WaterEvidence)
    provenance: Provenance | None = None
    samples: list[WalkingShadeSample] = Field(default_factory=list)
    sampled_speed_m_per_s: float | None = None
    sampled_distance_metres: float | None = None
    sampled_stop_minutes: float | None = None


class WalkingShadeSample(ContractModel):
    """Midpoint quadrature interval in route metres, sampled at traversal time.

    This estimates distance, not exact cell intersection or observed shade.
    A stop at an interval boundary affects all subsequent sample times.
    """

    start_metres: float
    end_metres: float
    requested_time: AwareDatetime
    metadata: ShadeMetadata | None = None
    state: ShadeState = ShadeState.UNKNOWN
    model: str = "unavailable"
    explanation: str


class WalkingStop(ContractModel):
    """Planned pause at a route distance; diversions already belong in geometry."""

    at_metres: Annotated[float, Field(ge=0)]
    minutes: Annotated[float, Field(ge=0)]
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class TripComparison(ContractModel):
    """Pure rescoring result for T6; manual choice only among eligible IDs.

    Metrics retain full-route denominators. Scores can be incomplete lower
    bounds; status and explanation determine whether a winner is available.
    Transit stays unavailable until T18/T19 admission and approval.
    """

    status: str
    winner: str | None = None
    route_statuses: dict[str, str]
    metrics: dict[str, dict[str, Any]] = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)
    contributions: dict[str, dict[str, float]] = Field(default_factory=dict)
    reasons: dict[str, list[str]] = Field(default_factory=dict)
    manual_choices: list[str] = Field(default_factory=list)
    explanation: str = ""
    transit_status: Literal["unavailable"] = "unavailable"


class WalkingRouteRequest(ContractModel):
    """Ephemeral Basel coordinates for provider pedestrian-network geometry."""

    start: Position
    end: Position
    mode: Literal["fixture", "online", "offline"] = "online"


class AddressSearchRequest(ContractModel):
    """Ephemeral address query; offline requests never contact a provider."""

    query: str = Field(min_length=3, max_length=120)
    mode: Literal["fixture", "online", "offline"] = "online"


class AddressPlace(ContractModel):
    """Plain-text official building address within the pinned Basel boundary."""

    id: str
    name: str
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


class AddressSearchResponse(ContractModel):
    """Provider search results confer no route or pedestrian-access validation."""

    places: list[AddressPlace] = Field(default_factory=list)
    status: Literal["available", "unavailable"] = "available"
    attribution: str = "© swisstopo — official building address directory"


class ComparisonPreferences(ContractModel):
    """Rescore complete cached evidence; preferences never change sample times."""

    weights: dict[str, Annotated[float, Field(ge=0, le=1)]] | None = None
    extra_time_limit_minutes: Literal[5] | None = None

    @model_validator(mode="after")
    def criteria(self):
        if self.weights is not None and set(self.weights) != {
            "shade",
            "duration",
            "water",
        }:
            raise ValueError("Supply shade, duration and water weights")
        return self


class ComparisonRequest(ContractModel):
    """Exact departure for the server-owned checked pair; no access overrides."""

    departure_time: AwareDatetime
    stops: dict[str, Annotated[list[WalkingStop], Field(max_length=16)]] = Field(
        default_factory=dict
    )


class ComparisonJob(ContractModel):
    """Bounded background calculation. Ready evidence can be rescored locally.

    Cache identity pins routes, complete stops, speed, policy and input versions.
    Source changes invalidate a job; only ready results can guide selection.
    """

    id: str
    status: Literal["running", "ready", "failed"]
    departure_time: AwareDatetime
    completed_samples: int = 0
    total_samples: int = 0
    evidence: list[WalkingEvidence] = Field(default_factory=list)
    choices: dict[str, TripComparison] = Field(default_factory=dict)
    explanation: str
