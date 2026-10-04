"""Reusable daily typed snapshot cache with cross-process refresh reservations."""

import json
import sqlite3
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx


def daily_snapshot(mode, path, fetch, model, empty, now=None):
    """One refresh attempt per Basel date, even across restarts and processes.

    Offline reads only. A failed refresh preserves the last complete snapshot.
    Refresh happens on first use each day; the browser also checks hourly.
    """
    now = now or datetime.now(UTC)
    day = now.astimezone(ZoneInfo("Europe/Zurich")).date().isoformat()
    if mode != "online" and not path.exists():
        return empty()
    if mode == "online":
        path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(
            path if mode == "online" else f"file:{path.as_posix()}?mode=ro",
            uri=mode != "online",
            timeout=5,
        ) as db:
            if mode == "online":
                db.execute(
                    "CREATE TABLE IF NOT EXISTS snapshot "
                    "(id INTEGER PRIMARY KEY, attempted TEXT, payload TEXT)"
                )
                db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT attempted, payload FROM snapshot WHERE id=1"
            ).fetchone()
            raw = json.loads(row[1]) if row and row[1] else {}
            refreshed = False
            saved = (
                model.model_validate(raw.get("data", raw))
                if row and row[1]
                else empty()
            )
            if mode == "online" and (not row or row[0] != day):
                # Reserve before HTTP work; other workers use saved data.
                db.execute(
                    "INSERT INTO snapshot VALUES(1,?,?) ON CONFLICT(id) "
                    "DO UPDATE SET attempted=excluded.attempted",
                    (day, row[1] if row else None),
                )
                db.commit()
                try:
                    saved = fetch(now)
                    refreshed = True
                    db.execute(
                        "UPDATE snapshot SET payload=? WHERE id=1",
                        (
                            json.dumps(
                                {
                                    "retrieved_at": now.isoformat(),
                                    "data": saved.model_dump(mode="json"),
                                }
                            ),
                        ),
                    )
                    db.commit()
                except (
                    httpx.HTTPError,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    AttributeError,
                ):
                    pass
            timestamp = raw.get("retrieved_at") or raw.get("provenance", {}).get(
                "retrieved_at"
            )
            retrieved = datetime.fromisoformat(timestamp) if timestamp else None
            if refreshed:
                retrieved = now
            current = (
                mode == "online"
                and retrieved
                and retrieved.astimezone(ZoneInfo("Europe/Zurich")).date().isoformat()
                == day
                and retrieved <= now
            )
            return saved.model_copy(
                update={
                    "availability": "current"
                    if current
                    else "stale"
                    if retrieved
                    else "missing"
                }
            )
    except (sqlite3.Error, OSError, ValueError):
        return empty()
