# Handoff: map badge and planner UI fixes

Status: done · Updated: 2026-10-04 · Branch: fix/map-badge-controls · Last owner: @ltorrecilla

## Goal
Keep badges independent, toggle all loaded weather stations/fountains and saved landmarks, hide the example shortcut and green walking-options area beneath Calculate.

## State
Implementation is complete and visually checked. 44 browser checks passed, with two existing skips. Separate full-suite checks require local offline/fallback assets and a Windows-compatible screenshot path; those do not block these UI checks. Formatter, lint and whitespace checks pass.

## Done
- Dedicated source-kind badge mapping; station display reuses the route-temperature source and fountains reuse real route-amenity source data.
- Saved landmark icons retain original coordinates and source inspection.
- Map badges remain available before route submission; shade outline remains visible with temperature active.
- Walking options moved into collapsed Information sources; saved-pair shortcut hidden; nearby taps remain in the planner.
- Regression verifies actual OpenLayers feature visibility across independent toggle combinations.

## Next
No UI work remains. Changes are saved locally on the fix branch; publishing or merging is separate.

## Files
- src/main.js, src/map.js, src/route-temperature-view.js, src/route-planner.css: map wiring and independent overlays.
- index.html: planner layout.
- backend/tests: updated hidden-fixture test helper and UI regression coverage.
- README.md, docs/decisions.md: updated behavior.

## Open questions
None about requested behavior. No interface models or backend routing calculations changed.

## Resume prompt
Continue the UI fixes on fix/map-badge-controls. Read this handoff and finish Next.
