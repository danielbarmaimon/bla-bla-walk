# T10 · Slot F cache/API checkpoint

Status: cache/API checkpoint ready for review; parent T10 open · Branch: feat/t10-shade-cache-api · Owner: @danielbarmaimon

## State

T8 PR #27 and E's calculation PR #29 are merged. This branch reuses E's calculator and adds local compact-grid cache/API integration. The compact real-scene receiver, horizon and route-sensitivity checks left open in E's handoff prevent full T10 acceptance. Do not mark T10 done or start T5 as though accepted shade exists.

## Done

- Added POST /api/shade with canonical request/response models, generated schemas/types, exact aware timestamps, snapped LV95 bounds and optional route corridor.
- Added a byte-bounded in-memory LRU, same-key request coalescing, two calculation workers and explicit busy/retry behaviour. Cache keys pin preparation, code, encoding, file state, boundary, receiver/ray policy, time and area. No time buckets or provider calls.
- Load checksum-verified compact windows through read_heights; preserve NoData, missing tiles and buffers, independent survey provenance and projection grid rotation. Large requests stay bounded.
- Every production compact receiver remains unknown until E validates support. Quantized surface/terrain equality is not accepted ground evidence. API responds with explicit unfinished-validation explanation, never false sun/shade/night credit.
- Sixteen new cache/API checks pass, including failure recovery, concurrency/coalescing, LRU eviction, timezone reuse, invalid/oversized requests, corrupt/missing geometry and corridor selection.
- Recorded five-repeat real-grid 1km API integration benchmarks in data/fixtures/shade-performance.json: cold p95 2.85s centre / 2.29s vegetation / 2.02s edge; warm p95 0.093s / 0.090s / 0.267s. These are unknown-output integration measurements, not useful real shade throughput.
- Separate synthetic 1km ray calculation p95 0.534s with a proven synthetic 12m ceiling. Whole-process peak after two concurrent real requests plus kernel: 672MiB; this is not isolated per-worker measurement.
- Full regression: 105 passed including five browser checks. Lint, Python/browser formatting and generated contracts pass. Fixed the existing Windows source-manifest checksum regression by pinning that JSON's checkout line endings to LF, without changing its content or prepared asset hashes; removed one existing import-spacing lint finding.
- Added a generated shade-schema/coordinate contract check; all 13 contract checks pass after generation. Strict documentation and staged privacy checks pass. A real HTTP smoke check on port 8001 returned MISS then HIT with explicit unknown counts.
- Public timing reports retain six decimal places; raw binary-float displays remain local. The privacy guard initially rejected a redundant long decimal matching an ID pattern; no allow marker or guard change was used.

## Next

1. Open/review the checkpoint PR. Merge only after explicit approval.
2. E/T8: validate compact receiver masks and elevations against unquantized scenes, including erased surface-below-terrain flags, bridges and canopy interiors. Supply evidence-backed support instead of deriving it from compact equality.
3. E/T10: establish independently verified horizon/relief bounds; keep unresolved unblocked rays unknown. Complete physical/independent scene and route-score sensitivity acceptance.
4. F: replace the deliberately empty receiver mask only with admitted support, version its evidence in the cache key and load native flags where required. Preserve the existing unknown/night distinction.
5. Rerun cold/warm/concurrent and seam checks across supported city scenes and corridors; measure isolated worker memory and an actual external-server deployment. Existing integration and synthetic timings cannot satisfy this.
6. Verify all T10 Done when criteria literally before marking the parent complete. T6 browser time/layer wiring remains separate.

## Full acceptance audit

Known-object direction/length, independent numerical tracing, low sun/night and halo/canopy/bridge cases: covered by E's calculation tests. Exact-time metadata, cache/API, resource bounds and no external shade calls: implemented here. Compact real-scene/support/route sensitivity, externally verified horizon, useful real city throughput, full-city shade seams and physical reference evidence: pending. Full T10 acceptance: **not passed**.

## Resume prompt

Continue T10 from handoff/t10-cache-api.md and E's calculation handoff. Reuse the cache/API checkpoint. Resolve compact receiver and horizon evidence before enabling non-unknown production results; complete real-scene/corridor performance and full T10 acceptance without claiming current unknown-output timings establish shade performance.
