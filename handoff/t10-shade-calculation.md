# T10 · Slot E shade calculation

Status: calculation checkpoint ready for review; T10 remains open · Branch: feat/t10-shade-calculation · Owner: @sergimos

## State

T8 PR #27 is merged. Native preparation and compact preparation coexist; the plan still lists compact spatial/scene validation as open. This calculation consumes decoded metre arrays and accepts native T8 flags, so it does not select or rewrite either pipeline. T10 is not done.

## Done

- Implemented offline geometric solar bearings and batched cell-prism ray traversal in `backend/bla_bla_walk/solar.py` and `backend/bla_bla_walk/shade.py`.
- Added 33 passing calculation checks: analytic shadow direction/length, an independent rectangle-intersection tracer, timestamps, unknown halo/missing/bridge cells, canopy receiver limits, night/low sun/zenith, overlapping halo consistency, and compact-height sensitivity.
- Recorded the synthetic 5m versus encoded 6m shadow-length example. This demonstrates a sensitivity, not accepted compact accuracy.
- Downloaded one checksum-pinned native Basel centre pair into ignored .hack/t10/ and reproduced 48 independent numerical reference matches; 37 shaded and 11 unknown. Evidence lives in `data/fixtures/shade-validation.json`; README has the reproduction command. The audited Mittlere Brücke reference is explicitly unknown under T8's flag policy.
- Final backend regression: 84 passed; five browser checks deselected for this backend-only change. Contract regeneration, changed-file lint/formatting, strict documentation and whitespace checks pass. Global Ruff reports five existing import-order findings in unrelated test files; no new findings in this checkpoint.

## Next

1. Review this calculation-only PR and merge only after explicit approval. Slot F starts its portion after this checkpoint merges.
2. Slot E/T8: complete compact real-scene accuracy and route-sample sensitivity acceptance against unquantized reference scenes. The 0.5m numerical spot check is not a physical shade/ground/foliage survey and does not close those checks.
3. Slot F: load aligned metre grids and flags across receiver viewports/corridors plus halos. Compact inputs use geometry.read_heights, including masks/scales; native inputs require masking NoData and passing pair flags. Provide verified supported receiver masks/elevations and each request's true/grid-north rotation. Missing tiles/buffer, unsupported terrain and unresolved canopy/bridge receivers stay unknown.
4. Reuse calculate_shade through the additive ShadeCalculator processing protocol and ShadeState enum in interfaces.py, plus the existing ShadeMetadata. Browser JSON payload fields are unchanged; server arrays are not wire data. Preserve night separately from shaded route metres. Effective time currently equals requested time. Do not silently add five-minute buckets.
5. Add cache/API with keys including geometry/preparation and calculation version, grid origin/resolution, request extent/receiver support, timestamp, solar location/grid rotation and ray/horizon policy. Any wire extensions must follow hack-interface and regenerate the browser contract with a decision line.
6. Establish the horizon ceiling from independently verified height/relief bounds, not a local maximum or assumed 250m height. Without a proven ceiling, finite unblocked rays remain unknown. Check memory, cold/warm/concurrent latency, full-city tile seams and local-offline requests. Full T10 acceptance remains required before T5 can claim accepted shade metrics.

## Limits

Unblocked rays require an externally verified absolute horizon ceiling to become sunlit; a local maximum alone cannot certify geometry beyond the input. Missing/flagged cells and insufficient halo stay unknown. Default receivers require equal surface/terrain; explicit verified ground masks and receiver elevations can handle small survey differences. Receivers below the surveyed upper surface remain unknown, including unresolved canopy interiors. There is no API, cache, route metric or claimed city-wide accuracy/performance in this checkpoint.

## Resume prompt

Continue T10 cache/API for Slot F after the calculation PR merges. Read this handoff, the calculator docstrings, data/fixtures/shade-validation.json and T10's full acceptance check. Reuse the calculation, preserve explicit unknown/night states and finish the remaining geometry, accuracy, cache, API and performance work before marking T10 done.
