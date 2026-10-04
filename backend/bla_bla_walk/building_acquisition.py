"""Resumable sanitized OSM building acquisition and saved-cache validation."""

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def cached_buildings(directory, polygon):
    """Reuse only intact, sanitized, same-coverage output; retain source dates."""
    path = directory / "manifest.json"
    if not path.is_file():
        return None
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if (
            urlsplit(metadata.get("endpoint", "")).hostname == "overpass.osm.ch"
            and metadata.get("coverage_constraint") is None
        ):
            return None
        filename = metadata["file"]
        if Path(filename).name != filename or metadata["coverage"] != polygon:
            return None
        content = (directory / filename).read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        if checksum != metadata["sha256"] or checksum != metadata["version"]:
            return None
        features = json.loads(content)
        allowed = {"id", "geometry", "height_m", "unresolved_geometry"}
        if len(features) != metadata["feature_count"] or any(
            set(feature) != allowed for feature in features
        ):
            return None
        if datetime.fromisoformat(metadata["retrieved_at"]).utcoffset() is None:
            return None
        if metadata.get("provider_timestamp") is not None:
            if (
                datetime.fromisoformat(metadata["provider_timestamp"]).utcoffset()
                is None
            ):
                return None
        return metadata
    except (OSError, ValueError, KeyError, TypeError):
        return None


def building_batch(
    client, endpoint, query, directory, refresh, sanitize, method="POST"
):
    """Checkpoint sanitized query output so a timeout can resume acquisition."""
    identity = endpoint + "\n" + query
    if method != "POST":
        identity = method + "\n" + identity
    key = hashlib.sha256(identity.encode()).hexdigest()
    path = directory / ".batches" / f"{key}.json"
    if path.is_file() and not refresh:
        try:
            batch = json.loads(path.read_text(encoding="utf-8"))
            content = json.dumps(batch["features"], separators=(",", ":")).encode()
            allowed = {"id", "geometry", "height_m", "unresolved_geometry"}
            if (
                "provider_timestamp" in batch
                and datetime.fromisoformat(batch["retrieved_at"]).utcoffset()
                is not None
                and hashlib.sha256(content).hexdigest() == batch["sha256"]
                and all(set(feature) == allowed for feature in batch["features"])
            ):
                return batch
        except (OSError, ValueError, KeyError, TypeError):
            print("Invalid saved building batch; requesting a verified replacement")
    response = (
        client.get(endpoint, params={"data": query})
        if method == "GET"
        else client.post(endpoint, data={"data": query})
    )
    response.raise_for_status()
    data = response.json()
    if data.get("remark") or "elements" not in data:
        raise ValueError("Building query was incomplete")
    features = sanitize(data["elements"])
    content = json.dumps(features, separators=(",", ":")).encode()
    batch = {
        "features": features,
        "sha256": hashlib.sha256(content).hexdigest(),
        "provider_timestamp": data.get("osm3s", {}).get("timestamp_osm_base"),
        "retrieved_at": datetime.now(UTC).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    partial.write_text(json.dumps(batch) + "\n", encoding="utf-8")
    partial.replace(path)
    return batch


def acquire_buildings(
    endpoint,
    query,
    polygon,
    directory,
    *,
    sanitize,
    refresh=False,
    method="POST",
    coverage_constraint=None,
):
    """Publish a new checksum-named cache only after complete sanitized retrieval."""
    parsed = urlsplit(endpoint)
    if method not in ("GET", "POST"):
        raise ValueError("Building retrieval supports only GET or POST")
    if parsed.hostname == "overpass.osm.ch" and coverage_constraint is None:
        raise ValueError(
            "Regional Swiss source requires a verified coverage constraint"
        )
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use a public HTTPS endpoint without credentials or query")
    with httpx.Client(
        timeout=120,
        follow_redirects=True,
        headers={
            "User-Agent": "bla-bla-walk/0.1 (https://github.com/danielbarmaimon/bla-bla-walk)"
        },
    ) as client:
        queries = [query] if isinstance(query, str) else query
        if not queries:
            raise ValueError("At least one building query is required")
        collected, timestamps, retrievals = {}, [], []
        for index, part in enumerate(queries):
            batch = building_batch(
                client, endpoint, part, directory, refresh, sanitize, method
            )
            for feature in batch["features"]:
                if feature["id"] in collected and collected[feature["id"]] != feature:
                    raise ValueError("Building changed between acquisition batches")
                collected[feature["id"]] = feature
            timestamp = batch["provider_timestamp"]
            if timestamp:
                timestamps.append(timestamp)
            retrievals.append(batch["retrieved_at"])
            print(f"Building batch {index + 1}/{len(queries)} complete", flush=True)
    features = [collected[key] for key in sorted(collected)]
    valid_timestamps, unparsed_timestamps = [], []
    for timestamp in timestamps:
        try:
            if datetime.fromisoformat(timestamp).utcoffset() is None:
                raise ValueError("Unzoned provider timestamp")
            valid_timestamps.append(timestamp)
        except (ValueError, TypeError):
            unparsed_timestamps.append(timestamp)
    content = json.dumps(features, separators=(",", ":")).encode()
    version = hashlib.sha256(content).hexdigest()
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"buildings-{version}.json"
    partial = directory / f"{filename}.part"
    partial.write_bytes(content)
    partial.replace(directory / filename)
    metadata = {
        "version": version,
        "sha256": version,
        "file": filename,
        "coverage": polygon,
        "retrieved_at": min(retrievals),
        "prepared_at": datetime.now(UTC).isoformat(),
        "provider_timestamp": (
            min(valid_timestamps)
            if valid_timestamps and not unparsed_timestamps
            else None
        ),
        "provider_timestamps": sorted(set(timestamps)),
        "query_count": len(queries),
        "attribution": (
            "© OpenStreetMap contributors · ODbL 1.0; roof heights © swisstopo"
        ),
        "endpoint": endpoint,
        "feature_count": len(features),
        "unresolved_geometries": sum(f["unresolved_geometry"] for f in features),
        "scope": (
            "Building-only flat-ground approximation; no tree shadows, terrain "
            "relief, measured cooling or verified walking ground"
        ),
    }
    if unparsed_timestamps:
        metadata["unparsed_provider_timestamps"] = sorted(set(unparsed_timestamps))
        metadata["attribution"] += "; Provider source date is unknown."
    if method != "POST":
        metadata["request_method"] = method
    if coverage_constraint is not None:
        metadata["coverage_constraint"] = coverage_constraint
        metadata["attribution"] += (
            "; Regional source: admitted only inside the verified Basel-Stadt "
            "boundary and requested halo. Cross-boundary rays remain unknown."
        )
    partial = directory / "manifest.json.part"
    partial.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    partial.replace(directory / "manifest.json")
    return metadata


def building_queries(bounds, maximum_degrees):
    """Partition the complete requested rectangle into bounded sequential queries."""
    if not math.isfinite(maximum_degrees) or maximum_degrees <= 0:
        raise ValueError("Positive finite building query cell size is required")
    south, west, north, east = bounds
    rows = max(1, math.ceil((north - south) / maximum_degrees))
    columns = max(1, math.ceil((east - west) / maximum_degrees))
    queries = []
    for row in range(rows):
        bottom, top = (
            south + (north - south) * row / rows,
            south + (north - south) * (row + 1) / rows,
        )
        for col in range(columns):
            left, right = (
                west + (east - west) * col / columns,
                west + (east - west) * (col + 1) / columns,
            )
            bbox = f"{bottom},{left},{top},{right}"
            queries.append(
                f'[out:json][timeout:30];(way["building"]({bbox});'
                f'relation["building"]({bbox});way["building:part"]({bbox});'
                f'relation["building:part"]({bbox}););out geom;'
            )
    return queries
