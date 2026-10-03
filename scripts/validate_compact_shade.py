"""Measure compact shade changes against pinned unquantized Basel geometry.

This is surveyed-envelope numerical evidence, not observed pedestrian shade or
route scoring. Only the pinned centre tile is covered; other route samples stay
unknown. Run after validate_shade_sample.py verifies the native source pair.
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
sys.path.insert(0, str(ROOT / "scripts"))
from bla_bla_walk.compact_evidence import (  # noqa: E402
    compact_receiver_evidence,
    read_receiver_evidence,
    write_receiver_evidence,
)
from bla_bla_walk.geometry import (  # noqa: E402
    geometry_settings,
    prepare_raster,
    read_heights,
    sha256_file,
)
from bla_bla_walk.shade import SHADED, UNKNOWN, shadow_mask  # noqa: E402
from bla_bla_walk.solar import solar_position  # noqa: E402
from test_shade import independent_reference  # noqa: E402

TILE = "2610-1266"
TERRAIN_2M_SHA256 = "10db3f33bef59d7fd4018aeeb1c7d47d787a396d2f69274d75e3473d06ad3bb5"
WEST, NORTH = 2610000, 1267000
TIMES = [f"2026-10-03T{hour:02}:00:00+00:00" for hour in (8, 12, 15)]


def trace(surface, terrain, cell, moment, receivers=None, heights=None, **evidence):
    """Use exact time and local convergence; no inferred horizon ceiling."""
    longitude, latitude = transform(
        "EPSG:2056", "EPSG:4326", [WEST + 500], [NORTH - 500]
    )
    east, north = transform(
        "EPSG:4326", "EPSG:2056", longitude * 2, [latitude[0], latitude[0] + 0.0001]
    )
    rotation = -math.degrees(math.atan2(east[1] - east[0], north[1] - north[0]))
    elevation, azimuth = solar_position(moment, latitude[0], longitude[0])
    options = dict(
        elevation_deg=elevation,
        azimuth_deg=azimuth - rotation,
        cell_size_m=cell,
        max_distance_m=1500,
        minimum_elevation_deg=10,
        receivers=receivers,
        receiver_elevations=heights,
    )
    return (
        shadow_mask(surface, terrain, **options, **evidence),
        elevation,
        azimuth - rotation,
    )


def scene_check(native_surface, native_terrain, compact_surface, compact_terrain):
    """Compare both representations with independent prism intersections."""
    checks = []
    # Aligned windows: same physical footprint, two grid resolutions.
    for row, column in ((970, 970), (1300, 1000), (500, 500)):
        for label, surface, terrain, cell in (
            ("native", native_surface, native_terrain, 0.5),
            ("compact", compact_surface, compact_terrain, 1.0),
        ):
            factor = int(cell / 0.5)
            r, c, size = row // factor, column // factor, 64 // factor
            surface = surface[r : r + size, c : c + size]
            terrain = terrain[r : r + size, c : c + size]
            candidates = np.argwhere(
                np.isfinite(surface) & (surface >= terrain) & (surface - terrain <= 0.1)
            )
            candidates = candidates[
                np.linspace(0, len(candidates) - 1, min(12, len(candidates)), dtype=int)
            ]
            receivers = np.zeros(surface.shape, dtype=bool)
            receivers[candidates[:, 0], candidates[:, 1]] = True
            for time in TIMES:
                states, elevation, azimuth = trace(
                    surface,
                    terrain,
                    cell,
                    datetime.fromisoformat(time),
                    receivers,
                    surface,
                )
                points = []
                for rr, cc in candidates:
                    expected = independent_reference(
                        surface,
                        rr,
                        cc,
                        azimuth,
                        elevation,
                        None,
                        cell=cell,
                        receiver_height=float(surface[rr, cc]),
                        terrain=terrain,
                        extent=1500,
                    )
                    if states[rr, cc] != expected:
                        raise AssertionError("Independent scene reference disagrees")
                    points.append([int(rr), int(cc), int(expected)])
                checks.append(
                    dict(
                        window_native=[row, column, 64, 64],
                        representation=label,
                        time=time,
                        points=points,
                    )
                )
    return checks


def edge_changes(native_surface, native_terrain, compact_surface, compact_terrain):
    """Measure state changes on aligned 32m scene footprints, without a tolerance."""
    evidence = []
    for row, col in ((970, 970), (1300, 1000), (500, 500)):
        native = (
            native_surface[row : row + 64, col : col + 64],
            native_terrain[row : row + 64, col : col + 64],
        )
        compact = (
            compact_surface[row // 2 : row // 2 + 32, col // 2 : col // 2 + 32],
            compact_terrain[row // 2 : row // 2 + 32, col // 2 : col // 2 + 32],
        )
        for time in TIMES:
            a, _, _ = trace(*native, 0.5, datetime.fromisoformat(time))
            b, _, _ = trace(*compact, 1, datetime.fromisoformat(time))
            b = b.repeat(2, axis=0).repeat(2, axis=1)
            evidence.append(
                dict(
                    window_native=[row, col, 64, 64],
                    time=time,
                    changed_state_square_m=float(np.count_nonzero(a != b) * 0.25),
                    native_shaded_square_m=float(np.count_nonzero(a == SHADED) * 0.25),
                    compact_shaded_square_m=float(np.count_nonzero(b == SHADED) * 0.25),
                )
            )
    return evidence


def route_samples(feature):
    """Sample segment midpoints with metre weights and proportional elapsed time."""
    coordinates = np.asarray(feature["geometry"]["coordinates"])
    x, y = transform("EPSG:4326", "EPSG:2056", coordinates[:, 0], coordinates[:, 1])
    vertices = np.column_stack((x, y))
    lengths = np.linalg.norm(np.diff(vertices, axis=0), axis=1)
    total = float(lengths.sum())
    travelled = 0
    samples = []
    for start, end, length in zip(vertices[:-1], vertices[1:], lengths, strict=True):
        count = max(1, math.ceil(length / 2))
        for index in range(count):
            fraction = (index + 0.5) / count
            point = start + fraction * (end - start)
            elapsed = (travelled + fraction * length) / total
            elapsed *= feature["properties"]["routing_duration_s"]
            samples.append((point, length / count, elapsed))
        travelled += length
    return samples, total


def route_check(
    routes,
    native_surface,
    native_terrain,
    compact_surface,
    compact_terrain,
    receiver_evidence,
):
    """Compare full-denominator sample metres; not a T5 recommendation/score."""
    evidence = []
    for feature in routes["features"]:
        samples, total = route_samples(feature)
        for time in TIMES:
            departure = datetime.fromisoformat(time)
            weights = np.asarray([sample[1] for sample in samples])
            results = {}
            for label, surface, terrain, cell in (
                ("native", native_surface, native_terrain, 0.5),
                ("compact", compact_surface, compact_terrain, 1.0),
                ("compact_preserved", compact_surface, compact_terrain, 1.0),
            ):
                values = np.full(len(samples), UNKNOWN, dtype="uint8")
                for index, (point, _, elapsed) in enumerate(samples):
                    row = math.floor((NORTH - point[1]) / cell)
                    col = math.floor((point[0] - WEST) / cell)
                    if not (
                        0 <= row < surface.shape[0] and 0 <= col < surface.shape[1]
                    ):
                        continue
                    # Numerical ground candidates, not verified pedestrian receivers.
                    if not (
                        np.isfinite(surface[row, col])
                        and 0 <= surface[row, col] - terrain[row, col] <= 0.1
                    ):
                        continue
                    if (
                        label == "compact_preserved"
                        and not receiver_evidence.ground_candidates[row, col]
                    ):
                        continue
                    receivers = np.zeros(surface.shape, dtype=bool)
                    receivers[row, col] = True
                    options = {}
                    heights = surface
                    if label == "compact_preserved":
                        options = dict(
                            cell_flags=receiver_evidence.cell_flags,
                            receiver_surface_elevations=receiver_evidence.surface_elevations,
                        )
                        heights = receiver_evidence.surface_elevations
                    states, _, _ = trace(
                        surface,
                        terrain,
                        cell,
                        departure + timedelta(seconds=elapsed),
                        receivers,
                        heights,
                        **options,
                    )
                    values[index] = states[row, col]
                results[label] = values
            native, compact = results["native"], results["compact"]
            preserved = results["compact_preserved"]
            evidence.append(
                dict(
                    route_id=feature["id"],
                    departure=time,
                    samples=len(samples),
                    projected_length_m=total,
                    native_shaded_m=float(weights[native == SHADED].sum()),
                    compact_shaded_m=float(weights[compact == SHADED].sum()),
                    preserved_shaded_m=float(weights[preserved == SHADED].sum()),
                    preserved_unknown_m=float(weights[preserved == UNKNOWN].sum()),
                    preserved_changed_state_m=float(weights[native != preserved].sum()),
                    native_unknown_m=float(weights[native == UNKNOWN].sum()),
                    compact_unknown_m=float(weights[compact == UNKNOWN].sum()),
                    changed_state_m=float(weights[native != compact].sum()),
                    compact_shade_native_unknown_m=float(
                        weights[(compact == SHADED) & (native == UNKNOWN)].sum()
                    ),
                )
            )
    return evidence


def validate(surface_path, terrain_path, terrain_2m_path, output_dir):
    """Prepare actual scaled GeoTIFFs and record reproducible comparison evidence."""
    if sha256_file(terrain_2m_path) != TERRAIN_2M_SHA256:
        raise ValueError("2m terrain differs from its pinned catalogue checksum")
    inventory = json.loads((ROOT / "data/tile-inventory.json").read_text())
    tile = next(row for row in inventory["tiles"] if row["tile"] == TILE)
    for kind, path in (("surface", surface_path), ("terrain", terrain_path)):
        expected = tile[kind]["catalog_checksum"][4:].lower()
        if sha256_file(path) != expected:
            raise ValueError("Native source differs from pinned catalogue")
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for kind, source in (("surface", surface_path), ("terrain", terrain_2m_path)):
        paths[kind] = output_dir / f"compact-{kind}.tif"
        prepare_raster(source, paths[kind], tile, kind)
    native_surface = read_heights(surface_path).filled(np.nan)
    native_terrain = read_heights(terrain_path).filled(np.nan)
    compact_surface = read_heights(paths["surface"]).filled(np.nan)
    compact_terrain = read_heights(paths["terrain"]).filled(np.nan)
    evidence_path = output_dir / "receiver-evidence.npz"
    sources = [sha256_file(surface_path), sha256_file(terrain_path)]
    receiver_evidence = compact_receiver_evidence(
        native_surface, native_terrain, maximum_surface_gap_m=0.1
    )
    write_receiver_evidence(
        receiver_evidence,
        evidence_path,
        source_sha256=sources,
        bounds=tile["bounds_epsg2056"],
    )
    receiver_evidence = read_receiver_evidence(
        evidence_path,
        source_sha256=sources,
        bounds=tile["bounds_epsg2056"],
        maximum_surface_gap_m=0.1,
    )
    scenes = scene_check(
        native_surface, native_terrain, compact_surface, compact_terrain
    )
    routes = route_check(
        json.loads((ROOT / "data/routes/demo.geojson").read_text()),
        native_surface,
        native_terrain,
        compact_surface,
        compact_terrain,
        receiver_evidence,
    )
    native_invalid = ~np.isfinite(native_surface) | ~np.isfinite(native_terrain)
    native_invalid |= native_surface < native_terrain
    invalid_blocks = native_invalid.reshape(1000, 2, 1000, 2).any(axis=(1, 3))
    compact_candidate = np.isfinite(compact_surface) & (
        compact_surface == compact_terrain
    )
    return dict(
        schema_version=1,
        tile=TILE,
        attribution="© swisstopo; © OpenStreetMap contributors",
        settings=geometry_settings(),
        source_sha256=dict(
            surface=sha256_file(surface_path),
            terrain_native=sha256_file(terrain_path),
            terrain_2m=TERRAIN_2M_SHA256,
        ),
        prepared_sha256={kind: sha256_file(path) for kind, path in paths.items()},
        receiver_evidence_sha256=sha256_file(evidence_path),
        receiver_evidence_bytes=evidence_path.stat().st_size,
        preserved_ground_candidates=int(receiver_evidence.ground_candidates.sum()),
        numerical_surface_gap_metres=0.1,
        route_fixture_sha256=sha256_file(ROOT / "data/routes/demo.geojson"),
        independent_matches=sum(len(check["points"]) for check in scenes),
        compact_ground_candidates_hiding_native_invalid=int(
            (invalid_blocks & compact_candidate).sum()
        ),
        scene_checks=scenes,
        scene_edge_changes=edge_changes(
            native_surface, native_terrain, compact_surface, compact_terrain
        ),
        route_sensitivity=routes,
        limits=[
            "Numerical surface-envelope candidates do not prove walkability or "
            "canopy interiors.",
            "Cell centres differ by up to 0.354m; state changes combine grid, "
            "height and terrain-source effects.",
            "No verified horizon ceiling: unblocked rays and samples outside "
            "this tile remain unknown.",
            "Route samples every <=2m use departure plus proportional saved "
            "routing duration; no route score or ranking.",
            "No physical shade accuracy, encoding tolerance, city-wide or "
            "cache/API acceptance is claimed.",
            "Raw compact values demonstrate the unsafe case; compact_preserved "
            "uses native pair flags and all-four-sample ground candidates.",
            "The 0.1m envelope is a numerical validation selection, not "
            "adopted pedestrian or canopy support evidence.",
        ],
    )


def main():
    global TILE, TERRAIN_2M_SHA256, WEST, NORTH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface", type=Path, required=True)
    parser.add_argument("--terrain", type=Path, required=True)
    parser.add_argument("--terrain-2m", type=Path, required=True)
    parser.add_argument("--work-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tile", default=TILE)
    parser.add_argument("--terrain-2m-sha256", default=TERRAIN_2M_SHA256)
    args = parser.parse_args()
    TILE = args.tile
    TERRAIN_2M_SHA256 = args.terrain_2m_sha256
    WEST, NORTH = int(args.tile[:4]) * 1000, (int(args.tile[5:]) + 1) * 1000
    evidence = validate(
        args.surface, args.terrain, args.terrain_2m, args.work_directory
    )
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"{evidence['independent_matches']} independent scene matches")
    for route in evidence["route_sensitivity"]:
        print(route)


if __name__ == "__main__":
    main()
