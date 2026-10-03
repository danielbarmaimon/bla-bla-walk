# T6 · Complete journey integration

Status: implemented · Prepared-data acceptance pending · Branch: feat/t6-journey-integration

## State

Started from main cc3207c and reused screen work from commit 93705a3.
Updated with main d89146e after PR #38 merged; retained the enabled screen
controls, calculation wiring, eligibility restrictions and keyboard focus handling.
PR #39 tracks this branch.
T4/T5/T3/T9 and the approved T10 approximation are merged.
Local compact geometry, building cache and saved offline snapshot are absent here.
Real prepared-data and external-server acceptance remain unverified.

## Done

- Typed exact-departure jobs, bounded workers/results, complete input identity,
  cancellation and pure cached rescoring; no access overrides or provider calls.
- Departure/Now, detour/weights, eligibility-only choice, inspect excluded routes,
  source/model/time details, night/unknown and route shade overlay, city boundary.
- Canonical generated browser contracts; 263 tests passed after merging latest main, including Chrome
  integration, with one real saved-offline test skipped because inputs are absent.
  Final browser regressions: four passed, including late-start cancellation.
  Formatter, lint, generated contracts and strict documentation checks pass.

## Next

Privacy check and reviewable PR; merge requires explicit approval.
Run the full prepared-data journey on a machine with local inputs before claiming
T6's real offline/external-server acceptance. Broader T8/T10 scene acceptance stays
with those tasks; transit is unavailable.

## Resume

Continue T6 on feat/t6-journey-integration. Read this handoff, comparison_service.py,
journey-calculation.js and test_journey_browser.py; finish Next without changing
T5 policy or inventing verified access/water evidence.
