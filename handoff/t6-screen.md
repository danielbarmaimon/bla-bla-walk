# T6 screen · Slot D handoff to Slot F

Status: screen portion ready · Parent T6 remains in progress

## State

Built the comparison presentation on `feat/t6-comparison-screen` from merged
`main` (T5 PR #37 is included). No shared interface, API, or plan status changed.

## Done

- Added reusable `renderTripComparison` presentation for Fastest overall and
  More shade views. It accepts route features and optional T5 `TripComparison`
  results, presents walking duration, shaded/exposed/unknown distance and
  percentages, water evidence, eligibility, reasons, and historical PET
  separately, and keeps unknown values explicit.
- Added Show on map and Choose route actions. When comparison data is supplied,
  manual selection is limited to `manual_choices`; the selected route keeps
  keyboard focus after the screen updates.
- Added the departure date/time and Now controls plus the optional five-minute
  More shade limit to the screen. They are visibly disabled until integration
  connects them to calculation behavior.
- Kept the parent T6 open. Full acceptance, online/offline integration, failure
  and coverage checks have not been completed.

## Validation

- `node --input-type=module --check` passed for `src/main.js` and
  `src/comparison.js`.
- `git diff --check` passed.
- Previewed the root screen in fixture and offline modes. Fixture has no route
  features, and the prepared offline provider snapshot was unavailable, so the
  rendered cards still need review with live API comparison results. The
  comparison controls and explicit pending states appeared in the UI.
- Did not run tests; this checkpoint is screen work only.

## Next · Slot F

1. Pass the chosen T5 `compare_choices` result to `renderTripComparison` as
   `comparison`, preserving the `fastest_overall` / `more_shade` keys and
   snake_case `TripComparison` fields.
2. Connect the departure controls to exact-time shade sampling and the selected
   five-minute detour limit to More shade rescoring. Enable these controls only
   when their behavior is wired. Keep cached rescoring for weight/view changes;
   see [T5 handoff](t5-route-comparison.md) for the cold-sampling latency and
   cache assumptions.
3. Confirm eligible-only manual choice, recommendations/reasons, and card
   rendering from real T5 results. Keep transit explicitly unavailable unless
   T18/T19 admission changes.
4. Complete and record the entire T6 acceptance check in `docs/plan.md` only
   after online external-server and local offline journeys pass, including
   zero offline external requests, missing data, pan/city extent, source and
   calculation failures, tile seams, city edges, freshness and effective time.
