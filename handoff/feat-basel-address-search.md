# Basel address search

Status: done; pull request publication in progress.
Branch: feat/basel-address-search.

## State

Both endpoint fields now use official GeoAdmin building-address suggestions,
bounded by the pinned Basel-Stadt polygon including holes/Riehen/Bettingen.
The user explicitly requested real addresses rather than a landmark-only search.
This feature selects map coordinates; arbitrary-endpoint routes remain unavailable.

## Done

- Canonical address wire models and generated browser declarations; decision logged.
- POST search API omits typed addresses from access-log URLs; no query persistence.
- Bounded provider response, timeout, address-only filtering and plain-text labels.
- Debounced cancellable search, keyboard selection, failure/no-match messages;
  offline lookup makes no provider request and keeps samples/map pins.
- Live public event venue lookup selected correctly in Chrome, no page errors.
- Full regression: 271 passed, including new address controls and existing browser
  journey checks. Live public venue result was selected with no page errors.
- Python lint/format and browser formatting passed.
- Updated source register, design and README to describe actual search capability.

## Next

Finish doc/privacy checks, commit/push and open PR. Merge needs approval.
Updated app runs on port 8002 with network-enabled provider access; port 8001's
restricted-process provider calls fail. Presentation distributions remain local.

## Resume

Finish verification and publish feat/basel-address-search. Read this handoff and
the new address adapter/UI modules; do not imply address selection supplies
arbitrary route calculation or verified pedestrian access.
