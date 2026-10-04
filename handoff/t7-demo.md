# T7 — English five-minute pitch checkpoint

Status: script and local fallback prepared; human delivery acceptance pending.
Branch: `docs/seven-beat-pitch`. No external deployment.

## State

The seven-beat solution pitch is exactly 300 seconds on paper, followed by the
separate 42-second HackAmRhein reflection. Speaker/clicker, personal story and
two spoken rehearsals remain pending. No submission receipt is available.

## Done

- Replaced the older three/five-minute-shaped script with the requested seven
  beats in order, plus a clearly illustrative scenario and private presenter
  fill-in; no invented testimony, users or statistics.
- Recorded the actual local smoke-check: app root 200; fixture API 200 with
  synthetic observations/fountain; offline map API 503 because the saved
  provider snapshot is absent in this checkout.
- Restored a local-only fallback summary at `.hack/t31-fallback/index.html`
  from exact route values in merged `handoff/t6-integration.md`. It says saved,
  dated and not live; it states that the original raw JSON is absent. It makes
  no provider requests and is ignored by Git.
- Browser fallback acceptance passed: two rows, saved/not-live label, no
  external requests. This is technical fallback verification, not a spoken
  rehearsal.
- Updated `docs/pitch.md` and `docs/demo.md` with the 5:42 cues, word budgets,
  source/limit notes, likely jury answers, verified setup, failure route and
  rehearsal log. Existing event details and pending submission status retained.

## Checks

- Local app: `/` HTTP 200; `/api/map?mode=fixture` HTTP 200; `/api/map?mode=offline`
  HTTP 503 with `Saved provider snapshot unavailable; run offline preparation`.
- `PYTHONPATH=backend CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python -m pytest
  -c backend/pyproject.toml backend/tests/test_trip_acceptance_browser.py -k
  saved_fallback` — 1 passed after matching the existing expected label.
- No human timed rehearsal was performed. The required run 1/run 2 remain open.

## Next

Confirm the speaker and clicker, and supply one true non-identifying story if
available. Have the human presenters rehearse the entire 5:42 twice, record real
times, and trim only after run 1 without changing the beat order or 300-second
solution budget. Confirm the team reflection and submission receipt. The
documented fallback is ready locally; do not mark full T7 acceptance complete
until spoken rehearsals and event submission confirmation are evidenced.
