"""Bounded background route sampling; preference changes reuse exact evidence."""

import hashlib
import json
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from pathlib import Path
from threading import Lock

from .adapters.routes import load_demo_routes
from .evaluation import compare_choices, load_rules
from .interfaces import JourneyResponse, ShadeRequest
from .route_shade import calculate_walking_evidence
from .shade_cache import ShadeBusy
from .snapshots import offline_snapshot


class JourneyService:
    """One active departure, four retained results; no queued unbounded work.

    Input identity includes route provenance, policies, implementation and every
    prepared asset's file state via ShadeService.context. No time rounding or
    provider fallback. Restart clears evidence. Stops remain unplanned.
    """

    def __init__(self, shade):
        self.shade = shade
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.lock = Lock()
        self.jobs = OrderedDict()

    def respond(self, request):
        if request.mode == "offline":
            snapshot = offline_snapshot(
                self.shade.root / ".cache/provider-snapshot.json"
            )
            routes = [
                feature
                for layer in snapshot.layers
                if layer.kind == "route"
                for feature in layer.features
            ]
        else:
            routes = load_demo_routes().features
        if {r.id for r in routes} != {"demo-route-a", "demo-route-b"}:
            raise ValueError("Saved checked route pair unavailable")
        rules = load_rules()
        departure = request.departure.astimezone(UTC)
        # Context pins ALL source-file stamps; bounds only establish identity.
        context = self.shade.context(
            ShadeRequest(
                bounds=(2610000, 1266000, 2610002, 1266002),
                requested_time=departure,
            )
        )[0]
        identity = {
            "departure": departure.isoformat(),
            "context": context,
            "rules": rules,
            "routes": [
                r.model_dump(
                    mode="json", include={"id", "geometry", "route", "provenance"}
                )
                for r in routes
            ],
            "sampling_code": [
                Path(__file__).with_name(name).read_text(encoding="utf-8")
                for name in (
                    "journey.py",
                    "route_shade.py",
                    "evaluation.py",
                    "walking_metrics.py",
                )
            ],
        }
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        with self.lock:
            if key not in self.jobs:
                if any(not job.done() for job in self.jobs.values()):
                    raise ShadeBusy("Another departure is calculating; retry later")
                while len(self.jobs) >= 4:
                    self.jobs.popitem(last=False)
                self.jobs[key] = self.executor.submit(
                    self._calculate, routes, departure, rules
                )
            self.jobs.move_to_end(key)
            job = self.jobs[key]
        if not job.done():
            return JourneyResponse(
                status="pending",
                departure=departure,
                explanation="Exact-time route sampling is running locally. A cold "
                "calculation can take about 20 minutes; no recommendation yet.",
            )
        try:
            evidence = job.result()
        except Exception:
            with self.lock:
                self.jobs.pop(key, None)
            raise
        return JourneyResponse(
            status="complete",
            departure=departure,
            evidence=evidence,
            comparison=compare_choices(
                evidence,
                rules=rules,
                extra_time_limit_minutes=request.extra_time_limit_minutes,
            ),
            explanation="Local midpoint building-shadow approximation; dated "
            "sources, no tree/terrain shade or measured cooling. Access, water "
            "operation and transit unavailable/unverified. Optional rest cues "
            "are not planned stops in these metrics.",
        )

    def _calculate(self, routes, departure, rules):
        evidence = [
            calculate_walking_evidence(
                route,
                departure,
                lambda value: self.shade.respond(value)[0],
                rules=rules,
            )
            for route in routes
        ]
        if any(route.shade_state == "failed" for route in evidence):
            raise ValueError("Local shade sampling failed; retry after checking inputs")
        return evidence
