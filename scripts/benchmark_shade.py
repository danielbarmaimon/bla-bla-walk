"""Measure Slot F integration separately from synthetic ray-kernel throughput."""

import argparse
import ctypes
import json
import os
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from bla_bla_walk import main  # noqa: E402
from bla_bla_walk.interfaces import ShadeState  # noqa: E402
from bla_bla_walk.shade import shadow_mask  # noqa: E402
from bla_bla_walk.shade_service import ShadeService  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def peak_process_bytes():
    """Read process peak working set/RSS, without adding a dependency."""
    if os.name != "nt":
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value * (1024 if sys.platform != "darwin" else 1))
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_working",
                "working",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
            )
        ]

    handle = ctypes.windll.kernel32.GetCurrentProcess
    handle.restype = wintypes.HANDLE
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not query(handle(), ctypes.byref(counters), counters.cb):
        raise OSError("Cannot measure process peak working set")
    return int(counters.peak_working)


def timed_request(payload):
    start = time.perf_counter()
    with TestClient(main.app) as client:
        response = client.post("/api/shade", json=payload)
    elapsed = time.perf_counter() - start
    response.raise_for_status()
    body = response.json()
    return {
        "seconds": elapsed,
        "cache": response.headers["x-shade-cache"],
        "counts": body["counts"],
        "availability": body["availability"],
        "response_bytes": len(response.content),
    }


def percentile(samples):
    return float(np.quantile([sample["seconds"] for sample in samples], 0.95))


def rounded_measurements(value):
    """Publish microsecond precision, not binary floating-point display noise."""
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: rounded_measurements(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded_measurements(item) for item in value]
    return value


def benchmark(repeats):
    """Use real local centre/vegetation/border grids and a separate analytic scene."""
    main.shade_service = ShadeService()
    moment = datetime(2026, 6, 21, 12, tzinfo=UTC)
    views = {
        "urban_centre": [2610000, 1266000, 2611000, 1267000],
        "vegetation": [2613000, 1269000, 2614000, 1270000],
        "city_edge": [2608500, 1267500, 2609500, 1268500],
    }
    results = {}
    for name, bounds in views.items():
        cold, warm = [], []
        for index in range(repeats):
            payload = {
                "bounds": bounds,
                "requested_time": (moment + timedelta(seconds=index)).isoformat(),
            }
            cold.append(timed_request(payload))
            warm.append(timed_request(payload))
        results[name] = {
            "bounds_lv95": bounds,
            "cold": cold,
            "warm": warm,
            "cold_p95_seconds": percentile(cold),
            "warm_p95_seconds": percentile(warm),
            "cold_budget_5s_pass": percentile(cold) <= 5,
            "warm_budget_0_5s_pass": percentile(warm) <= 0.5,
        }
    concurrent_payloads = [
        {"bounds": bounds, "requested_time": (moment + timedelta(hours=1)).isoformat()}
        for bounds in list(views.values())[:2]
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent = list(pool.map(timed_request, concurrent_payloads))
    # This separate benchmark exercises actual rays and has an analytically
    # proven 12m ceiling. It is not a measured building/canopy scene.
    surface = np.zeros((1128, 1128), dtype="float32")
    terrain = surface.copy()
    surface[500:510, 500:510] = 12
    receivers = np.zeros(surface.shape, dtype=bool)
    receivers[64:1064, 64:1064] = True
    kernel = []
    for _ in range(repeats):
        start = time.perf_counter()
        states = shadow_mask(
            surface,
            terrain,
            elevation_deg=45,
            azimuth_deg=90,
            cell_size_m=1,
            max_distance_m=1500,
            minimum_elevation_deg=10,
            horizon_ceiling_m=12,
            receivers=receivers,
        )
        kernel.append(time.perf_counter() - start)
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(UTC).isoformat(),
        "environment": {
            "system": platform.system(),
            "python": platform.python_version(),
            "logical_processors": os.cpu_count(),
        },
        "scope": (
            "In-process HTTP/API integration using real compact grids; all "
            "production receivers unknown. Separate synthetic 1km ray-kernel "
            "benchmark. No network, production deployment, physical accuracy "
            "or full T10 acceptance claimed."
        ),
        "repetitions": repeats,
        "views": results,
        "concurrent_two_misses": concurrent,
        "cache_serialized_bytes": main.shade_service.cache.size_bytes,
        "cache_budget_bytes": main.shade_service.cache.max_bytes,
        "peak_process_bytes": peak_process_bytes(),
        "memory_scope": (
            "Whole-process peak working set/RSS across two concurrent requests "
            "plus synthetic kernel; not isolated per-worker memory."
        ),
        "synthetic_kernel": {
            "grid_cells": int(surface.size),
            "receiver_area_cells": 1000000,
            "seconds": kernel,
            "p95_seconds": float(np.quantile(kernel, 0.95)),
            "counts": {
                state.name.lower(): int(np.sum(states == state)) for state in ShadeState
            },
            "verified_synthetic_ceiling_metres": 12,
        },
        "full_T10_acceptance": False,
        "remaining": [
            "Compact receiver/scene and route-score sensitivity validation",
            "Independent physical-scene evidence",
            "Externally verified horizon ceiling",
            "Useful real receiver cold/warm/concurrent city-wide shade performance",
            "Per-worker memory and external-server deployment checks",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--output", type=Path, default=ROOT / ".cache/shade-performance.json"
    )
    args = parser.parse_args()
    if not 2 <= args.repeats <= 20:
        parser.error("Use 2 to 20 repetitions")
    result = rounded_measurements(benchmark(args.repeats))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "api_p95": {
                    name: [value["cold_p95_seconds"], value["warm_p95_seconds"]]
                    for name, value in result["views"].items()
                },
                "synthetic_kernel_p95": result["synthetic_kernel"]["p95_seconds"],
                "peak_process_mib": result["peak_process_bytes"] / 1024**2,
                "full_T10_acceptance": False,
            },
            indent=2,
        )
    )
