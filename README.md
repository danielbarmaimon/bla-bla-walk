# Bla Bla Walk

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

Bla Bla Walk is a proposed heat-aware walking route planner for Basel. It aims to help people who are more affected by heat, and their caregivers, compare routes using shade, drinking water, cooler places, and known obstacles.

## The problem

The shortest walk may involve exposed streets, few places to rest, or inaccessible crossings. The project explores how public environmental and map data could make those tradeoffs visible when planning a walk.

## Project status

The map supports online provider observations/fountain locations, a historical PET heat layer with route-class distances, downloaded offline maps and saved provider snapshots, and separate synthetic fixtures. The PET map overlay needs internet; saved route classes remain visible offline with a stale label. PET describes a fixed 14:00 summer scenario. FastAPI serves the browser and API; no JavaScript package manager or build step is required. Compact city geometry preparation is available. Exact-time route shade and weighted comparison are connected through background jobs; local geometry and building preparation are required. Downloading heights alone does not enable shade. See the [current preparation handoff](handoff/data-compact-offline.md). T8 also keeps a native 0.5 m preparation for geometry validation; see [T8's handoff](handoff/t8.md).

- [Design and demo proposal](docs/design.md)
- [Build tasks and acceptance checks](docs/plan.md)
- [Pick a task and start](TASK_START.md)
- [Recorded decisions](docs/decisions.md)
- [Future features](docs/future-features.md)
- [Proposed six-person work split](ROADMAP.md)
- [Team roles and shared-repository rules](TEAM.md)
- [Team collaboration guide](TEAMWORK.md)
- [Original meeting notes](notes/261002-001_Meeting_Heat-_and_Safety-Aware_Routing_Map_App-Summary.md) (historical source; see the design and plan for current proposals)

## Run locally

Use Python 3.12 or newer and keep internet connected. From the repository root,
run one command for your operating system:

Windows (PowerShell or Command Prompt):

```powershell
.\scripts\run-windows.cmd
```

Linux:

```sh
bash scripts/run-linux.sh
```

Open [the local app](http://127.0.0.1:8000/). Online mode is the default. Each
launcher creates or reuses `.venv`, installs pinned project dependencies, verifies
browser assets, restores missing committed shade inputs without replacing local
data, validates the building cache and downloads missing rest-stop data before
starting the server. Keep the terminal open; Ctrl+C stops the app. Pass another
port as the only argument if needed, for example `.\scripts\run-windows.cmd 8001`
or `bash scripts/run-linux.sh 8001`.

Both the server and browser need outbound HTTPS. When a coding tool asks for
network access, allow it for the launcher/server; a network-restricted preview
cannot search addresses or calculate provider walking routes. No activation,
execution-policy change, API key or separate frontend server is needed. See
[external sources and troubleshooting](docs/local-online.md) for data limits,
source hosts and manual recovery.

## Route planner

The root page defaults to online mode and combines the route-planning flow with the main map data. It supports GPS or map-pinned starts, official Basel-Stadt address search and category shortcuts, the checked SBB → Marktplatz alternatives, map layers, route steps, and source details. Both start and destination can search real street addresses through GeoAdmin (© swisstopo), filtered to Basel-Stadt including Riehen and Bettingen. Type at least three characters and choose a result; online queries are sent to geo.admin.ch and are not saved by this app. Offline lookup is unavailable: use map pins or sample places. Calculate requests street-following walking routes for selected online endpoints from the FOSSGIS foot service and replaces the map lines. Walking time uses the configured walking-speed assumption. Endpoint coordinates are sent to FOSSGIS, whose service logs requests; this app does not persist the queries. Offline has no routing graph for new pairs. Only SBB → Marktplatz retains the checked saved geometry and current-departure shade comparison; new routes have unknown shade and access. Provider failure or changed endpoints clears old lines. Calculate retries a failed request. Rest, pause, nearby landmark and indoor-place cues retain their unverified status. Sensor summaries follow the selected snapshot. Route stops use real saved IWB fountains and OpenStreetMap benches/park centres, independently of the synthetic example overlays; Water, Bench and Rest stop markers are projected onto the selected route from candidates within 50m; their actual source coordinates and off-route distance remain in the details. The nearby list shows source dates and unknowns. Proximity does not establish an accessible detour, potable water, usable seating or cooling. Up to 80 mapped stop markers are drawn; the list follows the active stop badges. Source locations remain available in Information sources. Interior space uses supermarkets whose mapped weekly opening hours can be interpreted at the selected departure; unknown/complex schedules, unsupported holiday years and public holidays are withheld. The historical PET overlay is online-only; its saved route-class summaries remain labelled with their original availability. The start form begins with empty endpoints: select two addresses, use GPS explicitly or pin them. Desktop places the map beside the form; mobile opens it for a pin or route. Choose Now or a departure time (device local timezone), then Calculate. Selecting addresses does not calculate automatically. Typing or changing departure clears previous results; pending work can be cancelled and retried with Calculate. Nearby mapped destinations fill the destination only; illustrative fallback cards are labelled Sample. The saved-pair example shortcut is hidden. Walking options are available under Information sources; the area below Calculate shows nearby destination taps. The server samples exact traversal times in the background and displays progress; a cold calculation can take around 20 minutes. Fastest overall, More shade and Balanced use T5 eligibility and evidence rules. Unknown access prevents choosing the saved routes as eligible journeys; Show on map still permits inspection. The optional five-minute limit tightens More shade only. Balanced weights and mode changes rescore cached evidence without shade calls. Departure changes clear old credit and cancel superseded work. No planned stops are included by the screen; the API accepts an explicit stop plan. Solid/dashed/dotted route overlays distinguish approximate shaded/sunlit/unknown or night samples. Calculation detail retains requested/effective sample times, model limits, geometry identity and source attribution; historical PET and sensor times remain separate. The former isolated concept remains at `/poc` for reference; its synthetic temperatures and shadow patches are not part of the main map.

The browser assets are pinned by URL and SHA-256 in [config/browser-assets.json](config/browser-assets.json). The setup script downloads them into an ignored local cache, verifies their bytes and retains licence notices. Subsequent setup runs reuse matching files. Initial installation and downloads need internet. The root URL defaults to online mode for address search, walking routes, weather stations, fountains and forecasts; use the links in the app to choose a mode.

### Route calculation API

`POST /api/comparison` accepts an aware `departure_time` and optional route-indexed
`stops` (`at_metres`, `minutes`). It returns a job ID; poll
`GET /api/comparison/{id}` until ready or failed. Identical requests share one job.
`POST /api/comparison/{id}/rescore` accepts `weights` (shade, duration, water) and
an optional `extra_time_limit_minutes: 5`. `DELETE /api/comparison/{id}` cancels
a superseded calculation after the active bounded sample finishes.
One route job runs at a time; four results are retained in server memory.
Restart discards jobs. Cache identity includes exact departure, full stop plan,
route geometry/provenance, speed, source-file stamps, policy and implementation.
Changed prepared inputs invalidate results; missing inputs return a visible 503.
All route calculation and rescoring use local inputs in every mode. Online mode
refreshes provider layers independently; offline mode makes no external requests.
No transit service is admitted. Offline mode makes no external requests, but each
target machine still needs its saved provider/basemap caches and prepared shade
inputs; missing downloads remain explicit. The committed shade snapshot supplies
building inputs without provider downloads, while the dated local T31 fallback is
saved output, never a live calculation. The online external-server journey remains
unverified. See the [T31 acceptance record](handoff/T31.md) and [T6 acceptance
record](handoff/t6-integration.md) for the checked scope and limits.

## Download data before offline use

For building shade and the saved route comparison, first install the committed
**41.9MB prepared snapshot** without internet access:

```sh
python scripts/install_shade_snapshot.py
python scripts/prepare_building_shade.py --offline
```

This restores the existing local loader paths from checksum-verified data included
in the Git checkout. It preserves differing local data unless `--replace` is
explicitly requested. Stop the server before replacement and restart afterward.
See the [snapshot notes and licences](data/prepared/README.md). This replaces the
building/survey downloads for the saved demo; browser libraries, basemaps and
observation/fountain caches still need their separate preparation below.

With the project environment active and internet available, run from the repository root:

```sh
python scripts/fetch_browser_assets.py
python scripts/prepare_geometry.py --workers 2
python scripts/prepare_offline.py --workers 4
python scripts/verify_prepared_data.py
```

Geometry preparation downloads all available pinned city/buffer assets, verifies catalogue SHA-256 checksums, and writes compressed 1m grids with 2m height steps into ignored `data/geometry/`. It keeps native 0.5m surface detail until max aggregation and uses the smaller native 2m terrain sources. Verified temporary source downloads are discarded after conversion. The local manifest records source URLs/checksums, preparation version, output checksums and coverage gaps. Run the same command again to resume; `--limit 2` is a small validation batch, not full preparation. Encoding and accuracy limitations live in [the source register](docs/SOURCES.md#compact-geometry-and-offline-preparation).

Offline preparation saves sanitized observation/fountain layers, any available route PET class summary, and all basemap tiles in the finite advertised Basel rectangle at zooms 12–17. Saved PET route summaries are labelled stale; the PET map overlay itself requires internet. It retains source attribution and saved timestamps. Basemap downloads resume from checksum-verified files. Inspect .cache/basemap/manifest.json (generated locally by offline preparation) for `complete: true` and data/geometry/manifest.json (generated locally by geometry preparation) for `complete_available_inventory: true`; the latter means all available assets, not that the buffer gaps disappeared. Basemap and observation/fountain caches remain local; the versioned compact shade snapshot is included in a Git clone.

## Use offline

Keep the local server running with the Run locally command and open [offline mode](http://127.0.0.1:8000/?mode=offline). Internet is no longer required: browser libraries, basemap images, saved provider layers and prepared heights are local. Saved observations are historical and visibly labelled; fountain operation/drinking status remains unknown. Missing saved tiles and missing snapshots are explicit errors and never trigger external requests. Pan/zoom coverage is limited to the downloaded rectangle and zoom range. This is a local-server app, not an installed phone/PWA application; the server must remain reachable.

## Use online or on an external server

Open [online mode](http://127.0.0.1:8000/?mode=online) to request provider observations, fountain locations, the two checked walking routes, and PET-class distances through the API. The historical PET map is served by the canton WMS. PET is modelled for a clear summer high-pressure day at 14:00; it is not current weather. Source attribution, route class distances and unknown coverage remain visible. The first provider load may take longer; later requests follow the observation/fountain adapters' hourly/daily caches.

To run on an external server, install the same pinned environment and browser assets there. Run `python scripts/install_shade_snapshot.py` there for the saved shade demo, or prepare geometry and buildings for a different admitted dataset. Run:

```sh
python -m uvicorn bla_bla_walk.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Put the app behind the server's HTTPS reverse proxy and open its address with `/?mode=online`. Browser modules and `/api/map` use that same server origin; no separate API URL or CORS setup is needed. Users do not download the height data to their phones. The server needs outbound access to the observation/fountain sources, and browsers need access to the Basel WMTS service. Keep geometry on persistent storage. An external server cannot provide disconnected offline use once the device loses access to it; use the locally prepared setup for that. Nothing has been deployed by these instructions.

## Prepare native T8 geometry (validation)

T8 keeps the native 0.5 m Float32 surface and terrain grids outside Git under `data/geometry/`. The committed [geometry metadata](data/fixtures/geometry-metadata.json) records every selected tile, explicit source gaps, checksums, alignment and cell-flag policy. Preparation is safe to rerun: verified artifacts are reused and incomplete downloads resume.

```sh
python backend/prepare_native_geometry.py plan
python backend/prepare_native_geometry.py prepare --tiles 2613-1269 2614-1269 --workers 2 --batch-name vegetation-audit
python backend/prepare_native_geometry.py prepare --all --batch-size 8 --workers 2
python backend/prepare_native_geometry.py verify
```

Keep preparation at two workers or fewer. The full local output is about 3.7 GiB; a missing buffer source remains an explicit unknown rather than being filled or assumed clear. T10 consumes this prepared geometry and its flags but owns shade wire output.

## Development checks

### Building-shadow approximation API

`POST /api/shade` accepts an aware timestamp and west/south/east/north viewport bounds in LV95 (EPSG:2056) metres, up to 1000m per side after outward 1m snapping. An optional LV95 `corridor` polyline and `corridor_width_m` restrict the requested cells. The canonical request/response models live in [interfaces.py](backend/bla_bla_walk/interfaces.py); generated client schemas and declarations are separate from the existing map snapshot contract.

For example, POST this JSON to the running local or external server:

```json
{"bounds":[2610000,1266000,2611000,1267000],"requested_time":"2026-06-21T12:00:00Z"}
```

The response contains north-first, row-major uint8 raster bytes encoded as base64, snapped bounds, dimensions, per-state counts and requested/effective time plus preparation version. States are 0 unknown, 1 sunlit, 2 shaded and 3 night. The default model is the user-approved **building-shadow approximation along the saved demo routes**: dated OpenStreetMap footprints, explicit mapped metre heights or survey-derived roof heights cast onto flat ground within a declared 1500m reach. `model` identifies this approximation and `availability` is approximate when any supported cells are calculated. Sunlit means no modeled building shadow within that reach. Trees, terrain relief and physically verified walking ground are excluded; missing heights, source flags and coverage remain unknown. Counts describe raster cells, not walking distances or route scores. T5 evaluation and T6 browser integration consume exact-time samples through the route calculation API above.

Prepare the model and route-halo survey inputs once while connected (about 347MB of survey source transfer in the recorded preparation):

```sh
python scripts/prepare_building_shade.py --geometry
```

Preparation reuses a checksum-verified building cache for the same route halo and preserves its original source dates. Missing buildings are acquired in small sequential bounding-box queries; sanitized batch checkpoints survive a service timeout, so rerunning with the same endpoint resumes. The active manifest is replaced only after all batches succeed. Footprint geometry or heights that change between duplicate results cause preparation to fail rather than silently mixing them.

To verify an existing building cache without contacting a provider, run:

```sh
python scripts/prepare_building_shade.py --offline
```

This validates buildings only; prepared survey grids/flags must already be present for the offline shade API. Use `--refresh` to acquire fresh footprints, or `--endpoint` with a public HTTPS Overpass mirror if the configured endpoint is unavailable. The actual endpoint, earliest batch retrieval time and provider timestamps are recorded in the manifest. Endpoint URLs containing credentials or query parameters are rejected. Offline validation cannot be combined with download options. A failed acquisition retains the previous complete cache; an incomplete cache cannot produce a shadow layer.

Bounded queries can use `--request-method GET` when a mirror's POST transport is unavailable. For the regional Swiss service:

```sh
python scripts/prepare_building_shade.py --endpoint https://overpass.osm.ch/api/interpreter --request-method GET
```

This source is admitted only within the verified Basel-Stadt boundary and requested halo. Cross-boundary receiver/ray coverage stays unknown; it cannot establish clear sunlight beyond that area. GET batches have distinct resumable identities. Unparseable provider date markers are retained separately and labelled unknown, never replaced with retrieval time. Source constraints and transport are recorded in the local manifest and cache identity.

The active footprint cache lives under `.cache/buildings`; grids and flags live under `data/geometry/`. These runtime directories remain ignored. The committed [prepared snapshot](data/prepared/README.md) restores their verified contents without provider requests. Its geometry manifest includes the locally prepared survey assets; the building workflow selects the 25 survey tile pairs intersecting the two routes and their halo. Footprint provenance, original source dates and coverage constraints are preserved. To use the original strict survey policy, set receiver_policy in config/shade-service.json to unknown-until-compact-scene-validation; that policy still returns unknown until independently verified receivers are supplied.

Reproduce full-polyline, cold/warm, concurrent, seam, night and offline API checks:

```sh
python scripts/validate_building_shade.py --repeats 3
```

[Recorded route validation](data/fixtures/building-shade-validation.json) reports corridor cell counts separately from the surrounding unknown raster. It tests both full saved polylines in bounded chunks, zero external HTTP attempts, matching shared seam cells and process memory. Unknown cells remain prominent; this is an engineering validation of the approximation, not observed shade accuracy.

Shade uses local geometry and solar calculations in both online and offline modes; it makes no provider requests. Missing raster cells/buffer inputs remain unknown. A missing/invalid manifest or corrupt prepared file returns 503, oversized viewports return 413 and invalid request fields return 422. Busy workers return 503 with Retry-After. No geometry is downloaded automatically.

[Service limits](config/shade-service.json) bound geometry to 16 million cells per request, two simultaneous calculations and 128MiB of serialized cache entries per server process. Restart after changing worker/cache limits. Identical misses share one calculation; a different request is rejected when both workers are occupied. Cache keys include exact UTC time, geometry/preparation and implementation versions, encoding/grid, extent, corridor, boundary, source-file presence/size/mtime and ray/receiver policy. Grid hashes are verified on cold reads. There are no five-minute buckets or disk cache; restart clears the cache. The X-Shade-Cache header indicates MISS/HIT. HTTP responses use no-store because local input availability can change.

The earlier strict survey checkpoint has separate integration and synthetic ray-kernel measurements. On rerun, this script uses the currently configured receiver policy; switch to the strict policy described above to reproduce unknown-only behavior:

```sh
python scripts/benchmark_shade.py --repeats 5
```

[Recorded performance](data/fixtures/shade-performance.json) includes 1km centre, vegetation and boundary views and two concurrent requests. The real API measurements exercise geometry loading and unknown output; the synthetic benchmark exercises actual rays with an analytically verified ceiling. Neither establishes physical-scene accuracy or useful city-wide shade throughput. These historical measurements precede the building model; use the route validator above for its current measurements.

### Calculation validation

Slot E's strict survey calculator has analytic and independent numerical checks; [its handoff](handoff/t10-shade-calculation.md) records the completed approximation scope and remaining integration work. To reproduce the small real-raster spot check, supply the native source pair for tile 2610-1266 from [the pinned inventory](data/tile-inventory.json), saved locally as .hack/t10/surface.tif and .hack/t10/terrain.tif. The validator verifies both catalogue checksums and does not download files:

```sh
python scripts/validate_shade_sample.py --surface .hack/t10/surface.tif --terrain .hack/t10/terrain.tif --output .hack/t10/shade-validation.json
```

Audit vertical encoding loss using the four checksum-pinned native source pairs
from T0, saved as `<scene>-surface.tif` and `<scene>-terrain.tif`:

```sh
python scripts/audit_compact_receivers.py --source-directory .hack/t0 --output .hack/compact-receiver-audit.json
```

[Recorded encoding audit](data/fixtures/compact-receiver-audit.json) isolates the
2m height step at native 0.5m spacing. It measures erased inversion flags and
false equal pairs; it does not validate horizontal resampling or admit physical
receivers. The actual compact 1m grid and native 2m terrain still need separate
scene checks. See [E's handoff](handoff/t10-shade-calculation.md).

Reproduce the actual 1m compact pipeline and saved-route encoding sensitivity:

```sh
python scripts/validate_compact_pipeline.py --download --output .hack/compact-shade-validation.json
```

This downloads six checksum-pinned source pairs to `.hack/e-t10`, prepares local
compact rasters and source flags, and compares the encoded grids with an
unquantized 1m control. Omit `--download` to repeat offline with those files.
[Recorded compact comparison](data/fixtures/compact-pipeline-validation.json)
separates independent ray checks from invalid-receiver policy checks. Its route
samples are numerical upper-surface comparisons in 128m windows, with unknown
unresolved rays; they are not walking-shade metrics or route recommendations.

To reproduce the compact sensitivity check, supply the same pinned surface/native-0.5m terrain pair plus the matching native 2m terrain asset (same tile/year, replace `_0.5_2056_` with `_2_2056_` in its URL). The 2m SHA-256 pins for all three checked tiles are recorded in [compact validation evidence](data/fixtures/compact-shade-validation.json). The script makes no external requests, writes scaled compact rasters and compressed pre-encoding receiver evidence to the local work directory, and checks both representations independently:

```sh
python scripts/validate_compact_shade.py --surface .hack/t10/surface.tif --terrain .hack/t10/terrain.tif --terrain-2m .hack/t10/terrain-2m.tif --work-directory .hack/t10/compact --output .hack/t10/compact-validation.json
```

Repeat for route tiles 2611-1266 and 2611-1267 using `--tile` and `--terrain-2m-sha256` from the evidence, with their matching source paths and separate work/output paths. Each per-tile report uses the full route denominator and marks outside-tile samples unknown. Across these disjoint receiver tiles, sum shaded/changed-state metres; aggregate unknown metres equal the full route length minus summed shaded metres. The preserved-evidence case retains source flags and numerical ground candidates; it does not certify walking surfaces. Existing compact height files alone cannot reconstruct this evidence. Slot F must version and verify the companion files before cache/API use; see the handoff.

Activate the environment and run from the repository root:

```sh
python backend/export_contract.py
python -m pytest -c backend/pyproject.toml backend/tests
python -m ruff check --config backend/pyproject.toml backend scripts/fetch_browser_assets.py scripts/format_browser.py scripts/prepare_geometry.py scripts/prepare_offline.py scripts/verify_prepared_data.py scripts/benchmark_shade.py scripts/prepare_building_shade.py scripts/validate_building_shade.py
python -m ruff format --check --config backend/pyproject.toml backend scripts/fetch_browser_assets.py scripts/format_browser.py scripts/prepare_geometry.py scripts/prepare_offline.py scripts/verify_prepared_data.py scripts/benchmark_shade.py scripts/prepare_building_shade.py scripts/validate_building_shade.py
python scripts/format_browser.py --check
bash scripts/doc-check.sh --strict
```

Browser checks use an installed Chromium; set `CHROMIUM_PATH` to its executable if it is not on PATH. These checks skip with a visible reason when no browser is available. Offline browser integration checks also need the saved provider snapshot and basemap from offline preparation. Run only the API/model checks with `python -m pytest -c backend/pyproject.toml backend/tests -m 'not browser'`. No Node.js installation is required.

T5's backend comparison and traversal-time sampling are checked by the same test
command. With local building/geometry preparation available, run
`python scripts/validate_route_comparison.py` to calculate distance estimates
for both saved routes without external requests. It checks that rescoring makes
zero shade calls and unknown route access withholds all recommendations.
These are building-shadow midpoint approximations, with unknown/night retained;
see [routing rules](docs/routing-rules.md) for limits and T6's integration boundary.

Run `python scripts/validate_journey.py` with prepared local inputs and the saved
offline provider snapshot to exercise the background comparison API while blocking
outbound HTTP. It checks polling, duplicate-request reuse, detour rescoring and
withheld recommendations for unknown access, then saves the real response locally
under `.hack/`. See [T6's acceptance audit](handoff/t6-integration.md) for measured
results and the outstanding external-server check.

Format Python with `python -m ruff format backend scripts/fetch_browser_assets.py scripts/format_browser.py` and browser code with `python scripts/format_browser.py`. [backend/bla_bla_walk/interfaces.py](backend/bla_bla_walk/interfaces.py) is canonical; regeneration writes [src/interfaces.ts](src/interfaces.ts) for editor/JSDoc use and the browser validation schema. Include a decision line with model changes and never edit generated files by hand. Consumer ownership is listed in [ROADMAP.md](ROADMAP.md); the map modules now use .js filenames.

## Map badges and rest planning

Tap a title-only badge to toggle its layer (keyboard Enter/Space also works). Equal-size **Temperature**, **Fast route**, **Recommended**, **Water**, **Bench** and **Rest** badges start active. **More** starts collapsed with inactive **Heatmap**, **Shading**, **Weather stations**, **Fountains**, **Landmarks** and **Interior space** badges. All source descriptions, dates, licences, legends and method details are under collapsed **Information sources** at the end of the page.

Fast route displays the shortest walking-time estimate. Recommended displays only a supported comparison winner; it can remain empty while its badge is active. The controls are independent even when both refer to the same path. Temperature follows the selected visible route. Shading remains unavailable when prepared inputs are missing and unknown cells stay explicit. Route steps may include source-backed mapped references with visibility unverified; the Landmarks badge shows saved mapped places at their original coordinates, with route visibility unverified. Weather stations and Fountains toggle all loaded source points independently of route-stop badges.

Rest prompts are planned every **15 minutes of walking** before arrival, using the route's estimated walking time. They are displayed on the route, separate from mapped benches and park candidates; a prompt does not establish seating at that point. No stop duration or unverified detour is added to the trip calculation. The source point behind a projected Water/Bench/Rest marker retains its original coordinates.

Interior space lists all mapped Basel supermarkets whose supported schedules are open at the selected departure, with independent source-location markers; they are not projected rest stops. The conservative evaluator supports weekly day ranges, ordinary time windows and PH off, in Europe/Zurich at the selected departure. Complex/overnight/missing schedules and unknown holiday years are withheld; current holiday coverage is 2026. This is scheduled opening, not a live open-door or cooling guarantee. Preparation now saves 95 canton-clipped supermarkets (87 with hours) alongside benches/parks. Re-run the rest preparation command to acquire them; no new serving-time downloads.

## Route temperature colours

Enable **Sensor-based route temperature** to colour both visible walking routes from real meteoblue station readings (Open Data Basel-Stadt). Online mode refreshes the admitted adapter; example/offline mode uses explicitly saved readings. Colours are exploratory inverse-distance-squared estimates from up to three sensors within 1,000m, requiring at least two readings aligned within 60 minutes. Dotted grey marks unsupported sections. No shade/PET cooling is added. Both routes share one relative temperature scale and palette, with a minimum 2°C span; the same reading has the same colour on either route. Selecting a route keeps both gradients visible; the Fast and Recommended badges hide their own paths independently. Equal readings stay one colour. Actual estimated range, coverage, source times and a withheld-station check accompany the legend. Click a coloured route section to inspect its estimate and contributing readings. Disable temperature to see underlying shade strokes.

Summer uses green `#86efac`, amber `#fbbf24`, rose `#e11d48`; winter uses colder cyan `#a5f3fc` through warmer indigo `#4338ca`. Automatic selects winter below 15°C (a configurable display convention), otherwise summer. Current sensor estimates take priority for today; unavailable/stale readings or another departure day fall back to that day's Open-Meteo daily mean for the fixed Basel city point. Manual palette choice is also available. Forecast chooses colours only and never fills unknown route temperatures. These are observation-time estimates, not a forecast for the selected departure.

The forecast fallback uses the free **noncommercial** Open-Meteo API, with CC BY 4.0 attribution, a one-hour city cache, bounded timeout/response and a five-minute retry delay. Only the fixed Basel point is sent; no route/user coordinates. Offline reads the saved forecast and labels it saved; missing/out-of-range days remain explicit. If forecast also fails, saved sensor values may choose the palette with a visible fallback label. Settings live in `config/route-temperature.json` and `config/palette-forecast.json`; caches stay local. Details and limitations: [source register](docs/SOURCES.md).

## Prepare route stops

Download the fixed Basel-Stadt extent once (no route or address is sent):

```sh
python scripts/prepare_rest_stops.py --download
```

This saves sanitized, canton-clipped bench/park candidates in ignored `.cache/rest-stops.json`. Serving this file and the saved IWB fountain snapshot works offline and never downloads OSM data. Missing files produce an explicit unavailable state. To reuse the earlier, partial audit input without network access, run `python scripts/prepare_rest_stops.py --input .hack/t0/osm-sample.json`; this keeps its older acquisition status. Fountain preparation remains part of the documented offline provider snapshot. See [source register](docs/SOURCES.md) for licences and limits.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Fixture mode uses invented overlays. Online/offline provider modes use admitted sources with timestamps and uncertainty; offline data never claims a live refresh. Prepared geometry has coverage gaps and mismatched survey years; 1m grid spacing does not make native 2m terrain more detailed, and 2m elevation quantization can change shadows. Physical shade accuracy, city-wide throughput and route comparison are not established; the route building approximation has bounded numerical and performance checks. Scope, unknowns, and demo fallback are documented in the [design brief](docs/design.md).

## Team

The six-person work split is proposed in [ROADMAP.md](ROADMAP.md). Contributors still need to choose role slots and add their GitHub usernames in [TEAM.md](TEAM.md).

Map stop circles use Lucide droplets (Water), rocking-chair (Bench), and clock-fading (Rest). Same-type stops within 38 screen pixels collapse into counted circles; zooming separates them. Tap a count to inspect its members. Cluster anchors remain on a member’s route position, and original source records remain intact.
