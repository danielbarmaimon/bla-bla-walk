# T10 · Slot E shade calculation

Status: calculation/evidence checkpoint ready for review; receiver-support acceptance and full T10 remain open · Branch: feat/t10-compact-validation · Owner: @sergimos

## State

Calculation PR #29 is merged. This continuation checks the configured 1m grid/2m height encoding against pinned unquantized scenes and the saved demo routes. Raw rounded heights can hide native survey mismatch and create unsupported ground receivers. The user chose to keep compact geometry and preserve pre-encoding validity/receiver evidence. This checkpoint implements that safeguard; cache/API work stays with Slot F. No parent-task completion is claimed.

## Done

- Added known-object checks across three object heights, three solar elevations and two absolute elevation offsets, plus a regression showing that rounding can conceal a native surface-below-terrain pair.
- Added reproducible independent real-scene comparisons, changed-state footprint measurements and route sensitivity checks at departure plus cumulative walking time. Inputs are checksum-pinned source tiles, prepared through the actual compact writer and read using stored band scales. Numerical ground-envelope candidates do not establish pedestrian or canopy support.
- Added CompactReceiverEvidence to the canonical server interface, and a compressed evidence writer/reader with source, bounds, tolerance and version checks. All four native samples must support a candidate; any missing/below-terrain sample remains flagged after aggregation. Unrounded source maxima remain available for receiver height checks.
- Extended shadow_mask with explicit pre-encoding receiver surface elevations. This requires supported receiver masks, receiver elevations and flags; a compact rounded own column no longer buries an otherwise supported native ground receiver. Unsupported canopy interiors remain unknown.
- Three checksum-pinned real tiles produced 576 independent prism-reference matches. Three 32m scene footprints at three times per tile expose changed shadow/unknown boundaries; empty receiver scenes remain recorded without matches. Source/derived hashes, paired evidence sizes and route sensitivity are in data/fixtures/compact-shade-validation.json.
- At noon, Route A gives 191.5m native numerical shade versus 815.0m on raw compact heights; Route B gives 147.8m versus 765.4m. Preserving all-four-sample evidence leaves 5.3m and 1.6m respectively, with over 99% unknown. These are diagnostic sample results, not accepted route metrics. Changed receiver support dominates the raw differences; broad support/accuracy acceptance has not passed.
- 111 backend checks passed with five browser checks excluded, including 52 shade checks and evidence/provenance regressions. Changed-file lint, formatting and contract regeneration passed; no browser wire fields changed. The existing Starlette TestClient deprecation warning remains.

## Next

1. Review the calculation/evidence checkpoint and merge only with explicit approval. Numerical checks are complete; supported walking/canopy receiver evidence and compact suitability acceptance remain open. Do not treat a passing ray tracer as accepted route coverage.
2. Slot F: generate/verify the companion receiver evidence before consuming compact geometry. Existing height-only prepared files are insufficient; update preparation/cache versions and manifests to include native source pair pins, evidence hash/version/tolerance, origin and resolution. Preserve evidence for each halo/corridor window. Reuse verified prepared heights where possible; lost evidence cannot be reconstructed from rounded codes.
3. Intersect evidence.ground_candidates with independently supported walkway/ground receivers. Pass cell_flags, unrounded receiver surface elevations and verified receiver heights through the calculator. The validation's 0.1m numerical envelope is not a pedestrian support policy. Missing evidence, bridge/survey mismatch and unsupported canopy receivers remain unknown. Complete T8 spatial/scene/bridge acceptance separately.
4. Slot F: implement cache/API using ShadeCalculator/State/Metadata. Effective time equals requested time; five-minute buckets still need validation. Keep NIGHT distinct from daytime shade. Keys include geometry/preparation/calculation and evidence versions, origin/resolution, extent/receiver support, timestamp, solar location/grid rotation and ray/horizon policy. Wire extensions follow hack-interface and regenerate the browser contract with a decision line.
5. Establish independently verified horizon bounds; local maxima or an assumed 250m bound do not certify distant geometry. Finish cold/warm/concurrent latency, memory/cache limits, city seams/edges and offline request checks. Full T10 acceptance is required before marking it done or admitting T5 shade metrics.

## Limits

Numeric prism agreement tests the calculation, not observed physical shade, foliage or walkability. Compact state differences include horizontal pooling, height rounding, terrain-source differences and changed receiver support. Exact ray timestamps are used; proportional saved route duration is a sampling assumption, not measured segment walking time. No accepted route score, full-city shade coverage, API/cache or performance claim exists. Unblocked finite rays lack a verified horizon ceiling and remain unknown.

## Resume prompt

Continue T10 from this handoff and the compact validation evidence. Preserve pre-encoding flags/receiver evidence with the compact geometry; never infer supported ground from equal rounded heights. Finish Slot F cache/API, T8 scene support and full T10 acceptance before marking the parent task done.
