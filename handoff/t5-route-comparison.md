# T5 · Slot B route comparison

Status: done · Branch: feat/t5-route-comparison · Owner: @ltorrecilla

## State

Started from main 7dcd4e3. T2 PR #15, T9 PR #18 and approved T10
building-shadow approximation PR #34 are merged. Original physical/city-wide
T10 acceptance remains future work. Transit T18/T19 remains unadmitted.
Implementation is complete; PR review and explicit merge approval remain.

## Done / acceptance

- Canonical WalkingEvidence, WalkingShadeSample, WalkingStop, WaterEvidence
  and TripComparison models preserve source/model metadata and exact times.
- Full route length is partitioned along checked geometry. Intervals up to
  25m preserve bends and stop boundaries; midpoint times include cumulative
  walking and preceding stops. This is approximate quadrature, not exact cell
  intersection or observed physical shade. Night is explicit and earns no credit.
- Config/evaluator reproduce all 39 T2 cases, including weights, fixed ranges,
  reference/tie rules, constraints, unknown/stale evidence and route-order
  invariance. Excluded candidates retain cards/metrics/reasons. Manual choice
  stays limited to eligible IDs; incomplete active evidence withholds winners.
- Walking-only Fastest overall and More shade views supplement the unchanged
  baseline. No default five-minute preference or transit admission is imposed.
- Pure cached rescoring makes no shade calls. Speed, distance or stop-total
  changes invalidate cached shade credit; changed departure/stop locations or
  geometry require new sampling. Incomplete duration evidence earns no credit.
- Full real-route offline run: 248 exact-time shade calls, zero external HTTP
  requests and zero calls for preference rescoring. Total cold run 1203.231s.

| Saved route | Samples | Shaded m | Unshaded m | Unknown m |
|---|---:|---:|---:|---:|
| demo-route-a | 119 | 158.475 | 12.605 | 1151.620 |
| demo-route-b | 129 | 107.680 | 14.531 | 1196.889 |

These are dated building-model estimates for departure 2026-10-03 12:00 UTC,
not live measurements. Both fall below the baseline 80% known-length gate.
Saved T9 access remains unknown; water operation/inventory stays unknown. All
three comparison views correctly return no eligible route, with no winner.

## Validation

244 tests passed; five browser checks skipped because Chromium is unavailable.
All 39 production scenario cases and 26 additional scoring/sampling checks pass.
Generated-contract regression, formatting, lint, strict documentation and privacy
checks pass. No new dependency or schema/API/browser change.

Reproduce prepared-data acceptance with
`python scripts/validate_route_comparison.py`; it needs the local building and
geometry preparation documented in README. Source inputs remain local.

## Next / T6 handoff

1. Review the PR and merge only after explicit approval. Do not edit plan status
   from this task; this handoff is the task's live state.
2. T6 owns API/browser wiring. Reuse calculate_walking_evidence and
   compare_routes/compare_choices, caching complete WalkingEvidence by departure,
   geometry/model/source identity, speed, geometry and complete stop plan.
3. Show approximation limits, requested/effective sample times, unknown/night,
   provenance, active-evidence reasons and manual eligibility. Do not promote
   T9's unknown access or fountain observations to checked operation.
4. Cold full-route sampling took about 20 minutes on this machine. The repeated
   exact-time T10 requests reload/preprocess local inputs; do not claim interactive
   departure recalculation. T6/F must address latency or use explicitly dated
   prepared results with matching requests. Weight changes already avoid all
   shade work. No time buckets or fabricated source support were introduced.
5. Transit remains unavailable until T18/T19 admission and approval. The grocery
   destination and cross-mode proposal are still team decisions.

## Resume prompt

Review completed T5 on feat/t5-route-comparison. Preserve T2 policy and the T10
approximation limits. Read this handoff and routing rules, check the PR and ask
before merging. T6 connects the functions to UI/API and handles cold latency;
never infer checked access, water operation or admitted transit.
