# Daytime PET source recommendation

State: PET source audit and map/route integration complete on `feat/pet-route-integration`.

## Goal
Document Basel-Stadt Geoportal daytime PET findings and align the demo plan.

## Done
- Added official method, layer-model, catalogue, licence, and service-discovery references to docs/SOURCES.md.
- Recorded shade effects already included in PET, the 14:00 summer scenario, model resolution and source access checks.
- Updated docs/plan.md, docs/design.md, and docs/decisions.md to recommend PET for the first demo and defer arbitrary-time shadows.
- Kept route weighting and aggregation undecided; prevented duplicate shade cooling adjustments in the proposed rules.

## Next
- Review `handoff/pet-route-integration.md` and the updated source register for the implemented map and route flow.
- M4 should reuse `MapFeature.pet` and preserve the fixed-scenario explanation in its accessible transcript.

## Limits
PET is read from the public WMS as a rendered class map. GetFeatureInfo provides no numeric sample values; route distances are estimated from rendered pixels. This work does not validate real-world routes or forecast heat conditions.

## Resume prompt
Continue T0 using docs/SOURCES.md: verify access to Basel-Stadt daytime PET and record the exact dataset, endpoint, licence, format, values/classes, and missing-data behaviour before implementation.
