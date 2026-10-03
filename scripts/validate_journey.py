"""Real local T6 API journey, with zero outbound HTTP during offline sampling."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bla_bla_walk.main import app, comparison_service  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def validate():
    client = TestClient(app)
    request = {"departure_time": "2026-10-03T12:00:00Z"}
    start = time.perf_counter()
    count = 0
    original = comparison_service.shade.respond

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
        with patch.object(comparison_service.shade, "respond", calculate):
            admitted = client.post("/api/comparison", json=request)
            assert admitted.status_code == 202, admitted.text
            job_id = admitted.json()["id"]
            while True:
                response = client.get(f"/api/comparison/{job_id}")
                assert response.status_code == 200, response.text
                value = response.json()
                if value["status"] == "ready":
                    break
                assert value["status"] == "running", value["explanation"]
                time.sleep(3)
            sampled = count
            limited = client.post(
                f"/api/comparison/{job_id}/rescore",
                json={"extra_time_limit_minutes": 5},
            ).json()
            assert limited["status"] == "ready" and count == sampled
            reused = client.post("/api/comparison", json=request).json()
            assert reused["id"] == job_id and count == sampled
        assert outbound.call_count == 0
    assert all(view["winner"] is None for view in value["choices"].values())
    path = ROOT / ".hack/t6-merged-real-journey.json"
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "seconds": round(time.perf_counter() - start, 3),
                "samples": count,
                "external_http_requests": 0,
                "detour_rescore_samples": count - sampled,
                "statuses": {k: v["status"] for k, v in value["choices"].items()},
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
    comparison_service.close()


if __name__ == "__main__":
    validate()
