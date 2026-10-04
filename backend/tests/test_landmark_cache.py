"""Citywide acquisition retains public place fields; daily and offline reuse."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx
import pytest

from bla_bla_walk.adapters.landmarks import fetch_landmarks, landmarks

NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


def payload():
    return {
        "elements": [
            {
                "type": "node",
                "id": 123,
                "lon": 7.59,
                "lat": 47.55,
                "tags": {
                    "name": "Mapped test church",
                    "amenity": "place_of_worship",
                    "phone": "excluded-contact-field",
                    "contact:email": "excluded-contact-field",
                },
            },
            {
                "type": "way",
                "id": 124,
                "center": {"lon": 8, "lat": 48},
                "tags": {"name": "Outside canton", "historic": "monument"},
            },
        ]
    }


def test_sanitized_names_positions_and_sources_only():
    calls = []

    def reply(request):
        calls.append(request.content.decode())
        return httpx.Response(200, json=payload())

    client = httpx.Client(transport=httpx.MockTransport(reply))
    with patch("bla_bla_walk.adapters.landmarks.httpx.Client", return_value=client):
        result = fetch_landmarks(NOW)
    assert len(result.features) == 1
    assert result.features[0].label == "Mapped test church"
    assert result.features[0].provenance.source_url.endswith("/node/123")
    assert "excluded-contact-field" not in result.model_dump_json()
    assert "place_of_worship" in calls[0] and "historic" in calls[0]


def test_landmark_cache_daily_reuse_offline_and_stale_failure(tmp_path):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload())
        )
    )
    with patch("bla_bla_walk.adapters.landmarks.httpx.Client", return_value=client):
        data = fetch_landmarks(NOW)
    path = tmp_path / "landmarks.sqlite3"
    with patch(
        "bla_bla_walk.adapters.landmarks.fetch_landmarks", return_value=data
    ) as fetch:
        assert len(landmarks(path=path, now=NOW).features) == 1
        assert (
            landmarks(path=path, now=NOW + timedelta(hours=1)).availability == "current"
        )
        saved = landmarks("offline", path, NOW)
        assert (
            saved.availability == "stale" and saved.features[0].availability == "stale"
        )
        assert fetch.call_count == 1
    with patch("bla_bla_walk.adapters.landmarks.fetch_landmarks", side_effect=OSError):
        assert landmarks(path=path, now=NOW + timedelta(days=1)).availability == "stale"


def test_overpass_remark_is_not_a_complete_snapshot():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={**payload(), "remark": "Query timed out"}
            )
        )
    )
    with patch("bla_bla_walk.adapters.landmarks.httpx.Client", return_value=client):
        with pytest.raises(ValueError, match="Incomplete"):
            fetch_landmarks(NOW)
