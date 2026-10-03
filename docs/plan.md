# Revised build plan: layered map, shade, two routes

Based on [design](design.md). The team confirmed two-route comparison and current-time shade across Basel. The implemented stack is browser-native JavaScript/OpenLayers served by Python FastAPI, with canonical Python contracts and generated TypeScript declarations; no npm/Vite build is required. T0, T1, T2, T3, T4 and T9 are complete and merged; their original task labels remain crossed out below. T8 ingestion is merged, but spatial/scene/bridge acceptance remains open. Boundary and baseline walking rules are recorded in the source register and routing rules; cross-mode ranking and transit admission remain proposals. Owners for remaining tasks are unassigned; agree them by GitHub username. Listed paths may already exist or be created in the named tasks. Detailed task state belongs in handoff files.

Next-session priority: [M6 four-account journey work](#m6-next-session-priority--complete-the-address-to-journey-experience).

## M1: a map runs early; real layers replace fixtures independently

### Chunk A — parallel preparation (disjoint files)

#### ~~T0 Finish layer admission and city-wide shade feasibility~~
Owner: unassigned
Needs: nothing
Files: docs/SOURCES.md, data/source-manifest.json, data/tile-inventory.json
Done when: one basemap request and representative licensed raster downloads succeed; a pinned Basel boundary and full surface/terrain tile inventory record versions, units, NoData, terms and surrounding occluder coverage. Include urban centre, vegetation, tall-building and border samples. Identify mismatched surveys, missing tiles, cross-border gaps and service constraints. Measure sample processing cost and estimate full-city storage/workload; define an acceptance latency and memory budget before building the full-city processing pipeline.
Notes: existing audit is a starting point, not completion. Accept IWB only within agreed noncommercial terms, omit photos. Tree licence notice is inspected; verify feature access. PET and forecasts are optional; they do not block the core map.

For construction obstacles, inspect dataset 100335 for usable geometry, dates, closure semantics, update frequency and coverage. A worksite is blocked only when authoritative data confirms it; otherwise display a caution or unknown.
For optional bus and tram alternatives, check the 2026 GTFS timetable for BVB/BLT coverage, stops, access terms and usable trip times. Verify operator coverage in GTFS-RT Service Alerts; use alerts as service warnings unless they provide enough detail to route the detour. API access requires a key. Keep scheduled timetable evidence separate from live service status. Transit remains unavailable in the app until this admission succeeds.

For broader emergency notices, check Alertswiss separately from MeteoSwiss weather data. MeteoSwiss relays Alertswiss alarm-level messages through its app, but this does not confirm that its open-data feed carries the full Alertswiss stream. Verify whether a machine-readable Alertswiss feed is currently available and reusable before integration.

For rest stops, use Basel-Stadt's official cool-room list as a curated starting point. Verify current opening hours, visitor access, accessibility and any conditions; do not infer that churches or shops are open, cool or air-conditioned. Check whether the page has a reusable machine-readable feed. For outdoor stops, inspect tree-canopy coverage dataset 100357 and OpenStreetMap parks (`leisure=park`) and benches (`amenity=bench`). Verify dataset terms, freshness and local completeness; tree canopy is not a guarantee of shade at a given time, and mapped benches may lack details such as covering or accessibility. Label evidence and unknowns separately; don't call a location safe based on its category alone.



#### ~~T2 Agree one walk and comparison rules~~
Owner: unassigned
Needs: nothing
Files: docs/routing-rules.md, data/scenarios.json
Done when: the team selects one demo area/start/destination, explains the current workaround and one domain pitfall, and approves examples for shade-vs-distance, water access, blocked segments, and unknown data. Specify walking-speed/stop assumptions, acceptable detours, metrics and denominator rules. Recommend an eligible route using adjustable preference weights while preserving side-by-side metrics and manual choice. Agree criteria, fixed normalization ranges, default weights and unknown/stale completeness rules; constraints stay outside weights. Include ties, all-zero weights and examples where changing weights changes the winner. Do not invent health thresholds or shade cooling degrees.

#### ~~T3 Define the map and comparison screen~~
Owner: unassigned
Needs: nothing
Files: docs/style-guide.md
Done when: a reviewable screen includes layer toggles, readable legends, provenance/times, Now/departure time, two route cards, coverage boundary and stale/unknown states; keyboard and non-colour-only explanations are specified.

### Chunk B — foundation (can begin alongside preparation)

#### ~~T1 Build the smallest map foundation~~
Owner: unassigned
Needs: nothing (stack decision is recorded; verify the basemap endpoint within T1)
Files: README.md, docs/decisions.md, index.html, src/main.js, src/map.js, src/theme.css, src/interfaces.ts (generated), src/snapshot.schema.json (generated), config/browser-assets.json, scripts/fetch_browser_assets.py, backend/export_contract.py, backend/pyproject.toml, backend/requirements.txt, backend/bla_bla_walk/main.py, backend/bla_bla_walk/interfaces.py (canonical), backend/tests/test_contracts.py, backend/tests/test_browser.py
Done when: a fresh checkout starts with documented commands, displays a real Basel basemap, toggles two labelled fixture layers, and shows feature provenance and missing/stale states. One shared contract supports later observations, shade and routes; consumers have explicit owned paths before parallel work begins.
Notes: implemented as browser-native JavaScript/OpenLayers served by FastAPI, replacing the original Vite/npm proposal as recorded in docs/decisions.md. Keep Python models canonical and generate client declarations/schema; actual model changes require a decision line. Use the project virtual environment, pinned Python requirements and checksum-pinned browser assets. Do not install globally. Fixtures must not masquerade as live data. Follow the accepted T3 guide.

## M2: real layers, calculated shade and route alternatives

### Chunk C — parallel after T1 (T0/T2 inputs as listed)

#### ~~T4 Connect current observations and fountains~~
Owner: unassigned
Needs: T1, relevant T0 source admission
Files: backend/bla_bla_walk/adapters/temperature.py, backend/bla_bla_walk/adapters/fountains.py, backend/tests/test_observations.py, data/fixtures/observations.json, data/fixtures/fountains.json
Done when: recent values join stations by ID, each point displays observation age, IWB fountains retain type/unknown and attribution, and failed requests retain a visibly stale last-good snapshot. Fetch latest per station, bound responses and follow source cadence.

#### T8 Prepare reusable surface/terrain geometry
Owner: unassigned
Needs: T1, T0 city boundary and inventory
Files: backend/bla_bla_walk/geometry.py, backend/tests/test_geometry.py, scripts/prepare_geometry.py, config/geometry.json, data/geometry/ (local generated rasters), data/preparation-summary.json
Done when: every tile intersecting the city boundary is prepared or has an explicitly documented data gap; geometry renders aligned at centre and boundary reference points. Use the configured 1m horizontal cells and 2m elevation steps, apply the stored band scale before interpreting heights, and preserve NoData. Include buffered occluders, versioned geometry, coordinate/vertical system and native source resolution. Test seams, survey mismatch, border gaps and bridges. Document resumable tile preparation and storage/memory budgets; subdivide ingestion into separately verified batches if needed.
Notes: the compact ingestion/mode preparation handoff records implementation and downloaded evidence. Complete spatial/scene/bridge acceptance separately; do not mark the parent T8 complete solely because all available files downloaded. Native 2m terrain is resampled onto the 1m storage grid without adding detail; surface max aggregation and height quantization need scene validation.

#### ~~T9 Provide two checked walking alternatives~~
Owner: unassigned
Needs: T1, T2
Files: backend/bla_bla_walk/adapters/routes.py, backend/tests/test_routes.py, data/routes/demo.geojson
Done when: two routes connect the agreed endpoints using licensed, checked walking geometry, with distance/duration and available access restrictions. Store provenance and snapshot date. Routes outside calculation coverage are marked unsupported.

#### T18 Review route modes and verify transit feasibility (proposed)
Owner: unassigned
Needs: T0 source admission follow-up; T2 routing proposal
Files: docs/routing-rules.md, docs/style-guide.md, docs/SOURCES.md, data/source-manifest.json, docs/decisions.md
Done when: the team reviews Fastest overall, More shade, manual choice and the optional five-minute detour limit. Agree mode ranking and evidence labels. Verify BVB/BLT timetable access, coverage, terms, stop and transfer data, and usable journey times. Separately verify GTFS-RT alert access, key handling, operator coverage and freshness. Decide whether evidence supports scheduled trips, live disruption status, both or neither. Record gaps explicitly. Do not start transit integration unless its required inputs are admitted.

#### T19 Provide a transit-assisted candidate (conditional)
Owner: unassigned
Needs: T1, T2, T18 admitted data; T9 for checked walking legs
Files: backend/bla_bla_walk/adapters/transit.py, backend/tests/test_transit.py, data/fixtures/transit.json
Done when: a candidate includes checked access/egress walking legs, ride/wait/transfer durations, stop access state, source provenance and a clear scheduled or live label. Waiting shade stays unknown without stop evidence. Confirmed closures and unavailable service cannot appear as usable legs. If T18 does not admit a source, record the unavailable state and leave walking comparison usable.

### Chunk D — shade after prepared geometry

#### T10 Calculate and serve time-dependent shade
Owner: unassigned
Needs: T8
Files: backend/bla_bla_walk/shade.py, backend/bla_bla_walk/shade_cache.py, backend/tests/test_shade.py
Done when: current/selected timestamps produce direct-sun shadow masks for requested viewports and route corridors anywhere within Basel with requested/effective time and geometry version. Simple known-object cases verify direction/length, and spot checks compare with an independent reference. Measure cold/warm-cache latency, concurrency and tile-seam consistency across representative city views; test low sun/night, missing cells, occluder boundaries and canopy receivers. Unsupported cells stay unknown.
Notes: sun geometry changes with time; surveyed geometry does not. Consume scaled geometry through the geometry reader, not raw int16 codes. Validate the configured 1m grid and 2m height steps against unquantized known-object and independent real-scene references, including changed shadow edges and route-score sensitivity; the earlier 2m-grid kernel timings are historical and cannot establish the new pipeline's performance. Benchmark five-minute buckets and lazy tile/corridor calculation before adopting them; version cache keys by geometry/preparation version, cell spacing, height step and effective time. Measure cache size at 1m (four times the cells of the former 2m output). New requests must not wait for a full-city recomputation. Offline shade requests use local geometry and ephemerides without external calls; unavailable inputs remain unknown. Do not use relief hillshade or tree buffers as actual walking shade.

### Chunk E — route metrics after shade and routes

#### T5 Compare eligible trip options
Owner: unassigned
Needs: T10, T9, T2; T18/T19 only if transit sources pass admission
Files: backend/bla_bla_walk/evaluation.py, config/routing-rules.json, backend/tests/test_evaluation.py
Done when: walking candidates show shaded/unshaded/unknown metres and percentages at departure plus cumulative walking time. Where T19 is admitted, compare complete door-to-door time across walking and transit candidates, keeping walking, waiting, ride, transfer and stop time separate. Provide Fastest overall and More shade choices, preserve manual choice, and explain every recommendation. Do not score transit ride duration as walking time or infer shade for indoor/onboard segments. Unknown coverage cannot gain credit; known blocked paths cannot become eligible. Handle ties and insufficient evidence. Weight changes rescore cached metrics without repeating shade calculations.

## M3: complete journey and repeatable demonstration

### Chunk F — in order

#### T6 Connect and verify the journey
Owner: unassigned
Needs: T4, T5, T3; T19 only if transit sources pass admission
Files: src/map.js, src/main.js, src/comparison.js, src/theme.css, backend/bla_bla_walk/main.py, backend/bla_bla_walk/snapshots.py, backend/tests/test_browser.py, README.md
Done when: narrow-screen and keyboard users toggle layers, inspect freshness, choose Fastest overall or More shade, compare eligible trip options, and change departure time. If transit is admitted, show door-to-door duration and each trip leg with scheduled/live status. Keep the five-minute detour option clear. Pan and compare across the city; test source failure, calculation failure, tile seams, city-edge unknowns and outside-coverage behaviour; show effective time and route explanation without implying measured cooling or overall safety. Verify the complete journey in online external-server mode and local offline mode with downloaded geometry/imagery and dated provider snapshots. Offline makes zero external requests; missing downloads are explicit. Keep source observation times separate from locally calculated shade time; transit needs a saved timetable/candidate or an explicit unavailable state offline.
Notes: screen and journey implementation are merged. The [T6 acceptance record](../handoff/t6-integration.md) records the verified local offline journey and remaining online external-server check. Keep T6 open until that check passes; prepared datasets remain local to each validation/deployment machine.

#### T7 Prepare the five-minute pitch, 42-second hackathon reflection and demo fallback
Owner: unassigned
Needs: T6
Files: docs/pitch.md, docs/demo.md; media kept locally
Done when: prepare a presentation timed to exactly 5 minutes for the solution plus exactly 42 seconds for the team's HackAmRhein experience. The five-minute story covers the problem, what was built, how it works, what makes the approach interesting, and a live demo where possible. Include concise sources/licences, AI assistance, and limitations; distinguish measured, synthetic, saved, unavailable and unvalidated behaviour. Keep the final 42 seconds for what the team learned, what surprised them, what broke, or what they will remember. Provide likely jury questions with short evidence-based answers and a tested fallback for any live-demo failure. Rehearse the whole 5:42 twice with a timer, decide who speaks and clicks, and trim after the first run. Verify the team submission form is completed before the build cutoff, 14:59 on Sunday 4 October 2026. The venue is FHNW Dreispitz, Dornacherstrasse 394, Basel; doors open 13:30, building ends at 14:59, the introduction runs 15:00–15:30, presentations start at 15:30 in random order, and doors close at approximately 17:00. Record the final presentation file and backup location in the runbook. Do not imply the live shade and route journey works until T6 acceptance passes; a dated saved scenario or recording is a fallback, not a live calculation.

## M4: people without smartphones can follow a prepared route in a transparent phone simulation

Priority: after the core web demo (M3). This milestone reuses the same checked routes and evidence as the map. It does not include live phone service, collecting real addresses or emails, or actually sending printed maps.

### Chunk G — validate human wayfinding

#### T11 Validate landmarks and barriers on a demo route
Owner: unassigned
Needs: T7, T9
Files: docs/future-features.md, data/fixtures/call-scenarios.json
Done when: a short walk-along or sketch-map check on a prepared route records which global and local landmarks people recognize, confusing decision points, and reported barriers. Each cue/barrier has evidence, a check date and a known/unknown state. Findings consider different levels of route familiarity and omit participant names and contact details.

### Chunk H — agree and build the spoken directions (in order)

#### T12 Agree the spoken instruction format
Owner: unassigned
Needs: T11
Files: docs/future-features.md
Done when: the team agrees a short spoken step format with one maneuver at a time, a broad orientation cue when verified, a nearby landmark, a street-name fallback when available, and plain wording for missing or uncertain information. Examples cover a known landmark, an unfamiliar landmark and an unknown barrier. Do not promise safety or passability without evidence.

#### T13 Generate route-backed spoken steps in the Python backend
Owner: unassigned
Needs: T12, T5, T9
Files: backend/bla_bla_walk/interfaces.py, backend/bla_bla_walk/instructions.py, backend/tests/test_instructions.py, backend/export_contract.py, src/interfaces.ts, src/snapshot.schema.json, docs/decisions.md
Done when: the backend produces one structured spoken step per maneuver from the same route and evidence used by the map, carrying cue/source freshness and explicit unknowns. Use the agreed format and validated landmarks only. Define the shared contract through hack-interface; regenerate browser types/schema and add its decision line in the same change.

#### T14 Build the simulated call and map-request flow
Owner: unassigned
Needs: T13, T6, T7
Files: src/call-demo.js, src/main.js, src/theme.css, backend/tests/test_browser.py, docs/demo.md
Done when: a person chooses a prepared Basel trip, hears one instruction at a time, can repeat or slow it down, and can follow an accessible transcript. If browser speech is unavailable, the simulation still shows the scripted spoken lines. The caller can choose postal delivery or a neighbour's email and sees a generic simulated confirmation; the demo never asks for real contact details or sends anything. Missing and unverified route information remains explicit.

## M5: people can share timely map reports

This remains after the phone-access prototype in the team's priority order. `Needs` below lists actual technical dependencies.

### Chunk I — define the report rules

#### T15 Define shared-report rules and storage
Owner: unassigned
Needs: T1, T2
Files: docs/reporting-rules.md, docs/decisions.md
Done when: the team approves report categories, optional note limits, anonymous-by-default handling, confirmation/resolution and flagging behaviour, expiry, moderation, rate limits, and a persistent-storage approach. Examples cover a broken fountain, a closed place and a blocked path. Rules show report age and uncertainty without calling places safe.

### Chunk J — build the API and map experience (in order)

#### T16 Store and serve shared reports
Owner: unassigned
Needs: T15, T1
Files: backend/bla_bla_walk/reporting.py, backend/bla_bla_walk/main.py, backend/tests/test_reporting.py
Done when: reports persist across reloads, validate their category and location, receive server timestamps, expire by the agreed rule, and support confirmation, resolution and flagging. Apply the agreed rate limits; reporter identity is not collected by default.

#### T17 Add reports to the map
Owner: unassigned
Needs: T16, T6
Files: src/map.js, src/main.js, src/reporting.js, backend/tests/test_browser.py
Done when: a person can submit a map report, see current reports with age and status, confirm or resolve one, and flag a questionable report. Closed or broken items are visibly reports, not verified safe-stop data.
## Not scheduled yet

Live phone numbers/calls, actual postal or email map delivery, and volunteer accompaniment stay outside this plan. Re-plan them after the scripted call has been tried with users and the team has agreed on cost, privacy, reliability, safeguarding, and operating responsibilities.


## M6: next-session priority — complete the address-to-journey experience

This is the next work queue, ahead of the optional M4/M5 extensions. The team will assign GitHub usernames tomorrow; **A, B, C and D below are four temporary account lanes**, not the earlier six team slots or plan-chunk letters. They express file ownership, not participant identities. No application changes are included in this planning PR. Existing parent-task acceptance gaps remain open.

### Start together safely

1. Complete T20 once, then let four separate accounts work in their own clones from the same merged baseline.
2. Claim a lane in its task handoff before starting; assign usernames in TEAM.md at the team sync. Do not launch four chats against the same working directory.
3. Run **A: T21 → T22**, **B: T23 → T24**, **C: T25 → T26**, and **D: T27 → T28** concurrently. Tasks in each lane are sequential because they have one owner; no task depends on another lane's implementation during this wave.
4. C integrates the backend in T29 while D integrates the browser in T30 against T20's frozen contract. D can use contract fixtures before T29 lands. T31 verifies the joined result after both merge.
5. Only T20 owns canonical/generated contracts. Only T29 touches shared backend entry points/evaluation; only T30 touches shared browser entry points/map/theme/index. Feature lanes export modules and focused tests. Shared docs are consolidated by T31; each earlier task keeps evidence and source notes in its own handoff. Contract changes go through the T20 owner in a separate reviewed checkpoint.

| Lane | First task | Next task | Integration | Exclusive area during the parallel wave |
|---|---|---|---|---|
| A | T21 route-wide landmarks | T22 maneuver directions | Supplies modules to C/D | Landmark preparation and journey instruction modules |
| B | T23 shade diagnosis | T24 shade corridors and overlay | Supplies modules to C/D | Geometry/shade implementation and a separate overlay module |
| C | T25 construction admission | T26 closure-aware route policy | T29 backend | Construction data and candidate/closure policy |
| D | T27 simple start form | T28 options/loading UX | T30 browser | Isolated trip form/options/progress components |

The targets below are checkpoints of roughly 30–90 minutes, not promises that city-wide validation, source discovery or a routing-engine replacement will fit that time. If a checkpoint cannot establish its acceptance, record the exact gap and split the follow-up before continuing. Each task uses a fresh chat, a task branch, relevant checks, its own handoff and a reviewed PR. Merge needs explicit approval for that PR. No external deployment is required.

### Shared prerequisite — in order

#### T20 Establish the common baseline and freeze the journey contract
Owner: D (temporary coordinator; username assigned tomorrow)
Needs: this planning PR and the reviewed feature stack through PR #48 on merged main
Files: backend/bla_bla_walk/interfaces.py (canonical), backend/export_contract.py, generated src/interfaces.ts and schemas, backend/tests/test_journey_contracts.py, data/fixtures/journey-contract.json, docs/decisions.md, handoff/T20.md
Done when: all four clones start the same accepted app with address search, network routes, amenities, temperature, badges and icon clusters. A shared fixture covers two distinct candidates, one candidate, no route, unsupported shade, closure caution, confirmed blockage, pending calculation, failure and cancellation. Existing callers still run. Every lane can implement against the same versioned contract without editing it.
Notes: review/merge PRs #43–#48 in their dependency order only after approval; do not assume this local branch equals main. Record actual resulting commit and data preparation requirements. Contract fields must carry candidate ID and geometry identity, endpoint/departure identity, ordered maneuvers and distances, source/effective times, shade/exposed/unknown/night evidence, construction certainty and active interval, job progress/errors, independent Fast and Recommended roles, and a selected candidate. Fast and Recommended may reference the same candidate; missing evidence cannot manufacture a recommendation. Keep the existing unknown-access eligibility rules; any change needs a team decision. Freeze component/function signatures and endpoint ownership in the handoff. Regenerate declarations and schema and add the contract decision in the same commit. This prerequisite does not depend on full T8/T10/T6 acceptance and must not claim it.

### Four lanes — parallel, disjoint files

#### T21 Show relevant landmarks for every selected route
Owner: A (username assigned tomorrow)
Needs: T20
Files: src/route-landmarks.js, scripts/prepare_landmarks.py, config/landmarks.json, backend/tests/test_route_landmarks.py, backend/tests/test_route_landmarks_browser.py, local .cache/landmarks.json, handoff/T21.md
Done when: at least the saved pair and two different Basel address pairs have route-near landmark candidates with source metadata. Turning Landmarks on/off produces/removes markers in a focused browser harness; switching routes changes the candidates and clears old markers. It works without a demo-route-a special case. Missing saved data gives an explicit unavailable state. Landmark points remain at their source locations.
Notes: reuse admitted OSM/source work and existing WAYFINDING_PLACES as dated samples only. Choose useful named public features, bounded queries and route-distance filtering; omit personal/contact tags. A mapped landmark is a candidate, not a verified visible or familiar navigation cue. Physical wayfinding validation remains T11. Export marker candidates for T30; do not edit src/main.js or src/map.js.

#### T22 Produce actual ordered maneuver steps for arbitrary walking routes
Owner: A (username assigned tomorrow)
Needs: T20
Files: backend/bla_bla_walk/instructions.py, src/journey-steps.js, backend/tests/test_journey_instructions.py, backend/tests/test_journey_steps_browser.py, handoff/T22.md
Done when: route-provider maneuver payloads become ordered start/turn/continue/arrive instructions with available street names and per-step distance, bound to the exact route ID/geometry. The saved alternatives also have truthful steps. Switching between two routes changes the displayed sequence below the map; a second address pair never shows SBB/Marktplatz text. Missing maneuvers say directions unavailable rather than inventing turns from sampled vertices. Water/rest prompts insert in route order, including each 15-minute walking milestone before arrival.
Notes: lane A normally picks this after T21, but there is no technical dependency on landmark preparation. Use the T20 model. Parse maneuvers in a pure module against provider fixtures; T29 owns requesting and attaching provider steps in adapters/walking.py. Retain walking-speed/stop assumptions, handle roundabouts, unnamed streets, endpoint snapping and empty replies. Keep unverified landmarks separate from confirmed turns. This web task does not mark the spoken phone tasks T12/T13 complete. T30 owns placement and selection wiring.

#### T23 Diagnose shadow calculation, credit and display
Owner: B (username assigned tomorrow)
Needs: T20
Files: backend/tests/test_shade_journey_diagnostics.py, config/shade-service.json, handoff/T23.md
Done when: a reproducible evidence table follows selected departure → prepared geometry/footprints → /api/shade → route samples → comparison score → map visibility for both saved routes and an arbitrary address route. A known building casts a shadow of checked direction/length at two daylight times; night, low sun, missing data and seams remain distinguishable. The handoff identifies which failures are missing preparation, unsupported coverage, calculation, eligibility or UI wiring, with cold/warm timings.
Notes: casting shadows from real geometry was planned and a building-only approximation exists. Reuse the accepted building footprints plus surveyed/explicit metre heights; do not restart the raster pipeline without a demonstrated gap. Inspect the current finite flat-ground model and original stricter survey implementation. Trees and terrain do not currently cast shadows. Temperature/PET are separate evidence. Diagnose before changing algorithms; do not relax unknowns to make a route win. Budget/algorithm follow-ups beyond this checkpoint require a split task.

#### T24 Serve shade for selected route candidates and display real shadow areas
Owner: B (username assigned tomorrow)
Needs: T20, T23
Files: backend/bla_bla_walk/shade_service.py, backend/bla_bla_walk/route_shade.py, backend/bla_bla_walk/building_shade.py, backend/bla_bla_walk/shade_geometry.py, scripts/prepare_building_shade.py, config/building-shade.json, src/shadow-overlay.js, backend/tests/test_shade_candidates.py, backend/tests/test_shadow_overlay_browser.py, handoff/T24.md
Done when: two supplied route candidates can obtain bounded departure-plus-traversal shade evidence without requiring fixed demo IDs. A focused map harness draws georeferenced shaded/unknown/night cells for a supported viewport at the selected effective time; changing time replaces old cells. Route-line shade samples and area shadow masks are clearly different outputs. Missing caster/receiver/halo coverage stays unknown, and stale jobs cannot overwrite a new trip. Cold/warm/concurrent timings and source coverage are recorded.
Notes: use existing bounded workers and versioned cache keys; prepare missing building footprints explicitly before serving. Split large corridors into bounded requests; never trigger a full-city recomputation. Preserve surveyed scale/NoData, finite reach and stated building-only approximation. Export overlay mounting/updating APIs; T30 owns map.js wiring and layer order with the temperature gradient. Full tree/terrain/physical validation remains outside this checkpoint. A successful saved-pair overlay alone does not complete arbitrary-route acceptance.

#### T25 Admit a spatial, dated construction/closure source
Owner: C (username assigned tomorrow)
Needs: T20
Files: scripts/prepare_construction.py, backend/bla_bla_walk/adapters/construction.py, config/construction.json, data/construction-source-manifest.json, backend/tests/test_construction_admission.py, local .cache/construction.json, handoff/T25.md
Done when: current official source inspection records licence, geometry/CRS, retrieval/update cadence, active start/end times and exact pedestrian-closure meaning. Examples cover an active confirmed walking closure, a worksite caution without confirmed closure, an expired worksite and missing geometry. If no usable authoritative spatial source is found, the handoff names what is missing and a next source-verification action; routing closure admission remains open.
Notes: the existing audit of dataset 100335 found no geometry or structured pedestrian closure field. Check a spatial permit/closure layer and a reliable join separately; do not place sites by guessing coordinates from street descriptions. Do not treat every construction project as impassable. T31 consolidates verified admission into docs/SOURCES.md. Do not import arbitrary linked documents without checking rights and semantics.

#### T26 Apply construction constraints and establish feasible rerouting
Owner: C (username assigned tomorrow)
Needs: T20, T25 admitted spatial evidence (otherwise this task remains blocked)
Files: backend/bla_bla_walk/construction_policy.py, backend/bla_bla_walk/route_candidates.py, backend/tests/test_construction_policy.py, backend/tests/test_route_candidates.py, handoff/T26.md
Done when: confirmed active pedestrian closures intersecting a route make it ineligible; caution-only worksites generate a dated reason without becoming a hard block. Test time-zone boundaries, expiry, nearby nonintersecting worksites and unknown freshness. A checked street-following alternative avoids a confirmed closure and its added distance/time and reason are returned. If every available candidate is blocked or the router cannot avoid the affected edges, return unavailable and record the routing capability gap.
Notes: verify the chosen provider/engine can avoid the actual closed edges. The current FOSSGIS candidate response is not proof of dynamic avoidance. Filtering returned alternatives is useful but cannot promise a new detour; never repeatedly retry the same request or draw a straight bypass. If an additional local graph/provider is necessary, propose and split that implementation after the capability check. C owns provider routing changes later in T29. Closure certainty must stay outside preference weights.

#### T27 Build a concise start form with nearby destination shortcuts
Owner: D (username assigned tomorrow)
Needs: T20
Files: src/trip-form.js, src/trip-flow.css, config/quick-places.json, backend/tests/test_trip_form_browser.py, handoff/T27.md
Done when: a mobile/keyboard user sees Start, Destination, Departure time and one Calculate action, with Now and nearby-place shortcuts. Selecting a shortcut supplies a real admitted location; proximity follows the selected start or permitted GPS location. Missing location/search data has a short helpful state. A focused harness mounts the form against T20 fixtures without changing existing app entry points.
Notes: preserve address search and GPS/map-pin fallback; no fake store coordinates. Use existing actual supermarkets/places where their data permit the shortcut; opening/access unknowns remain accessible. Reduce explanatory prose in the main flow; detailed sources/limits stay in Information sources. Do not edit index.html, main.js or shared theme/map during the parallel wave. T30 connects the form once.

#### T28 Build Fast/Recommended choice and useful loading states
Owner: D (username assigned tomorrow)
Needs: T20, T27
Files: src/trip-options.js, src/trip-progress.js, config/trip-tips.json, src/icons/fast-forward.svg, src/icons/trees.svg (reuse if present), backend/tests/test_trip_options_browser.py, handoff/T28.md
Done when: one calculation state prepares both roles, then offers Fast with Lucide fast-forward and Recommended with Lucide trees. Cards show duration/distance, available shade, construction cautions and the concise evidence-based reason. Selecting a card opens its map/step view in the component harness. Pending work shows real progress/status plus three or four concise preparation tips; success, failure, cancellation and retry behave correctly. Tips do not obscure errors or fake progress.
Notes: source generic tips from current official heat advice, e.g. carry water, prefer shade, take breaks, consider cooler times. Keep them nonpersonal and avoid absolute safety claims or invented medical thresholds. Include source URLs in the config for Information sources consolidation. Preserve source licence for local Lucide assets. When the same route wins both roles, explain it without drawing a duplicate; when shade/eligibility is unsupported, explain Recommended unavailable rather than assigning trees to an unverified shade winner. UI work uses T20 fixtures until T29 integrates real results.

### Integration — C and D can work in parallel against T20

#### T29 Connect a single trip calculation to both route roles
Owner: C (username assigned tomorrow)
Needs: T20, T22, T24; T26 only for admitted closure-aware rerouting
Files: backend/bla_bla_walk/main.py, backend/bla_bla_walk/adapters/walking.py, backend/bla_bla_walk/comparison_service.py, backend/bla_bla_walk/evaluation.py, config/walking-routing.json, backend/tests/test_trip_calculation.py, handoff/T29.md
Done when: one request for selected endpoints/departure fetches candidate walking geometry and maneuvers once, evaluates supported candidate corridors through the bounded shade workers, applies admitted closure constraints and returns Fast and Recommended roles in one cancellable job. Both become available together after completion. One/no alternatives, failures, stale replies, departure/endpoint changes and concurrent requests have checked behavior. No duplicate provider calls are made merely because there are two UI roles.
Notes: reuse T5 ranking/unknown/access rules and local source state. Fast means the lowest estimated walking time among usable checked candidates; Recommended explains its shade/detour/construction evidence. Ranking provider-returned alternatives is not global shade-optimal pathfinding. If alternatives/coverage are insufficient, state the gap rather than promise two distinct or shaded routes. Source discovery failures in T25 must not block unrelated walking UX: return construction unavailable explicitly, without marking T26 complete. New routing-engine integration, if needed, is a separate task after T26. T29 is the only backend entry-point owner.

#### T30 Connect the simple flow, two map routes and selected journey
Owner: D (username assigned tomorrow)
Needs: T20, T21, T22, T24, T27, T28 (T29 integration can be developed against fixtures; real acceptance needs it)
Files: index.html, src/main.js, src/map.js, src/comparison.js, src/layer-badges.js, src/route-planner.css, src/theme.css, backend/tests/test_trip_flow_browser.py, handoff/T30.md
Done when: Calculate once prepares Fast and Recommended, shows both available paths, and allows independent visibility plus a clear selected route. Selecting a route card or drawn path updates the journey below the map, amenities/rests, landmarks and temperature/shade display without showing old route data. Start page contains the requested three fields and nearby shortcuts with little prose. Map badges are smaller, centred, have no underline, and retain keyboard focus/aria-pressed and another visible active-state cue. The success text “Basel basemap loaded · live tile service” is removed from the main map; actual errors remain actionable and attribution remains present.
Notes: mount the isolated lane components, preserve icon clustering and active defaults, keep sources/limits collapsed at the end. Fast/Recommended selector icons are fast-forward/trees. Both role geometries appear when distinct; one geometry with dual roles must be explained. Keep temperature gradient visible independently from shadow areas; chosen route steps cannot come from an unselected option. Avoid nested controls, mobile overflow and source paragraphs in the main flow. T30 alone owns shared browser files; other lanes submit module hooks in handoffs.

### Acceptance — in order after integration

#### T31 Verify four-lane integration and prepare the local fallback
Owner: D coordinating; A/B/C verify their own evidence
Needs: T29, T30
Files: backend/tests/test_trip_acceptance_browser.py, README.md, docs/SOURCES.md, docs/style-guide.md, docs/demo.md, handoff/T31.md; dated fallback and screenshots remain local
Done when: a narrow-screen and keyboard walkthrough succeeds for the saved pair, two arbitrary Basel address pairs, reversed endpoints and a changed departure. Test both route selections, ordered directions, landmark toggles, shadows at two daylight times/night/missing coverage, closure vs caution vs expired site, clustered stops and every source/calculation failure. Record actual cold/warm/concurrent latency and chosen build commit. Existing address/route/temperature/amenity tests still pass. Local offline behavior makes zero external requests and missing data stays explicit. A dated saved output is tested and labelled saved, never live.
Notes: consolidate each lane's source/licence/evidence notes into the canonical docs and update the runbook for the real behavior. Keep no-external-deployment preference. Do not close original T8/T10/T6 acceptance gaps based only on these feature tests. If a lane is unavailable, show it explicitly and list its remaining task; do not declare complete shade/rerouting. Review every PR and run the privacy guard before commit/push. Only mark this task done after its whole check passes.
