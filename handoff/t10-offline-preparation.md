# T10 · Offline preparation follow-up

> Historical preparation-code checkpoint. This clone's subsequent data restoration and real API readiness are recorded in [T10 cache completion](t10-cache-completion.md); the missing-data state below is retained as history.

Status: preparation-code fix complete and verified; publication in progress · Branch: fix/t10-offline-preparation · Owner: @danielbarmaimon

## State

Cache/API PR #30 and building approximation PR #34 are already merged. This follow-up fixes repeated building downloads and lost progress after acquisition timeouts. It does not change the approximation or claim the original physical/city-wide T10 acceptance.

## Done

- Default preparation reuses only an intact sanitized same-coverage cache, preserving source times. Explicit offline validation makes no provider calls; refresh is deliberate.
- Added identifying application headers and public HTTPS endpoint overrides with source provenance. URLs carrying credentials/query parameters are rejected.
- Partitioned route-halo acquisition into small sequential queries. Sanitized checksum-verified checkpoints resume failed acquisitions; overlapping IDs are deduplicated and conflicting versions fail closed. The active manifest switches atomically only after complete success.
- Recorded the oldest batch retrieval/provider times, preserving dated evidence when acquisition resumes. Raw names/address tags are discarded before checkpoint storage.
- Twelve preparation tests pass: cache/offline reuse, preserved good cache after refresh failure, corrupt/unsanitized inputs, partial batches, conflict rejection, query coverage, resume and endpoint validation.
- Full regression: 184 tests passed, including five browser checks. Offline CLI validation correctly refuses incomplete local footprints. Lint, formatting, strict documentation and staged privacy checks pass.
- Local geometry: 25 route-halo pairs and source flags prepared without errors, 346,967,228 unique source bytes and 32,313,112 current-version prepared bytes. Full-city inventory completion is not claimed.
- Local building acquisition: the configured endpoint timed out; mirrors returned HTTP 504 for larger requests. Smaller requests retrieved three of 72 batches, saved locally. A complete footprint cache is not yet available here; the live API correctly returns 503 for missing prepared inputs.

## Next

1. Publish and merge the verified fix under the user's explicit instruction for this work. GitHub PR status records publication; the data dependency below remains independent of merge.
2. Finish local acquisition when the source is available, using the same public endpoint to reuse validated checkpoints. Alternatively copy an existing complete prepared cache from the accepted setup and validate it offline.
3. Run the full saved-route offline validator after complete buildings are available. Broader physical/city-wide shade accuracy remains future work; route scoring/browser integration belongs to T5/T6.
