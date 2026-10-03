# Route fountains, benches and rest candidates

Status: done locally; publication pending. Branch: feat/route-rest-stops, based on routing PR #44.

## State

User requested fountains, benches and stops along any calculated route. Stops are rest candidates; transit remains unavailable. The app at http://127.0.0.1:8004 uses real saved IWB fountains and sanitized admitted OSM benches/park centres independently of synthetic example overlays.

## Done

- Canonical rest subtype/amenities response, generated contracts and decision line.
- Fixed canton extent preparation with bounded download and boundary clipping; 2,142 mapped candidates saved locally on 2026-10-04 with actual retrieval timestamps. Raw names/contact tags discarded.
- Every selected route filters candidates within 50m geometric proximity, displays WATER/BENCH/REST source-point markers (maximum 80) and a source-detail list. Optional sourced indoor candidates use the same rule. Access, condition, drinking and cooling remain unknown.
- Offline/example API makes zero external requests; missing data is explicit. Routing changes replace candidate sets; source-point clicks retain provenance.
- 285 full tests passed, including browser checks. Real Chrome routes: SBB to public venue, 118 network vertices and three benches; Freie Strasse to venue, 213 vertices, six fountains, eighteen benches and one rest candidate. No browser errors. Screenshot saved locally in .hack/route-stops-preview.png.
- README preparation/run instructions, source register and demo runbook updated. T7 static fallback does not claim this new interactive feature.

## Next

Publish the checked branch as a stacked PR based on #44. PRs #43 and #44 remain unmerged; merge only after explicit authorization for each PR. Saved source candidates still need field verification. Timed presenter rehearsals/submission receipt remain pending in T7.
