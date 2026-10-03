"""T6 exact-time API, cached rescoring and truthful failure/eligibility boundaries."""

import base64
import time
from datetime import UTC, datetime, timedelta
from threading import Event
from unittest.mock import patch

import pytest
from bla_bla_walk import main
from bla_bla_walk.comparison_service import ComparisonService
from bla_bla_walk.interfaces import (
    ComparisonRequest,
    ShadeMetadata,
    ShadeResponse,
)
from fastapi.testclient import TestClient


class LocalShade:
    def __init__(self):
        self.calls = []
        self.version = "synthetic-validation-only"
        self.gate = None
        self.broken = False

    def context(self, request):
        if self.broken:
            raise OSError("Missing local inputs")
        return (self.version,)

    def respond(self, request):
        if self.gate is not None:
            self.gate.wait(5)
        self.calls.append(request)
        west, south, east, north = request.bounds
        result = ShadeResponse(
            bounds=request.bounds,
            width=2,
            height=2,
            states=base64.b64encode(bytes([2, 2, 2, 2])).decode(),
            counts={"unknown": 0, "sunlit": 0, "shaded": 4, "night": 0},
            shade=ShadeMetadata(
                requested_time=request.requested_time,
                effective_time=request.requested_time,
                geometry_version=self.version,
                resolution_m=1,
            ),
            availability="approximate",
            model="building-shadow-approximation",
            explanation="Synthetic test only",
        )
        return result, False


@pytest.fixture
def journey(monkeypatch):
    shade = LocalShade()
    service = ComparisonService(shade)
    monkeypatch.setattr(main, "comparison_service", service)
    yield TestClient(main.app), service, shade
    if shade.gate:
        shade.gate.set()
    service.close()


def start_ready(client, departure="2026-10-03T12:00:00Z"):
    response = client.post("/api/comparison", json={"departure_time": departure})
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    for _ in range(300):
        result = client.get(f"/api/comparison/{job_id}")
        assert result.headers["cache-control"] == "no-store"
        job = result.json()
        if job["status"] != "running":
            assert job["status"] == "ready", job
            return job
        time.sleep(0.01)
    pytest.fail("Local synthetic calculation did not complete")


def test_exact_times_eligibility_and_rescoring_without_network(journey):
    client, service, shade = journey
    with patch(
        "httpx.HTTPTransport.handle_request", side_effect=AssertionError("HTTP")
    ):
        job = start_ready(client)
        assert len(job["evidence"]) == 2
        assert len(shade.calls) == job["completed_samples"] == job["total_samples"]
        for evidence in job["evidence"]:
            assert evidence["access_state"] == "unknown"
            assert evidence["water"]["state"] == "unknown"
            assert evidence["shaded_metres"] == pytest.approx(
                evidence["distance_metres"]
            )
            samples = evidence["samples"]
            assert all(
                s["metadata"]["requested_time"]
                == s["requested_time"]
                == s["metadata"]["effective_time"]
                for s in samples
            )
            assert samples[0]["requested_time"] < samples[-1]["requested_time"]
        assert all(
            v["manual_choices"] == [] and v["winner"] is None
            for v in job["choices"].values()
        )
        previous = len(shade.calls)
        response = client.post(
            f"/api/comparison/{job['id']}/rescore",
            json={
                "weights": {"shade": 0, "duration": 0, "water": 0},
                "extra_time_limit_minutes": 5,
            },
        )
        assert response.status_code == 200
        assert len(shade.calls) == previous
        duplicate = client.post(
            "/api/comparison", json={"departure_time": "2026-10-03T14:00:00+02:00"}
        )
        assert duplicate.json()["id"] == job["id"]
        assert len(shade.calls) == previous


def test_source_changes_invalidate_cached_credit(journey):
    client, service, shade = journey
    job = start_ready(client)
    shade.version = "changed-inputs"
    result = client.get(f"/api/comparison/{job['id']}").json()
    assert result["status"] == "failed"
    assert result["evidence"] == [] and result["choices"] == {}
    shade.broken = True
    assert (
        client.post(
            "/api/comparison", json={"departure_time": "2026-10-03T12:00:00Z"}
        ).status_code
        == 503
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"departure_time": "2026-10-03T12:00:00"},
        {"departure_time": "invalid"},
        {"departure_time": "2026-10-03T12:00:00Z", "access_state": "checked_open"},
        {"departure_time": "2026-10-03T12:00:00Z", "stops": {"unknown-route": []}},
        {
            "departure_time": "2026-10-03T12:00:00Z",
            "stops": {"demo-route-a": [{"at_metres": 999999, "minutes": 2}]},
        },
    ],
)
def test_bad_requests_cannot_override_server_evidence(journey, payload):
    assert journey[0].post("/api/comparison", json=payload).status_code == 422


def test_bounded_worker_and_cancellation(journey):
    client, service, shade = journey
    shade.gate = Event()
    first = client.post(
        "/api/comparison", json={"departure_time": "2026-10-03T12:00:00Z"}
    ).json()
    assert (
        client.post(
            "/api/comparison", json={"departure_time": "2026-10-03T12:00:00Z"}
        ).json()["id"]
        == first["id"]
    )
    assert (
        client.post(
            "/api/comparison", json={"departure_time": "2026-10-03T13:00:00Z"}
        ).status_code
        == 503
    )
    assert client.delete(f"/api/comparison/{first['id']}").status_code == 204
    shade.gate.set()
    for _ in range(100):
        result = client.get(f"/api/comparison/{first['id']}").json()
        if result["status"] == "failed":
            break
        time.sleep(0.01)
    assert result["status"] == "failed"
    assert not result["choices"]


def test_new_departure_and_stop_plan_require_new_samples(journey):
    client, service, shade = journey
    first = start_ready(client)
    previous = len(shade.calls)
    second = start_ready(client, "2026-10-03T13:00:00Z")
    assert second["id"] != first["id"] and len(shade.calls) > previous
    request = ComparisonRequest(
        departure_time=datetime(2026, 10, 3, 13, tzinfo=UTC),
        stops={"demo-route-a": [{"at_metres": 0, "minutes": 2}]},
    )
    third = service.start(request)
    for _ in range(200):
        result = service.get(third.id)
        if result.status == "ready":
            break
        time.sleep(0.01)
    assert result.status == "ready"
    a = result.evidence[0]
    prior_a = second["evidence"][0]
    assert a.planned_stop_minutes == 2
    prior = datetime.fromisoformat(
        prior_a["samples"][0]["requested_time"].replace("Z", "+00:00")
    )
    assert a.samples[0].requested_time == prior + timedelta(minutes=2)


def test_missing_jobs_preferences_and_local_boundary(journey):
    client, _, _ = journey
    assert client.get("/api/comparison/missing").status_code == 404
    assert (
        client.post(
            "/api/comparison/missing/rescore", json={"weights": {"shade": 1}}
        ).status_code
        == 422
    )
    polygons = client.get("/api/coverage")
    assert polygons.status_code == 200
    assert all(p["type"] == "Polygon" for p in polygons.json())
    routes = client.get("/api/walking-routes").json()
    assert len(routes["features"]) == 2
    assert all(r["availability"] == "unknown" for r in routes["features"])
