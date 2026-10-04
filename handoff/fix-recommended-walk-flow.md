# Handoff: recommended walking flow

Status: done · Updated: 2026-10-04 · Branch: fix/recommended-walk-flow · Owner: @ltorrecilla

## Goal
Show Fast and Recommended choices with Recommended initially selected, then replace the form with a walking guide and dismissible preparation tips.

## State
Implementation and verification are complete. The network-enabled Windows launcher serves the updated app on ports 8000 and 8001.

## Done
- Online routing requests two bounded waypoint candidates in addition to direct alternatives. Fast minimizes estimated walking duration; Recommended first prefers avoiding loaded active-project permit polygons, then positive sparse building-shadow samples at departure. Unknown input cells never earn shade credit. Both roles remain present, explicitly sharing a path when necessary (user confirmed this).
- Added canonical optional route_role and timezone-aware departure_time, regenerated contracts, and recorded the interface decision.
- Landmarks active initially. The calculated guide replaces the left form; Plan trip returns to it. Tips open once per calculation and support Close/Escape. Guide water/bench candidates appear within 150 m along the route of 15-minute pauses and 50 m off-route; groups above two collapse.
- Declared Shapely 2.1.2 for geometry intersections and tzdata 2025.2 for Basel-date construction queries on Windows/Linux.
- Live preview returned Fast 1124 m and Recommended 1199 m in 16 seconds, with positive modeled shade and mapped construction-site avoidance. Physical closures, full-walk shade and input gaps remain explicitly unverified.
- Final backend run: 315 passed. Browser coverage: 62 passed across the full run and final targeted correction; three optional local-fixture/platform checks skipped. Guide/modal and rest-group scenarios passed; screenshot review found no page errors. Formatting, changed-file lint and whitespace checks pass.

## Next
Refresh http://127.0.0.1:8001/?mode=online to use the guide. Review the verified branch before merging this follow-up work. Privacy and strict documentation checks passed.

## Files
backend/bla_bla_walk/walking_preferences.py, adapters/walking.py, shade_service.py, interfaces.py; src/main.js, journey-steps.js, route-amenities.js; index.html and route-planner.css. Design, source/run documentation and decisions explain approximation limits.
