"""Real local T6 API journey, with zero outbound HTTP during offline sampling."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bla_bla_walk.main import app, journey_service  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def validate():
    client = TestClient(app)
    request = {"mode": "offline", "departure": "2026-10-03T12:00:00Z"}
    start = time.perf_counter()
    count = 0
    original = journey_service.shade.respond

    def calculate(value):
        nonlocal count
        result = original(value)
        count += 1
        if count % 20 == 0:
            print(f"Completed exact-time samples: {count}", flush=True)
        return result

    with patch(
        "httpx.HTTPTransport.handle_request",
        side_effect=AssertionError("Offline external request"),
    ) as outbound:
        assert client.get("/api/map?mode=offline").status_code == 200
        with patch.object(journey_service.shade, "respond", calculate):
            while True:
                response = client.post("/api/comparison", json=request)
                assert response.status_code == 200, response.text
                value = response.json()
                if value["status"] == "complete":
                    break
                time.sleep(3)
            sampled = count
            limited = client.post(
                "/api/comparison",
                json={
                    **request,
                    "extra_time_limit_minutes": 5,
                },
            ).json()
            assert limited["status"] == "complete" and count == sampled
            online = client.post(
                "/api/comparison",
                json={
                    **request,
                    "mode": "online",
                },
            ).json()
            assert online["status"] == "complete" and count == sampled
        assert outbound.call_count == 0
    assert all(view["winner"] is None for view in value["comparison"].values())
    path = ROOT / ".hack/t6-real-journey.json"
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "seconds": round(time.perf_counter() - start, 3),
                "samples": count,
                "external_http_requests": 0,
                "detour_rescore_samples": count - sampled,
                "statuses": {k: v["status"] for k, v in value["comparison"].items()},
                "routes": [
                    {
                        "id": r["id"],
                        "shade": round(r["shaded_metres"], 3),
                        "unknown": round(r["unknown_metres"], 3),
                    }
                    for r in value["evidence"]
                ],
            }
        ),
        flush=True,
    )
    journey_service.executor.shutdown()


if __name__ == "__main__":
    validate()
