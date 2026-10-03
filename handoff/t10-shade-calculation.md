# T10 · Slot E shade calculation

Status: receiver validation resumed; T10 remains open · Branch: feat/t10-receiver-validation · Owner: @ltorrecilla

## State

T8 PR #27 and E's calculation PR #29 are merged. The continuation branch starts
from F's cache/API checkpoint (9a802cc), which remains subject to review/merge.
Native preparation and compact preparation coexist; compact spatial/scene
validation remains open. No production receivers have been admitted. T10 is not
done.

## Done

- Resumed E validation with four local, catalogue-checksum-verified T0 native
  raster pairs: centre, vegetation, tall building and border. Added
  scripts/audit_compact_receivers.py and data/fixtures/compact-receiver-audit.json.
  The controlled vertical-only audit found 1041683 / 278083 / 1190161 / 413427
  erased surface-below-terrain flags respectively. It isolates the 2m height step
  at native 0.5m spacing; it does not represent the production 1m/2m-terrain
  resampling pipeline and cannot admit ground receivers.
- Reproduced the existing 48 independent reference matches with the local centre
  pair: 37 shaded, 11 unknown. No new physical reference claim.
- Six audit tests cover erased inversions, false equality, masked/NaN inputs and
  invalid encoding steps. Backend regression: 107 passed, five browser tests
  deselected. Backend and audit lint/format checks pass. Local source-manifest
  line endings were normalized to the already-configured LF policy, restoring
  its pinned checksum without changing Git content.
- This checkout lacks data/geometry and the native prepared arrays. T0 native
  0.5m samples are available under ignored .hack/t0; the missing project NumPy
  and Rasterio packages were restored to their declared versions in .venv.

- Implemented offline geometric solar bearings and batched cell-prism ray traversal in `backend/bla_bla_walk/solar.py` and `backend/bla_bla_walk/shade.py`.
- Added 33 passing calculation checks: analytic shadow direction/length, an independent rectangle-intersection tracer, timestamps, unknown halo/missing/bridge cells, canopy receiver limits, night/low sun/zenith, overlapping halo consistency, and compact-height sensitivity.
- Recorded the synthetic 5m versus encoded 6m shadow-length example. This demonstrates a sensitivity, not accepted compact accuracy.
- Downloaded one checksum-pinned native Basel centre pair into ignored .hack/t10/ and reproduced 48 independent numerical reference matches; 37 shaded and 11 unknown. Evidence lives in `data/fixtures/shade-validation.json`; README has the reproduction command. The audited Mittlere Brücke reference is explicitly unknown under T8's flag policy.
- Final backend regression: 84 passed; five browser checks deselected for this backend-only change. Contract regeneration, changed-file lint/formatting, strict documentation and whitespace checks pass. Global Ruff reports five existing import-order findings in unrelated test files; no new findings in this checkpoint.

## Next

1. Obtain/reproduce the checksum-pinned actual compact assets (including native
   2m terrain), and compare aligned 1m ground/corridor samples with unquantized
   reference scenes. Source inversion evidence must survive preparation; never
   infer receiver support from equal height codes. Locate independently checked
   ground/bridge/canopy receiver and physical shade evidence; the user has been
   asked whether the team already has it.
2. Slot E/T8: complete compact real-scene accuracy and route-sample sensitivity acceptance against unquantized reference scenes. The 0.5m numerical spot check is not a physical shade/ground/foliage survey and does not close those checks.
3. Slot F: load aligned metre grids and flags across receiver viewports/corridors plus halos. Compact inputs use geometry.read_heights, including masks/scales; native inputs require masking NoData and passing pair flags. Provide verified supported receiver masks/elevations and each request's true/grid-north rotation. Missing tiles/buffer, unsupported terrain and unresolved canopy/bridge receivers stay unknown.
4. Reuse calculate_shade through the additive ShadeCalculator processing protocol and ShadeState enum in interfaces.py, plus the existing ShadeMetadata. Browser JSON payload fields are unchanged; server arrays are not wire data. Preserve night separately from shaded route metres. Effective time currently equals requested time. Do not silently add five-minute buckets.
5. Add cache/API with keys including geometry/preparation and calculation version, grid origin/resolution, request extent/receiver support, timestamp, solar location/grid rotation and ray/horizon policy. Any wire extensions must follow hack-interface and regenerate the browser contract with a decision line.
6. Establish the horizon ceiling from independently verified height/relief bounds, not a local maximum or assumed 250m height. Without a proven ceiling, finite unblocked rays remain unknown. Check memory, cold/warm/concurrent latency, full-city tile seams and local-offline requests. Full T10 acceptance remains required before T5 can claim accepted shade metrics.

## Limits

Unblocked rays require an externally verified absolute horizon ceiling to become sunlit; a local maximum alone cannot certify geometry beyond the input. Missing/flagged cells and insufficient halo stay unknown. Default receivers require equal surface/terrain; explicit verified ground masks and receiver elevations can handle small survey differences. Receivers below the surveyed upper surface remain unknown, including unresolved canopy interiors. There is no API, cache, route metric or claimed city-wide accuracy/performance in this checkpoint.

## Resume prompt

Continue E/T10 receiver validation on feat/t10-receiver-validation. Read this
handoff, F's handoff, the calculator docstrings and the encoding audit. E's
calculation is merged; F's checkpoint is included in this branch but requires
its own merge approval. Audit actual compact assets and checked physical
receivers next. Preserve unknown/night states and complete geometry accuracy,
route sensitivity, horizon and performance acceptance before marking T10 done.
