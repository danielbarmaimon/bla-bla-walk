# PET map and route integration

State: implementation ready for review · Branch: `feat/pet-route-integration`

## Done

- Added the Basel-Stadt daytime PET WMS as a toggleable online map overlay with source attribution.
- Added route PET class-distance estimates to the canonical route feature and generated browser contract. The online map API attaches these metrics to the same two demo routes used for display.
- Sampled the WMS-rendered raster at its 10 m grid and mapped its colours to the published PET class legend. Unsupported image size, unavailable source and unknown pixels remain explicit.
- Saved route summaries stay marked stale in offline mode; the map overlay is disabled offline.
- Updated the source register, design, README and decisions. M4 can read the same `MapFeature.pet` data from `/api/map?mode=online` or a prepared snapshot.

## Limits

- This is a fixed modelled clear-summer 14:00 scenario, not a forecast or live weather.
- WMS GetFeatureInfo returned no pixel values. Route distances therefore come from classification of rendered WMS colours against the published legend. The implementation does not average PET degrees or produce a combined route recommendation.
- T6's full shade journey and M4's scripted phone UI remain separate open work. The API now carries the PET summary needed for that phone flow; spoken step generation does not yet place these classes into turn-by-turn speech.
- No tests were run, per session instructions.

## Next

1. Review the online demo at `/?mode=online`; toggle PET, inspect both route lines and compare the distance in each PET class.
2. When continuing M4, include the route's PET summary and fixed-scenario explanation in its accessible transcript. Keep turn-by-turn claims limited to evidence present on each instruction's own segment.
