"""Pre-encoding evidence survives compact rounding and provenance checks."""

import numpy as np
import pytest
from bla_bla_walk.compact_evidence import (
    compact_receiver_evidence,
    read_receiver_evidence,
    write_receiver_evidence,
)
from bla_bla_walk.interfaces import CompactReceiverEvidence
from bla_bla_walk.shade import SHADED, UNKNOWN, shadow_mask
from test_shade import independent_reference


def test_missing_mismatch_and_canopy_are_not_hidden_by_aggregation():
    surface = np.full((4, 8), 1.1, dtype="float32")
    terrain = surface.copy()
    surface[0, 2] = 1.09  # Both would round to the same 2m code.
    surface[0, 4] = np.nan
    surface[0, 6] = 1.5  # A single canopy sample forbids ground inference.
    evidence = compact_receiver_evidence(surface, terrain, maximum_surface_gap_m=0.1)
    assert isinstance(evidence, CompactReceiverEvidence)
    assert evidence.cell_flags[0].tolist() == [1, 3, 0, 1]
    assert evidence.ground_candidates[0].tolist() == [True, False, False, False]
    assert evidence.surface_elevations[0, 0] == pytest.approx(1.1)
    assert np.isnan(evidence.surface_elevations[0, 2])


def test_receiver_evidence_round_trip_requires_matching_provenance(tmp_path):
    evidence = compact_receiver_evidence(
        np.ones((4, 4)), np.ones((4, 4)), maximum_surface_gap_m=0.1
    )
    target = tmp_path / "evidence.npz"
    context = dict(source_sha256=["a" * 64, "b" * 64], bounds=[0, 0, 2, 2])
    write_receiver_evidence(evidence, target, **context)
    restored = read_receiver_evidence(target, maximum_surface_gap_m=0.1, **context)
    assert np.array_equal(restored.cell_flags, evidence.cell_flags)
    for replacement in [
        dict(source_sha256=["c" * 64, "b" * 64]),
        dict(bounds=[1, 0, 3, 2]),
        dict(maximum_surface_gap_m=0.2),
    ]:
        arguments = dict(context, maximum_surface_gap_m=0.1)
        arguments.update(replacement)
        with pytest.raises(ValueError, match="mismatch"):
            read_receiver_evidence(target, **arguments)


def test_unrounded_supported_ground_is_not_buried_in_rounded_own_cell():
    surface = np.full((30, 30), 2, dtype="float32")
    terrain = surface.copy()
    surface[15, 20] = 8
    receiver = np.full_like(surface, 1.1)
    flags = np.ones(surface.shape, dtype="uint8")
    selected = np.zeros(surface.shape, dtype=bool)
    selected[15, 17] = True
    options = dict(
        elevation_deg=45,
        azimuth_deg=90,
        cell_size_m=1,
        max_distance_m=100,
        minimum_elevation_deg=10,
        receivers=selected,
        receiver_elevations=receiver,
        cell_flags=flags,
    )
    assert shadow_mask(surface, terrain, **options)[15, 17] == UNKNOWN
    states = shadow_mask(
        surface, terrain, receiver_surface_elevations=receiver, **options
    )
    assert states[15, 17] == SHADED
    # Independently represent the receiver's known unrounded own column.
    reference = surface.copy()
    reference[15, 17] = receiver[15, 17]
    assert states[15, 17] == independent_reference(
        reference, 15, 17, 90, 45, None, receiver_height=1.1, extent=100
    )
    lower_ground = np.zeros_like(receiver)
    assert np.all(
        shadow_mask(
            surface,
            terrain,
            receiver_surface_elevations=receiver,
            **dict(options, receiver_elevations=lower_ground),
        )
        == UNKNOWN
    )
    flags[15, 17] = 3
    assert np.all(
        shadow_mask(surface, terrain, receiver_surface_elevations=receiver, **options)
        == UNKNOWN
    )
    with pytest.raises(ValueError, match="flags"):
        shadow_mask(
            surface,
            terrain,
            receiver_surface_elevations=receiver,
            **dict(options, cell_flags=None),
        )


@pytest.mark.parametrize(
    "surface,terrain,gap",
    [
        (np.ones((3, 4)), np.ones((3, 4)), 0.1),
        (np.ones((4, 4)), np.ones((2, 2)), 0.1),
        (np.ones((4, 4)), np.ones((4, 4)), -1),
    ],
)
def test_evidence_rejects_invalid_grids_or_tolerance(surface, terrain, gap):
    with pytest.raises(ValueError):
        compact_receiver_evidence(surface, terrain, maximum_surface_gap_m=gap)
