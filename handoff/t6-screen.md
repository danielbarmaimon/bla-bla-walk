# T6 screen · Slot D handoff to Slot F

Status: done — screen portion merged in PR #38 · Historical handoff

## State

PR #38 merged the comparison screen. PR #39 connected its controls and API;
PR #40 reconciled the implementation and recorded local acceptance. The
[current T6 acceptance record](t6-integration.md) owns remaining work.

## Done

- Reusable `renderTripComparison` presentation for route metrics, eligibility,
  reasons and historical PET, with explicit unknown values.
- Show on map and Choose route actions with keyboard focus handling.
- Departure date/time, Now and optional five-minute More shade controls.

## Historical validation

This screen checkpoint checked syntax, whitespace and previews before API wiring.
Its controls were disabled and calculated comparisons were pending at that point.
Those limitations were addressed by the later integration; current regression and
prepared-data evidence live in the [acceptance record](t6-integration.md).

## Next

Follow the [T6 acceptance record](t6-integration.md) for the remaining
external-server check. The screen and local integration are already merged.
