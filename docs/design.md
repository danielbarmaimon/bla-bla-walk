# Bla Bla Walk

Track: Social impact · Updated: 2026-10-03
Status: agreed direction and scope; the grocery-first multimodal journey below is a proposal for team review. [Demo endpoints and domain defaults](routing-rules.md) are specified for T2. T1's runnable map foundation and T0's source/geometry inventory are merged to `main`. T8 prepares the pinned native geometry and explicit gaps; shade accuracy and performance remain for T10. See task handoffs for implementation state.

## Problem
People affected by heat, and caregivers planning on their behalf, need to understand shade, drinking water and walking effort together. A short route can leave someone exposed; a shaded detour may be impractical. The [routing rules](routing-rules.md) describe the selected demo walk, assumed current workaround and one concrete domain pitfall; the workaround is a scenario assumption rather than an observed participant habit.

## What we build
Proposed user experience: a mobile-friendly Basel map with independent data layers, city-wide calculated shade, and walking alternatives. The user chooses Fastest overall or More shade, sees the tradeoffs, and selects an eligible option. A transit-assisted option appears only when its sources and trip times pass admission checks.

The user scenario proposed for review is an older person travelling to a grocery store, such as a selected Migros. Show shade from trees and buildings, benches, refill fountains, and confirmed construction closures. Offer transit when door-to-door evidence makes it a useful alternative. Do not promise overall safety; show evidence and unknowns.

### Proposed journey flow (three minutes)
1. Open Basel, toggle sensor temperatures, fountains and calculated shade. Inspect a feature's source, timestamp and uncertainty.
2. Search for a grocery store and compare eligible trips. Keep the existing Basel SBB–Marktplatz walk as the current checked example; do not imply a specific Migros route is verified.
3. Choose Fastest overall or More shade. Show walking time/distance, shaded/exposed/unknown lengths, benches, fountains and confirmed closures. If transit is admitted, show walking access, wait, ride, transfers and schedule/live status separately.
4. Choose Now or another departure time. Recalculate shade along outdoor walking legs; show the recommendation and its evidence.
5. Disconnect a source: show retained observations as stale and saved shade results with their original effective time.

- Start with a mobile-friendly web map focused on heat in Basel.
- Explore routes to cooler destinations using shade, fountains, and known closures or accessibility barriers.
- Investigate public and aggregated data before committing to live integrations.
- Preserve access for people without smartphones; the phone-access concept and demo direction are captured in [future features](future-features.md), with implementation deferred until the core web-app demo is ready.
- Treat volunteer accompaniment and community assistance as a later phase, with operating and vetting arrangements still unresolved.
Coverage includes all Basel, rather than one neighbourhood. The T0 engineering boundary is pinned to Basel-Stadt canton, including Riehen/Bettingen; use the source register and inventory for exact extent and buffer gaps. Inventory city-wide geometry plus surrounding shadow-casting objects. Calculate requested map tiles and route corridors on demand. The first demo uses two checked walking alternatives; arbitrary-endpoint route generation is a later decision.

## Data
The [source register](SOURCES.md) is authoritative for endpoints, licensing, attribution, evidence and admission checks.

| Input | Source | Meaning / admission |
|---|---|---|
| Air temperature and stations | Basel 100009 / 100082 | CC BY 4.0; timestamped raw observations |
| Fountains | IWB / Basel 100008 | Noncommercial reuse with attribution; preserve drinking-type unknowns |
| Surface and terrain heights | swissSURFACE3D Raster / swissALTI3D | Swisstopo OGD terms; surveyed geometry for calculated shadows |
| Tree context | Basel 100052 | Canton CC BY terms and OSM incorporation notice; locations alone do not establish shade |
| Basemap and walking alternatives | Basel map service / OSM candidate | Verify basemap mapping/access; OSM attribution and database obligations apply |
| Optional context | Historical PET, MeteoSwiss forecasts, construction feed | Separate scenario, forecast and caution states; source admission remains required |
| Public transport | BVB/BLT GTFS and GTFS-RT | Proposed; scheduled times and live alerts need separate admission and freshness checks |

## How it is built
Chosen stack: OpenLayers browser UI and a Python FastAPI API/worker. At the T1 user's request, serve browser-native JavaScript modules directly from FastAPI without a JavaScript package manager or build step. Python models remain canonical, with generated TypeScript declarations for editor/JSDoc use and a generated browser validation schema. Pin browser distribution URLs/checksums and Python requirements. Rasterio prepares compact geometry and provides windowed raster access; T8 also keeps bounded native-grid 0.5 m preparation for validation; the shadow algorithm still needs validation. Keep geometry processing and versioned caches outside the browser. Hosting must support a worker and persistent geometry storage.

Browser code lives under src; adapters, geometry, shade and evaluation under backend/bla_bla_walk; domain values under config; licensed manifests under data. Large rasters and caches stay outside Git. T1 defines one authored Python interface, generates browser types, and checks cross-language fixtures. Actual interface edits include decision lines in the same commit. File ownership lives in the [plan](plan.md).

Build the basemap and a fixture API round trip first; add verified observations, geometry and routes independently. Use LV95 metres for geometry, checked coordinate conversion for display, terrain-level receivers and buffered surface heights for shadows. Preserve unknown cells and off-screen occluders. Evaluate shade at departure plus cumulative walking time. Cache versioned results; five-minute buckets require benchmarking. Validate canopy receivers, low sun, tile seams, bridges and borders.

Geometry preparation now targets 1m horizontal cells and 2m elevation steps; [config/geometry.json](../config/geometry.json) owns the values and [SOURCES.md](SOURCES.md#compact-geometry-and-offline-preparation) documents transformations and limits. The tile footprint remains 1km square with the admitted surrounding halo. This resolution is requested storage precision, not established shadow accuracy.

Use the same app in three explicit modes: synthetic fixtures, online provider data, or local downloaded imagery/saved provider layers. Online hosting places the API/geometry on an external server; offline use keeps a local server reachable without internet. Missing saved files remain missing, and offline observations keep their original timestamps and historical labels. The [README](../README.md) owns setup and operation commands. Disconnected phone/PWA installation is outside this implementation.

## Recommendation rules
Offer Fastest overall and More shade choices, with manual route selection retained. Compare public transport only when its source and trip-time evidence pass admission. Include walking access, waiting, transfers and riding in door-to-door duration; do not treat vehicle time as walking time or vehicle interiors as measured shade. The [routing rules](routing-rules.md) define walking metrics, weights and evidence completeness. Cross-mode ranking still needs team agreement. Show raw metrics and evidence; missing or stale data must not improve a score. Known access/blocking constraints stay outside preferences.

Waiting outdoors has unknown heat exposure unless stop shade or shelter data are available. Store search and arbitrary-endpoint routing are proposals; the current checked routes remain the fixed T9 pair until a destination and route source are verified.

## Later extension: shared user reports
Let users report a broken fountain, a temporarily closed place, or a blocked path. Reports appear as shared map alerts with a category, location, submission time and status; a short note is optional. Users can confirm, resolve or flag reports. Show report age and confirmation state so unverified reports are clear. Define expiry, moderation and rate limits before launch. Start without accounts or stored reporter identities. Do not label any reported place as safe. Choose persistent storage and abuse controls when this extension is designed; it is outside the core demo.

## Out of scope and approximations
No health profiles or stored location histories. Current-time shade is calculated from surveyed geometry, not observed cloud shadows or live canopy measurements. Foliage and gaps are approximate; unsupported areas stay unknown. Do not turn shade fraction into temperature/PET degrees. Historical PET remains a summer 14:00 scenario. City-wide shade is in scope; shared reports, volunteer matching and phone service remain extensions.

## Team and domain input
Owners remain unassigned until contributors choose tasks by GitHub username. Domain examples determine walking constraints, acceptable detours and water interpretation. Explore the look together with hack-design before or after the first map works.

## Risks and fallback
Preflight city-wide tile coverage, border occluders, survey alignment, memory and latency before promising current-time performance. Keep licensed geometry snapshots and dated calculation outputs. If a source/calculation fails, show a labelled saved scenario without a Now claim. Missing data must not become sunlit, cool or passable by default.
