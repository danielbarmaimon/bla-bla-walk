"""Download pinned Basel height assets and prepare compact local geometry."""

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from bla_bla_walk.geometry import (  # noqa: E402
    compact_pair_flags,
    geometry_settings,
    prepare_raster,
    read_heights,
    sha256_file,
)


def write_json(path, value):
    """Publish manifest checkpoints atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    # Windows file indexing/antivirus may briefly hold an existing checkpoint.
    for attempt in range(7):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 6:
                raise
            time.sleep(0.05 * (attempt + 1))


def checksum_digest(checksum):
    """Accept the provider's SHA-256 multihash and reject other algorithms."""
    if (
        not isinstance(checksum, str)
        or len(checksum) != 68
        or not checksum.lower().startswith("1220")
    ):
        raise ValueError("Expected a SHA-256 catalogue multihash")
    return checksum[4:].lower()


def resolve_asset(tile, kind, client):
    """Keep surface pins; resolve the same terrain year/tile at native 2m."""
    original = tile[kind]
    if kind == "surface":
        return {
            "url": original["asset_url"],
            "sha256": checksum_digest(original["catalog_checksum"]),
            "bytes": original["header"]["asset_bytes"],
            "item_id": original["item_id"],
        }
    url = original["asset_url"].replace("_0.5_2056_", "_2_2056_")
    item_url = (
        "https://data.geo.admin.ch/api/stac/v1/collections/"
        "ch.swisstopo.swissalti3d/items/" + original["item_id"]
    )
    response = client.get(item_url)
    response.raise_for_status()
    item = response.json()
    asset = next((a for a in item["assets"].values() if a.get("href") == url), None)
    if asset is None:
        raise ValueError("Pinned native 2m terrain asset not present in catalogue")
    checksum = asset.get("checksum:multihash") or asset.get("file:checksum")
    head = client.head(url)
    head.raise_for_status()
    return {
        "url": url,
        "sha256": checksum_digest(checksum),
        "bytes": int(head.headers["content-length"]),
        "item_id": original["item_id"],
    }


def download_verified(asset, target, client):
    """Resume an interrupted transfer, then verify size and catalogue checksum."""
    size = target.stat().st_size if target.exists() else 0
    if size > asset["bytes"]:
        raise ValueError("Partial download exceeds expected source size")
    if size < asset["bytes"]:
        headers = {"Range": f"bytes={size}-"} if size else {}
        with client.stream("GET", asset["url"], headers=headers) as response:
            response.raise_for_status()
            append = size > 0 and response.status_code == 206
            if append and not response.headers.get("content-range", "").startswith(
                f"bytes {size}-"
            ):
                raise ValueError("Invalid resume Content-Range")
            with target.open("ab" if append else "wb") as output:
                for block in response.iter_bytes(1024 * 1024):
                    output.write(block)
                    if output.tell() > asset["bytes"]:
                        raise ValueError("Source exceeds catalogue size")
    if target.stat().st_size != asset["bytes"]:
        raise ValueError("Incomplete source download")
    if sha256_file(target) != asset["sha256"]:
        # Remove only this task's failed temporary file inside its fixed workspace.
        target.unlink()
        raise ValueError("Source checksum mismatch; discarded failed download")


def prepare_one(tile, kind, directory, previous, version):
    """Retry network failures and reuse only verified matching prepared files."""
    key = f"{tile['tile']}-{kind}"
    target = directory / f"{key}.tif"
    record = previous.get(key)
    partial = directory / ".downloads" / f"{key}.part"
    flag_path = directory / f"{tile['tile']}-flags.npy"
    other_kind = "terrain" if kind == "surface" else "surface"
    source_evidence_available = (
        tile[other_kind]["status"] != "catalog_available"
        or (
            partial.is_file()
            and record
            and sha256_file(partial) == record["source"]["sha256"]
        )
        or (
            flag_path.is_file()
            and record
            and record.get("pair_flags_sha256") == sha256_file(flag_path)
        )
    )
    if (
        record
        and record.get("preparation_version") == version
        and target.exists()
        and sha256_file(target) == record["sha256"]
        and source_evidence_available
    ):
        return key, record
    partial.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                asset = resolve_asset(tile, kind, client)
                download_verified(asset, partial, client)
            record = prepare_raster(partial, target, tile, kind)
            record.update(
                source=asset,
                tile=tile["tile"],
                kind=kind,
                role=tile["role"],
                preparation_version=version,
                survey_year_mismatch=tile.get("survey_year_mismatch", False),
            )
            # This path is constructed within the fixed geometry directory only.
            # Keep the verified source until its pair's source flags are saved.
            if tile[other_kind]["status"] != "catalog_available":
                partial.unlink()
            return key, record
        except (httpx.HTTPError, OSError, ValueError) as error:
            if attempt == 2:
                raise RuntimeError(f"{key}: {error}") from error
            time.sleep(attempt + 1)


def prepare_pair_flags(tile_id, directory, assets, version):
    """Preserve source evidence before temporary native source files disappear."""
    records = [assets.get(f"{tile_id}-{kind}") for kind in ("surface", "terrain")]
    paths = [
        directory / ".downloads" / f"{tile_id}-{kind}.part"
        for kind in ("surface", "terrain")
    ]
    if not all(
        record and record["preparation_version"] == version for record in records
    ):
        return None
    if not all(path.is_file() for path in paths):
        return None
    if any(
        sha256_file(path) != record["source"]["sha256"]
        for path, record in zip(paths, records)
    ):
        raise ValueError("Source flag input checksum mismatch")
    flags = compact_pair_flags(*(read_heights(path) for path in paths))
    target = directory / f"{tile_id}-flags.npy"
    temporary = target.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        np.save(stream, flags, allow_pickle=False)
    temporary.replace(target)
    record = {
        "file": target.name,
        "sha256": sha256_file(target),
        "bytes": target.stat().st_size,
        "preparation_version": version,
    }
    for asset in records:
        asset["pair_flags_sha256"] = record["sha256"]
    return record


def prepare_geometry(workers=2, limit=None):
    """Checkpoint each asset; preserve inventory gaps instead of synthesising data."""
    inventory_path = ROOT / "data/tile-inventory.json"
    inventory = json.loads(inventory_path.read_text())
    settings = geometry_settings()
    directory = ROOT / settings["geometry_directory"]
    directory.mkdir(parents=True, exist_ok=True)
    # Increment the algorithm revision when encoding/resampling semantics change.
    # Formatting and documentation changes must not trigger full re-downloads.
    version = hashlib.sha256(
        b"compact-height-pipeline-revision-2-source-subcell-flags"
        + json.dumps(settings, sort_keys=True).encode()
        + inventory_path.read_bytes()
    ).hexdigest()
    manifest_path = directory / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    assets = old.get("assets", {})
    jobs = [
        (tile, kind)
        for tile in inventory["tiles"]
        for kind in ("surface", "terrain")
        if tile[kind]["status"] == "catalog_available"
    ]
    selected = jobs[:limit] if limit else jobs
    manifest = {
        "settings": settings,
        "preparation_version": version,
        "inventory_sha256": sha256_file(inventory_path),
        "attribution": "© swisstopo",
        "assets": assets,
        "pair_flags": old.get("pair_flags", {}),
        "gaps": [
            {"tile": tile["tile"], "role": tile["role"], "kind": kind}
            for tile in inventory["tiles"]
            for kind in ("surface", "terrain")
            if tile[kind]["status"] != "catalog_available"
        ],
        "errors": [],
        "expected_assets": len(jobs),
    }
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(prepare_one, tile, kind, directory, assets, version)
            for tile, kind in selected
        ]
        for index, future in enumerate(as_completed(futures), 1):
            flags = None
            try:
                key, record = future.result()
                assets[key] = record
                tile_id = record["tile"]
                flags = prepare_pair_flags(tile_id, directory, assets, version)
                if flags:
                    manifest["pair_flags"][tile_id] = flags
                print(
                    f"[{index}/{len(selected)}] {key}: {record['bytes']} bytes",
                    flush=True,
                )
            except (
                RuntimeError,
                OSError,
                ValueError,
                KeyError,
                StopIteration,
            ) as error:
                manifest["errors"].append(str(error))
                print(str(error), file=sys.stderr, flush=True)
            manifest["prepared_at"] = datetime.now(UTC).isoformat()
            write_json(manifest_path, manifest)
            if flags:
                for kind in ("surface", "terrain"):
                    (directory / ".downloads" / f"{tile_id}-{kind}.part").unlink(
                        missing_ok=True
                    )
                flags = None
    current = [r for r in assets.values() if r["preparation_version"] == version]
    manifest["complete_available_inventory"] = (
        len(current) == len(jobs)
        and not manifest["errors"]
        and all(
            manifest["pair_flags"].get(tile["tile"], {}).get("preparation_version")
            == version
            for tile in inventory["tiles"]
            if all(
                tile[kind]["status"] == "catalog_available"
                for kind in ("surface", "terrain")
            )
        )
    )
    manifest["source_bytes"] = sum(r["source"]["bytes"] for r in current)
    manifest["prepared_bytes"] = sum(r["bytes"] for r in current) + sum(
        record["bytes"]
        for record in manifest["pair_flags"].values()
        if record.get("preparation_version") == version
    )
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in (
                    "complete_available_inventory",
                    "source_bytes",
                    "prepared_bytes",
                    "errors",
                )
            }
        ),
        flush=True,
    )
    return not manifest["errors"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--limit", type=int, help="Prepare a bounded validation batch")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    raise SystemExit(0 if prepare_geometry(args.workers, args.limit) else 1)
