"""Source flags survive production preparation, reuse and corrupt-file recovery."""

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import rasterio
from bla_bla_walk.geometry import geometry_settings, sha256_file
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
import prepare_geometry as preparation  # noqa: E402


def test_production_preparation_preserves_source_flags_and_repairs_corruption(
    tmp_path, monkeypatch
):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "config/geometry.json").write_text(json.dumps(geometry_settings()))
    tile = {
        "tile": "2611-1266",
        "role": "receiver",
        "bounds_epsg2056": [2611000, 1266000, 2612000, 1267000],
        "surface": {"status": "catalog_available"},
        "terrain": {"status": "catalog_available"},
    }
    (tmp_path / "data/tile-inventory.json").write_text(json.dumps({"tiles": [tile]}))
    sources = {}
    for kind, cell, size in (("surface", 0.5, 2000), ("terrain", 2, 500)):
        path = tmp_path / f"native-{kind}.tif"
        values = np.full((size, size), 100, dtype="float32")
        if kind == "surface":
            values[0, 0], values[0, 1] = 98.5, 110
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=size,
            width=size,
            count=1,
            dtype="float32",
            crs="EPSG:2056",
            nodata=-9999,
            transform=from_origin(2611000, 1267000, cell, cell),
            compress="DEFLATE",
        ) as dataset:
            dataset.write(values, 1)
        sources[kind] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "url": path.name,
        }
    downloads = []

    def download(asset, target, client):
        shutil.copyfile(tmp_path / asset["url"], target)
        downloads.append(asset["url"])

    monkeypatch.setattr(preparation, "ROOT", tmp_path)
    monkeypatch.setattr(
        preparation, "resolve_asset", lambda tile, kind, client: sources[kind]
    )
    monkeypatch.setattr(preparation, "download_verified", download)
    assert preparation.prepare_geometry(workers=2)
    directory = tmp_path / "data/geometry"
    manifest = json.loads((directory / "manifest.json").read_text())
    flag_path = directory / manifest["pair_flags"]["2611-1266"]["file"]
    assert np.load(flag_path)[0, 0] == 7
    assert not list((directory / ".downloads").glob("*.part"))
    assert len(downloads) == 2
    downloads.clear()
    assert preparation.prepare_geometry(workers=2)
    assert not downloads
    flag_path.write_bytes(b"corrupt")
    assert preparation.prepare_geometry(workers=2)
    assert len(downloads) == 2
    assert np.load(flag_path)[0, 0] == 7
