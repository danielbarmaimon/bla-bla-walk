"""Forecast fallback is a licensed bounded city query, with offline saved status."""

from datetime import UTC, datetime
from unittest.mock import patch

import httpx
from bla_bla_walk.adapters import palette_forecast as adapter
from bla_bla_walk.main import app
from fastapi.testclient import TestClient


def test_forecast_query_units_and_saved_status(tmp_path):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "daily_units": {"temperature_2m_mean": "°C"},
                "daily": {"time": ["2026-10-04"], "temperature_2m_mean": [8.0]},
            },
        )

    transport = httpx.MockTransport(respond)
    original = httpx.Client
    with patch.object(
        adapter.httpx,
        "Client",
        side_effect=lambda **kw: original(transport=transport, **kw),
    ):
        result = adapter.fetch_forecast(datetime(2026, 10, 4, tzinfo=UTC))
    assert result.availability == "current"
    assert float(requests[0].url.params["latitude"]) == 47.5596
    assert "route" not in requests[0].url.params
    target = tmp_path / "forecast.json"
    target.write_text(result.model_dump_json(), encoding="utf-8")
    with patch.object(adapter, "fetch_forecast", side_effect=AssertionError("network")):
        saved = adapter.palette_forecast("offline", target)
    assert saved.availability == "stale"
    assert saved.provenance.retrieved_at == result.provenance.retrieved_at
    assert adapter.saved_forecast(tmp_path / "missing").availability == "missing"


def test_real_sensor_and_forecast_offline_apis_make_zero_http():
    with patch(
        "httpx.HTTPTransport.handle_request", side_effect=AssertionError("external")
    ) as transport:
        client = TestClient(app)
        for mode in ("fixture", "offline"):
            reply = client.get(f"/api/route-temperatures?mode={mode}")
            assert reply.status_code == 200
            assert all(
                not point["provenance"]["fixture"] for point in reply.json()["features"]
            )
        assert client.get("/api/palette-forecast?mode=offline").status_code == 200
    transport.assert_not_called()
