# Handoff: recommended walking flow

Status: done · Updated: 2026-10-04 · Branch: fix/recommended-walk-flow · Owner: @ltorrecilla

## Goal
Show Fast and Recommended choices with Recommended initially selected, then replace the form with a walking guide and dismissible preparation tips.

## State
Implementation and verification are complete; latest main includes the team's map popups and Windows pip bootstrap fix. The network-enabled Windows launcher serves the updated app on ports 8000 and 8001.

## Done
- Online routing requests two bounded waypoint candidates in addition to direct alternatives. Fast minimizes estimated walking duration; Recommended first prefers avoiding loaded active-project permit polygons, then positive sparse building-shadow samples at departure. Unknown input cells never earn shade credit. Both roles remain present, explicitly sharing a path when necessary (user confirmed this).
- Added canonical optional route_role and timezone-aware departure_time, regenerated contracts, and recorded the interface decision.
- Landmarks active initially. The calculated guide replaces the left form; Plan trip returns to it. Tips open once per calculation and support Close/Escape. Guide water/bench candidates appear within 150 m along the route of 15-minute pauses and 50 m off-route; groups above two collapse.
- Declared Shapely 2.1.2 for geometry intersections and tzdata 2025.2 for Basel-date construction queries on Windows/Linux.
- Live preview returned Fast 1124 m and Recommended 1199 m in 16 seconds, with positive modeled shade and mapped construction-site avoidance. Physical closures, full-walk shade and input gaps remain explicitly unverified.
- Final backend run: 315 passed. Browser coverage: 64 passed across the full run, final targeted correction and two incoming popup checks; three optional local-fixture/platform checks skipped. Guide/modal and rest-group scenarios passed; screenshot review found no page errors. Formatting, changed-file lint and whitespace checks pass.

- Follow-up: both visible walking paths now carry sensor-temperature gradients using one combined range/palette. Selecting a route preserves both gradients; route badges independently hide their paths. Seven gradient/badge/guide browser checks pass, including shared normalization, click details and palette changes. Browser formatting, changed-test lint and whitespace checks pass.

- Follow-up: preparation tips now open immediately on each valid Calculate click while routing continues. Four responsive cards reuse local icons; closing tips does not cancel calculation or reopen on completion. Background status becomes ready when results arrive. Ten targeted guide/trip-flow/walking browser checks passed, two optional local-fixture checks skipped; desktop/mobile screenshots reviewed. Route calculation and instruction logic remain unchanged. Delay inspection found sequential external route alternatives, construction queries and local building-shade work; the saved pair also evaluates exact-time shade samples.

- Construction follow-up: canonical ConstructionSite/ConstructionSnapshot and construction feature kind, regenerated contracts, sanitized SQLite snapshot with one refresh attempt per Basel date shared across processes/restarts. Current/upcoming project and permit intervals are intersected; only complete valid bounded results replace the cache. Offline reads only; stale evidence cannot earn avoidance credit. Browser checks hourly and shows source-anchored icons within approximately 100 m of visible paths, with independent More badge and compact source popup. Live acquisition saved 460 polygons in 2.2 s; cached read 13 ms. Both launchers restarted and new endpoint verified current on ports 8000/8001. Full backend: 322 passed; nine final cache/contract checks passed (two added after full run). Eight affected browser checks passed, then the construction tap-detail check passed. Formatting, production/changed-test lint and whitespace pass. Cache stays ignored.

## Next
Refresh http://127.0.0.1:8001/?mode=online to use the guide. Review the verified branch before merging this follow-up work. Privacy and strict documentation checks passed.

## Files
backend/bla_bla_walk/walking_preferences.py, adapters/walking.py, shade_service.py, interfaces.py; src/main.js, journey-steps.js, route-amenities.js; index.html and route-planner.css. Design, source/run documentation and decisions explain approximation limits.
