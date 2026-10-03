# T10 · Slot E shade calculation

Status: paused for handoff; PR #30 is merged; T10 and Slot E acceptance are not complete · Branch: `feat/t10-handoff-followup` · Project Slot E owner in `TEAM.md`: @danielbarmaimon · Current checkpoint contributor: @sergimos

## Start here

Read `AGENTS.md`, `TASK_START.md`, `TEAM.md`, `ROADMAP.md`, and the T8/T10 entries in `docs/plan.md`. Then read this handoff and inspect the merged PR #30 before taking work. The repository's launch guide says a slot should start from merged `main`. PR #30 is merged; the latest handoff-only update is on `feat/t10-handoff-followup`. Do not assume the checkpoint is accepted or mark T10 done. The calculation and evidence code are in `main`.

PR #29, the first shade-calculation checkpoint, is merged into `main`. PR #30 carries the compact-grid validation, pre-encoding evidence model, calculator support and tests. This follow-up carries the reproducible takeover details. The user chose to keep the configured compact geometry while preserving its pre-encoding validity and receiver evidence. That choice does not approve any pedestrian receiver threshold, route-score tolerance or T10 completion.

## What is implemented

- `backend/bla_bla_walk/solar.py` and `shade.py`: offline geometric sun position and cell-prism ray tracing. Timestamps are exact; night and unknown remain explicit. Unblocked rays remain unknown without a verified horizon bound.
- `backend/bla_bla_walk/compact_evidence.py`: companion evidence derived from an aligned native 0.5 m surface/terrain pair before compact rounding. It preserves conservative native pair flags, all-four-sample numerical ground-envelope candidates, and unrounded source surface maxima. The `.npz` reader checks version, source hashes, bounds, 1 m shape and validation tolerance. `CompactReceiverEvidence` is a server-side model; no browser payload fields changed.
- `shadow_mask` can use preserved receiver surface elevations only when explicit receiver mask, receiver heights and flags are also supplied. This addresses compact rounding burying a supported receiver in its own cell. It does not identify usable pavements, roofs or foliage interiors by itself.
- `scripts/validate_compact_shade.py` compares the actual compact preparation with checksum-pinned native geometry, an independent prism-intersection implementation, scene-edge masks and the saved demo routes. `data/fixtures/compact-shade-validation.json` holds the summarized public evidence. Detailed source downloads and generated rasters stayed local in ignored `.hack/t10/`.

## Results and limits

- **111 backend checks passed; 5 browser checks were excluded.** Changed-file lint, formatting, contract regeneration, strict documentation check and the privacy guard passed. There is one existing Starlette `TestClient` deprecation warning.
- Three pinned Basel tiles yielded **576 independent numerical prism-reference matches**. This checks the ray implementation against a different intersection method on the same height representation; it is not a physical shadow survey.
- At noon on the two saved routes, raw compact heights report about **815 m shaded on Route A and 765 m on Route B**, compared with about **192 m and 148 m** on the native numeric reference. The raw compact case also assigns shade to samples where the native comparison is unknown.
- Requiring all four source samples in a 1 m cell to fit the **0.1 m numerical validation envelope**, and preserving their flags, reduces compact shade to about **5 m on Route A and 2 m on Route B** at noon. Over 99% of each route remains unknown. The 0.1 m value is a test selection, not an agreed walkway/canopy rule. This conservative result removes unsupported credit but does not demonstrate useful or accepted route coverage.
- The reference uses 0.5 m surface/terrain and the compact case uses 1 m pooled surface plus 2 m terrain and 2 m elevation steps. Differences include changed cell centres, surface pooling, height rounding, terrain source and receiver eligibility. Route sampling is at intervals no greater than 2 m; saved route duration is spread proportionally along length. These are sensitivity measurements, not accepted route metrics.
- Missing receiver evidence cannot be reconstructed from existing rounded height codes. Do not relax the evidence filter merely to reduce the unknown share. Unresolved bridges, missing cells, unsupported canopy interiors, insufficient halo, low sun and missing horizon proof stay unknown.

## Remaining work, in order

1. **Review and merge checkpoint PR #30** only with the repository's explicit approval. If it is not merged, coordinate with the PR owner rather than starting dependent integration on `main`.
2. **Finish Slot E/T8 scene and receiver acceptance.** `docs/plan.md` says T8 still needs spatial alignment at centre/boundary references and seam, survey mismatch, border-gap and bridge checks. Use `handoff/t8.md` and `handoff/data-compact-offline.md`; do not repeat completed ingestion. For T10, find admitted evidence for actual walking receivers and any supported elevated/canopy receivers, or keep them unknown. A route line alone and a raster maximum do not prove a walkable ground surface. Record the source/licence and a reviewer-agreed acceptance measure. In particular, the team has not set an acceptable compact-versus-native route-sensitivity tolerance or coverage target.
3. **Prepare compact geometry with its companion evidence.** Existing `data/geometry/` height files are not enough. Update the preparation manifest/version to bind each evidence file to native pair checksums, grid origin/resolution, bounds, evidence version and tolerance. Carry flags/evidence across the full caster halo and tile seams. Verify missing or mismatched evidence fails closed. Keep generated rasters/caches local; do not add city rasters to Git.
4. **Validate accepted scenes and routes.** Compare known-object analytic lengths, independent real-scene references and the two demo routes at departure plus cumulative walking time. Report shaded, sunlit and unknown lengths with full-route denominators. Measure how preparation resolution changes shadow edges and eligible route lengths using the agreed tolerance. Do not infer suitability from the numeric comparison alone.
5. **Hand off to Slot F for the rest of T10.** After Slot E's checkpoint is merged, F connects calculation to viewport/corridor requests and a versioned cache/API, preserving effective time, evidence provenance and unknown/night states. F still needs a verified horizon bound, tile-seam/border checks, memory/cache accounting, cold/warm/concurrent latency and zero-external-request offline verification. T10 is done only after every item in its `docs/plan.md` acceptance check passes.

## Reproducing the evidence

The first tile's native 0.5 m pair and 2 m terrain pair are:

| Tile | Surface SHA-256 | Native terrain SHA-256 | 2 m terrain SHA-256 |
|---|---|---|---|
| 2610-1266 | `7e2f118c72b6b3813a0342fcc276b5842f894673be913d7a37e64d353dc01d03` | `bb59e26e6adcddb165274415c7b4f73368cf40a127705316ee1729e1a3ee8bbe` | `10db3f33bef59d7fd4018aeeb1c7d47d787a396d2f69274d75e3473d06ad3bb5` |
| 2611-1266 | `d01542c8ce768fab73284381f40a3baf07c8b159fc8f792bbbbfee6c144d8e7b` | `780554300f9a262e7737beb3a1607d1efe876f43c5dce34387318f9f8bf1aa0e` | `a76fe265544ed3ecd906b3492db2e1b179a216e5b11f68012c38baffde7a15de` |
| 2611-1267 | `04e20e16aa50c039779cc8c0f1d416112c6b9805878e848d7a7067f832030a04` | `189c58348c814182aa9a77b8b4caf918c65935c6c2481e2d2cb0c114c92f9265` | `4bb4ae42648f0530f7e02e4e13b54cec03487250a740626443a08ced03184f6f` |

With the first tile files saved under ignored `.hack/t10/`, reproduce its comparison with:

```sh
python scripts/validate_compact_shade.py \
  --surface .hack/t10/surface.tif \
  --terrain .hack/t10/terrain.tif \
  --terrain-2m .hack/t10/terrain-2m.tif \
  --work-directory .hack/t10/compact \
  --output .hack/t10/compact-validation.json
```

For route tiles `2611-1266` and `2611-1267`, pass `--tile` and `--terrain-2m-sha256` from the fixture, and use that tile's matching source files and separate work/output paths. The script does not download sources. See the README's development-check section for setup and the command pattern. Run backend acceptance from repository root with:

```sh
python -m pytest -c backend/pyproject.toml backend/tests -m 'not browser'
```

## Resume prompt

Continue the open Slot E/T10 validation from this handoff. First inspect PR #30 and merged `main`, then verify which T8 scene checks and receiver-support sources have since been accepted. Reuse the pinned compact validation fixture and existing preparation. Keep compact encoding with pre-encoding evidence, preserve unknowns, and agree measurable receiver/route acceptance before relaxing the evidence filter. Update this handoff after each checkpoint. Do not mark T10 done until Slot F's full cache/API, horizon, offline, seam, load/performance and route-accuracy acceptance also passes.
