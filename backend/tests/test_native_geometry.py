"""Acceptance checks for resumable T8 geometry preparation."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from bla_bla_walk.geometry_io import (
    PAIR_VALID,
    SURFACE_BELOW_TERRAIN,
    SURFACE_BELOW_TERRAIN_BY_MORE_THAN_1M,
    build_pair_flags,
    decode_native_grid,
    edge_statistics,
    normalized_sha256,
)
from bla_bla_walk.native_geometry import (
    DEFAULT_INVENTORY,
    DEFAULT_MANIFEST,
    DEFAULT_METADATA,
    batches,
    build_metadata,
    grid_gap,
    rounded_measurements,
    sha256_path,
    tile_status,
)
from rasterio.transform import from_origin


def test_inventory_plan_pins_139_tiles_and_explicit_buffer_gaps():
    metadata = build_metadata(DEFAULT_INVENTORY, DEFAULT_MANIFEST)

    assert len(metadata["tiles"]) == 139
    assert metadata["source_inventory"]["receiver_tiles"] == 65
    assert metadata["source_inventory"]["buffer_only_tiles"] == 74
    assert metadata["coverage"] == {"pending": 139}
    assert (
        sum(
            tile["products"]["surface"]["source_status"] != "catalog_available"
            for tile in metadata["tiles"].values()
        )
        == 10
    )
    assert (
        sum(
            tile["products"]["terrain"]["source_status"] != "catalog_available"
            for tile in metadata["tiles"].values()
        )
        == 43
    )
    assert all(
        not tile["gaps"]
        for tile in metadata["tiles"].values()
        if tile["role"] == "receiver"
    )


def test_mismatch_policy_is_explicit_for_t10():
    metadata = build_metadata(DEFAULT_INVENTORY, DEFAULT_MANIFEST)
    policy = metadata["surface_terrain_policy"]

    assert policy["surface_below_terrain"]["bit"] == SURFACE_BELOW_TERRAIN
    assert "unknown" in policy["surface_below_terrain"]["action_for_T10"]
    assert "never silently clamp" in policy["surface_below_terrain"]["action_for_T10"]
    assert "does not invalidate" in policy["nominal_year_mismatch"]["action_for_T10"]
    border = metadata["tiles"]["2611-1270"]
    assert border["survey_year_mismatch"] is True
    assert border["t10_flag_policy"] == {
        "version": "native-0.5m-scene-flags-v1",
        "definitions": "#/surface_terrain_policy",
        "nominal_year_mismatch": True,
        "pair_flags_expected": True,
        "action": "read pair_flags; cells without bit 1 or with bit 2/4 are unknown",
    }

    gap = metadata["tiles"]["2607-1268"]
    assert gap["t10_flag_policy"]["pair_flags_expected"] is False
    assert "source gap remains unknown" in gap["t10_flag_policy"]["action"]


def test_stac_multihash_is_normalized_to_raw_sha256():
    raw = "f7c7308e2b8aca3be820d6f429d52ec6b275f7e77e8ed88646ea95f4309041cb"

    assert normalized_sha256(raw) == raw
    assert normalized_sha256("1220" + raw.upper()) == raw


def test_bridge_like_cells_keep_raw_values_and_flag_scene_mismatch(tmp_path: Path):
    surface = np.array([[270.0, 268.0, 264.0, -9999.0]], dtype="float32")
    terrain = np.array([[265.0, 268.5, 266.0, 265.0]], dtype="float32")
    surface_path = tmp_path / "surface.npy"
    terrain_path = tmp_path / "terrain.npy"
    flags_path = tmp_path / "flags.npy"
    np.save(surface_path, surface)
    np.save(terrain_path, terrain)

    record = build_pair_flags(surface_path, terrain_path, flags_path)
    flags = np.load(flags_path)

    assert np.array_equal(np.load(surface_path), surface)
    assert flags[0, 0] == PAIR_VALID
    assert flags[0, 1] == PAIR_VALID | SURFACE_BELOW_TERRAIN
    assert flags[0, 2] == (
        PAIR_VALID | SURFACE_BELOW_TERRAIN | SURFACE_BELOW_TERRAIN_BY_MORE_THAN_1M
    )
    assert flags[0, 3] == 0
    assert record["counts"] == {
        "pair_valid": 3,
        "surface_below_terrain": 2,
        "below_by_gt_1m": 1,
    }


def test_decode_checks_native_grid_and_preserves_nodata(tmp_path: Path):
    source = tmp_path / "source.tif"
    target = tmp_path / "prepared.npy"
    values = np.full((2000, 2000), 275.0, dtype="float32")
    values[0, 0] = -9999.0
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        width=2000,
        height=2000,
        count=1,
        dtype="float32",
        crs="EPSG:2056",
        transform=from_origin(2611000, 1271000, 0.5, 0.5),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(values, 1)
    tile = {
        "tile": "2611-1270",
        "bounds_epsg2056": [2611000, 1270000, 2612000, 1271000],
    }

    record = decode_native_grid(source, target, tile)

    assert record["horizontal_crs"] == "EPSG:2056"
    assert record["vertical_reference"] == "LN02 / EPSG:5728"
    assert record["resolution_metres"] == 0.5
    assert record["valid_cells"] == 3_999_999
    assert record["nodata_cells"] == 1
    assert np.load(target, mmap_mode="r")[0, 0] == -9999.0


def test_adjacent_seam_statistics_keep_real_height_deltas(tmp_path: Path):
    west = np.array([[1.0, 2.0], [3.0, 4.0]], dtype="float32")
    east = np.array([[2.5, 9.0], [4.5, 9.0]], dtype="float32")
    west_path, east_path = tmp_path / "west.npy", tmp_path / "east.npy"
    np.save(west_path, west)
    np.save(east_path, east)

    seam = edge_statistics(west_path, east_path, "east")
    first = {"bounds_epsg2056": [0, 0, 1000, 1000]}
    second = {"bounds_epsg2056": [1000, 0, 2000, 1000]}

    assert grid_gap(first, second, "east") == 0
    assert seam["valid_cell_pairs"] == 2
    assert seam["absolute_delta_metres"]["median"] == 0.5


def test_batching_and_gap_status_are_deterministic():
    assert batches(["a", "b", "c", "d", "e"], 2) == [
        ["a", "b"],
        ["c", "d"],
        ["e"],
    ]
    partial = {
        "role": "occluder_buffer",
        "products": {
            "surface": {"prepared": {"path": "surface.npy"}},
            "terrain": {"prepared": None},
        },
    }
    assert tile_status(partial) == "prepared_partial_buffer_gap"


def test_metadata_measurements_drop_binary_float_noise():
    assert rounded_measurements({"value": 1.234567890123}) == {"value": 1.234568}


def test_committed_geometry_metadata_covers_city_and_buffer():
    metadata = json.loads(DEFAULT_METADATA.read_text(encoding="utf-8"))
    summary = metadata["verification_summary"]

    assert metadata["status"] == "prepared"
    assert metadata["source_manifest"]["sha256"] == sha256_path(DEFAULT_MANIFEST)
    assert metadata["coverage"] == {
        "prepared_pair": 96,
        "prepared_partial_buffer_gap": 33,
        "documented_buffer_gap": 10,
    }
    assert summary["receiver_tiles_with_prepared_pairs"] == 65
    assert summary["survey_year_mismatch_tiles"] == 96
    assert summary["survey_year_not_comparable_tiles"] == 43
    assert summary["prepared_artifacts"] == {
        "source_grids": 225,
        "pair_flags": 96,
        "bytes": 3_984_041_088,
        "gib": 3.710427,
        "within_geometry_disk_budget": True,
    }
    assert summary["seams"] == {
        "checks": 397,
        "all_grid_gaps_zero": True,
    }
    assert summary["alignment_references"] == [
        "border_kleinhuningen",
        "mittlere_bruecke",
        "urban_centre",
    ]
    assert metadata["alignment_reference_points"]["mittlere_bruecke"]["pair_flag"] == (
        PAIR_VALID | SURFACE_BELOW_TERRAIN
    )
    assert (
        metadata["tiles"]["2613-1269"]["pair_flags"]["counts"]["below_by_gt_1m"] == 4563
    )
    assert all(
        tile["status"] == "prepared_pair"
        for tile in metadata["tiles"].values()
        if tile["role"] == "receiver"
    )
    assert all(
        tile["t10_flag_policy"]["version"] == "native-0.5m-scene-flags-v1"
        for tile in metadata["tiles"].values()
    )
