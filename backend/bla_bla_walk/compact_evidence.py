"""Preserve native validity and receiver evidence beside compact heights."""

from pathlib import Path

import numpy as np

from .interfaces import CompactReceiverEvidence

EVIDENCE_VERSION = "native-pair-before-compact-rounding-v1"


def compact_receiver_evidence(surface, terrain, *, maximum_surface_gap_m):
    """Aggregate an aligned 0.5m pair into 1m evidence without rounding heights.

    Any missing sample invalidates its whole compact cell. Any native pair
    mismatch flags the whole cell; averaging/max aggregation must not hide it.
    The caller supplies a numerical envelope tolerance, not a walking policy.
    """
    surface = np.ma.asarray(surface, dtype="float32").filled(np.nan)
    terrain = np.ma.asarray(terrain, dtype="float32").filled(np.nan)
    if (
        surface.ndim != 2
        or terrain.shape != surface.shape
        or not surface.size
        or any(size % 2 for size in surface.shape)
    ):
        raise ValueError("Evidence requires matching even-sized 0.5m grids")
    if not np.isfinite(maximum_surface_gap_m) or maximum_surface_gap_m < 0:
        raise ValueError("Numerical surface gap must be finite and nonnegative")
    shape = (surface.shape[0] // 2, 2, surface.shape[1] // 2, 2)
    valid = np.isfinite(surface) & np.isfinite(terrain)
    gap = surface - terrain
    known = valid.reshape(shape).all(axis=(1, 3))
    below = (valid & (gap < 0)).reshape(shape).any(axis=(1, 3))
    severe = (valid & (gap < -1)).reshape(shape).any(axis=(1, 3))
    flags = known.astype("uint8") | below.astype("uint8") * 2
    flags |= severe.astype("uint8") * 4
    candidates = valid & (gap >= 0) & (gap <= maximum_surface_gap_m)
    candidates = candidates.reshape(shape).all(axis=(1, 3))
    maxima = surface.reshape(shape).max(axis=(1, 3))
    maxima[~known] = np.nan
    return CompactReceiverEvidence(flags, candidates, maxima, maximum_surface_gap_m)


def write_receiver_evidence(evidence, path: Path, *, source_sha256, bounds):
    """Save compressed evidence and source/grid provenance without native tiles."""
    np.savez_compressed(
        path,
        cell_flags=evidence.cell_flags,
        ground_candidates=evidence.ground_candidates,
        surface_elevations=evidence.surface_elevations,
        source_sha256=np.asarray(source_sha256),
        bounds=np.asarray(bounds),
        evidence_version=EVIDENCE_VERSION,
        maximum_surface_gap_m=evidence.maximum_surface_gap_m,
    )


def read_receiver_evidence(path: Path, *, source_sha256, bounds, maximum_surface_gap_m):
    """Load only matching, aligned evidence; missing files never imply validity."""
    with np.load(path, allow_pickle=False) as stored:
        if (
            str(stored["evidence_version"]) != EVIDENCE_VERSION
            or float(stored["maximum_surface_gap_m"]) != maximum_surface_gap_m
            or not np.array_equal(stored["source_sha256"], source_sha256)
            or not np.array_equal(stored["bounds"], bounds)
        ):
            raise ValueError("Receiver evidence version, source or bounds mismatch")
        flags = stored["cell_flags"]
        candidates = stored["ground_candidates"]
        elevations = stored["surface_elevations"]
    if (
        flags.ndim != 2
        or flags.dtype != np.uint8
        or candidates.shape != flags.shape
        or candidates.dtype != bool
        or elevations.shape != flags.shape
        or elevations.dtype != np.float32
    ):
        raise ValueError("Invalid receiver evidence arrays")
    expected_shape = (bounds[3] - bounds[1], bounds[2] - bounds[0])
    if flags.shape != expected_shape or not flags.size:
        raise ValueError("Receiver evidence shape differs from its 1m bounds")
    if np.any(
        candidates
        & (((flags & 1) == 0) | ((flags & 6) != 0) | ~np.isfinite(elevations))
    ):
        raise ValueError("Ground candidate lacks valid source evidence")
    return CompactReceiverEvidence(flags, candidates, elevations, maximum_surface_gap_m)
