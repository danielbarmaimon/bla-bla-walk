# T6 integration · Slot F

Status: in progress · Branch: feat/t6-journey-integration · Parent acceptance open

## State

Started from merged main d89146e; D's screen PR #38 and T5 PR #37 are included.
The approved T10 building approximation is reused. T18/T19 remains unadmitted.

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

## Next

- Finish privacy/documentation checks and review; changed-file lint is clean.
- Real prepared-data journey validation; cold full sampling previously took
  approximately 20 minutes. Synthetic orchestration tests are not physical validation.
- Real prepared-data API validation is running; record its final results.
- External online deployment URL requested; none supplied yet. Full external
  online and real downloaded local offline acceptance must be recorded before
  marking parent T6 complete. City-wide shade is outside the approved route model.
- Commit/push a reviewable checkpoint PR; merge only with explicit approval.

## Resume

Continue Slot F T6 on feat/t6-journey-integration. Read this handoff and D's
t6-screen.md. Complete the outstanding real-resource/external-server acceptance
checks; preserve exact times, unknowns, bounded jobs and zero offline external
requests. Do not mark T6 complete based only on synthetic browser/API checks.
