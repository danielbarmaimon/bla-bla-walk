# Sources

## T0 admission audit — 2026-10-03

The source audit is complete. Geometry preparation is feasible **with explicit unknown coverage and scene-validation requirements**, not a promise of known shade everywhere. T4 adapters supply the app's online/saved provider modes; T6 still connects shade and route evaluation to the full journey. [Source manifest](../data/source-manifest.json) records requests, samples, provenance, cost measurements and acceptance budgets. [Tile inventory](../data/tile-inventory.json) pins the boundary, every required tile, asset versions, checksums, grids and missing geometry. Original audit samples remain local under ignored `.hack/t0/`; current compact preparation is documented below.

Admission permits the stated use; it does not establish live availability, measured cooling, drinking-water safety or pedestrian access. Preserve source-specific rights and attribution, transformations, observation/scenario time, publication time and retrieval date. The repository's prioritised resources are project references; their inclusion does not independently establish organiser endorsement or reuse permission.

| Layer | Verified access and evidence | Rights / attribution | Admission and limits |
|---|---|---|---|
| Basel grey basemap | [WMTS capabilities](https://wmts.geo.bs.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml), layer `VS_Vektorstadtplan_grau`, EPSG:3857, zooms 0–17, 256px tiles. Central PNG returned 200, nonblank, CORS `*`, one-day cache, and rendered directly in browser. [Official model §11.3 p23](https://models.geo.bs.ch/Modellbeschreibungen/VS_Vektorstadtplan_KGDM_V1_0.pdf) maps this layer to Vektorstadtplan / [VSBS](https://api.geo.bs.ch/stac/v1/collections/VSBS). | CC BY 4.0; **Quelle: Geodaten Kanton Basel-Stadt**. [Geoservices](https://www.bs.ch/en/node/28694) permits free GIS/web WMTS use; no numerical quota found on inspected page. | Admitted. Advertised extent and request hash in manifest. T1 displayed the live map and boundary. Tile modification date is not underlying survey date. |
| Observed temperature | [100009](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100009), bounded latest-per-station query verified for `0020F940`; 19.39°C at 2026-10-03 11:00:01 UTC. T4 fetches selected fields, sorts latest first, and joins using `name_original`. | CC BY 4.0; **meteoblue AG via Open Data Basel-Stadt**. | Admitted raw points. Provider description says hourly; catalogue says daily. Adapter refreshes hourly and labels values stale after 90 minutes. Values are uncorrected and may be missing. Reads up to 5,000 recent records per refresh; stations absent from that bounded window remain missing. |
| Station locations | [100082](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100082), 198 records; sample ID/time match above. | CC BY 4.0; **meteoblue AG via Open Data Basel-Stadt**. | Admitted. T4 joins `name_original` and clips points to advertised Basel map bounds; that rectangle is not exact canton clipping. The wider catalogue does not mean all stations are active or inside the canton. |
| IWB fountains | [100008](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100008), 305 records; names/point geometry retrieved. T4 selects only names and coordinates. | Noncommercial use with **IWB Industrielle Werke Basel** attribution; commercial reuse requires supplier permission. Team accepted these terms 2026-10-03. | Admitted locations for this noncommercial prototype. Cache refreshes daily; provider updates are irregular. Dataset has no structured fountain type, drinking-water, operational, or access fields. Those values stay unknown. Photos, media URLs, descriptions and free text are excluded. |
| Managed trees | [100052](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100052), 32,378 records; points/species accessed. | CC BY 4.0 + OSM notice; **Geodaten Kanton Basel-Stadt**. [Notice](https://data-bs.ch/stata/dataspot/permalinks/20240822-osm-vektordaten.pdf) permits incorporation into OSM; attribution waiver is specific to OSM, not standalone canton use. | Admitted context points. Daily; Basel/Riehen managed trees do not cover all private vegetation. No inspected height/crown-radius fields; not a physical shadow source. |
| Construction projects | [100335](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100335), 103 records; project/date/link fields, no geometry. | CC BY 4.0; Tiefbauamt, preserve catalogue attribution. | Admitted caution only. Irregular cadence; project dates are not closure intervals. No structured pedestrian-closure field. |
| Spatial permits | [100018](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100018), polygon records joined on `100335.id = 100018.begehrenid`. Project `9139079` matched two permits. | CC BY 4.0 + same canton OSM notice; **Geodaten Kanton Basel-Stadt**. | Admitted caution polygons. Daily; approved occupancy / `Baustelle` does not prove walking edges blocked. Attached documents and contact/free-text fields are not admitted automatically. |
| Canopy context | [100357](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100357), three snapshots 2012/2021/2024; 2024 raster/directory returned 206, worldfile 200; 0.5m EPSG:2056, 21767×18189 uint8. | CC BY 4.0, preserve catalogue attribution. Published/processed 2025-09-09; three-year cadence, next 2027/2030. | Admitted context, pending full value/class validation. Bounded directory/metadata ranges verified CRS and NoData `0` after the initial 64KiB image decoder failed. 396,060,323 bytes. Do not treat NoData 0 as confirmed canopy absence or sunlight. Canopy does not establish time-specific shade or public access. |
| OSM parks / benches | [Swiss Overpass](https://overpass.osm.ch/); queried `leisure=park`, `amenity=bench`. Bounding box 7.55–7.69 E / 47.53–47.61 N returned 223 mapped parks and 2,872 benches. | [ODbL 1.0](https://www.openstreetmap.org/copyright); **© OpenStreetMap contributors**; retain applicable derived/redistributed database obligations. | Admitted mapped candidates. Not canton-clipped or completeness-verified. Bench tags: backrest 2,435, covered 197, wheelchair 0, check_date 348. Missing tags mean unknown, not absent facility/access. Endpoint snapshot field was not an ISO date. Recheck important stops. |

### T4 fetch and freshness behaviour

Each source request times out after eight seconds and reads at most 2MB. The [Explore API caps ordinary records pages at 100](https://help.opendatasoft.com/apis/ods-explore-v2/explore_v2.1.html#records); T4 follows that limit. It reads up to 250 stations across three pages and 350 fountain records across four pages. It selects the newest 5,000 observations in one bounded JSON export, then joins matching station IDs. The live export returned 5,000 selected records in 903,383 bytes. Station points are clipped to the advertised map rectangle, not an exact canton polygon.

Temperature snapshots refresh hourly because source documentation says hourly; catalogue metadata says daily. A point stays current for 90 minutes after its observation, then becomes stale. IWB locations refresh daily because catalogue changes are irregular. Their current source snapshot never means a fountain works, offers drinking water, or permits access.

Adapters keep the last successful snapshot in process memory. Failed refreshes return that snapshot as stale; cold failures return a missing layer. A one-minute retry delay bounds repeated failures. T6 owns API wiring and must preserve these explicit states. Fixtures are dated, small, rights-labelled examples; they are not a live fallback.

### Construction semantics

The [Tiefbauamt page](https://www.bs.ch/bvd/tiefbauamt/baustellen) is the project's starting reference. Spatial permits supply usable polygons, not authoritative pedestrian closures. Keep project dates, permit dates and statuses separate. One project may have several occupancies. Exclude an edge only when a separately verified source confirms that walking is blocked; otherwise show a caution/unknown. Do not geocode a street name into a fictitious closure or mark every worksite impassable.

## Pinned city geometry and coverage

Engineering extent: **Basel-Stadt canton, including Basel, Riehen and Bettingen**. Pin [swissBOUNDARIES3D 2026-01](https://www.swisstopo.admin.ch/en/landscape-model-swissboundaries3d) from the checksum-verified EPSG:2056/LN02 GeoPackage; the archive URL, SHA-256, feature UUID, original geometry hash and extracted 2D polygon are in the inventory. Area 36.95km². Dropped Z ordinates for planar selection; coordinates otherwise unchanged. Extent is a working interpretation of all Basel, recorded in decisions.

Use [swissSURFACE3D Raster](https://www.swisstopo.admin.ch/de/hoehenmodell-swisssurface3d-raster) and [swissALTI3D](https://www.swisstopo.admin.ch/de/hoehenmodell-swissalti3d). [Federal OGD terms](https://www.swisstopo.admin.ch/en/faq-free-geodata) permit reuse for all purposes with **© swisstopo**. These are actual OGD assets, not test-only product samples. Catalogue selection uses latest nominal year per available 0.5m LV95/LN02 tile; alternatives remain recorded.

Followed all pagination: 204 surface items over three pages, 330 terrain items over four pages, bounded box 7.50–7.75 E / 47.50–47.65 N enclosing the polygon and buffer. Selected 139 one-kilometre tiles: **65 receiver, 74 buffer only**. There are 129 surface assets and 96 terrain assets. **All 65 receiver tiles have both asset URLs; 10 surface and 43 terrain buffer tiles are missing.** Missing surrounding/cross-border geometry prevents blanket border-shade claims; do not invent infill. Available assets may still contain NoData not detectable from headers.

All **225/225** available assets returned bounded HTTP 206 header requests: 2000×2000, float32, EPSG:2056, matching tile origins, 0.5m pixels, NoData `-9999`. Heights are metres in LN02 / vertical EPSG:5728 per product specification and identifiers; inspected GeoTIFF horizontal keys do not prove embedded vertical CRS. NoData and scene consistency need full T8 decoding. Range access does not imply a provider SLA or unlimited request quota.

Buffer selection conservatively encloses a **1,500m Euclidean buffer** using a square expansion. Planning envelope: 250m height, minimum solar elevation 10° → 1,418m flat-ground ray reach; the measured tower sample exceeds 200m, so 200m would be insufficient. This is not proof of a city height maximum. Terrain relief and actual sunward ray reach must be validated; extend the halo or mark unsupported/unknown when coverage is insufficient. Below 10° is unsupported/unknown; night is separate. Missing/invalid sunward geometry cannot imply sunlight. Canopy receivers, bridges and tunnels require explicit handling.

### Representative full downloads and processing

Eight full rasters (four pairs) passed their STAC SHA-256 checks. Every sample had four million valid paired cells and zero NoData cells. All current pairs are nominal surface **2023** / terrain **2025**; all 96 available full-inventory pairs share this year mismatch. Catalogue January 1 datetimes are not exact acquisition dates. Negative surface-minus-terrain cells remain a scene-consistency flag, not a proved cause or a reason to silently clamp heights.

| Environment | Tile | Surface minus terrain range (m) | Cells below −1m | Median 2m kernel (s) |
|---|---|---:|---:|---:|
| urban_centre | `2610-1266` | -10.90 to 60.01 | 3,106 | 0.142 |
| vegetation_lange_erlen | `2613-1269` | -5.74 to 41.99 | 4,563 | 0.110 |
| tall_building_roche | `2612-1267` | -4.73 to 205.13 | 1,383 | 0.116 |
| border_kleinhuningen | `2611-1270` | -11.40 to 84.48 | 3,515 | 0.116 |

Benchmark: bundled Pillow/NumPy, full float32 decoding, conservative 4×4 surface max-pooling and nearest terrain to 500×500 at 2m. Three warmed runs per pair, fixed solar elevation 30° / azimuth 135°, ray reach 1,500m; a simple 10m cardinal object checked direction/length. Unknown cells are retained where rays leave the tile or encounter invalid geometry. **This isolated-tile kernel is cost evidence, not accepted street-level shade or a full-halo/API benchmark.** It does not validate ephemerides, canopy gaps, seasonal foliage or independent real-scene accuracy. Version/hash and exact decode/kernel timings are in the manifest. The earlier terrain-2019 centre checkpoint is retained as historical evidence, superseded for current selection.

Four pair decodes plus twelve kernels took 2.57s locally; two simultaneous threaded kernels took 0.18–0.23s per pair of requests. Windows measured peak process working set was 149,274,624 bytes (142.4MiB), including prior decodes and the two kernels. These measurements use warmed local files in one process; separate production workers and real halos must be measured independently.

### Storage, workload and acceptance budgets

Available buffered assets total **3,311,403,377 compressed bytes (~3.08GiB)**; decoding all 225 float32 inputs requires **3,600,000,000 bytes (~3.35GiB)** before masks/overhead. Receiver pairs alone total 1,927,486,658 compressed bytes. Missing buffer assets are excluded from these totals; new infill increases them.

Native receivers: 147.8 million cells by canton area, up to 260 million across intersecting whole tiles. Candidate 2m output: 9.24 million canton cells, up to 16.25 million receiver-tile cells; all 139 buffered tiles total 34.75 million cells. Two one-byte status/mask grids would cost 69.5MB per full-buffer time bucket. Linear summed sample kernel cost is about 7.56s for 65 receiver tiles / 16.16s for 139 tiles at the sampled angle, **excluding halos, IO and all serving overhead**. This is a planning estimate, not valid full-city computation or a request latency guarantee; lower sun and full halos may cost substantially more. Native 0.5m calculations require a separate benchmark.

Before T8/T10 implementation, adopt these engineering acceptance targets:

- Geometry disk ≤8GiB including compressed/decoded assets and metadata; shade cache ≤2GiB, bounded eviction.
- Peak worker memory ≤768MiB, maximum two workers (≤1,536MiB aggregate worker memory).
- Candidate viewport: 1km×1km receiver footprint plus required halo. The current requested grid/height encoding is in [config/geometry.json](../config/geometry.json), superseding the original 2m output candidate; **shade accuracy remains pending validation**.
- Prepared local geometry, empty shade cache: cold p95 ≤5s; repeated cached requests: warm p95 ≤0.5s.
- Measure 20 distinct representative requests and 20 repeated requests; repeat at two simultaneous requests. Include halo processing, serialization and memory. Network ingestion is separate.

## Compact geometry and offline preparation

The T0 inventory and sample timings above describe the original native data and 2m-grid feasibility experiment. They remain historical evidence. Current preparation uses [config/geometry.json](../config/geometry.json), [the ingestion script](../scripts/prepare_geometry.py) and [geometry reader](../backend/bla_bla_walk/geometry.py). Actual completed download counts/sizes and preparation hashes live in [data/preparation-summary.json](../data/preparation-summary.json); per-asset source/output checksums are retained in ignored data/geometry/manifest.json (generated locally by geometry preparation).

The summary's source-download bytes are the unique input-file sizes, not measured network traffic including retries. Its prepared sizes count compressed rasters separately from manifests, basemap, snapshots and browser assets. Run [the verification script](../scripts/verify_prepared_data.py) to check every prepared/image hash, raster grid/scale and unknown-cell count and regenerate this shareable summary.

Tile footprints remain 1km×1km, with the same canton boundary and 1500m caster buffer. Prepared grids have 1000×1000 **1m horizontal cells**, encoded as signed int16 **2m elevation steps**. Read heights as `code × band scale` after masking NoData `-32768`; GeoTIFF scale is 2 and offset 0. Use `read_heights` rather than treating raw codes as metres. Heights retain the provider's LN02 reference; the tag records the product reference, not a new vertical transformation or independent accuracy proof.

Surface input remains the pinned native 0.5m swissSURFACE3D Raster. Each 2×2 input block contributes its maximum height; this retains potential thin casters but can enlarge buildings/canopy and fill gaps. Any missing/non-finite input in that block makes the prepared cell unknown. Terrain uses the **same pinned survey year/tile at native 2m** swissALTI3D, verified against its own catalogue SHA-256 checksum, and repeats values onto the 1m grid using nearest resampling. This adds no terrain detail and avoids interpolating across tile edges. Source survey-year mismatch flags remain; no height differences are silently clamped.

After horizontal resampling, elevation values round to the nearest 2m step (half-step ties toward positive infinity). Quantization contributes at most 1m error per absolute height and up to 2m to a difference between two independently rounded heights. This is storage precision, **not surveyed vertical accuracy**. At low solar elevations, height error can displace shadow boundaries by multiple metres; T10 must quantify that against unquantized references before route recommendations rely on it. Missing buffer inputs, bridge/tunnel/canopy semantics and negative surface-minus-terrain differences still require T8/T10 validation.

Downloads are bounded to at most four concurrent assets, resume interrupted source transfers, validate source size and SHA-256, then decode/prepare one tile per worker. Outputs are tiled 256×256 internal blocks with DEFLATE/predictor compression. Manifest checkpoints and output hashes permit verified reuse. Verified temporary source rasters are discarded after conversion; the full provider transfer is still required on a new setup. All 225 int16 output grids require 450MB uncompressed before masks/overhead. At a 1m shade output grid, two one-byte full-buffer masks would require 278MB per time bucket, four times the old 2m estimate. Historical 2m timings are not new 1m latency results; the existing memory/cache/latency budgets remain acceptance targets.

[Offline preparation](../scripts/prepare_offline.py) saves the finite basemap extent/zoom range from [config/basemap.json](../config/basemap.json), retaining **Geodaten Kanton Basel-Stadt / CC BY 4.0** attribution, plus sanitized T4 provider output with its observation/retrieval times and source licences. Its local manifests record image checksums and retrieval time; map retrieval date does not establish an underlying survey date. Snapshot temperatures remain raw uncorrected observations, and IWB reuse remains noncommercial. Photos/contact fields are excluded by the T4 adapters.

Offline API reads saved bytes only, marks previously current features/layers stale, preserves missing/unknown states, and never refreshes providers. Local tile misses return 404 without a remote fallback; a missing/invalid provider snapshot returns 503. Online API uses the existing hourly/daily adapter caches and last-good stale behavior. Both modes retain visible source times and uncertainty. Geometry ingestion alone does not supply a working shade/evaluation API. [README](../README.md) owns local offline and external-server run instructions.

No claim that the prototype meets these API targets. T10 must optimise or revisit targets with the team if measurements fail. No whole-city recalculation in the request path. Five-minute cache buckets and 2m shade remain candidates; validate accuracy before adopting them. Preserve geometry version, requested/effective time, resolution and explicit unknowns in any derived outputs. Distinguish geometric occlusion from observed cloud cover and measured temperature.

## Optional sources: checked and deliberately deferred

### Transit timetable and service alerts

[2026 GTFS catalogue](https://data.opentransportdata.swiss/en/dataset/timetable-2026-gtfs2020) currently lists `GTFS_FP2026_20260930.zip` (275.6MB), valid 2025-12-14 through 2026-12-12, updates twice weekly. The official resource page was inspected. Direct download/API attempts returned 403; browser archive download did not complete within 60s. **BVB/BLT agency, route and stop contents were not verified**, so transit is excluded from adapters until that check passes. Preserve [provider terms](https://opentransportdata.swiss/en/terms-of-use/) and reference; catalogue lists commercial/noncommercial reuse allowed.

[Service Alerts documentation](https://opentransportdata.swiss/de/cookbook/event-cookbook/gtfs-sa/) describes `https://api.opentransportdata.swiss/la/gtfs-sa`, key required, two requests/minute; use binary GTFS-RT for production (JSON is test-only). No key supplied, so no live payload inspected. [Connected-operator catalogue](https://data.opentransportdata.swiss/en/dataset/go-siri-sx) was checked, but its CSV download could not be verified; **BVB/BLT live-alert coverage remains unknown**. Alerts may be text/entity warnings without detour geometry; do not infer routable diversion paths. Optional transit does not block core geometry/observations.

### Alertswiss

[Alertswiss FAQ](https://www.alert.swiss/en/faq.html), [BABS multi-channel strategy](https://www.babs.admin.ch/dam/de/sd-web/yqZESGSo8RVq/20241001-Multikanastrategie-de.pdf) and [CAP Suisse 1.1 specification](https://www.babs.admin.ch/dam/de/sd-web/H6vSh6NHF65G/Spezifikation%20CAP%20Suisse%201-1.pdf) checked. A standard and planned API do not establish an available public full-stream feed. **No documented publicly reusable Alertswiss endpoint verified; link-only admission.** MeteoSwiss app alarm relay does not establish full Alertswiss content in MeteoSwiss open data.

[Alertswiss legal terms](https://www.alert.swiss/de/home/meta/rechtliches.html) state website content may be forwarded free with **Quelle: www.alert.swiss**, under CC BY-NC-SA 2.5 Switzerland; framing requires written permission. These are separate from MeteoSwiss terms and do not grant access to an undocumented API.

### Indoor rest candidates

[Canton heat/health list](https://www.bs.ch/it/node/31069) is a curated starting reference. No reusable machine-readable feed identified on the inspected page. Small factual summaries below are checked 2026-10-03; website prose/photos and bulk republication are not automatically licensed. Recheck operator exceptions before suggesting a stop; do not infer safe cooling from a church/shop category.

| Candidate | Operator evidence | Access / accessibility / limits |
|---|---|---|
| [Theater Basel Foyer Public](https://www.theater-basel.ch/de/foyerpublic) | Standard Tue–Sun 11:00–18:00, Monday closed. Published exceptions for Sep29–Oct4: Tue closed, Wed closes 17:00, Fri 17:30, Sun Oct4 closes 15:00. | Free, no purchase needed, own food permitted. Accessibility and air conditioning unverified; not measured temperature. |
| [Stadtbibliothek Schmiedenhof](https://www.stadtbibliothekbasel.ch/de/schmiedenhof.html) | Staffed Mon12–19, Tue–Fri10–19, Sat10–17, Sun13–17. | Operator lists wheelchair access. Extended Open Library07–22 restricted to registered customers16+; not unrestricted visitor hours. Canton list says no AC, lower floors relatively cool. |

The Kunstmuseum cool-room link from the canton list returned 404; remaining listed places need independent operator checks. These candidates have dated factual evidence and unknowns, not a live opening or temperature feed. Outdoor parks and canopy likewise do not establish public access or current shade; mapped benches need local verification.

## Observations, predictions and optional estimates

Timestamped sensor observations, calculated geometric shade, forecasts and historical PET are separate variables. Refreshing the map cannot refresh an old reading. Retain a visibly stale last-good snapshot on feed failure. Any future sensor interpolation needs aligned readings, bounded coverage, method disclosure and withheld-station validation; no current-temperature offset to historical PET and no guessed shade cooling degrees.

[MeteoSwiss local forecast documentation](https://opendatadocs.meteoswiss.ch/e-forecast-data/e4-local-forecast-data) describes hourly air temperature `tre200h0`, collection `ch.meteoschweiz.ogd-local-forecasting`, hourly updates and nine-day point forecasts. [CC BY 4.0 terms](https://opendatadocs.meteoswiss.ch/general/terms-of-use), attribution **Source: MeteoSwiss**; proprietary pictogram graphics excluded. Basel asset/time validation is deferred; forecasts/PET do not block core map admission.

Optional OSM drinking-water extraction (`amenity=drinking_water` or explicit `drinking_water=yes`) remains unchecked locally. Keep lifecycle/access/seasonal tags and ODbL rights; generic fountain categories do not establish potable water. Never import restricted IWB records into OSM.

## Historical heat scenario: Basel-Stadt Geoportal daytime PET

Documentation checked: 2026-10-03. PET is a candidate historical context layer, not the live-temperature foundation. Numeric access and dataset-specific open licensing still need verification; no application integration exists.

PET (Physiological Equivalent Temperature) estimates thermal conditions for a modelled person from air temperature, humidity, wind, and short- and long-wave radiation. Although expressed in °C, PET is not thermometer air temperature or a personalised health-risk estimate.

| Item | Finding / reference |
|---|---|
| Dataset to investigate | Stadtklima: `HumanbioklimSituation`, the daytime PET layer; keep the separate `HumanbioklimSituation_2030` projection out of the initial baseline |
| Map and catalogue | [MapBS Stadtklima](https://www.geo.bs.ch/stadtklima), [Basel-Stadt geodata catalogue](https://shop.geo.bs.ch/geodaten-katalog/) |
| Layer description | [Official Stadtklima data model, sections 6.1.12–6.1.13](https://models.geo.bs.ch/Modellbeschreibungen/KL_Stadtklima_KGDM_V1_0.pdf) |
| Method and shade evidence | [2019 climate analysis, sections 4 and 4.4](https://map.geo.bs.ch/file_proxy/KL_Stadtklima_Windstroemungsfeld/Endbericht_Basel_Klimaanalyse_Rev09_ohne_Anhang.pdf): reduced heat stress under tree canopies and from building shade in the old town |
| Scenario | Modelled clear summer weather at 14:00, not live weather or a forecast for a chosen departure time |
| Model resolution | 10 × 10 m cells, evaluated at 2 m above ground; verify the delivered layer's resolution and whether values are numeric PET or classified ranges |
| Licence and attribution | Verify the selected dataset's access and download terms. Basel-Stadt applies CC BY 4.0 to public-access geodata with a download service; attribute Kanton Basel-Stadt and retain dataset-specific notices. [Official terms](https://www.bs.ch/en/node/29871) |
| API / download discovery | [Official geoservices](https://www.bs.ch/en/node/28694). GetCapabilities verified at https://wms.geo.bs.ch/?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0; exact baseline layer is KL_HumanbioklimaSituation, projection is KL_HumanbioklimaSituation_2030. GetMap rendering, numeric GetFeatureInfo/sampling, download and dataset-specific licence remain to be verified; advertised layers alone do not establish working numeric access |

Optional historical-context mode: compare within the documented 14:00 PET scenario, alongside distance, water and known obstacles. The agreed main comparison uses time-dependent shade and adjustable preferences; PET is not required for it. Shade effects are already represented in PET, so do not apply an additional assumed shade cooling adjustment to those values. A separate shade overlay may explain conditions, but is not evidence for subtracting temperature or PET degrees.

Keep model/scenario time, dataset publication or update time, and retrieval time distinct. Missing cells or unavailable data must remain unknown; a synthetic fallback must be visibly labelled. Do not present this historical baseline or its 2030 projection as today's conditions.

Time-specific shadow modelling is now in scope; see the current-time shade preflight below. SunCalc remains one candidate sun-position utility. It would need its own validation and would not automatically produce updated PET values. The sources below remain candidates for that extension.

## Selected implementation tools — documentation checked 2026-10-03

The implemented browser uses native JavaScript modules with OpenLayers served by Python FastAPI; Python models are canonical and TypeScript declarations/browser schemas are generated. [OpenLayers](https://openlayers.org/) supports raster/tiled OGC layers and vector formats; [licence](https://github.com/openlayers/openlayers/blob/main/LICENSE.md): BSD-2-Clause, retain notice. [Rasterio windowed reads](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html) allow chunked raster processing; [licence](https://github.com/rasterio/rasterio/blob/main/LICENSE.txt): BSD-3-Clause, retain notice. A custom or separately verified shadow algorithm is still needed. [Leptos JavaScript integration](https://book.leptos.dev/web_sys.html) documents wasm-bindgen integration and DOM ownership considerations; [project](https://github.com/leptos-rs/leptos) offers MIT licensing. Check exact pinned versions and transitive notices at adoption. Open-source libraries do not determine the licences of displayed data.

The T1 decision replaced the earlier Vite/npm proposal with native browser modules served by [FastAPI](https://fastapi.tiangolo.com/); there is no JavaScript package manager or build step. Browser assets are checksum-pinned, and Python packages are pinned in backend/requirements.txt. [Rasterio](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html) is installed for compact raster preparation and windowed reads; retain upstream notices. The shadow algorithm and deployment are still under validation.


[100335 metadata](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100335) lists CC BY 4.0, publisher Tiefbauamt, with project name/descriptions, start/end dates, project/document links and an Allmend permit reference. The inspected schema has **no geometry fields and no structured pedestrian-closure field**. Therefore the feed alone cannot place construction zones on the map or exclude walking edges. T0 must find a separately checked spatial permit layer and verify join/closure meaning, or leave this as linked caution information. Do not infer coordinates from a street name or treat every worksite as impassable. No records or attached documents have been imported; linked documents need independent rights/content checks.

## Basel wayfinding research — checked 2026-10-03

Research for the deferred phone-access feature; these sources inform design and do not represent integrated data or validated Basel route guidance.

| Topic | Source | Use and limits |
|---|---|---|
| Mental maps | Kevin Lynch, [*The Image of the City*](https://mitpress.mit.edu/9780262620017/the-image-of-the-city/) (MIT Press) | Framework of paths, edges, districts, nodes, and landmarks. Lynch's perceived edges are not verified physical barriers. |
| Spoken and visual route instructions | Anacta et al., [“Orientation information in wayfinding instructions”](https://link.springer.com/article/10.1007/s10708-016-9703-5) (2016) | Supports studying how local and global orientation cues and landmarks work in instructions; findings do not make a landmark universally familiar. |
| Landmark versus street-name directions | Tom, [“Language and spatial cognition”](https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1045) (2004) | Reports better route-drawing memory after landmark-based than street-name instructions in the studied task; do not generalize to every caller. |
| Landmark selection | [Review of the existing literature](https://pmc.ncbi.nlm.nih.gov/articles/PMC8324579/) | Background on communicable, visible, decision-point, and negative landmarks; validate each cue with actual users and routes. |
| Basel street-name cues | [Basel-Stadt street names dataset 100189](https://data.bs.ch/explore/dataset/100189/) | Candidate spoken street-name fallback; check the current dataset schema and terms before integration. |
| Basel sights and transit orientation | Basel-Stadt, [Geoinformation / MapBS](https://www.bs.ch/en/node/28629) | Official MapBS description mentions sights and tram stops; it does not establish that a feature is visible, familiar, accessible, or suitable for a particular route. |
| Construction and barriers | [Dataset 100335 metadata](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100335) | Inspected metadata/schema has no geometry or structured pedestrian-closure field. A construction record alone cannot prove a walking route is blocked or passable. |
## Other project references, not admitted datasets

[Canton heat action plan](https://media.bs.ch/original_file/cf38be8695e1cb3e0aefcaf832b4b89c65863658/hitzemassnahmenplan-basel-stadt.pdf), [age/quarter population 100128](https://data.bs.ch/explore/dataset/100128/), [quarter indicators 100011](https://data.bs.ch/explore/dataset/100011/), and [federal heat mortality KL077](https://www.indikatoren.admin.ch/public/v2/detail?ind=KL077&lng=de) remain contextual project references. Verify terms, aggregation, relevance and freshness before reuse. SBB / the meeting's unidentified “OVA” provider does not establish a selected transport integration.

Codex (OpenAI), [coding assistant](https://chatgpt.com/codex), used for AI-assisted development and audit. Bundled Pillow/NumPy were used locally for research; no new runtime dependency or production shadow algorithm was installed. Synthetic fallback data must be labelled and contain no real users' location/health information.
