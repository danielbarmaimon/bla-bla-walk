"""Daily persistence, privacy boundary, partial failures and shared refresh lease."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Event
from unittest.mock import patch

import httpx
import pytest

from bla_bla_walk.adapters.construction import construction_snapshot, fetch_snapshot
from bla_bla_walk.interfaces import ConstructionSnapshot, Provenance

NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


def snapshot(now=NOW):
    return ConstructionSnapshot(
        covers_from=now.date(),
        availability="current",
        provenance=Provenance(
            provider="Official test provider",
            source_url="https://data.bs.ch/",
            attribution="Test",
            licence="CC BY 4.0",
            fixture=False,
            retrieved_at=now,
        ),
    )


def test_daily_cache_survives_restart_and_offline_never_fetches(tmp_path):
    path = tmp_path / "construction.sqlite3"
    with patch(
        "bla_bla_walk.adapters.construction.fetch_snapshot", return_value=snapshot()
    ) as fetch:
        assert construction_snapshot(path=path, now=NOW).availability == "current"
        assert (
            construction_snapshot(path=path, now=NOW + timedelta(hours=1)).availability
            == "current"
        )
        assert construction_snapshot("offline", path, NOW).availability == "stale"
        assert fetch.call_count == 1
    tomorrow = NOW + timedelta(days=1)
    with patch(
        "bla_bla_walk.adapters.construction.fetch_snapshot",
        return_value=snapshot(tomorrow),
    ) as fetch:
        assert construction_snapshot(path=path, now=tomorrow).availability == "current"
        assert fetch.call_count == 1


def test_failed_refresh_preserves_snapshot_and_reserves_the_day(tmp_path):
    path = tmp_path / "construction.sqlite3"
    with patch(
        "bla_bla_walk.adapters.construction.fetch_snapshot", return_value=snapshot()
    ):
        construction_snapshot(path=path, now=NOW)
    with patch(
        "bla_bla_walk.adapters.construction.fetch_snapshot", side_effect=OSError
    ) as fetch:
        stale = construction_snapshot(path=path, now=NOW + timedelta(days=1))
        assert stale.availability == "stale" and stale.provenance.retrieved_at == NOW
        construction_snapshot(path=path, now=NOW + timedelta(days=1, hours=1))
        assert fetch.call_count == 1


def test_empty_offline_does_not_create_cache(tmp_path):
    path = tmp_path / "construction.sqlite3"
    assert construction_snapshot("offline", path, NOW).availability == "missing"
    assert not path.exists()


def test_simultaneous_workers_refresh_once(tmp_path):
    path = tmp_path / "construction.sqlite3"
    started, release = Event(), Event()

    def fetch(now):
        started.set()
        assert release.wait(5)
        return snapshot(now)

    with patch(
        "bla_bla_walk.adapters.construction.fetch_snapshot", side_effect=fetch
    ) as refresh:
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(construction_snapshot, path=path, now=NOW)
            assert started.wait(5)
            assert (
                pool.submit(construction_snapshot, path=path, now=NOW)
                .result()
                .availability
                == "missing"
            )
            release.set()
            assert first.result().availability == "current"
        assert refresh.call_count == 1


@pytest.mark.parametrize(
    "geometry", [None, {"type": "Point", "coordinates": [7.59, 47.55]}]
)
def test_missing_invalid_geometry_rejects_entire_snapshot(geometry):
    project = {"id": 123, "datum_von": "2026-10-01", "datum_bis": "2026-10-31"}
    permit = {
        "begehrenid": 123,
        "datum_von": "2026-10-03",
        "datum_bis": "2026-10-09",
        "geo_shape": geometry,
    }
    with patch(
        "bla_bla_walk.adapters.construction.records", side_effect=[[project], [permit]]
    ):
        with pytest.raises((ValueError, AttributeError)):
            fetch_snapshot(NOW)


def test_fetch_only_admitted_fields_and_clip_project_dates():
    calls = []

    def reply(request):
        calls.append(dict(request.url.params))
        project = {"id": 123, "datum_von": "2026-10-05", "datum_bis": "2026-10-08"}
        permit = {
            "begehrenid": 123,
            "datum_von": "2026-10-01",
            "datum_bis": "2026-10-31",
            "geo_shape": {
                "type": "Polygon",
                "coordinates": [
                    [[7.59, 47.55], [7.60, 47.55], [7.60, 47.56], [7.59, 47.55]]
                ],
            },
        }
        return httpx.Response(
            200,
            json={
                "total_count": 1,
                "results": [project if "100335" in str(request.url) else permit],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(reply))
    with patch("bla_bla_walk.adapters.construction.httpx.Client", return_value=client):
        result = fetch_snapshot(NOW)
    assert result.sites[0].starts_on == date(2026, 10, 5)
    assert result.sites[0].ends_on == date(2026, 10, 8)
    assert [call["select"] for call in calls] == [
        "id,datum_von,datum_bis",
        "begehrenid,geo_shape,datum_von,datum_bis",
    ]
    assert "2026-10-04" in calls[1]["where"]


def test_partial_pagination_is_rejected():
    from bla_bla_walk.adapters.construction import records

    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"total_count": 2, "results": [{}]}
            )
        )
    )
    with client:
        with pytest.raises(ValueError, match="Missing construction records"):
            records(client, "https://data.bs.ch/", "id", 500)


def test_generated_construction_contract_and_endpoint():
    from fastapi.testclient import TestClient

    from bla_bla_walk.adapters.construction import ROOT
    from bla_bla_walk.contract_types import typescript_contract
    from bla_bla_walk.main import app

    schema = ConstructionSnapshot.model_json_schema()
    assert json.loads((ROOT / "src/construction.schema.json").read_text()) == schema
    assert (ROOT / "src/construction-interfaces.ts").read_text() == typescript_contract(
        schema
    )
    with patch(
        "bla_bla_walk.main.construction_snapshot", return_value=snapshot()
    ) as provider:
        response = TestClient(app).get("/api/construction-sites?mode=offline")
    assert response.status_code == 200
    assert (
        ConstructionSnapshot.model_validate(response.json()).covers_from == NOW.date()
    )
    provider.assert_called_once_with("offline")
