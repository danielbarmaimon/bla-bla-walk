# T10 — building-cast shadows along demo routes

Status: in progress — agreed approximation validated; sharing and main update pending.
Branch: feat/t10-receiver-validation

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
  and tag sanitization. Full regression: 142 passed, one browser test skipped;
  two additional focused checks added since that full run also pass.
- Reproduction and interpretation are documented in README and docs/SOURCES.md;
  physical/city-wide acceptance is retained in docs/future-features.md.

## Next

1. Bring this branch up to current origin/main, resolve shared-file conflicts
   without losing the new route UI, PET contract or independent compact audit.
2. Rerun contracts, complete regression, strict docs and privacy guard, then
   commit/push and create the review PR. Explicit approval is required to merge.
3. T5/T6 still own scoring and browser shade integration; do not claim those
   complete from the API checks. Many corridor cells deliberately remain unknown.

## Resume prompt

Finish the user-approved T10 building-shadow approximation on
feat/t10-receiver-validation. Use local .cache/buildings and data/geometry.
Complete validation and documentation, preserve unknown/night states and model
labels, then save and share for review. Do not restore the obsolete requirement
for independently observed ground before completing this agreed approximation.
