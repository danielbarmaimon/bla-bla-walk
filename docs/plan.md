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

**Short-session revision: at most two tasks per account.** A–D are temporary account lanes, assigned by the team tomorrow, distinct from the older six team slots. This replaces the longer T20–T31 launch sequence. PRs #43–#49 are merged; start from current main at or after `1554167`. There is no preliminary T20 task and no wait for a broad new contract. Reuse the current interfaces and APIs.

### Priorities and parallel start

| Lane | Task 1: start immediately, in parallel | Task 2 | Model / effort |
|---|---|---|---|
| A | **P0 · T22** reliable route-specific journey steps | **P2 · T21** landmarks, only if task 1 is ready | T22: GPT-6.1 Sol Medium; T21: GPT-6 Luna High |
| B | **P0 · T23** diagnose/repair existing shade pipeline | **P2 · T24** shadow-area overlay, only if task 1 is ready | T23: GPT-6.1 Sol High; T24: GPT-6.1 Sol Medium |
| C | **P1 · T25** verify construction source and routing gap | **P0 · T31** final walkthrough and local fallback | Both: GPT-6 Luna High; escalate source ambiguity to Sol Medium |
| D | **P0 · T27** concise start form and single Calculate action | **P0 · T30** route choice, map/steps wiring and loading UX | Both: GPT-6.1 Sol Medium |

P0 protects a usable, truthful demo. P1 resolves important missing evidence. P2 is optional polish: omit it before reducing integration, verification or fallback. Each task targets a 30–60 minute checkpoint; this is an effort estimate, not a deadline. One finished task is better than two half-connected tasks. Keep one reviewed checkpoint per task and a handoff with exact hooks/results.

All four first tasks can start now in four **separate clones**. A owns backend maneuver delivery and any strictly necessary additive canonical contract changes; B owns shade implementation and an isolated overlay module; C owns construction audit plus acceptance/runbook; D alone owns index.html, main.js, map.js, comparison.js and shared CSS. A/B expose modules and sample results for D; they never edit D's files. D can build against current fixtures while waiting for real modules. Coordinate a required contract addition through A; no other lane edits generated models. Each feature records source/evidence notes in its own handoff; C consolidates them in canonical docs during T31. Do not edit this plan from feature tasks. No external deployment.

### Task definitions — two per lane maximum

#### T22 Deliver truthful maneuver steps for the selected route
Owner: A (GitHub username assigned tomorrow)
Needs: merged baseline through PR #49
Files: backend/bla_bla_walk/adapters/walking.py, backend/bla_bla_walk/instructions.py, backend/bla_bla_walk/interfaces.py and generated declarations/schemas only if necessary, backend/export_contract.py only if necessary, src/journey-steps.js, backend/tests/test_journey_instructions.py, backend/tests/test_journey_steps_browser.py, docs/decisions.md for contract changes, handoff/T22.md
Done when: the provider requests real maneuver steps and returns ordered start/turn/continue/arrive instructions for two different Basel address pairs and their alternatives, tied to candidate ID/geometry. Existing saved routes have honest instructions without invented turns. Switching route changes the steps in a focused browser harness; a new pair never displays SBB/Marktplatz text. Missing maneuver evidence gives a concise unavailable message. The exported renderer supports route-ordered water/rest prompts, including 15-minute walking milestones before arrival.
Notes: reuse the existing POST /api/walking-routes MapLayer; optional additive fields only, with regenerated declarations/schema and a same-commit decision. Do not change backend/main.py or D's browser entry points. Keep street-name fallback, roundabout/unnamed-road cases and route identity tested. Supply D a small real/fixture payload and the mount/update signature. Spoken phone service and field validation remain deferred.

#### T21 Restore relevant landmark markers (optional second task)
Owner: A
Needs: T22; no new dependency on T20
Files: src/route-landmarks.js, scripts/prepare_landmarks.py only if needed, config/landmarks.json, backend/tests/test_route_landmarks_browser.py, local .cache/landmarks.json, handoff/T21.md
Done when: Landmarks no longer depends on demo-route-a. The saved pair plus another address route can get route-near named public candidates; switching routes clears old points and the toggle adds/removes markers in a harness. Original source positions and source dates remain intact. Missing data is explicit.
Notes: reuse existing admitted places before adding a download. Mapped/nearby is not verified visible/familiar. Export marker candidates for D to mount; do not edit main.js/map.js. If only known saved places are available, disclose limited coverage rather than claim city-wide landmarks. Skip this task if journey steps or integration are unfinished.

#### T23 Diagnose and repair the existing shade journey (first checkpoint)
Owner: B
Needs: merged baseline through PR #49
Files: backend/bla_bla_walk/shade_service.py, backend/bla_bla_walk/route_shade.py, backend/bla_bla_walk/building_shade.py only for demonstrated defects, config/shade-service.json, backend/tests/test_shade_journey_diagnostics.py, handoff/T23.md
Done when: evidence traces departure → verified local geometry/footprints → /api/shade → route samples → comparison result for the saved pair. Reproduce a known building at two daylight times, plus night/missing-input states, and record cold/warm timings. Fix a demonstrated defect within this pipeline or name the exact preparation/coverage/eligibility gap. Provide D checked sample evidence and the correct layer/progress hooks; no unknown cell receives shade credit.
Notes: real geometry casting already exists as a finite building-only flat-ground approximation. Reuse it; no raster pipeline replacement, new engine, tree/terrain promises or full-city recomputation. Arbitrary-route shade remains unavailable unless actually supported and tested. Missing access/eligibility can still prevent a recommendation even with shade samples. Keep the source/model/effective-time label. Do not edit main.py, canonical contracts or D's browser files. Diagnostic completion does not mean physical/city-wide T8/T10 acceptance.

#### T24 Draw supported shadow areas (optional second task)
Owner: B
Needs: T23
Files: src/shadow-overlay.js, backend/tests/test_shadow_overlay_browser.py, handoff/T24.md
Done when: an isolated OpenLayers overlay correctly georeferences actual /api/shade cells for one supported viewport, distinguishes shaded/unknown/night and replaces cells when effective time changes. The harness proves alignment and zero invented fallback shadows. D receives mount/update/dispose hooks using existing ShadeResponse.
Notes: this is a bounded display checkpoint, not arbitrary-route/city-wide backend expansion. Temperature gradient and route shade samples remain distinct. D alone wires map.js and layer stacking. Skip this task if pipeline repair or integration is unfinished; keep unsupported shade explicit.

#### T25 Verify construction evidence and feasible next routing step
Owner: C
Needs: merged baseline through PR #49
Files: data/construction-source-manifest.json, config/construction.json only if admitted, handoff/T25.md
Done when: current official source checks record terms, spatial geometry/CRS, dates/freshness and confirmed pedestrian-closure meaning. Record at least an active site, an expired site and a closure/caution distinction if the data support them. Inspect whether the current routing service can avoid those closed edges. Supply D a concise truthful construction-coverage/status message; if geometry or semantics are absent, state unavailable and identify the next source/action.
Notes: the audit of 100335 found no geometry or structured pedestrian closure field; recheck a spatial official layer/join before assuming it is usable. Do not guess locations from street text or make every worksite a blockage. **No new rerouting engine or live closure integration in this short session.** Admitted findings seed later T26. Keep evidence/source notes in the handoff for T31; no shared entry-point or contract edits.

#### T31 Verify the joined flow and keep a usable local fallback
Owner: C; A/B/D provide their checkpoint evidence
Needs: T22, T23, T25, T30; optional T21/T24 only if they are ready and merged
Files: backend/tests/test_trip_acceptance_browser.py, README.md, docs/SOURCES.md, docs/style-guide.md, docs/demo.md, handoff/T31.md; dated fallback/screenshots stay local
Done when: test the saved pair, two arbitrary address pairs, route switching, changed departure, keyboard/mobile layout, available shade and missing inputs, provider failure/retry, source details, stops and clusters. Check landmark/shadow overlays only if included. Verify construction status never implies live avoidance without admission. Record actual build commit, consolidate source/licence/limit notes, and test a dated saved fallback labelled saved, never live. Offline makes zero external requests and missing downloads stay explicit.
Notes: start preparatory smoke checks while other lanes work; final acceptance waits for their merged checkpoints. A test cannot declare unknown routes safe or close original T8/T10/T6 gaps. Preserve no-external-deployment preference. Do not add optional features during acceptance. Save fallback even if a feature must be omitted.

#### T27 Simplify the start form and calculation trigger
Owner: @ltorrecilla (T27 start-page UI; temporary lane D)
Needs: merged baseline through PR #49
Files: index.html, src/main.js, src/route-planner.css, src/theme.css, backend/tests/test_trip_form_browser.py, handoff/T27.md
Done when: mobile and keyboard users see Start, Destination, Departure time/Now, existing nearby-place shortcuts and one Calculate action with less prose. Preserve official address lookup and GPS/map pins. Changing fields clears stale results; Calculate resolves the selected pair through existing APIs once and begins supported comparison without asking the person to choose Fast/Recommended first. No extra geometry fetch occurs just to render two route roles.
Notes: use current endpoints and component code; do not build a second UI or broad new contract. Reuse actual admitted destinations, label illustrative shortcuts. Shade comparison currently supports the saved pair; preserve arbitrary-route unknowns. D owns shared browser files through T30. Use relevant checks and a demoable checkpoint before proceeding.

#### T30 Finish route selection, compact map controls and loading UX
Owner: D
Needs: T27; T22/T23 for their real integration; T21/T24 only if ready (current fixtures permit work while waiting)
Files: index.html, src/main.js, src/map.js, src/comparison.js, src/layer-badges.js, src/route-planner.css, src/theme.css, config/trip-tips.json, local Lucide fast-forward/trees icons (reuse if present), backend/tests/test_trip_flow_browser.py, handoff/T30.md
Done when: one calculation prepares available Fast/Recommended roles before the choice. Show both distinct supported geometries, then selecting Fast (fast-forward) or Recommended (trees) opens its map with the matching steps below. Route changes update stops, markers and temperature; supported shade evidence/overlay is mounted from B. Smaller centred badges have no underline, retain focus/aria-pressed and an alternate active-state cue. Remove the successful “Basel basemap loaded · live tile service” sentence from the main flow; keep errors and attribution. Pending work shows real status plus 3–4 concise officially sourced preparation tips, with working error/cancel/retry states.
Notes: reuse current APIs and ranking. If both roles share one route, explain it once; if only one alternative or unsupported shade/eligibility exists, offer manual route inspection and label Recommended unavailable. Never invent a shaded route, closure detour, fake progress or medical thresholds. Integrate A/B exports once; C supplies construction status. Keep sources/limits in Information sources. Do not wait for optional T21/T24; omit them clearly if unfinished. No full routing-engine rewrite or broad backend orchestrator in this session.

### Deferred: not tomorrow's launch queue

T20 broad shared-contract redesign, T26 construction-driven rerouting, T28 standalone new trip component system and T29 new arbitrary-route calculation orchestrator are deferred. The short plan reuses existing contracts and puts essential UI/loading work inside T27/T30. Also defer city-wide optimal shaded-path search, tree/terrain shadows, new routing engines, transit, phone/report features and external deployment. Preserving available evidence and a tested fallback takes priority over claiming these exist.

Full T8/T10/T6 acceptance remains unchanged. The presentation must reflect the actual merged build, including unavailable recommendation, construction, directions or shade states. Launch prompts and model settings are in TASK_START.md.

## M7: inspect conditions along a calculated route

Follow-up after the M6 joined-flow acceptance; this is outside the short-session launch queue.

#### T32 Show details for a selected route point
Owner: unassigned
Needs: T31, T30
Files: src/route-node-details.js, src/map.js, src/route-planner.css, backend/tests/test_route_node_details_browser.py, handoff/T32.md; extend an existing interface only if the current route response cannot supply required values, with its decision line in docs/decisions.md
Done when: hovering over a calculated route point on desktop, or tapping/clicking it on touch, opens a compact readable detail card for that point. It shows the corresponding temperature, remaining distance to the destination and estimated time remaining; it includes the local route-segment shadow percentage only when supported data is available and otherwise omits that row. The card stays near the selected point without covering the route or controls, can be dismissed, and works with keyboard focus. Moving to another point updates the values; selecting another route clears or updates the selection. Missing temperature or route-progress data is labelled unavailable rather than guessed.
Notes: derive remaining distance and ETA from the selected route's geometry and supported timing data. Use the existing temperature and shade results; do not interpolate or imply measurements the sources do not support. Keep hover transient and tap/click selection usable on touch screens.
