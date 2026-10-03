# T6 · Slot F integration acceptance

Status: local checkpoint verified · Parent external-server acceptance open · Branch: feat/t6-slot-f-integration

## State

This is the current T6 acceptance record. PR #39 merged into main f438090;
PR #40 merged into main 4e28b71. The reconciled implementation keeps its
canonical ComparisonRequest, ComparisonJob and ComparisonPreferences contracts,
cancellation, polling and pure cached rescoring. The overlapping Slot F API was
removed. See [the historical implementation handoff](t6-journey-integration.md) and
[the historical screen handoff](t6-screen.md).

## Done

- Retained real evidence/model wrapping in comparison cards and provider timestamps
  in layer controls. Phone-width tests expand long model identifiers.
- Disabled PROJ network access explicitly during route planning and input identity
  transforms. Calculation still uses only saved routes and prepared local shade.
- Added `scripts/validate_journey.py` to run the canonical background API with
  outbound HTTP blocked and save its actual result locally. It checks job polling,
  duplicate-request reuse, detour rescoring and unknown-access withholding.
- Full reconciled regression: 264 passed, including nine Chrome browser checks.
  The actual downloaded offline snapshot/basemap check ran, without skips.
- Prepared local dated provider snapshot and all 4,418 offline basemap images,
  complete with zero download errors. Local files stay outside Git.
- Real canonical API validation completed 248 exact-time samples in 827.833
  seconds with zero outbound HTTP requests. Detour rescoring and duplicate
  request reuse made zero additional samples. All three views return
  no_eligible_routes because access remains unknown. Route A: 158.475m shaded,
  1151.620m unknown; route B: 107.680m shaded, 1196.889m unknown. Departure:
  2026-10-03 12:00 UTC. The actual response stays local in
  `.hack/t6-merged-real-journey.json`.

## Acceptance audit

| T6 criterion | Evidence / remaining scope |
|---|---|
| Narrow screen, keyboard, toggles, freshness | Nine browser checks; real downloaded provider timestamps and expanded long model identifiers fit phone width. |
| Modes, eligible choices, five-minute option | Canonical T5 evaluator; explicit synthetic eligible/unknown browser evidence. Real access remains unknown. |
| Departure, effective time, limits | Exact-time invalidation/cancellation and cached-rescoring tests; sample time and model limits remain separate from source observation time. |
| Failure and missing resources | API/browser failure and recovery tests; missing tiles/preparation explicit, obsolete recommendations cleared. |
| City pan, seams, edges/outside coverage | Existing T8/T10 regression; independently checked real adjacent shade-window seam and outside-model unknown cells. Only saved route samples have calculated shade; other endpoint pairs have no checked route. Physical/city-wide shade remains unvalidated. |
| Local offline zero external requests | Actual downloaded browser and missing-resource checks record zero external requests; actual prepared API run completed 248 samples with outbound HTTP blocked and zero attempted requests. |
| Online external server | Unverified: no deployment URL supplied. Local provider acquisition and cache reuse do not satisfy this criterion. |
| Transit offline | Explicitly unavailable; no admitted timetable/candidate. |

## Historical evidence

The superseded Slot F API completed 248 exact-time samples in 702.683 seconds
with zero external HTTP, and saved-output rendering was checked at desktop/phone
width. That result is historical; it is not evidence that the reconciled API ran.
An independent real shade API check found matching adjacent seam cells and all
16 cells unknown for an outside-model request, with zero outbound HTTP.
No measured cooling, overall safety or physical shade accuracy is claimed.

## Next

Obtain an external online deployment URL and verify the complete journey with
its prepared datasets: provider freshness/failures, exact departure calculation,
polling, preference rescoring, eligibility, map layers and missing-resource states.
Record that deployment and its results here before marking parent T6 complete.
Broader physical/city-wide shade acceptance remains with T8/T10; transit remains
unavailable until T18/T19 admission.
