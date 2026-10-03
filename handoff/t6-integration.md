# T6 integration · Slot F

Status: integration checkpoint verified · Branch: feat/t6-slot-f-integration · Parent acceptance open

## State

Started from merged main d89146e; D's screen PR #38 and T5 PR #37 are included.
The approved T10 building approximation is reused. T18/T19 remains unadmitted.
An independent unmerged `feat/t6-journey-integration` branch appeared during
final fetch, with implementation ba8f95f and its own handoff. This checkpoint
uses a distinct branch; compare the overlapping implementations before merging.

## Done

- Added canonical comparison API request/response and browser schema validation.
- Bounded background exact-time sampling (one active departure, four retained
  results), with input identity and pure detour rescoring. No provider calls in
  route calculation; offline requires saved route snapshot and local shade inputs.
- Connected departure/Now, optional five-minute limit, comparison metrics and
  eligibility; pending/failure clears old recommendations. Sources, model limits,
  requested/effective traversal times and night remain separate and visible.
- Six orchestration/contract tests pass, including zero outbound HTTP under
  synthetic local shade responses, failure recovery and exact-time invalidation.
- Eight browser checks pass with installed Chrome; full regression: 258 passed.
- Prepared sanitized provider snapshot and all 4,418 licensed offline basemap
  images (complete, no errors; approximately 57 MB). They stay local.
- Added toggleable traversal-sample map markers, with explicit unknown/night
  and model limits. Shade source times are separate from observation times.
- Fixed real provider timestamp wrapping on narrow map controls and checked
  the downloaded provider snapshot at phone width. Strict docs, full lint,
  formatting, generated schema and staged privacy guard pass.
- Real API validation: 248 exact traversal-time samples in 702.683 seconds,
  zero external HTTP calls, zero detour-rescore samples and immediate online
  reuse. Baseline/Fastest/More shade all return no eligible route because access
  stays unknown. Route A: 158.475m shaded, 1151.620m unknown; route B: 107.680m
  shaded, 1196.889m unknown. Departure: 2026-10-03 12:00 UTC.
- Real downloaded offline browser: snapshot/tiles/routes, layer toggle and pan
  at phone width pass with zero external browser requests. Saved real API
  results also render metrics, reasons, sample map and time/model detail with
  a visible saved-output label. This rendering replay is not a live recalculation.

## Acceptance audit

| T6 criterion | Evidence / remaining scope |
|---|---|
| Narrow screen, keyboard, toggles, freshness | Eight Chrome browser checks and real downloaded snapshot review; long timestamp wrapping fixed. |
| Modes, eligible choices, five-minute limit | T5 evaluator unchanged; browser checks use explicit synthetic eligible/unknown evidence; real routes correctly have no recommendation. |
| Departure, effective time, limits | Exact-time invalidation tests; real 248-sample API run; requested/effective traversal times and model exclusions visible. |
| Source/calculation failure, missing tiles | Existing adapter/shade regression and browser failure/recovery checks; previous comparison is cleared, missing offline requests stay local. |
| City pan, seams, edges/outside coverage | Real offline basemap pan; existing T10/T8 seam/boundary tests pass in regression. Map explicitly limits shade to traversal samples and other endpoint pairs have no checked route. Broader physical/city-wide shade is unvalidated. |
| Local offline zero external requests | Actual prepared API run blocks outbound HTTP, actual downloaded browser records zero external requests; missing-resource paths also tested. |
| Online external server | Not verified: no deployment URL supplied. Local online provider acquisition and API cache reuse do not satisfy this criterion. |
| Transit offline | Explicitly unavailable; no T18/T19 admission, timetable or candidate inferred. |

## Next

- Compare the independently published T6 branch before selecting an implementation
  to merge. Keep both histories and avoid force-pushing either branch.
- External online deployment URL requested; none supplied yet. Full external
  online acceptance must be recorded before
  marking parent T6 complete. City-wide shade is outside the approved route model.
- Commit/push a reviewable checkpoint PR; merge only with explicit approval.

## Resume

Continue Slot F T6 on feat/t6-slot-f-integration. Read this handoff and D's
t6-screen.md. Complete the outstanding real-resource/external-server acceptance
checks; preserve exact times, unknowns, bounded jobs and zero offline external
requests. Do not mark T6 complete based only on synthetic browser/API checks.
