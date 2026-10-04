# T10 local cache completion

Status: done — this clone has verified sourced inputs and can execute T23's real journey validation on this branch. Branch: fix/t10-complete-local-shade-cache. Updated baseline: 68cab0f, including T22/T25. Merge the model fix before resuming on main.

## Result

Restored the ignored building cache on 2026-10-04: 72 complete Swiss Overpass GET batches, 17,432 sanitized building/part footprints and one unresolved extent. The complete manifest and checksum-named footprint file are present locally. The original T10 handoff's completed cache belonged to the earlier setup; a GitHub merge does not transfer ignored data between clones. Three older global-source batches were retained independently.

Offline preparation now reuses and validates this cache with zero provider requests. The 25 route-halo survey pairs and source flags were already prepared. Nothing in the acquisition admits invalid ground/roof evidence or arbitrary provider routes.

## Changes and source limits

Added optional GET transport to existing bounded, sequential, atomic/resumable acquisition. POST remains the default and retains its previous batch keys. GET has distinct keys, preserves source/retrieval times and uses the same caster-only sanitizer. Interrupted acquisition still cannot publish a complete manifest.

The global configured service timed out; another global service returned 406/504 and a second global mirror timed out. The Swiss service was responsive to GET, while its POST probe returned HTML. Its declared Switzerland coverage is conservatively constrained to the official Basel-Stadt boundary intersected with the requested halo. Regional acquisition/reuse requires this source constraint. Casting and receivers outside it remain unknown; an in-area known blocker can still prove shade before a ray reaches unknown coverage. No international halo completeness is claimed.

The provider marker 117480 cannot be parsed as a source date. It is retained in raw/unparsed provenance while provider_timestamp is null. The API explanation explicitly says source date unknown, separately from known UTC retrieval times. Existing source attribution/licences and detailed limits are in [docs/SOURCES.md](../docs/SOURCES.md). No new dependencies, shared wire contracts or browser changes were introduced.

## Real verification

- Offline preparation passes and reuses the complete same-query-coverage cache.
- Existing full-polyline validator passes for both saved routes in two bounded chunks each, including cold/warm, two concurrent calls, shared tile seam, night and zero external HTTP attempts. One measurement per viewport in this run: aggregate reported cold p95 4.478850s, warm p95 0.123205s; peak process working set 585,830,400 bytes. These are engineering measurements of the constrained approximation, not repeat-rich latency estimates or physical shade accuracy.
- A sourced mapped 33m building and surrounding real footprint window gives 459 shaded cells at 10:00 and 286 shaded / 14 sunlit cells at 14:00 on 2026-10-04 (+02:00). Respective unknown counts are 8,571 and 8,730. At 00:00, 600 cells are night and 8,430 unknown, with no shade/sunlight credit. Requested and effective timestamps match exactly. Latest cold/warm measurements on combined main: 3.129546/0.154902s, 2.594335/0.119561s and 2.216610/0.107658s. This reproduces a real-input model scene; it is not independent field verification of that building's shadows.
- POST /api/comparison now accepts the saved pair with HTTP 202 and completes real sampling: 1 of 248 samples observed before deliberate cancellation. This was a readiness check; a full 248-sample comparison and its final ranking are not claimed. The job was cancelled and its active sample allowed to finish, with zero external HTTP attempts.
- Added regression checks for GET/resume, method validation, regional source constraints, cross-boundary unknown rays and uninterpretable source dates. Final combined-main focused suite including contracts: 110 tests passed. Changed-file formatting/lint and diff checks pass. Repository-wide lint on this Windows setup reports 22 existing import-order findings in untouched files; the modified building-model test now passes. Existing FastAPI/TestClient deprecation warning remains. Strict documentation check reports the same six pre-existing missing local rest-stop/demo/fallback outputs recorded in T23; no new missing paths are introduced. Self-review found no new merge blockers; teammate review remains pending.

Raw measured reports are local under tmp: t10-real-api-validation.json and t10-real-readiness.json. The latter contains the exact known-building viewport and effective times. API geometry/model identity pins the prepared geometry version and footprint SHA-256; source constraints also participate in cache/job identity. These datasets/reports remain local.

## Commands

```sh
python scripts/prepare_building_shade.py --endpoint https://overpass.osm.ch/api/interpreter --request-method GET
python scripts/prepare_building_shade.py --offline
python scripts/validate_building_shade.py --repeats 1 --output tmp/t10-real-api-validation.json
```

README owns general preparation instructions. Retain .cache/buildings and data/geometry when moving the demo; each clone needs its own verified data or a trusted complete copy. A restart should load the changed model code before testing the regional cache.

## Next

1. Resume T23 from [its handoff](T23.md): the earlier missing-cache diagnosis is historical on this clone. Run the complete saved-pair job to readiness, record actual route metres/timings and preserve unknown access/water eligibility. Source freshness remains unknown; no recommendation follows merely from available shade.
2. D's existing progress/layer hooks remain unchanged. Only consider T24 once T23 and essential integration are ready. Original physical/city-wide T8/T10/T6 acceptance remains open.
3. Review and merge this preparation fix only after explicit approval for its PR. The data are already restored locally; other clones need the code changes and independently prepared/copied cache before claiming the same result.

Resume prompt: Continue T23 using the restored, canton-constrained Swiss footprint cache and this completion record. Verify offline inputs, execute the full 248-sample saved-pair job, and record route distances/eligibility and real daylight/night evidence. Keep arbitrary-route and physical validation limits explicit; do not edit D's browser files.
