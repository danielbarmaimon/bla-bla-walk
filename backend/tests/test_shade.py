"""Independent geometric checks for Slot E; city/API acceptance belongs to T10."""

import math
from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from bla_bla_walk.geometry import compact_heights, geometry_settings
from bla_bla_walk.shade import (
    NIGHT,
    SHADED,
    SUNLIT,
    UNKNOWN,
    calculate_shade,
    shadow_mask,
)
from bla_bla_walk.solar import solar_position


def mask(surface, terrain=None, **options):
    if terrain is None:
        terrain = np.zeros_like(surface)
    arguments = dict(
        elevation_deg=45,
        azimuth_deg=90,
        cell_size_m=1,
        max_distance_m=100,
        minimum_elevation_deg=10,
        horizon_ceiling_m=10,
    )
    arguments.update(options)
    return shadow_mask(surface, terrain, **arguments)


def test_solar_bearing_against_published_nrel_spa_geometric_example():
    # NREL/TP-560-34302 appendix A.5: azimuth 194.34024°, apparent zenith
    # 50.11162°. Removing its 820mbar/11°C refraction gives ~39.87205°.
    elevation, azimuth = solar_position(
        datetime.fromisoformat("2003-10-17T12:30:30-07:00"),
        39.742476,
        -105.1786,
    )
    assert elevation == pytest.approx(39.872046, abs=0.01)
    assert azimuth == pytest.approx(194.340241, abs=0.01)


def test_solar_timezones_same_instant_and_basel_day_night():
    utc = datetime(2026, 6, 21, 12, tzinfo=UTC)
    assert solar_position(utc, 47.56, 7.59) == solar_position(
        utc.astimezone(timezone(timedelta(hours=2))),
        47.56,
        7.59,
    )
    assert solar_position(utc, 47.56, 7.59)[0] > 60
    assert solar_position(utc.replace(hour=0), 47.56, 7.59)[0] < 0
    morning = solar_position(utc.replace(hour=6), 47.56, 7.59)
    afternoon = solar_position(utc.replace(hour=16), 47.56, 7.59)
    assert morning[1] < 180 < afternoon[1]


@pytest.mark.parametrize(
    "moment, latitude, longitude",
    [
        (datetime(2026, 1, 1), 47, 7),
        (datetime(2026, 1, 1, tzinfo=UTC), float("nan"), 7),
        (datetime(2026, 1, 1, tzinfo=UTC), 47, 181),
        (datetime(1700, 1, 1, tzinfo=UTC), 47, 7),
    ],
)
def test_solar_rejects_invalid_context(moment, latitude, longitude):
    with pytest.raises(ValueError):
        solar_position(moment, latitude, longitude)


@pytest.mark.parametrize(
    "azimuth, shaded, sunlit",
    [
        (90, (15, 12), (15, 22)),
        (270, (15, 18), (15, 12)),
        (0, (18, 15), (12, 15)),
        (180, (12, 15), (22, 15)),
    ],
)
def test_known_five_metre_prism_direction_and_length(azimuth, shaded, sunlit):
    surface = np.zeros((40, 40))
    surface[15, 15] = 5
    states = mask(surface, azimuth_deg=azimuth)
    assert states[shaded] == SHADED
    assert states[sunlit] == SUNLIT
    assert states[15, 15] == UNKNOWN  # a rooftop/canopy is not a known walkway
    if azimuth == 90:
        assert list(states[15, 9:15]) == [
            SUNLIT,
            SHADED,
            SHADED,
            SHADED,
            SHADED,
            SHADED,
        ]


def test_lower_sun_lengthens_shadow_and_limits_remain_explicit():
    surface = np.zeros((40, 40))
    surface[20, 20] = 5
    assert mask(surface, elevation_deg=45)[20, 12] == SUNLIT
    assert mask(surface, elevation_deg=30)[20, 12] == SHADED
    assert mask(surface, elevation_deg=5)[20, 12] == UNKNOWN
    assert mask(surface, elevation_deg=-1)[20, 12] == NIGHT
    assert mask(surface, elevation_deg=-1)[20, 20] == UNKNOWN


def test_exact_zenith_requires_no_distant_horizon():
    surface = np.zeros((3, 3))
    surface[1, 1] = 5
    states = mask(surface, elevation_deg=90, horizon_ceiling_m=None)
    assert states[0, 0] == SUNLIT
    assert states[1, 1] == UNKNOWN


def test_edge_halo_cap_and_unverified_horizon_do_not_claim_sunlit():
    surface = np.zeros((20, 20))
    assert mask(surface)[10, 19] == UNKNOWN
    assert mask(surface, max_distance_m=2)[10, 10] == UNKNOWN
    assert mask(surface, horizon_ceiling_m=None)[10, 10] == UNKNOWN
    assert mask(surface)[10, 9] == SUNLIT
    with pytest.raises(ValueError, match="ceiling"):
        mask(surface + 11, terrain=surface + 11)


def test_missing_and_scene_flagged_ray_but_known_blocker_still_proves_shade():
    surface = np.zeros((30, 30))
    surface[15, 17] = np.nan
    assert mask(surface)[15, 15] == UNKNOWN
    surface[15, 19] = 8
    assert mask(surface)[15, 15] == SHADED
    assert mask(surface)[15, 17] == UNKNOWN
    flags = np.ones_like(surface, dtype="uint8")
    surface[15, 17] = 0
    surface[15, 19] = 0
    for flag in (0, 3, 5, 7):
        flags[15, 17] = flag
        assert mask(surface, cell_flags=flags)[15, 15] == UNKNOWN
        assert mask(surface, cell_flags=flags)[15, 17] == UNKNOWN


def test_terrain_relief_and_surface_below_terrain_are_not_clamped():
    surface = np.zeros((30, 30))
    terrain = np.zeros_like(surface)
    surface[15, 18] = terrain[15, 18] = 7
    assert mask(surface, terrain)[15, 15] == SHADED
    surface[15, 18] = 0  # unresolved bridge/survey mismatch
    assert mask(surface, terrain)[15, 15] == UNKNOWN
    assert mask(surface, terrain)[15, 18] == UNKNOWN


def test_masked_nodata_and_corridor_selection_preserve_unknown():
    surface = np.ma.zeros((30, 30))
    surface[15, 17] = np.ma.masked
    receivers = np.zeros(surface.shape, dtype=bool)
    receivers[15, 15] = True
    states = mask(surface, receivers=receivers)
    assert np.all(states == UNKNOWN)
    surface[15, 17] = 0
    states = mask(surface, receivers=receivers)
    assert states[15, 15] == SUNLIT
    assert np.count_nonzero(states != UNKNOWN) == 1


def test_requested_time_version_resolution_and_projection_rotation():
    moment = datetime(2026, 6, 21, 12, tzinfo=UTC)
    surface = np.zeros((30, 30))
    surface[15, 15] = 6
    elevation, azimuth = solar_position(moment, 47.56, 7.59)
    states, metadata = calculate_shade(
        surface,
        surface * 0,
        requested_time=moment,
        geometry_version="fixture-v1",
        latitude=47.56,
        longitude=7.59,
        cell_size_m=1,
        grid_north_rotation_deg=azimuth - 90,
        horizon_ceiling_m=10,
    )
    assert np.array_equal(states, mask(surface, elevation_deg=elevation))
    assert metadata.requested_time == metadata.effective_time == moment
    assert metadata.geometry_version == "fixture-v1"
    assert metadata.resolution_m == 1


def test_height_quantization_changes_shadow_and_route_sample_length():
    # A 5m surveyed object becomes 6m under the configured 2m height steps.
    # This is a sensitivity finding, not acceptance of compact shade accuracy.
    native = np.zeros((80, 80))
    native[30:34, 40:42] = 5
    terrain = np.zeros_like(native)
    native_states = mask(native, terrain, cell_size_m=0.5)
    settings = geometry_settings()
    compact = (
        compact_heights(native, "surface", 0.5, settings)
        * settings["height_step_metres"]
    )
    compact_terrain = (
        compact_heights(terrain, "surface", 0.5, settings)
        * settings["height_step_metres"]
    )
    compact_states = mask(compact, compact_terrain)
    assert np.count_nonzero(native_states[32] == SHADED) * 0.5 == 5
    assert np.count_nonzero(compact_states[16] == SHADED) == 6


def _slab_entry(origin, direction, lower, upper):
    """Independent ray/rectangle intersection, not grid-boundary stepping."""
    if abs(direction) < 1e-12:
        return (
            (-math.inf, math.inf) if lower < origin < upper else (math.inf, -math.inf)
        )
    first, second = (lower - origin) / direction, (upper - origin) / direction
    return min(first, second), max(first, second)


def independent_reference(
    surface,
    row,
    col,
    azimuth,
    elevation,
    ceiling,
    *,
    cell=1,
    receiver_height=0,
    terrain=None,
    flags=None,
    extent=100,
):
    """Intersect each grid prism individually and check horizon exit coverage."""
    dr, dc = -math.cos(math.radians(azimuth)), math.sin(math.radians(azimuth))
    slope = math.tan(math.radians(elevation))
    distance = (
        min(extent, max(0, ceiling - receiver_height) / slope)
        if ceiling is not None
        else extent
    )
    known = np.isfinite(surface)
    if terrain is not None:
        known &= np.isfinite(terrain) & (surface >= terrain)
    if flags is not None:
        known &= ((flags & 1) != 0) & ((flags & 6) == 0)
    unknown = False
    for r, c in np.ndindex(surface.shape):
        r_enter, r_exit = _slab_entry((row + 0.5) * cell, dr, r * cell, (r + 1) * cell)
        c_enter, c_exit = _slab_entry((col + 0.5) * cell, dc, c * cell, (c + 1) * cell)
        enter, leave = max(0, r_enter, c_enter), min(distance, r_exit, c_exit)
        if leave - enter <= 1e-9:
            continue
        if not known[r, c]:
            unknown = True
        elif surface[r, c] > receiver_height + enter * slope:
            return SHADED
    _, row_exit = _slab_entry((row + 0.5) * cell, dr, 0, surface.shape[0] * cell)
    _, col_exit = _slab_entry((col + 0.5) * cell, dc, 0, surface.shape[1] * cell)
    return (
        UNKNOWN
        if (
            unknown
            or ceiling is None
            or distance > min(row_exit, col_exit)
            or (ceiling - receiver_height) / slope > extent
        )
        else SUNLIT
    )


@pytest.mark.parametrize("azimuth", [13, 45, 130, 220, 314])
def test_diagonal_rays_match_independent_prism_intersections(azimuth):
    surface = np.zeros((12, 12))
    surface[4, 5], surface[7, 3], surface[8, 8] = 3, 5, np.nan
    states = mask(surface, elevation_deg=35, azimuth_deg=azimuth, horizon_ceiling_m=5)
    for row, column in np.argwhere(surface == 0):
        assert states[row, column] == independent_reference(
            surface, row, column, azimuth, 35, 5
        )


def test_receiver_batches_and_overlapping_halos_have_no_seam_change():
    surface = np.zeros((40, 40))
    surface[15:20, 20] = 6
    whole = mask(surface, azimuth_deg=90)
    # Both requests include sufficient geometry toward the sun for these cells.
    crop = mask(surface[10:30, 10:35], azimuth_deg=90)
    assert np.array_equal(whole[12:28, 12:22], crop[2:18, 2:12])
    import bla_bla_walk.shade as calculator

    original = calculator.RAY_BATCH_SIZE
    try:
        calculator.RAY_BATCH_SIZE = 3
        assert np.array_equal(whole, mask(surface, azimuth_deg=90))
    finally:
        calculator.RAY_BATCH_SIZE = original


def test_verified_ground_elevations_and_canopy_interior_policy():
    surface = np.full((30, 30), 0.01)
    surface[15, 20] = 5
    terrain = np.zeros_like(surface)
    receivers = np.zeros(surface.shape, dtype=bool)
    receivers[15, 17] = True
    assert mask(surface, terrain)[15, 17] == UNKNOWN
    elevated_ground = surface.copy()
    elevated_ground[15, 17] = 3
    assert (
        mask(
            surface, terrain, receivers=receivers, receiver_elevations=elevated_ground
        )[15, 17]
        == SUNLIT
    )
    elevated_ground[15, 17] = 0.01
    assert (
        mask(
            surface, terrain, receivers=receivers, receiver_elevations=elevated_ground
        )[15, 17]
        == SHADED
    )
    elevated_ground[15, 17] = 0  # under the surveyed upper envelope
    assert (
        mask(
            surface, terrain, receivers=receivers, receiver_elevations=elevated_ground
        )[15, 17]
        == UNKNOWN
    )


def test_audited_bridge_reference_keeps_t8_scene_flag_unknown():
    import json
    from pathlib import Path

    metadata = json.loads(
        (Path(__file__).parents[2] / "data/fixtures/geometry-metadata.json").read_text()
    )
    bridge = metadata["alignment_reference_points"]["mittlere_bruecke"]
    surface = np.full((3, 3), bridge["surface_metres"])
    terrain = np.full((3, 3), bridge["terrain_metres"])
    flags = np.full((3, 3), bridge["pair_flag"], dtype="uint8")
    assert bridge["pair_flag"] & 2
    assert np.all(
        mask(surface, terrain, cell_flags=flags, horizon_ceiling_m=300) == UNKNOWN
    )


@pytest.mark.parametrize(
    "options",
    [
        {"cell_size_m": 0},
        {"max_distance_m": -1},
        {"azimuth_deg": float("nan")},
        {"minimum_elevation_deg": 0},
        {"elevation_deg": 91},
        {"receivers": np.ones((2, 2), dtype=bool)},
        {"cell_flags": np.ones((30, 30))},
    ],
)
def test_rejects_invalid_grid_and_ray_options(options):
    with pytest.raises(ValueError):
        mask(np.zeros((30, 30)), **options)
