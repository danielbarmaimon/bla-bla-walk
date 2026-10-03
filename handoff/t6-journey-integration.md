# T6 · Complete journey integration

Status: done — implementation merged in PR #39 · Historical handoff

## State

PR #39 merged into main f438090. The implementation was subsequently reconciled
and validated in PR #40. The [current T6 acceptance record](t6-integration.md)
owns validation evidence and remaining work.

## Done

- Typed exact-departure jobs, bounded workers/results, complete input identity,
  cancellation and pure cached rescoring; no access overrides or provider calls.
- Departure/Now, detour/weights, eligibility-only choice, inspection of excluded
  routes, source/model/time details, night/unknown, route shade overlay and city
  boundary.
- Canonical generated browser contracts and API/browser regression checks.
- Reused the screen work from commit 93705a3 and merged main d89146e while
  preserving calculation wiring, eligibility restrictions and keyboard focus.

## Historical validation

This implementation checkpoint passed its checks while prepared datasets were
absent on its validation machine. Later real offline acceptance supersedes that
limitation; see the [current acceptance record](t6-integration.md).

## Next

Continue from the [T6 acceptance record](t6-integration.md), which tracks the
remaining external-server check. Do not restart the merged implementation.
