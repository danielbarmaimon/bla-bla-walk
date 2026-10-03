"""Prepare versioned Basel surface and terrain grids for the shade worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from rasterio.warp import transform as transform_coordinates

from .geometry_io import (
    NODATA,
    build_pair_flags,
    decode_native_grid,
    download_verified,
    edge_statistics,
    sha256_path,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = PROJECT_ROOT / "data/tile-inventory.json"
DEFAULT_MANIFEST = PROJECT_ROOT / "data/source-manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/geometry"
DEFAULT_METADATA = PROJECT_ROOT / "data/fixtures/geometry-metadata.json"
SCHEMA_VERSION = 1
POLICY_VERSION = "native-0.5m-scene-flags-v1"
FLAG_POLICY = {
    "pair_valid": {"bit": 1, "meaning": "both source cells are finite and not NoData"},
    "surface_below_terrain": {
        "bit": 2,
        "condition": "surface < terrain",
        "action_for_T10": (
            "preserve both source values but treat the cell, and an otherwise "
            "unresolved ray crossing it, as unknown; never silently clamp"
        ),
    },
    "surface_below_terrain_by_more_than_1m": {
        "bit": 4,
        "condition": "surface < terrain - 1 metre",
        "action_for_T10": "same unknown policy; separate count is a QA severity flag",
    },
    "nominal_year_mismatch": {
        "scope": "tile",
        "action_for_T10": (
            "retain the tile with both nominal years in the geometry version; the "
            "mismatch alone does not invalidate unflagged cells"
        ),
    },
}


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    """Return a metadata timestamp with explicit UTC."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def geometry_version(inventory_path: Path) -> str:
    """Version prepared bytes by the pinned inventory and flag policy."""
    digest = hashlib.sha256()
    digest.update(inventory_path.read_bytes())
    digest.update(POLICY_VERSION.encode())
    return f"basel-lv95-{POLICY_VERSION}-{digest.hexdigest()[:12]}"


def relative_path(path: Path) -> str:
    """Store a portable project-relative path."""
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def build_metadata(inventory_path: Path, manifest_path: Path) -> dict[str, Any]:
    """Create the complete deterministic 139-tile preparation plan."""
    inventory = load_json(inventory_path)
    tiles = {item["tile"]: tile_plan(item) for item in inventory["tiles"]}
    return {
        "schema_version": SCHEMA_VERSION,
        "task": "T8",
        "status": "planned",
        "geometry_version": geometry_version(inventory_path),
        "source_inventory": {
            "path": relative_path(inventory_path),
            "sha256": sha256_path(inventory_path),
            "required_tile_squares": inventory["summary"]["required_tile_squares"],
            "receiver_tiles": inventory["summary"]["receiver_tiles"],
            "buffer_only_tiles": inventory["summary"]["buffer_only_tiles"],
        },
        "source_manifest": {
            "path": relative_path(manifest_path),
            "sha256": sha256_path(manifest_path),
        },
        "boundary": {
            key: inventory["boundary"][key]
            for key in (
                "name",
                "includes",
                "release",
                "asset_sha256",
                "geometry_sha256",
                "crs",
                "bounds",
            )
        },
        "grid": {
            "horizontal_crs": inventory["horizontal_crs"],
            "vertical_reference": inventory["vertical_reference"],
            "height_units": "metres",
            "source_resolution_metres": inventory["resolution_metres"],
            "prepared_resolution_metres": inventory["resolution_metres"],
            "dtype": "float32",
            "nodata": NODATA,
            "format": "NumPy NPY v1/v2 as emitted by numpy.save/open_memmap",
        },
        "occluder_buffer": inventory["buffer"],
        "surface_terrain_policy": FLAG_POLICY,
        "storage_budget": {
            "geometry_disk_gib": 8,
            "maximum_worker_peak_mib": 768,
            "maximum_concurrent_workers": 2,
        },
        "tiles": tiles,
        "batches": [],
        "alignment_reference_points": {},
        "coverage": coverage_summary(tiles),
    }


def tile_plan(tile: dict[str, Any]) -> dict[str, Any]:
    """Reduce the source inventory to fields needed by preparation and T10."""
    products = {}
    for product in ("surface", "terrain"):
        source = tile[product]
        products[product] = {
            "source_status": source["status"],
            "item_id": source.get("item_id"),
            "nominal_datetime": source.get("nominal_datetime"),
            "catalog_checksum": source.get("catalog_checksum"),
            "prepared": None,
        }
    return {
        "role": tile["role"],
        "bounds_epsg2056": tile["bounds_epsg2056"],
        "status": "pending",
        "survey_year_mismatch": tile["survey_year_mismatch"],
        "t10_flag_policy": per_tile_flag_policy(tile),
        "products": products,
        "pair_flags": None,
        "gaps": source_gaps(tile),
        "reference_alignment": None,
    }


def per_tile_flag_policy(tile: dict[str, Any]) -> dict[str, Any]:
    """Make T10's action explicit for each pair or source-gap tile."""
    pair_expected = all(
        tile[product]["status"] == "catalog_available"
        for product in ("surface", "terrain")
    )
    return {
        "version": POLICY_VERSION,
        "definitions": "#/surface_terrain_policy",
        "nominal_year_mismatch": tile["survey_year_mismatch"],
        "pair_flags_expected": pair_expected,
        "action": (
            "read pair_flags; cells without bit 1 or with bit 2/4 are unknown"
            if pair_expected
            else "source gap remains unknown; do not infer or fill missing geometry"
        ),
    }


def source_gaps(tile: dict[str, Any]) -> list[dict[str, str]]:
    """Make each absent source an explicit, non-inferred gap."""
    return [
        {
            "product": product,
            "reason": "not present in the pinned STAC selection; no infill fabricated",
        }
        for product in ("surface", "terrain")
        if tile[product]["status"] != "catalog_available"
    ]


def coverage_summary(tiles: dict[str, Any]) -> dict[str, int]:
    """Summarise preparation state without hiding partial buffer coverage."""
    statuses = {}
    for tile in tiles.values():
        statuses[tile["status"]] = statuses.get(tile["status"], 0) + 1
    return statuses


def rounded_measurements(value: Any) -> Any:
    """Keep review metadata precise without emitting noisy binary-float tails."""
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: rounded_measurements(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded_measurements(item) for item in value]
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Replace metadata only after a complete JSON serialization."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(rounded_measurements(value), indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def load_or_create_metadata(
    metadata_path: Path, inventory_path: Path, manifest_path: Path
) -> dict[str, Any]:
    """Resume matching metadata, otherwise create a fresh pinned plan."""
    expected = geometry_version(inventory_path)
    if metadata_path.exists():
        metadata = load_json(metadata_path)
        if metadata.get("geometry_version") != expected:
            raise ValueError("metadata geometry_version does not match tile inventory")
        metadata["source_manifest"]["sha256"] = sha256_path(manifest_path)
        sources = {tile["tile"]: tile for tile in load_json(inventory_path)["tiles"]}
        for tile_id, tile in metadata["tiles"].items():
            tile["t10_flag_policy"] = per_tile_flag_policy(sources[tile_id])
        return metadata
    return build_metadata(inventory_path, manifest_path)


def reusable(prepared: dict[str, Any] | None) -> bool:
    """Accept a prepared artifact only when its recorded bytes still match."""
    if not prepared:
        return False
    path = PROJECT_ROOT / prepared["path"]
    return path.exists() and sha256_path(path) == prepared["sha256"]


def prepare_product(
    tile_id: str,
    tile_source: dict[str, Any],
    product: str,
    output_root: Path,
    keep_source: bool,
) -> dict[str, Any]:
    """Acquire, validate and decode one inventory asset."""
    source = tile_source[product]
    source_path = output_root / "source" / product / f"{tile_id}.tif"
    target = output_root / "prepared" / tile_id / f"{product}.npy"
    acquisition = download_verified(
        source["asset_url"], source["catalog_checksum"], source_path
    )
    prepared = decode_native_grid(source_path, target, tile_source)
    prepared["path"] = relative_path(target)
    prepared["source"] = acquisition
    if not keep_source:
        source_path.unlink(missing_ok=True)
    return prepared


def prepare_tile(
    tile_source: dict[str, Any],
    tile_record: dict[str, Any],
    output_root: Path,
    keep_source: bool = False,
) -> dict[str, Any]:
    """Prepare all available products and flags for one selected square."""
    tile_id = tile_source["tile"]
    for product in ("surface", "terrain"):
        source = tile_source[product]
        current = tile_record["products"][product]["prepared"]
        if source["status"] != "catalog_available" or reusable(current):
            continue
        prepared = prepare_product(
            tile_id, tile_source, product, output_root, keep_source
        )
        tile_record["products"][product]["prepared"] = prepared

    surface = tile_record["products"]["surface"]["prepared"]
    terrain = tile_record["products"]["terrain"]["prepared"]
    if surface and terrain and reusable(surface) and reusable(terrain):
        flags_path = output_root / "prepared" / tile_id / "pair-flags.npy"
        flags = build_pair_flags(
            PROJECT_ROOT / surface["path"], PROJECT_ROOT / terrain["path"], flags_path
        )
        flags["path"] = relative_path(flags_path)
        tile_record["pair_flags"] = flags
        tile_record["reference_alignment"] = reference_alignment(tile_id, tile_record)
    tile_record["status"] = tile_status(tile_record)
    tile_record["prepared_at"] = utc_now()
    return tile_record


def tile_status(tile: dict[str, Any]) -> str:
    """Classify prepared receiver coverage and explicit buffer gaps."""
    prepared = [
        tile["products"][name]["prepared"] is not None
        for name in ("surface", "terrain")
    ]
    if all(prepared):
        return "prepared_pair"
    if any(prepared) and tile["role"] == "occluder_buffer":
        return "prepared_partial_buffer_gap"
    if tile["role"] == "receiver":
        return "unsupported_receiver_gap"
    return "documented_buffer_gap"


def reference_alignment(tile_id: str, tile: dict[str, Any]) -> dict[str, Any]:
    """Round-trip a central LV95 pixel centre through both prepared grids."""
    west, _, _, north = tile["bounds_epsg2056"]
    x, y = west + 500.25, north - 500.25
    row = int((north - y) / 0.5)
    column = int((x - west) / 0.5)
    values = {}
    for product in ("surface", "terrain"):
        prepared = tile["products"][product]["prepared"]
        if prepared:
            array = np.load(PROJECT_ROOT / prepared["path"], mmap_mode="r")
            values[product] = float(array[row, column])
    return {
        "name": f"{tile_id}-central-pixel",
        "point_epsg2056": [x, y],
        "row_column": [row, column],
        "round_trip_pixel_centre_epsg2056": [
            west + (column + 0.5) * 0.5,
            north - (row + 0.5) * 0.5,
        ],
        "products_share_cell": len(values) == 2,
        "values_metres": values,
    }


def prepare_tiles(
    tile_ids: list[str],
    metadata: dict[str, Any],
    inventory: dict[str, Any],
    metadata_path: Path,
    output_root: Path,
    workers: int,
    batch_name: str,
) -> dict[str, Any]:
    """Prepare a separately recorded batch, saving after every completed tile."""
    sources = {tile["tile"]: tile for tile in inventory["tiles"]}
    batch = {
        "name": batch_name,
        "tiles": tile_ids,
        "status": "running",
        "started_at": utc_now(),
    }
    metadata["batches"] = [
        item for item in metadata["batches"] if item["name"] != batch_name
    ]
    metadata["batches"].append(batch)
    atomic_write_json(metadata_path, metadata)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                prepare_tile, sources[tile_id], metadata["tiles"][tile_id], output_root
            ): tile_id
            for tile_id in tile_ids
        }
        failures = {}
        for future in as_completed(futures):
            tile_id = futures[future]
            try:
                metadata["tiles"][tile_id] = future.result()
            except Exception as error:
                failures[tile_id] = f"{type(error).__name__}: {error}"
                metadata["tiles"][tile_id]["status"] = "failed"
            metadata["coverage"] = coverage_summary(metadata["tiles"])
            atomic_write_json(metadata_path, metadata)
            print(
                json.dumps(
                    {
                        "batch": batch_name,
                        "tile": tile_id,
                        "status": metadata["tiles"][tile_id]["status"],
                        "coverage": metadata["coverage"],
                    }
                ),
                flush=True,
            )
    if failures:
        batch["status"] = "failed"
        batch["failures"] = failures
        batch["finished_at"] = utc_now()
        atomic_write_json(metadata_path, metadata)
        failed_ids = ", ".join(sorted(failures))
        raise RuntimeError(f"batch {batch_name} failed for: {failed_ids}")
    batch["seams"] = verify_seams(metadata, set(tile_ids))
    batch["status"] = "verified"
    batch["finished_at"] = utc_now()
    metadata["coverage"] = coverage_summary(metadata["tiles"])
    metadata["status"] = overall_status(metadata)
    atomic_write_json(metadata_path, metadata)
    print(json.dumps({"batch": batch_name, "status": "verified"}), flush=True)
    return metadata


def overall_status(metadata: dict[str, Any]) -> str:
    """Complete only when every receiver pair and every source/gap is recorded."""
    allowed = {
        "prepared_pair",
        "prepared_partial_buffer_gap",
        "documented_buffer_gap",
    }
    complete = all(tile["status"] in allowed for tile in metadata["tiles"].values())
    return "prepared" if complete else "in_progress"


def verify_seams(
    metadata: dict[str, Any], selected: set[str] | None = None
) -> list[dict[str, Any]]:
    """Verify exact grid adjacency and record observed edge elevation deltas."""
    results = []
    tiles = metadata["tiles"]
    for tile_id, tile in sorted(tiles.items()):
        x, y = (int(value) for value in tile_id.split("-"))
        neighbors = ((f"{x + 1}-{y}", "east"), (f"{x}-{y + 1}", "north"))
        for neighbor, orientation in neighbors:
            if neighbor not in tiles or (
                selected and not ({tile_id, neighbor} & selected)
            ):
                continue
            for product in ("surface", "terrain"):
                first = tile["products"][product]["prepared"]
                second = tiles[neighbor]["products"][product]["prepared"]
                if not first or not second:
                    continue
                record = edge_statistics(
                    PROJECT_ROOT / first["path"],
                    PROJECT_ROOT / second["path"],
                    orientation,
                )
                record.update(
                    {
                        "tiles": [tile_id, neighbor],
                        "product": product,
                        "orientation": orientation,
                        "grid_gap_metres": grid_gap(tile, tiles[neighbor], orientation),
                    }
                )
                if record["grid_gap_metres"] != 0:
                    raise ValueError(f"misaligned seam {tile_id}/{neighbor}/{product}")
                results.append(record)
    return results


def grid_gap(first: dict[str, Any], second: dict[str, Any], orientation: str) -> float:
    """Return the coordinate gap between nominal adjacent bounds."""
    if orientation == "east":
        return float(second["bounds_epsg2056"][0] - first["bounds_epsg2056"][2])
    return float(second["bounds_epsg2056"][1] - first["bounds_epsg2056"][3])


def add_named_references(metadata: dict[str, Any]) -> None:
    """Record centre, boundary and bridge checks for downstream review."""
    points = {
        "urban_centre": (2610, 1266, 2610500.25, 1266499.75),
        "border_kleinhuningen": (2611, 1270, 2611500.25, 1270499.75),
    }
    xs, ys = transform_coordinates("EPSG:4326", "EPSG:2056", [7.5886], [47.5596])
    bridge_x, bridge_y = xs[0], ys[0]
    points["mittlere_bruecke"] = (
        math.floor(bridge_x / 1000),
        math.floor(bridge_y / 1000),
        bridge_x,
        bridge_y,
    )
    for name, (x_tile, y_tile, x, y) in points.items():
        tile_id = f"{x_tile}-{y_tile}"
        check = reference_at_point(tile_id, metadata["tiles"][tile_id], x, y)
        check["name"] = name
        metadata["alignment_reference_points"][name] = check


def reference_at_point(
    tile_id: str, tile: dict[str, Any], x: float, y: float
) -> dict[str, Any]:
    """Sample paired grids and flags at one LV95 reference point."""
    west, _, _, north = tile["bounds_epsg2056"]
    row, column = int((north - y) / 0.5), int((x - west) / 0.5)
    result = {
        "tile": tile_id,
        "point_epsg2056": [x, y],
        "row_column": [row, column],
    }
    for product in ("surface", "terrain"):
        prepared = tile["products"][product]["prepared"]
        result[f"{product}_metres"] = (
            float(np.load(PROJECT_ROOT / prepared["path"], mmap_mode="r")[row, column])
            if prepared
            else None
        )
    flags = tile.get("pair_flags")
    result["pair_flag"] = (
        int(np.load(PROJECT_ROOT / flags["path"], mmap_mode="r")[row, column])
        if flags
        else None
    )
    result["products_share_cell"] = (
        result["surface_metres"] is not None and result["terrain_metres"] is not None
    )
    return result


def batches(tile_ids: list[str], batch_size: int) -> list[list[str]]:
    """Split sorted inventory IDs into deterministic resumable batches."""
    return [
        tile_ids[index : index + batch_size]
        for index in range(0, len(tile_ids), batch_size)
    ]


def verification_summary(
    metadata: dict[str, Any],
    manifest: dict[str, Any],
    observed_peak_working_set_bytes: int | None = None,
) -> dict[str, Any]:
    """Summarise final artifacts and budget evidence for review and T10."""
    source_grid_count = 0
    pair_flag_count = 0
    prepared_bytes = 0
    flag_counts = {
        "pair_valid": 0,
        "surface_below_terrain": 0,
        "below_by_gt_1m": 0,
    }
    for tile in metadata["tiles"].values():
        for product in ("surface", "terrain"):
            prepared = tile["products"][product]["prepared"]
            if prepared:
                source_grid_count += 1
                prepared_bytes += prepared["bytes"]
        flags = tile.get("pair_flags")
        if flags:
            pair_flag_count += 1
            prepared_bytes += flags["bytes"]
            for name in flag_counts:
                flag_counts[name] += flags["counts"][name]

    seams = metadata.get("all_seams", [])
    source_memory = manifest["processing_cost"]
    memory = {
        "maximum_worker_peak_mib": metadata["storage_budget"][
            "maximum_worker_peak_mib"
        ],
        "maximum_concurrent_workers": metadata["storage_budget"][
            "maximum_concurrent_workers"
        ],
        "window_rows": 256,
        "float32_bytes_per_product_window": 256 * 2000 * 4,
        "t0_audit_peak_working_set_bytes": source_memory["peak_working_set_bytes"],
        "t0_audit_method": source_memory["method"],
    }
    if observed_peak_working_set_bytes is not None:
        memory.update(
            {
                "t8_full_preparation_peak_working_set_bytes": (
                    observed_peak_working_set_bytes
                ),
                "t8_measurement_method": (
                    "Windows Get-Process PeakWorkingSet64 for the Python child "
                    "during the full two-worker preparation run"
                ),
                "within_single_worker_budget": observed_peak_working_set_bytes
                <= metadata["storage_budget"]["maximum_worker_peak_mib"] * 1024 * 1024,
            }
        )
    disk_limit = metadata["storage_budget"]["geometry_disk_gib"] * 1024**3
    return {
        "verified_at": utc_now(),
        "coverage": metadata["coverage"],
        "prepared_artifacts": {
            "source_grids": source_grid_count,
            "pair_flags": pair_flag_count,
            "bytes": prepared_bytes,
            "gib": round(prepared_bytes / 1024**3, 6),
            "within_geometry_disk_budget": prepared_bytes <= disk_limit,
        },
        "cell_flags": flag_counts,
        "survey_year_mismatch_tiles": sum(
            tile["survey_year_mismatch"] is True for tile in metadata["tiles"].values()
        ),
        "survey_year_not_comparable_tiles": sum(
            tile["survey_year_mismatch"] is None for tile in metadata["tiles"].values()
        ),
        "receiver_tiles_with_prepared_pairs": sum(
            tile["role"] == "receiver" and tile["status"] == "prepared_pair"
            for tile in metadata["tiles"].values()
        ),
        "seams": {
            "checks": len(seams),
            "all_grid_gaps_zero": all(seam["grid_gap_metres"] == 0 for seam in seams),
        },
        "alignment_references": sorted(metadata["alignment_reference_points"]),
        "memory": memory,
    }


def parse_args() -> argparse.Namespace:
    """Parse the T8 preparation command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "prepare", "verify"))
    parser.add_argument("--tiles", nargs="*")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--batch-name")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--observed-peak-working-set-bytes", type=int)
    return parser.parse_args()


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one plan, preparation or verification operation."""
    metadata = load_or_create_metadata(args.metadata, args.inventory, args.manifest)
    inventory = load_json(args.inventory)
    if args.command == "plan":
        atomic_write_json(args.metadata, metadata)
        return metadata
    if args.command == "verify":
        metadata["all_seams"] = verify_seams(metadata)
        if overall_status(metadata) == "prepared":
            add_named_references(metadata)
        metadata["status"] = overall_status(metadata)
        metadata["verification_summary"] = verification_summary(
            metadata,
            load_json(args.manifest),
            args.observed_peak_working_set_bytes,
        )
        atomic_write_json(args.metadata, metadata)
        return metadata
    selected = sorted(metadata["tiles"]) if args.all else sorted(args.tiles or [])
    if not selected:
        raise ValueError("prepare requires --all or at least one --tiles value")
    if not 1 <= args.workers <= 2:
        raise ValueError("workers must stay within the measured two-worker budget")
    groups = batches(selected, args.batch_size)
    for index, group in enumerate(groups, start=1):
        name = args.batch_name or f"batch-{index:02d}-of-{len(groups):02d}"
        if len(groups) > 1 and args.batch_name:
            name = f"{args.batch_name}-{index:02d}"
        metadata = prepare_tiles(
            group,
            metadata,
            inventory,
            args.metadata,
            args.output,
            args.workers,
            name,
        )
    return metadata


def main() -> None:
    """Run the resumable T8 pipeline and print a compact status."""
    metadata = run(parse_args())
    print(json.dumps({"status": metadata["status"], "coverage": metadata["coverage"]}))


if __name__ == "__main__":
    main()
