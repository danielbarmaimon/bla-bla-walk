# T4 — observations and fountains

## State

Status: done · Slot A · Branch: `feat/t4-observations-fountains`.
T1, T0 and latest main are merged.

## Done

- Pull current main. Confirmed T1 PR #14 and T0 PR #16 merged.
- Added bounded Open Data Basel-Stadt temperature and fountain adapters.
- Confirmed the Explore API's 100-row page cap; adapters paginate within source limits.
- Switched temperature history to one bounded 5,000-row JSON export.
- Live export returned 5,000 rows in 903,383 bytes.
- Live adapters returned 177 stations and 305 fountains.
- Temperature: 90 readings; 87 stations missing.
- Readings included 74 current and 16 stale.
- Full tests passed: 24 passed, 3 skipped.
- T4 lint and formatting passed.
- Existing T9 routes.py lint issues remain on main.
- Joined observations using station ID; points include reading age.
- Marked old readings and failed-refresh snapshots visibly stale.
- Preserved fountain drinking, operating and access status as unknown.
- Added minimal, dated, rights-labelled source fixtures.
- Kept API integration with T6 ownership.

## Publish

Pull request #19: https://github.com/danielbarmaimon/bla-bla-walk/pull/19

## Limits

The observation export caps at 5,000 recent records. Stations absent from that window remain missing. Process caches do not survive restarts. The map-bound rectangle can include points outside the canton. Fountain metadata has no structured water or operational fields. Fixture timestamps are historical source samples.

The T4 adapter change introduced no model contract changes. Subsequent compact/offline preparation connected these adapters through snapshots.py and main.py; online and offline provider modes are merged. T6 still owns the complete shade/comparison journey.

## Next owner

T6 reuses merged provider-mode API wiring and completes shade/comparison integration. Preserve adapter freshness states.
