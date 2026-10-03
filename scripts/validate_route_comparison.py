"""Reproduce full saved-route T5 metrics with local T10 inputs and zero HTTP."""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bla_bla_walk.adapters.routes import load_demo_routes  # noqa: E402
from bla_bla_walk.evaluation import compare_choices  # noqa: E402
from bla_bla_walk.route_shade import calculate_walking_evidence  # noqa: E402
from bla_bla_walk.shade_service import ShadeService  # noqa: E402


def validate():
    """Print rounded evidence only; no source files or access flags are modified."""
    service = ShadeService(ROOT)
    evidence = []
    calls = 0

    def calculate(request):
        nonlocal calls
        calls += 1
        return service.respond(request)[0]

    start = time.perf_counter()
    with patch(
        "httpx.HTTPTransport.handle_request",
        side_effect=AssertionError("External HTTP"),
    ) as outbound:
        for route in load_demo_routes().features:
            result = calculate_walking_evidence(
                route, datetime(2026, 10, 3, 12, tzinfo=UTC), calculate
            )
            evidence.append(result)
            assert result.access_state == "unknown"
            assert result.shaded_metres + result.unshaded_metres > 0
            assert (
                abs(
                    result.shaded_metres
                    + result.unshaded_metres
                    + result.unknown_metres
                    - result.distance_metres
                )
                < 1e-6
            )
            print(
                json.dumps(
                    {
                        "route": result.id,
                        "samples": len(result.samples),
                        "shaded_metres": round(result.shaded_metres, 3),
                        "unshaded_metres": round(result.unshaded_metres, 3),
                        "unknown_metres": round(result.unknown_metres, 3),
                        "model": sorted({s.model for s in result.samples}),
                    }
                ),
                flush=True,
            )
        previous = calls
        choices = compare_choices(evidence)
        assert all(r.status == "no_eligible_routes" for r in choices.values())
        assert calls == previous and outbound.call_count == 0
    print(
        json.dumps(
            {
                "seconds": round(time.perf_counter() - start, 3),
                "shade_calls": calls,
                "rescore_shade_calls": calls - previous,
                "external_http_calls": 0,
                "statuses": {k: v.status for k, v in choices.items()},
                "scope": (
                    "Midpoint building-shadow approximation; saved route access unknown"
                ),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    validate()
