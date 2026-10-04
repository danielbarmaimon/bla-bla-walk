"""Sanitized daily construction snapshot shared across server processes."""

import hashlib
import json
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from shapely.geometry import mapping, shape

from ..daily_cache import daily_snapshot
from ..interfaces import ConstructionSite, ConstructionSnapshot, Provenance

ROOT = Path(__file__).resolve().parents[3]
SETTINGS = json.loads((ROOT / "config/construction-sites.json").read_text())
PATH = ROOT / ".cache/construction.sqlite3"


def records(client, endpoint, select, limit, where=None):
    """Require complete bounded pagination; import only admitted fields."""
    total = None
    result = []
    for offset in range(0, limit, 100):
        params = {"select": select, "limit": 100, "offset": offset}
        if where:
            params["where"] = where
        with client.stream("GET", endpoint, params=params) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > SETTINGS["max_response_bytes"]:
                    raise ValueError("Construction response too large")
        payload = json.loads(content)
        count = payload["total_count"]
        if count > limit or (total is not None and count != total):
            raise ValueError("Incomplete construction pagination")
        total = count
        batch = payload["results"]
        if len(batch) != min(100, total - offset):
            raise ValueError("Missing construction records")
        result.extend(batch)
        if len(result) == total:
            return result
    raise ValueError("Construction record limit exceeded")


def fetch_snapshot(now):
    day = now.astimezone(ZoneInfo("Europe/Zurich")).date()
    with httpx.Client(timeout=SETTINGS["timeout_seconds"]) as client:
        projects = records(
            client,
            SETTINGS["projects_endpoint"],
            "id,datum_von,datum_bis",
            SETTINGS["max_projects"],
            f"datum_bis >= date'{day}'",
        )
        intervals = {
            str(int(p["id"])): (
                date.fromisoformat(p["datum_von"]),
                date.fromisoformat(p["datum_bis"]),
            )
            for p in projects
        }
        permits = (
            records(
                client,
                SETTINGS["permits_endpoint"],
                "begehrenid,geo_shape,datum_von,datum_bis",
                SETTINGS["max_records"],
                f"begehrenid in ({','.join(intervals)}) AND datum_bis >= date'{day}'",
            )
            if intervals
            else []
        )
    sites = {}
    for permit in permits:
        project_id = str(int(permit["begehrenid"]))
        start, end = intervals[project_id]
        start = max(start, date.fromisoformat(permit["datum_von"]))
        end = min(end, date.fromisoformat(permit["datum_bis"]))
        if start > end or end < day:
            continue
        geometry = permit["geo_shape"]
        polygon = shape(geometry.get("geometry", geometry))
        if (
            polygon.is_empty
            or not polygon.is_valid
            or polygon.geom_type not in ("Polygon", "MultiPolygon")
        ):
            raise ValueError("Invalid construction polygon")
        for part in polygon.geoms if polygon.geom_type == "MultiPolygon" else [polygon]:
            data = mapping(part)
            identity = hashlib.sha256(
                json.dumps(
                    [project_id, str(start), str(end), data], sort_keys=True
                ).encode()
            ).hexdigest()[:20]
            sites[identity] = ConstructionSite(
                id=identity,
                project_id=project_id,
                starts_on=start,
                ends_on=end,
                geometry=data,
            )
    return ConstructionSnapshot(
        sites=list(sites.values()),
        availability="current",
        covers_from=day,
        provenance=Provenance(
            provider="Basel-Stadt construction projects and permits",
            source_url="https://data.bs.ch/explore/dataset/100018/",
            attribution=(
                "Tiefbauamt / Geodaten Kanton Basel-Stadt · "
                "© OpenStreetMap contributors"
            ),
            licence="CC BY 4.0 + OpenStreetMap",
            fixture=False,
            retrieved_at=now,
        ),
    )


def construction_snapshot(mode="online", path=PATH, now=None):
    """Reuse the typed daily cache; only valid full snapshots replace saved data."""
    return daily_snapshot(
        mode, path, fetch_snapshot, ConstructionSnapshot, ConstructionSnapshot, now
    )
