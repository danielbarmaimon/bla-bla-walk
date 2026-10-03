"""API orchestration: exact times, bounded jobs, local-only and cached rescoring."""

import json
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from bla_bla_walk.adapters.routes import load_demo_routes
from bla_bla_walk.interfaces import JourneyRequest, JourneyResponse, MapSnapshot
from bla_bla_walk.journey import JourneyService
from bla_bla_walk.main import app
from bla_bla_walk.shade_cache import ShadeBusy
from fastapi.testclient import TestClient
from test_route_shade import DEPARTURE, response


@pytest.fixture
def service(tmp_path):
    shade = SimpleNamespace(root=tmp_path, context=Mock(return_value=("inputs-v1",)))
    shade.respond = Mock(side_effect=lambda request: (response(request), False))
    worker = JourneyService(shade)
    routes = load_demo_routes()
    saved = tmp_path / ".cache/provider-snapshot.json"
    saved.parent.mkdir()
    saved.write_text(
        MapSnapshot(
            mode="online", generated_at=DEPARTURE, layers=[routes]
        ).model_dump_json(),
        encoding="utf-8",
    )
    yield worker
    worker.executor.shutdown(wait=True)


def completed(service, request):
    first = service.respond(request)
    for job in list(service.jobs.values()):
        job.result(timeout=20)
    result = service.respond(request)
    assert first.status in {"pending", "complete"}
    assert result.status == "complete"
    return result


def test_offline_exact_time_and_rescore_without_external_requests(service):
    request = JourneyRequest(mode="offline", departure=DEPARTURE)
    with patch(
        "httpx.HTTPTransport.handle_request", side_effect=AssertionError("HTTP")
    ) as http:
        result = completed(service, request)
        calls = service.shade.respond.call_count
        limited = completed(
            service, request.model_copy(update={"extra_time_limit_minutes": 5})
        )
        assert service.shade.respond.call_count == calls
        assert not http.called
    assert result.evidence == limited.evidence
    assert all(
        view.winner is None and not view.manual_choices
        for view in result.comparison.values()
    )
    assert all(
        view.transit_status == "unavailable" for view in result.comparison.values()
    )
    for route in result.evidence:
        assert route.access_state == "unknown"
        for sample in route.samples:
            assert sample.metadata.effective_time == sample.requested_time
            assert sample.requested_time > DEPARTURE


def test_departure_and_prepared_input_changes_invalidate_evidence(service):
    request = JourneyRequest(mode="online", departure=DEPARTURE)
    completed(service, request)
    calls = service.shade.respond.call_count
    completed(
        service,
        request.model_copy(update={"departure": DEPARTURE + timedelta(seconds=1)}),
    )
    assert service.shade.respond.call_count > calls
    calls = service.shade.respond.call_count
    service.shade.context.return_value = ("inputs-v2",)
    completed(service, request)
    assert service.shade.respond.call_count > calls


def test_only_one_active_departure_and_repeated_request_coalesces(service):
    release = Event()
    original = service._calculate
    service._calculate = lambda *args: (release.wait(10), original(*args))[1]
    request = JourneyRequest(mode="online", departure=DEPARTURE)
    try:
        assert service.respond(request).status == "pending"
        assert service.respond(request).status == "pending"
        with pytest.raises(ShadeBusy):
            service.respond(
                request.model_copy(
                    update={"departure": DEPARTURE + timedelta(seconds=1)}
                )
            )
        assert len(service.jobs) == 1
    finally:
        release.set()


def test_api_missing_saved_resources_validation_and_recovery(service, monkeypatch):
    monkeypatch.setattr("bla_bla_walk.main.journey_service", service)
    client = TestClient(app)
    request = {"mode": "offline", "departure": DEPARTURE.isoformat()}
    path = service.shade.root / ".cache/provider-snapshot.json"
    saved = path.read_text(encoding="utf-8")
    path.unlink()
    with patch(
        "httpx.HTTPTransport.handle_request", side_effect=AssertionError("HTTP")
    ) as http:
        assert client.post("/api/comparison", json=request).status_code == 503
        assert not http.called
    path.write_text(saved, encoding="utf-8")
    completed(service, JourneyRequest(**request))
    result = client.post("/api/comparison", json=request)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    JourneyResponse.model_validate(result.json())
    request["departure"] = "2026-10-03T12:00:00"
    assert client.post("/api/comparison", json=request).status_code == 422
    request.update(departure=DEPARTURE.isoformat(), extra_time_limit_minutes=10)
    assert client.post("/api/comparison", json=request).status_code == 422


def test_calculation_failure_is_explicit_and_retryable(service):
    request = JourneyRequest(mode="online", departure=DEPARTURE)
    service.shade.respond.side_effect = ValueError("missing grids")
    service.respond(request)
    for job in list(service.jobs.values()):
        with pytest.raises(ValueError):
            job.result(timeout=20)
    with pytest.raises(ValueError):
        service.respond(request)
    assert not service.jobs
    service.shade.respond.side_effect = lambda request: (response(request), False)
    assert completed(service, request).status == "complete"


def test_generated_browser_journey_schema_matches_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    module = (root / "src/journey.schema.js").read_text()
    assert (
        json.loads(module.split("export const journeySchema = ", 1)[1][:-2])
        == JourneyResponse.model_json_schema()
    )
