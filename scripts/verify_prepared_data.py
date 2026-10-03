"""Verify local offline resources and publish a small shareable evidence summary."""

import json
import sys
from collections import Counter
from datetime import UTC, datetime

import numpy as np
import rasterio
from prepare_geometry import ROOT, sha256_file, write_json

sys.path.insert(0, str(ROOT / "backend"))
from bla_bla_walk.geometry import geometry_settings  # noqa: E402
from bla_bla_walk.shade_geometry import load_pair_flags  # noqa: E402
from bla_bla_walk.snapshots import offline_snapshot  # noqa: E402


def verify_prepared_data():
    """Check every output hash/grid and image hash; keep source data local."""
    settings = geometry_settings()
    directory = ROOT / settings["geometry_directory"]
    geometry = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    basemap_path = ROOT / ".cache/basemap"
    basemap = json.loads((basemap_path / "manifest.json").read_text(encoding="utf-8"))
    inventory = json.loads(
        (ROOT / "data/tile-inventory.json").read_text(encoding="utf-8")
    )
    tiles = {tile["tile"]: tile for tile in inventory["tiles"]}
    if not geometry.get("complete_available_inventory") or not basemap.get("complete"):
        raise ValueError("Offline preparation is not complete")
    if geometry["settings"] != settings:
        raise ValueError("Local geometry settings differ from current configuration")
    unknown = Counter()
    counts = Counter()
    source_bytes = Counter()
    prepared_bytes = Counter()
    for record in geometry["assets"].values():
        path = directory / record["file"]
        if sha256_file(path) != record["sha256"]:
            raise ValueError(f"Prepared checksum mismatch: {path.name}")
        with rasterio.open(path) as grid:
            if (
                grid.shape != (1000, 1000)
                or grid.res != (1, 1)
                or grid.scales != (2,)
                or grid.offsets != (0,)
                or grid.nodata != -32768
                or grid.dtypes != ("int16",)
                or grid.crs.to_epsg() != 2056
                or list(grid.bounds) != tiles[record["tile"]]["bounds_epsg2056"]
            ):
                raise ValueError(f"Prepared grid/scale mismatch: {path.name}")
            missing = int(np.count_nonzero(grid.read(1) == -32768))
            if missing != record["unknown_cells"]:
                raise ValueError(f"Prepared unknown-count mismatch: {path.name}")
        kind = record["kind"]
        counts[kind] += 1
        unknown[kind] += missing
        source_bytes[kind] += record["source"]["bytes"]
        prepared_bytes[kind] += path.stat().st_size
    for key, record in basemap["tiles"].items():
        if sha256_file(basemap_path / key) != record["sha256"]:
            raise ValueError(f"Basemap checksum mismatch: {key}")
    flag_bytes = 0
    for tile_id, record in geometry.get("pair_flags", {}).items():
        if record.get("preparation_version") != geometry["preparation_version"]:
            raise ValueError("Source flags have an outdated preparation version")
        path = directory / record["file"]
        if not path.is_file():
            raise ValueError("Prepared source flags are missing")
        load_pair_flags(directory, geometry, tiles[tile_id]["bounds_epsg2056"])
        flag_bytes += path.stat().st_size
    snapshot = offline_snapshot()
    summary = {
        "checked_at": datetime.now(UTC).isoformat(),
        "encoding_config": "config/geometry.json",
        "geometry": {
            "preparation_version": geometry["preparation_version"],
            "inventory_sha256": geometry["inventory_sha256"],
            "available_assets_prepared": dict(counts),
            "all_available_assets_prepared": True,
            "source_download_bytes": dict(source_bytes),
            "prepared_raster_bytes": dict(prepared_bytes),
            "prepared_raster_total_bytes": sum(prepared_bytes.values()),
            "source_pair_flags_verified": len(geometry.get("pair_flags", {})),
            "source_pair_flag_bytes": flag_bytes,
            "manifest_bytes": (directory / "manifest.json").stat().st_size,
            "unknown_cells_in_available_rasters": dict(unknown),
            "missing_inventory_assets": geometry["gaps"],
            "validation": (
                "All output hashes, shapes, bounds, CRS, scales and NoData counts "
                "checked; this does not validate shade, bridges, scene consistency "
                "or survey alignment."
            ),
        },
        "basemap": {
            "tiles_verified": len(basemap["tiles"]),
            "image_bytes": basemap["bytes"],
            "manifest_bytes": (basemap_path / "manifest.json").stat().st_size,
            "downloaded_at": basemap["downloaded_at"],
            "configuration": "config/basemap.json",
        },
        "provider_snapshot": {
            "saved_at": snapshot.generated_at.isoformat(),
            "layers": {layer.id: len(layer.features) for layer in snapshot.layers},
            "bytes": (ROOT / ".cache/provider-snapshot.json").stat().st_size,
            "status": (
                "Offline saved data; timestamps and unknowns retained, "
                "previously current entries stale"
            ),
        },
    }
    write_json(ROOT / "data/preparation-summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    verify_prepared_data()
