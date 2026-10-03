"""Validate the approved route approximation using prepared inputs, offline."""

import argparse
import base64
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np
from rasterio.warp import transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from benchmark_shade import peak_process_bytes, rounded_measurements  # noqa: E402
from bla_bla_walk import main  # noqa: E402
from bla_bla_walk.interfaces import ShadeRequest  # noqa: E402
from bla_bla_walk.shade_geometry import corridor_cells  # noqa: E402
from bla_bla_walk.shade_service import ShadeService  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def payload(points, moment="2026-10-03T12:00:00Z"):
    x, y = zip(*points)
    return {
        "bounds": [min(x) - 6, min(y) - 6, max(x) + 6, max(y) + 6],
        "corridor": points,
        "corridor_width_m": 10,
        "requested_time": moment,
    }


def route_chunks(points):
    chunks, current = [], [points[0]]
    for point in points[1:]:
        candidate = current + [point]
        bounds = payload(candidate)["bounds"]
        if (
            max(bounds[2] - bounds[0], bounds[3] - bounds[1]) > 900
            or len(candidate) > 128
        ):
            if len(current) < 2:
                raise ValueError("Route segment exceeds the viewport budget")
            chunks.append(current)
            current = [current[-1], point]
        else:
            current = candidate
    chunks.append(current)
    return chunks


def measured(value):
    start = time.perf_counter()
    with TestClient(main.app) as client:
        response = client.post("/api/shade", json=value)
    elapsed = time.perf_counter() - start
    response.raise_for_status()
    body = response.json()
    assert body["model"] == "building-shadow-approximation"
    request = ShadeRequest.model_validate(value)
    area = corridor_cells(request, body["bounds"], 1)
    states = np.frombuffer(base64.b64decode(body["states"]), dtype="uint8").reshape(
        body["height"], body["width"]
    )
    counts = {
        name: int(np.sum(states[area] == code))
        for code, name in enumerate(("unknown", "sunlit", "shaded", "night"))
    }
    return {
        "seconds": elapsed,
        "cache": response.headers["x-shade-cache"],
        "corridor_cell_counts": counts,
        "availability": body["availability"],
        "response_bytes": len(response.content),
    }, body


def validate(repeats):
    routes = json.loads((ROOT / "data/routes/demo.geojson").read_text())
    main.shade_service = ShadeService(ROOT)
    report = {
        "scope": (
            "Building-only flat-ground 1500m approximation; cell counts, "
            "not route-distance metrics"
        ),
        "offline_external_http_attempts": 0,
        "routes": {},
    }
    # TestClient uses ASGI, so real external HTTP transports can be denied.
    with patch(
        "httpx.HTTPTransport.handle_request",
        side_effect=AssertionError("External HTTP"),
    ) as outbound:
        values = []
        for index, feature in enumerate(routes["features"]):
            points = feature["geometry"]["coordinates"]
            x, y = transform(4326, 2056, [p[0] for p in points], [p[1] for p in points])
            chunks = route_chunks(list(zip(x, y)))
            measurements = []
            for chunk in chunks:
                value = payload(chunk)
                values.append(value)
                cold, warm = [], []
                for repeat in range(repeats):
                    value = dict(
                        value, requested_time=f"2026-10-03T12:00:{repeat:02d}Z"
                    )
                    a, _ = measured(value)
                    b, _ = measured(value)
                    assert a["cache"] == "MISS" and b["cache"] == "HIT"
                    assert a["corridor_cell_counts"] == b["corridor_cell_counts"]
                    cold.append(a)
                    warm.append(b)
                assert (
                    sum(a["corridor_cell_counts"][s] for s in ("sunlit", "shaded")) > 0
                )
                measurements.append(
                    {
                        "bounds_lv95": payload(chunk)["bounds"],
                        "cold": cold,
                        "warm": warm,
                    }
                )
            report["routes"][f"route_{index + 1}"] = {
                "complete_polyline": True,
                "source_points": len(points),
                "chunks": measurements,
            }
        main.shade_service = ShadeService(ROOT)
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent = list(pool.map(measured, [values[0], values[-1]]))
        report["concurrent"] = {
            "wall_seconds": time.perf_counter() - start,
            "requests": [item[0] for item in concurrent],
        }
        # Two views straddling a prepared 1km tile boundary; compare shared cells.
        seam_a = {
            "bounds": [2610996, 1266496, 2611004, 1266504],
            "requested_time": values[0]["requested_time"],
        }
        seam_b = dict(seam_a, bounds=[2610997, 1266496, 2611005, 1266504])
        _, a = measured(seam_a)
        _, b = measured(seam_b)

        def decode(body):
            return np.frombuffer(
                base64.b64decode(body["states"]), dtype="uint8"
            ).reshape(body["height"], body["width"])

        difference = int(np.sum(decode(a)[:, 1:] != decode(b)[:, :-1]))
        assert difference == 0
        report["tile_seam_shared_cells"] = 56
        report["tile_seam_disagreements"] = difference
        night, _ = measured(dict(values[0], requested_time="2026-10-03T00:00:00Z"))
        assert night["corridor_cell_counts"]["night"] > 0
        assert night["corridor_cell_counts"]["shaded"] == 0
        report["night"] = night
        report["offline_external_http_attempts"] = outbound.call_count
    cold_seconds = [
        v["seconds"]
        for route in report["routes"].values()
        for chunk in route["chunks"]
        for v in chunk["cold"]
    ]
    warm_seconds = [
        v["seconds"]
        for route in report["routes"].values()
        for chunk in route["chunks"]
        for v in chunk["warm"]
    ]
    report.update(
        cold_p95_seconds=float(np.quantile(cold_seconds, 0.95)),
        warm_p95_seconds=float(np.quantile(warm_seconds, 0.95)),
        peak_process_bytes=peak_process_bytes(),
        cache_bytes=main.shade_service.cache.size_bytes,
    )
    report["budgets"] = {
        "cold_under_5s": report["cold_p95_seconds"] <= 5,
        "warm_under_half_second": report["warm_p95_seconds"] <= 0.5,
        "peak_under_2gib": report["peak_process_bytes"] < 2 * 1024**3,
    }
    manifest = json.loads(
        (ROOT / ".cache/buildings/manifest.json").read_text(encoding="utf-8")
    )
    report["building_source"] = {
        key: manifest[key]
        for key in (
            "version",
            "retrieved_at",
            "provider_timestamp",
            "feature_count",
            "unresolved_geometries",
        )
    }
    report["geometry_version"] = json.loads(
        (ROOT / "data/geometry/manifest.json").read_text()
    )["preparation_version"]
    return rounded_measurements(report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 11))
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data/fixtures/building-shade-validation.json",
    )
    args = parser.parse_args()
    result = validate(args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "cold_p95_seconds",
                    "warm_p95_seconds",
                    "peak_process_bytes",
                    "budgets",
                )
            }
        )
    )
