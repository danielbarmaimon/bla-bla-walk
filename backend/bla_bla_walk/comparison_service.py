"""Bounded background route sampling and pure, input-versioned rescoring."""

import hashlib
import json
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from pathlib import Path
from threading import Event, RLock
from uuid import uuid4

from rasterio import Env
from rasterio.warp import transform

from .adapters.routes import load_demo_routes
from .evaluation import compare_choices, compare_routes, load_rules
from .interfaces import (
    ComparisonJob,
    ComparisonPreferences,
    ComparisonRequest,
    ShadeRequest,
)
from .route_shade import calculate_walking_evidence, route_intervals
from .shade_cache import ShadeBusy


class ComparisonService:
    """One active calculation and four memory-only results per server process.

    All routes and access evidence are server-owned. No provider calls occur;
    departure, speed, source identity and full stop plans pin exact samples.
    """

    MAX_RESULTS = 4

    def __init__(self, shade_service):
        self.shade = shade_service
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.lock = RLock()
        self.jobs = OrderedDict()
        self.inputs = {}
        self.cancelled = {}

    def identity(self, request, routes, rules):
        """Reuse T10's file/policy/version identity without doing shade work."""
        contexts = []
        for route in routes:
            lon, lat = route.geometry.coordinates[0]
            with Env(PROJ_NETWORK="OFF"):
                x, y = transform(4326, 2056, [lon], [lat])
            contexts.append(
                self.shade.context(
                    ShadeRequest(
                        bounds=(x[0] - 1, y[0] - 1, x[0] + 1, y[0] + 1),
                        requested_time=request.departure_time,
                    )
                )[0]
            )
        implementation = hashlib.sha256()
        for name in ("route_shade.py", "evaluation.py", "walking_metrics.py"):
            implementation.update(Path(__file__).with_name(name).read_bytes())
        return hashlib.sha256(
            json.dumps(
                {
                    "request": request.model_dump(mode="json"),
                    "routes": [r.model_dump(mode="json") for r in routes],
                    "rules": rules,
                    "shade_contexts": contexts,
                    "implementation": implementation.hexdigest(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

    def start(self, request: ComparisonRequest):
        """Validate local inputs before admitting work; duplicate runs share a job."""
        request = request.model_copy(
            update={"departure_time": request.departure_time.astimezone(UTC)}
        )
        routes = load_demo_routes().features
        rules = load_rules()
        ids = {r.id for r in routes}
        if set(request.stops) - ids:
            raise ValueError("Stops must belong to the checked walking routes")
        for route in routes:
            if any(
                s.at_metres > route.route.distance_m
                for s in request.stops.get(route.id, [])
            ):
                raise ValueError("Stop locations must lie along the checked route")
        try:
            key = self.identity(request, routes, rules)
        except (ValueError, OverflowError) as error:
            raise OSError("Prepared inputs invalid") from error
        with self.lock:
            for job_id, (existing, _, _) in self.inputs.items():
                if key == existing and self.jobs[job_id].status != "failed":
                    return self.jobs[job_id].model_copy(deep=True)
            if any(j.status == "running" for j in self.jobs.values()):
                raise ShadeBusy("Another route calculation is running; retry later")
            while len(self.jobs) >= self.MAX_RESULTS:
                removed, _ = self.jobs.popitem(last=False)
                del self.inputs[removed]
                del self.cancelled[removed]
            job = ComparisonJob(
                id=uuid4().hex,
                status="running",
                departure_time=request.departure_time,
                total_samples=sum(
                    len(route_intervals(r, rules, request.stops.get(r.id, [])))
                    for r in routes
                ),
                explanation="Calculating exact traversal times in the background. "
                "A cold run can take around 20 minutes; no route is recommended yet.",
            )
            self.jobs[job.id] = job
            self.cancelled[job.id] = Event()
            self.inputs[job.id] = (key, request, rules)
            self.executor.submit(self._calculate, job.id, routes)
            return job.model_copy(deep=True)

    def _calculate(self, job_id, routes):
        key, request, rules = self.inputs[job_id]
        evidence = []

        def calculate(sample_request):
            if self.cancelled[job_id].is_set():
                raise ValueError("Calculation cancelled")
            response = self.shade.respond(sample_request)[0]
            with self.lock:
                self.jobs[job_id].completed_samples += 1
            return response

        try:
            for route in routes:
                if self.cancelled[job_id].is_set():
                    raise ValueError("Calculation cancelled")
                evidence.append(
                    calculate_walking_evidence(
                        route,
                        request.departure_time,
                        calculate,
                        stops=request.stops.get(route.id, []),
                        rules=rules,
                    )
                )
            if self.cancelled[job_id].is_set():
                raise ValueError("Calculation cancelled")
            if any(r.shade_state == "failed" for r in evidence):
                raise ValueError("A shade sample failed")
            if key != self.identity(request, load_demo_routes().features, load_rules()):
                raise ValueError("Inputs changed during calculation")
            with self.lock:
                job = self.jobs[job_id]
                job.evidence = evidence
                job.total_samples = sum(len(r.samples) for r in evidence)
                job.status = "ready"
                job.explanation = (
                    "Exact-time building-shadow estimates ready. Tree shade and "
                    "terrain relief are excluded; unknown access and water remain "
                    "unverified. Transit is unavailable."
                )
        except (OSError, ValueError, KeyError, OverflowError, ShadeBusy):
            with self.lock:
                self.jobs[job_id].status = "failed"
                self.jobs[job_id].explanation = (
                    "Route calculation failed or prepared inputs changed. Verify "
                    "local geometry/buildings and start a new calculation."
                )

    def get(self, job_id, preferences=None):
        """Return a detached result; changed inputs cannot keep old shade credit."""
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(job_id)
            key, request, rules = self.inputs[job_id]
            job = self.jobs[job_id].model_copy(deep=True)
        if job.status == "ready":
            try:
                matches = key == self.identity(
                    request, load_demo_routes().features, load_rules()
                )
            except (OSError, ValueError, KeyError, OverflowError):
                matches = False
            if not matches:
                job.status = "failed"
                job.evidence = []
                job.explanation = "Prepared inputs changed; recalculate this journey."
            else:
                preferences = preferences or ComparisonPreferences()
                job.choices = compare_choices(
                    job.evidence,
                    rules=rules,
                    extra_time_limit_minutes=preferences.extra_time_limit_minutes,
                )
                job.choices["baseline"] = compare_routes(
                    job.evidence,
                    preferences.weights,
                    rules=rules,
                )
        return job

    def cancel(self, job_id):
        """Release a superseded job after its active shade sample finishes."""
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError(job_id)
            self.cancelled[job_id].set()

    def close(self):
        """Stop accepting new work; active local sampling finishes before exit."""
        for event in self.cancelled.values():
            event.set()
        self.executor.shutdown(wait=False, cancel_futures=True)
