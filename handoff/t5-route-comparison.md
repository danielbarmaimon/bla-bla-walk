# T5 · Slot B route comparison

Status: in progress · Branch: feat/t5-route-comparison · Owner: @ltorrecilla

## State

Started from main 7dcd4e3. T2 PR #15, T9 PR #18 and the approved T10
building-shadow approximation PR #34 are merged. Original physical/city-wide
T10 acceptance remains future work. No active T5 handoff exists; transit T18/T19
remains unadmitted. Saved T9 access stays unknown.

## Done

- Read shared launcher, task acceptance, ownership, routing proposal and handoffs.
- Added additive server evidence/comparison models; browser/API wiring stays T6.
- Implemented production evaluator/config and walking-only proposed mode views.
- All 39 T2 cases pass unchanged and route-order-invariant, plus sampling checks.
- Full backend regression passed (241 tests before the final two added checks).
- Full real-route local validation is running; no access/source flags changed.

## Next

Finish real-route validation and final regression/format/privacy checks. Commit,
refresh from main, push and open a PR; ask before merging. T6 reuses
calculate_walking_evidence and compare_routes/compare_choices for API/UI wiring.
