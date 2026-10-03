"""Building-only model boundaries and explicit finite-ray semantics."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from bla_bla_walk.building_shade import model_grids
from bla_bla_walk.shade import NIGHT, SHADED, SUNLIT, UNKNOWN, shadow_mask


def polygon(west, south, east, north):
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


def grids(features, **updates):
    surface = np.zeros((20, 20), dtype="float32")
    surface[10, 10] = 6  # surveyed roof
    surface[10, 15] = 12  # a tree outside footprints, never a building caster
    flags = np.ones(surface.shape, dtype="uint8")
    flags[9, 9] = 7
    settings = {"cell_size_metres": 1, "ground_difference_metres": 2}
    arguments = dict(
        surface=surface,
        terrain=np.zeros_like(surface),
        flags=flags,
        buildings=features,
        coverage=polygon(0, 0, 20, 20),
        bounds=(0, 0, 20, 20),
        settings=settings,
    )
    arguments.update(updates)
    return model_grids(**arguments)


def test_footprints_separate_roofs_trees_and_plausible_ground():
    roof, ground, receivers = grids([{"geometry": polygon(10, 9, 11, 10)}])
    assert roof[10, 10] == 6
    assert roof[10, 15] == 0
    assert not receivers[10, 10] and not receivers[10, 15]
    assert not receivers[9, 9]
    assert receivers[12, 12] and np.all(ground == 0)


def test_missing_roof_height_and_unresolved_extent_are_unknown():
    roof, _, receivers = grids(
        [
            {"geometry": polygon(5, 5, 6, 6)},
            {
                "geometry": polygon(10, 9, 11, 10),
                "height_m": 15,
                "unresolved_geometry": True,
            },
        ]
    )
    assert np.isnan(roof[14, 5]) and np.isnan(roof[10, 10])
    assert not receivers[14, 5]


def test_explicit_height_overrides_survey_and_coverage_stays_unknown():
    feature = {"geometry": polygon(10, 9, 11, 10), "height_m": 25}
    roof, _, _ = grids([feature])
    assert roof[10, 10] == 25
    roof, _, receivers = grids([feature], coverage=polygon(0, 0, 8, 20))
    assert np.isnan(roof[10, 10]) and not receivers[10, 10]


def test_two_metre_ground_proxy_rejects_negative_and_higher_differences():
    values = np.zeros((20, 20), dtype="float32")
    values[10, 5:9] = [-1, 0, 2, 3]
    _, _, receivers = grids([], surface=values)
    assert list(receivers[10, 5:9]) == [False, True, True, False]


def finite(surface, **options):
    arguments = dict(
        elevation_deg=45,
        azimuth_deg=90,
        cell_size_m=1,
        max_distance_m=10,
        minimum_elevation_deg=10,
        finite_model=True,
    )
    arguments.update(options)
    return shadow_mask(surface, np.zeros_like(surface), **arguments)


def test_finite_model_declares_clear_reach_without_changing_strict_mode():
    surface = np.zeros((40, 40))
    assert finite(surface)[20, 20] == SUNLIT
    assert finite(surface, finite_model=False)[20, 20] == UNKNOWN
    assert finite(surface)[20, 39] == UNKNOWN  # grid ends before declared reach


@pytest.mark.parametrize(
    "azimuth, receiver",
    [(90, (20, 16)), (270, (20, 24)), (0, (24, 20)), (180, (16, 20))],
)
def test_five_metre_building_shadow_matches_analytic_direction(azimuth, receiver):
    surface = np.zeros((50, 50))
    surface[20, 20] = 5
    assert finite(surface, azimuth_deg=azimuth)[receiver] == SHADED
    assert finite(surface)[20, 13] == SUNLIT


def test_missing_ray_cell_cannot_become_clear_but_known_blocker_proves_shade():
    surface = np.zeros((40, 40))
    surface[20, 22] = np.nan
    assert finite(surface)[20, 20] == UNKNOWN
    surface[20, 24] = 8
    assert finite(surface)[20, 20] == SHADED
    assert finite(surface, elevation_deg=-1)[20, 20] == NIGHT
    assert finite(surface, elevation_deg=5)[20, 20] == UNKNOWN


spec = importlib.util.spec_from_file_location(
    "building_preparation",
    Path(__file__).resolve().parents[2] / "scripts/prepare_building_shade.py",
)
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("14 m", 14),
        ("6.5", 6.5),
        ("3 storeys", None),
        ("15 ft", None),
        ("0", None),
        ("-2", None),
        ("1001", None),
        (None, None),
    ],
)
def test_only_explicit_positive_metre_heights(value, expected):
    assert preparation.height_metres(value) == expected


def test_relation_segments_join_in_reverse_and_incomplete_rings_fail_closed():
    segments = [[(0, 0), (1, 0), (1, 1)], [(0, 0), (0, 1), (1, 1)]]
    rings = preparation.join_rings(segments)
    assert len(rings) == 1 and rings[0][0] == rings[0][-1]
    assert preparation.join_rings([segments[0]]) is None


def test_relation_hole_and_unresolved_extent():
    def member(role, coords):
        return {"role": role, "geometry": [{"lon": x, "lat": y} for x, y in coords]}

    outer = [(7.59, 47.55), (7.60, 47.55), (7.60, 47.56), (7.59, 47.56), (7.59, 47.55)]
    inner = [
        (7.592, 47.552),
        (7.598, 47.552),
        (7.598, 47.558),
        (7.592, 47.558),
        (7.592, 47.552),
    ]
    geometry, unresolved = preparation.footprint(
        {
            "type": "relation",
            "members": [member("outer", outer), member("inner", inner)],
        }
    )
    assert not unresolved and len(geometry["coordinates"][0]) == 2
    geometry, unresolved = preparation.footprint(
        {"type": "relation", "members": [member("outer", outer[:-1])]}
    )
    assert unresolved and geometry is not None


def test_sanitization_keeps_only_caster_fields_and_missing_geometry_aborts():
    element = {
        "type": "way",
        "id": 42,
        "tags": {
            "building": "yes",
            "height": "12m",
            "name": "Example",
            "addr:street": "Example",
            "building:levels": "4",
        },
        "geometry": [
            {"lon": x, "lat": y}
            for x, y in [
                (7.59, 47.55),
                (7.60, 47.55),
                (7.60, 47.56),
                (7.59, 47.56),
                (7.59, 47.55),
            ]
        ],
    }
    saved = preparation.sanitized_features([element])[0]
    assert set(saved) == {"id", "geometry", "height_m", "unresolved_geometry"}
    assert saved["height_m"] == 12
    with pytest.raises(ValueError, match="Unlocatable"):
        preparation.sanitized_features([dict(element, geometry=[])])


def test_overlapping_explicit_parts_keep_highest_roof_regardless_of_order():
    geometry = polygon(10, 9, 11, 10)
    roof, _, _ = grids(
        [{"geometry": geometry, "height_m": 25}, {"geometry": geometry, "height_m": 10}]
    )
    assert roof[10, 10] == 25
