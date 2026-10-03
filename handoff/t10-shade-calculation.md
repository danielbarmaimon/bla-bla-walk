# T10 — building-cast shadows along demo routes

Status: done — user-approved building-shadow approximation, merged in PR #34; broader original acceptance remains future work.
Branch: feat/t10-building-shadows

## Goal and decision

The user explicitly chose an approximation based on cast shadows from buildings
along route paths. This replaces the physical receiver/horizon acceptance for
this continuation. It does not certify walking ground, tree shade, terrain relief
or city-wide physical sunlight. Original broader acceptance stays future work.

## State

The local API now produces shaded and sunlit approximation cells rather than
all unknown. It uses dated OSM building footprints, explicit mapped metre heights
or surveyed roof-minus-terrain heights, flat ground, and a declared 1500m ray
reach. Receivers require valid source flags, no footprint and a 0–2m survey
height difference; they are plausible ground, not observed walkways.
Missing roof geometry/heights, invalid receivers and missing ray coverage remain
unknown. Night remains separate. The wire contract labels model and approximate
availability. The strict survey calculator remains available and unchanged in
its horizon requirements.

## Earlier merged checkpoints

PRs #29, #30 and #32 are merged. Their strict calculator, compact receiver
evidence model and validator remain intact. The six-tile pipeline comparison
is separately named scripts/validate_compact_pipeline.py and
data/fixtures/compact-pipeline-validation.json to retain both independent audits.

## Done

- Source flag preservation, compact encoding audit and six-tile numerical
  validation are committed and pushed in a82a435 and a1ed80b.
- Downloaded 17,366 sanitized OSM buildings/parts to ignored .cache/buildings;
  one unresolved relation extent stays unknown. No names or address tags saved.
- Prepared 25 route-halo tile pairs and flags in ignored data/geometry, using
  revision 2. Route coverage is a partial inventory, not full-city preparation.
- Both complete saved polylines pass the offline API validator, in two bounded
  chunks each. Shared tile seam: 56 cells agree; night never earns shade credit.
  Cold p95 2.96s, cached p95 0.064s; peak process working set about 564MiB.
  Two distinct concurrent cold calls succeed; zero external HTTP attempts.
- Model/parser/API tests cover analytic shadows, missing heights and geometry,
  explicit heights, coverage limits, ground proxy, source flags, cache identity
  and tag sanitization. Updated legacy browser checks to the current route-screen
  controls. Final regression after main integration: 171 passed, one browser
  check skipped because offline imagery/provider snapshots are absent.
- Reproduction and interpretation are documented in README and docs/SOURCES.md;
  physical/city-wide acceptance is retained in docs/future-features.md.

## Publication

The continuation is published on a fresh review branch. Updating the old review
branch brought an already-published GitHub web-merge identity into its push
range, which the local strict privacy hook refused. Shared history was retained;
the new branch uses the unchanged hook to check newly introduced commits.

## Next

1. Continue from merged PR #34. Offline preparation follow-up is tracked in [its handoff](t10-offline-preparation.md).
2. T5/T6 own route-distance scoring and browser shade integration. Supply
   corridor requests in bounded chunks, show approximate model identity and
   requested/effective times, retain unknown cells and keep night separate.
3. Preparation: python scripts/prepare_building_shade.py --geometry. Validation:
   python scripts/validate_building_shade.py --repeats 3. Large inputs remain local.
4. Broader observed ground/shade, vegetation, terrain and city-wide acceptance
   are future work documented in docs/future-features.md. Many corridor cells
   deliberately remain unknown; do not invent percentages of shaded route metres.

## Resume prompt

Review the completed T10 building-shadow approximation on
feat/t10-building-shadows. Reuse the dated local building cache and prepared
geometry, the canonical labelled response and recorded route validation. Carry
T5/T6 browser/scoring integration forward without claiming physical or city-wide
shade acceptance. Do not merge this PR without its explicit approval.
