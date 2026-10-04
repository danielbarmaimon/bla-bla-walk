# Sources

## Official Basel address lookup — checked 2026-10-03

The [GeoAdmin SearchServer](https://docs.geo.admin.ch/access-data/search.html)
supplies official building addresses (`origins=address`). The online lookup is
admitted under [FSDI terms](https://www.geo.admin.ch/en/general-terms-of-use-fsdi)
and [swisstopo open-data terms](https://www.swisstopo.admin.ch/en/faq-free-geodata),
with **© swisstopo** attribution. No key or registration required. Debounced
interactive requests follow fair use; this implementation does not scrape or
download the directory. The provider supports partial/fuzzy matching: a result
is a suggestion to select, not an exact-match guarantee.

Requests use the pinned Basel-Stadt canton bounding box in LV95; every returned
point is checked against its exact polygon, including holes, Riehen and Bettingen.
Only address label and WGS84 coordinates pass to the browser; provider HTML is
removed. Public venue Dornacherstrasse 394 returned a real Basel match during
the source check. The live street query also returned partial house-number matches.
Out-of-canton points are excluded, even when provider fuzzy matching returns them.

Typed queries are sent to geo.admin.ch in online/example mode. The app uses a POST
body so local access-log URLs omit them, never persists queries or selected
addresses, and marks replies no-store. Offline mode makes no address-provider
request; map pins and sample places remain available. Address coordinates do not
certify pedestrian access or supply arbitrary-endpoint route geometry.

## Selected-endpoint walking routes — checked 2026-10-04

The admitted [FOSSGIS OSM service](https://routing.openstreetmap.de/about.html)
now supplies ephemeral street geometry for selected Basel endpoints via its
`routed-foot/route/v1/driving` endpoint. The server uses a foot profile despite
the URL's final profile token. Attribution: **© OpenStreetMap contributors**,
ODbL 1.0, **Routing by OSRM (FOSSGIS)**. The UI links to OpenStreetMap's
map-correction page. A valid user agent and one upstream request per second per
server process follow the provider's terms; no scraping or persistent route cache.

Endpoint coordinates are sent to FOSSGIS, which states that requests are saved
in its server log; the controls disclose this. Local POST access-log URLs omit
coordinates. Both endpoints must lie inside Basel-Stadt. Paths may cross the
canton boundary and carry no shade-coverage guarantee. Snaps to the pedestrian
network over 100m are rejected rather than drawing invented building connectors.

Live public-address tests produced two routes to Dornacherstrasse 394; changing
the start to Freie Strasse 10 replaced the line with different network geometry.
Distances come from OSRM; walking time uses the configured T2 speed assumption.
Access, temporary closures and shade ranking stay unknown for these new pairs.
Only the saved checked pair has current-departure shade comparison. Offline has
no arbitrary-endpoint routing graph; unavailable routing clears old lines.

## Approved building-shadow route model

The user chose a building-cast shadow approximation to finish the T10 continuation.
[Preparation](../scripts/prepare_building_shade.py) uses the public Overpass
instance configured in [building settings](../config/building-shade.json),
queries building/building-part polygons around the two saved routes plus 1500m,
and saves only feature identifiers, geometry, explicit metre heights and an
unresolved-geometry flag. Names, addresses, user metadata and other tags are
omitted. No floor-count-to-height guesses are used. OpenStreetMap data is under
[ODbL 1.0, with attribution to OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
The [Overpass instance listing](https://wiki.openstreetmap.org/wiki/Overpass_API)
documents public endpoints; preparation is an explicit network operation, not
part of API serving. Retrieved/provider times and footprint checksum are in the
local model manifest; summarized provenance is in the recorded validation.

Survey-derived roof heights retain the swisstopo attribution and source versions
described below. Footprints restrict surveyed casters to buildings. Roof-minus-
terrain heights or explicit mapped metre heights form prisms on flat ground.
Overlapping surveyed building parts remain approximations; dated footprints and
survey years may differ. Incomplete relation extents and missing roof heights
stay unknown. Outside footprints, valid paired source flags and a 0–2m compact
height difference admit a plausible ground proxy; no physical walkability is
claimed. Trees and terrain relief do not cast shadows in this model.

The ray reach is explicitly finite: sunlit means no modeled building occlusion
within 1500m, with valid model coverage throughout the ray. Missing coverage does
not imply clear sunlight. Below 10 degrees remains unknown; night is separate.
This finite model does not use a pretend global horizon ceiling. The original
strict survey algorithm below retains its physical-horizon requirement.

[Recorded building validation](../data/fixtures/building-shade-validation.json)
covers both complete route polylines, cold/cache/concurrent requests, a shared
prepared-tile seam, night and zero external HTTP transport calls. Numerical and
analytic tests cover model selection, roof failures and shadow direction.
Raster-cell counts are not route distances or physical shade observations.
README owns preparation and reproduction commands. T5/T6 integration is merged;
the [T6 acceptance record](../handoff/t6-integration.md) tracks journey validation.
Observed ground/shade accuracy and full-city coverage remain separate work.

### Local building-cache restoration, 2026-10-04

The [versioned prepared shade snapshot](../data/prepared/README.md) now distributes
the sanitized building database and checksum-verified compact survey artifacts
with their original manifests. The OSM database remains ODbL 1.0; survey artifacts
retain © swisstopo attribution and the open-data terms. Installation is local and
makes no provider calls. Acquisition checkpoints and unrelated provider caches
are excluded. Sharing this snapshot does not change source freshness, coverage
constraints or physical-validation limits.

The configured global service was unavailable on this clone. The [Swiss Overpass service](https://overpass.osm.ch/) supplied 72 completed, sanitized GET batches containing 17,432 building/part footprints. The [OSM instance register](https://wiki.openstreetmap.org/wiki/Overpass_API#Instances_with_data_only_for_a_specific_region) declares Switzerland coverage; the [SOSM terms](https://sosm.ch/about/terms-of-service/) apply. Attribution remains © OpenStreetMap contributors / ODbL 1.0, with surveyed roof evidence © swisstopo.

This restoration constrains model support to the official Basel-Stadt boundary already admitted in the tile inventory, intersected with the requested halo. A ray leaving that area remains unknown unless a known in-area blocker proves building shade. Complete batch retrieval does not claim international halo coverage, full-city receiver validation or current physical shade. One unresolved building extent remains unknown. The provider's raw source marker `117480` is not an interpretable date: provider source freshness is explicitly unknown; UTC retrieval times are separately retained. Footprints contain source ID, geometry, optional mapped metre height and unresolved flag only, with no raw name/address/contact tags.

The earlier global-source validation above remains historical. New local validation and T23 readiness evidence are in [the cache-completion handoff](../handoff/t10-cache-completion.md); source and model constraints differ, so earlier measurements cannot be substituted for this setup's results.

## Slot E shade calculation checkpoint

The offline [solar bearing implementation](../backend/bla_bla_walk/solar.py) uses the NOAA/Meeus Julian-century equations with geometric sun-centre elevation, without atmospheric refraction. [NOAA's calculation details](https://gml.noaa.gov/grad/solcalc/calcdetails.html) describe the approximation; this implementation restricts dates to 1800–2100. The independent [NREL SPA report, appendix A.5](https://www.nlr.gov/docs/fy08osti/34302.pdf) supplies the 2003-10-17 Colorado reference example. Geometric elevation and azimuth match that case within 0.01 degrees. SPA software is not bundled.

The [shade calculator](../backend/bla_bla_walk/shade.py) traces grid-cell prisms toward the sun. It consumes decoded metre heights and preserves missing/surface-below-terrain flags. A raster top is an opaque caster approximation; it cannot establish leaf transmissivity, a walkable roof or a receiver beneath a canopy. Explicitly supported ground receiver heights and projection convergence belong to the request's geometry preparation. Night is distinct from daytime shade.

The limits in [config/shade.json](../config/shade.json) reuse T0's 10-degree/1500m engineering envelope. An unblocked ray becomes sunlit only after crossing an externally verified absolute horizon ceiling within valid geometry and the ray limit. A maximum from a cropped scene cannot certify distant terrain or missing buffer cells. Rays lacking that evidence remain unknown; a known blocker can still prove occlusion.

[Calculation validation evidence](../data/fixtures/shade-validation.json) records a checksum-pinned native 0.5m Basel centre window: 48 receiver/time combinations match an independent ray/rectangle-intersection reference, with 37 shaded and 11 unknown. Candidate receivers compare numerical geometry; no observed pedestrian shade or walkability is claimed. The synthetic compact-grid check changes a 5m object to 6m and its 45-degree shadow from 5m to 6m, demonstrating that quantization can change route samples. Compact real-scene accuracy, canopy/bridge receiver support, city-scale performance and route-score sensitivity remain future physical/city-wide acceptance beyond the approved route approximation. README owns the reproduction command.
[Calculation validation evidence](../data/fixtures/shade-validation.json) records a checksum-pinned native 0.5m Basel centre window: 48 receiver/time combinations match an independent ray/rectangle-intersection reference, with 37 shaded and 11 unknown. Candidate receivers compare numerical geometry; no observed pedestrian shade or walkability is claimed. The synthetic compact-grid check changes a 5m object to 6m and its 45-degree shadow from 5m to 6m, demonstrating that quantization can change route samples. [Compact sensitivity evidence](../data/fixtures/compact-shade-validation.json) adds independent numerical scene checks and full-denominator samples of the two saved demo routes at three departure times. It separates raw compact heights from compact heights with pre-encoding validity/receiver evidence. Rounding can hide survey mismatch and ground/canopy distinctions; the preserved case rejects unsupported receiver credit. Its numerical 0.1m ground envelope is a validation selection, not a walkability or canopy rule. All four source samples must qualify, and unrounded surface maxima remain available for explicitly supported receiver heights. The native 0.5m reference and compact 2m terrain differ in resolution; changed states combine terrain-source, pooling, height and receiver-support effects. The spot checks measure surveyed-envelope behaviour, not physical shade accuracy. Canopy/bridge support, city-scale integration/performance and accepted route scoring remain open. README owns the reproduction commands.

## T0 admission audit — 2026-10-03

The source audit is complete. Geometry preparation is feasible **with explicit unknown coverage and scene-validation requirements**, not a promise of known shade everywhere. T4 adapters supply the app's online/saved provider modes; T6 connects shade and route evaluation to the journey; its [acceptance record](../handoff/t6-integration.md) tracks verified behavior and the remaining deployment check. [Source manifest](../data/source-manifest.json) records requests, samples, provenance, cost measurements and acceptance budgets. [Tile inventory](../data/tile-inventory.json) pins the boundary, every required tile, asset versions, checksums, grids and missing geometry. Original audit samples remain local under ignored `.hack/t0/`; current compact preparation is documented below.

Admission permits the stated use; it does not establish live availability, measured cooling, drinking-water safety or pedestrian access. Preserve source-specific rights and attribution, transformations, observation/scenario time, publication time and retrieval date. The repository's prioritised resources are project references; their inclusion does not independently establish organiser endorsement or reuse permission.

| Layer | Verified access and evidence | Rights / attribution | Admission and limits |
|---|---|---|---|
| Basel grey basemap | [WMTS capabilities](https://wmts.geo.bs.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml), layer `VS_Vektorstadtplan_grau`, EPSG:3857, zooms 0–17, 256px tiles. Central PNG returned 200, nonblank, CORS `*`, one-day cache, and rendered directly in browser. [Official model §11.3 p23](https://models.geo.bs.ch/Modellbeschreibungen/VS_Vektorstadtplan_KGDM_V1_0.pdf) maps this layer to Vektorstadtplan / [VSBS](https://api.geo.bs.ch/stac/v1/collections/VSBS). | CC BY 4.0; **Quelle: Geodaten Kanton Basel-Stadt**. [Geoservices](https://www.bs.ch/en/node/28694) permits free GIS/web WMTS use; no numerical quota found on inspected page. | Admitted. Advertised extent and request hash in manifest. T1 displayed the live map and boundary. Tile modification date is not underlying survey date. |
| Observed temperature | [100009](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100009), bounded latest-per-station query verified for `0020F940`; 19.39°C at 2026-10-03 11:00:01 UTC. T4 fetches selected fields, sorts latest first, and joins using `name_original`. | CC BY 4.0; **meteoblue AG via Open Data Basel-Stadt**. | Admitted raw points. Provider description says hourly; catalogue says daily. Adapter refreshes hourly and labels values stale after 90 minutes. Values are uncorrected and may be missing. Reads up to 5,000 recent records per refresh; stations absent from that bounded window remain missing. |
| Station locations | [100082](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100082), 198 records; sample ID/time match above. | CC BY 4.0; **meteoblue AG via Open Data Basel-Stadt**. | Admitted. T4 joins `name_original` and clips points to advertised Basel map bounds; that rectangle is not exact canton clipping. The wider catalogue does not mean all stations are active or inside the canton. |
| IWB fountains | [100008](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100008), 305 records; names/point geometry retrieved. T4 selects only names and coordinates. | Noncommercial use with **IWB Industrielle Werke Basel** attribution; commercial reuse requires supplier permission. Team accepted these terms 2026-10-03. | Admitted locations for this noncommercial prototype. Cache refreshes daily; provider updates are irregular. Dataset has no structured fountain type, drinking-water, operational, or access fields. Those values stay unknown. Photos, media URLs, descriptions and free text are excluded. |
| Pedestrian route example | [FOSSGIS OSM routing service](https://routing.openstreetmap.de/about.html), routed-foot OSRM profile; `data/routes/demo.geojson` pins the 2026-10-03 Basel SBB/Centralbahnplatz → Marktplatz geometry and retrieval metadata. | **© OpenStreetMap contributors**, ODbL 1.0; **Routing by OSRM (FOSSGIS)**. | One checked pedestrian network path for the PoC, not arbitrary routing. The provider does not verify temporary closures or each edge's current access. Other pinned destinations have no street directions yet. |
| Managed trees | [100052](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100052), 32,378 records; points/species accessed. | CC BY 4.0 + OSM notice; **Geodaten Kanton Basel-Stadt**. [Notice](https://data-bs.ch/stata/dataspot/permalinks/20240822-osm-vektordaten.pdf) permits incorporation into OSM; attribution waiver is specific to OSM, not standalone canton use. | Admitted context points. Daily; Basel/Riehen managed trees do not cover all private vegetation. No inspected height/crown-radius fields; not a physical shadow source. |
| Construction projects | [100335](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100335), 103 records; project/date/link/permit-ID fields, no geometry. Direct API recheck 2026-10-04: data and metadata processed at 2026-10-04 06:01 UTC; 81 records overlap 2026-10-04 using `datum_von`/`datum_bis`. | CC BY 4.0; publisher Tiefbauamt, preserve catalogue attribution. | Admitted caution only. Official cadence is irregular. Project dates are active-project intervals, not closure intervals. Schema has no structured pedestrian-closure field. |
| Spatial permits | [100018](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100018), polygon records joined on `100335.id = 100018.begehrenid`; direct API recheck 2026-10-04 reports `geometry_types: [Polygon]`, daily cadence, and data processed 2026-10-04 05:09 UTC. | CC BY 4.0 + OpenStreetMap notice; **Geodaten Kanton Basel-Stadt**. | Reusable polygon geometry for caution/context only. The official description says the shown areas are non-binding; occupancy/status fields do not prove a pedestrian edge is blocked. Attached documents and contact/free-text fields are not admitted automatically. |
| Canopy context | [100357](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100357), three snapshots 2012/2021/2024; 2024 raster/directory returned 206, worldfile 200; 0.5m EPSG:2056, 21767×18189 uint8. | CC BY 4.0, preserve catalogue attribution. Published/processed 2025-09-09; three-year cadence, next 2027/2030. | Admitted context, pending full value/class validation. Bounded directory/metadata ranges verified CRS and NoData `0` after the initial 64KiB image decoder failed. 396,060,323 bytes. Do not treat NoData 0 as confirmed canopy absence or sunlight. Canopy does not establish time-specific shade or public access. |
| OSM parks / benches | [Swiss Overpass](https://overpass.osm.ch/); queried `leisure=park`, `amenity=bench`. Bounding box 7.55–7.69 E / 47.53–47.61 N returned 223 mapped parks and 2,872 benches. | [ODbL 1.0](https://www.openstreetmap.org/copyright); **© OpenStreetMap contributors**; retain applicable derived/redistributed database obligations. | Admitted mapped candidates. Not canton-clipped or completeness-verified. Bench tags: backrest 2,435, covered 197, wheelchair 0, check_date 348. Missing tags mean unknown, not absent facility/access. Endpoint snapshot field was not an ISO date. Recheck important stops. |

### T4 fetch and freshness behaviour

Each source request times out after eight seconds and reads at most 2MB. The [Explore API caps ordinary records pages at 100](https://help.opendatasoft.com/apis/ods-explore-v2/explore_v2.1.html#records); T4 follows that limit. It reads up to 250 stations across three pages and 350 fountain records across four pages. It selects the newest 5,000 observations in one bounded JSON export, then joins matching station IDs. The live export returned 5,000 selected records in 903,383 bytes. Station points are clipped to the advertised map rectangle, not an exact canton polygon.

Temperature snapshots refresh hourly because source documentation says hourly; catalogue metadata says daily. A point stays current for 90 minutes after its observation, then becomes stale. IWB locations refresh daily because catalogue changes are irregular. Their current source snapshot never means a fountain works, offers drinking water, or permits access.

Adapters keep the last successful snapshot in process memory. Failed refreshes return that snapshot as stale; cold failures return a missing layer. A one-minute retry delay bounds repeated failures. T6 owns API wiring and must preserve these explicit states. Fixtures are dated, small, rights-labelled examples; they are not a live fallback.

The isolated `/poc` page includes `poc/provider-snapshot.json`, a sanitized 2026-10-03 capture of the admitted T4 layers (177 station points and 305 IWB fountain locations). The page marks this capture as saved and treats current readings as stale until a live provider response succeeds. A 50 m route buffer finds fountain candidates; a 250 m buffer displays nearby sensor points. The route's 26/29/36/31°C colour sequence is illustrative and does not interpolate those readings. The user-supplied `poc/assets/inferno.png` is a visual legend for this example.

### Construction semantics

The [Tiefbauamt page](https://www.bs.ch/bvd/tiefbauamt/baustellen) is the project's starting reference. Spatial permits supply usable polygons, not authoritative pedestrian closures. Keep project dates, permit dates and statuses separate. One project may have several occupancies. Exclude an edge only when a separately verified source confirms that walking is blocked; otherwise show a caution/unknown. Do not geocode a street name into a fictitious closure or mark every worksite impassable.

### T25 current construction follow-up — 2026-10-04

The direct [100335 API metadata](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100335) recheck confirms CC BY 4.0, publisher Tiefbauamt, irregular update frequency, `records_count: 103`, no `geo_shape`/geometry field, and no pedestrian-closure field. The records endpoint returned 81 projects whose source dates include 2026-10-04. These are current project records, not proof that a walking edge is closed.

The linked [100018 API metadata](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100018) confirms Polygon geometry, daily processing, and CC BY 4.0 + OpenStreetMap attribution. Its official description says the areas shown are non-binding. It is therefore reusable spatial context for a construction caution, not an authoritative closure mask. No coordinates were invented or copied into the app.

The current route snapshot is [OSRM foot-profile geometry](../data/routes/demo.geojson) retrieved 2026-10-03. The adapter explicitly reports no temporary-closure feed and no per-segment access audit, and keeps route availability `unknown`. It cannot currently avoid newly closed edges; no blanket blockage or rerouting rule was added.

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

Downloads are bounded to at most four concurrent assets, resume interrupted source transfers, validate source size and SHA-256, then decode/prepare one tile per worker. Outputs are tiled 256×256 internal blocks with DEFLATE/predictor compression. Manifest checkpoints and output hashes permit verified reuse. Preparation revision 2 retains verified source pairs until 1m subcell validity/inversion flags are saved with pinned hashes, then discards the temporaries. Missing flag evidence stays unknown. The pair_flags registry adds one byte per 1m cell and is checked by offline verification; the full provider transfer is still required on a new setup. All 225 int16 output grids require 450MB uncompressed before masks/overhead. At a 1m shade output grid, two one-byte full-buffer masks would require 278MB per time bucket, four times the old 2m estimate. Historical 2m timings are not new 1m latency results; the existing memory/cache/latency budgets remain acceptance targets.

[Offline preparation](../scripts/prepare_offline.py) saves the finite basemap extent/zoom range from [config/basemap.json](../config/basemap.json), retaining **Geodaten Kanton Basel-Stadt / CC BY 4.0** attribution, plus sanitized T4 provider output with its observation/retrieval times and source licences. Its local manifests record image checksums and retrieval time; map retrieval date does not establish an underlying survey date. Snapshot temperatures remain raw uncorrected observations, and IWB reuse remains noncommercial. Photos/contact fields are excluded by the T4 adapters.

Offline API reads saved bytes only, marks previously current features/layers stale, preserves missing/unknown states, and never refreshes providers. Local tile misses return 404 without a remote fallback; a missing/invalid provider snapshot returns 503. Online API uses the existing hourly/daily adapter caches and last-good stale behavior. Both modes retain visible source times and uncertainty. Geometry ingestion alone does not supply a working shade/evaluation API. [README](../README.md) owns local offline and external-server run instructions.

The historical T0 preflight did not establish these API targets; the current route-model measurements are recorded above. T10 must optimise or revisit targets with the team if measurements fail. No whole-city recalculation in the request path. Five-minute cache buckets and 2m shade remain candidates; validate accuracy before adopting them. Preserve geometry version, requested/effective time, resolution and explicit unknowns in any derived outputs. Distinguish geometric occlusion from observed cloud cover and measured temperature.

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

Documentation checked: 2026-10-03. The historical PET layer is now displayed in online map mode and sampled for route-class distances. It remains a fixed historical scenario, not the live-temperature foundation.

PET (Physiological Equivalent Temperature) estimates thermal conditions for a modelled person from air temperature, humidity, wind, and short- and long-wave radiation. Although expressed in °C, PET is not thermometer air temperature or a personalised health-risk estimate.

| Item | Finding / reference |
|---|---|
| Dataset | Stadtklima: `HumanbioklimSituation`, the daytime PET layer; the separate `HumanbioklimSituation_2030` projection is excluded from the baseline |
| Map and catalogue | [MapBS Stadtklima](https://www.geo.bs.ch/stadtklima), [Basel-Stadt geodata catalogue](https://shop.geo.bs.ch/geodaten-katalog/) |
| Layer description | [Official Stadtklima data model, sections 6.1.12–6.1.13](https://models.geo.bs.ch/Modellbeschreibungen/KL_Stadtklima_KGDM_V1_0.pdf) |
| Method and shade evidence | [2019 climate analysis, sections 4 and 4.4](https://map.geo.bs.ch/file_proxy/KL_Stadtklima_Windstroemungsfeld/Endbericht_Basel_Klimaanalyse_Rev09_ohne_Anhang.pdf): reduced heat stress under tree canopies and from building shade in the old town |
| Scenario | Modelled clear summer weather at 14:00, not live weather or a forecast for a chosen departure time |
| Model resolution and values | 10 × 10 m cells, evaluated at 2 m above ground. The WMS serves rendered PET classes; its GetFeatureInfo response contains no numeric value. |
| Licence and attribution | The catalogue lists both PET products as public and available through the Geodaten-Shop. Basel-Stadt's terms apply CC BY 4.0 to public-access geodata with a download service; attribute **Quelle: Geodaten Kanton Basel-Stadt**. [Official terms](https://www.bs.ch/en/node/29871) |
| API / download | [Official geoservices](https://www.bs.ch/en/node/28694). Current WMS GetCapabilities names the baseline layer `KL_HumanbioklimaSituation`; the projection is `KL_HumanbioklimaSituation_2030`. A GetMap request returned a four-band PNG. GetFeatureInfo returned an empty feature properties object, so the route adapter samples the rendered PET class colours and matches them against the published legend. Unknown/unmatched pixels remain unknown. |

Optional historical-context mode: compare route distance across PET classes alongside distance, water and known obstacles. Route samples use 10 m intervals and retain unclassified distance as unknown. PET classes supplement route evidence; they do not produce a combined score or automatic health recommendation. Shade effects are already represented in PET, so do not apply an additional assumed shade cooling adjustment to those values. A separate shade overlay may explain conditions, but is not evidence for subtracting temperature or PET degrees.

Keep model/scenario time, dataset publication or update time, and retrieval time distinct. Missing cells or unavailable data must remain unknown; a synthetic fallback must be visibly labelled. The browser overlay and route sampler require internet and are absent in offline mode. Do not present this historical baseline or its 2030 projection as today's conditions.

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

The `/poc` wayfinding layer uses OSM centres for [Barfüsserplatz](https://www.openstreetmap.org/way/132752251), [Stadtcasino Basel](https://www.openstreetmap.org/way/147634462), and [Barfüsserkirche](https://www.openstreetmap.org/way/137472263), checked through Swiss Overpass on 2026-10-03. The square is a node on the example route; the buildings are nearby landmark candidates. Centre proximity does not verify visibility, accessibility, or navigation value. The cool-place layer uses [Theater Basel Foyer Public](https://www.theater-basel.ch/de/foyerpublic) from the [canton heat list](https://www.bs.ch/it/node/31069). Recheck opening hours; AC is unverified. The PoC's area heat surface and shadow patches are synthetic display examples, not admitted provider layers or safety evidence.
## Other project references, not admitted datasets

[Canton heat action plan](https://media.bs.ch/original_file/cf38be8695e1cb3e0aefcaf832b4b89c65863658/hitzemassnahmenplan-basel-stadt.pdf), [age/quarter population 100128](https://data.bs.ch/explore/dataset/100128/), [quarter indicators 100011](https://data.bs.ch/explore/dataset/100011/), and [federal heat mortality KL077](https://www.indikatoren.admin.ch/public/v2/detail?ind=KL077&lng=de) remain contextual project references. Verify terms, aggregation, relevance and freshness before reuse. SBB / the meeting's unidentified “OVA” provider does not establish a selected transport integration.

Codex (OpenAI), [coding assistant](https://chatgpt.com/codex), used for AI-assisted development and audit. Bundled Pillow/NumPy were used locally for research; no new runtime dependency or production shadow algorithm was installed. Synthetic fallback data must be labelled and contain no real users' location/health information.

## Saved route-stop acquisition — 2026-10-04

The route-stop preparation queries the fixed Basel-Stadt bounding box through the admitted [Swiss Overpass endpoint](https://overpass.osm.ch/api/interpreter), then clips bench points and park centres to the pinned canton boundary. The local acquisition contains 2,142 sanitized mapped candidates, with its actual UTC retrieval time recorded per feature. Only source IDs, coordinates, generic labels and provenance are retained; raw names/contact tags are discarded. This newer acquisition is separate from the earlier partial T0 audit above. The ignored cache is not redistributed in GitHub.

**© OpenStreetMap contributors**, [ODbL 1.0](https://www.openstreetmap.org/copyright). Park centres are not entrances; benches and public access are not field-verified. Route proximity uses a 50m geometric buffer, not walking detour distance. Indoor candidates keep their operator sources and unknown opening/temperature status. IWB fountains retain their existing noncommercial terms, saved source dates and unknown operation, drinking-water and access status. The API uses the saved IWB snapshot for example/offline mode and the admitted provider for online mode; fixture fountain overlays are not route-stop evidence. Source details accompany both markers and the nearby list.

## Exploratory route temperature and palette forecast — 2026-10-04

The root app now interpolates admitted raw meteoblue observations from 100009 onto the selected walking geometry. This supersedes neither the separate PoC illustrative colour sequence nor historical PET. A latest-reading cohort excludes missing/nonfinite/fixture values and timestamps more than five minutes in the future and timestamps more than 60 minutes behind the latest observation. Estimates require two nearby readings; up to three nearest stations within 1km receive inverse-distance-squared weights (1m distance floor). The line is sampled at nominal 25m intervals, bounded at 1,200 segments. Unsupported distance is grey/unknown. Source observation/retrieval times, saved/stale status and contributing readings are displayed. No shade subtraction, tree cooling or PET offset is inferred. Raw values are uncorrected and the 1km/60min settings are exploratory display choices, not physical-accuracy guarantees.

A leave-one-station-out check on the saved acquisition supported 65 of 79 time-aligned stations, with mean absolute error 0.758°C. This is a same-cohort consistency check, not independent street/route validation. A real online SBB–Marktplatz display yielded 16.3–18.1°C, seven contributing stations and full geometric coverage at check time; a saved Freie Strasse–venue display yielded 17.3–19.7°C, twelve stations and full coverage. These are dated checks, not permanent/live claims. Relative scales preserve at least a 2°C span; identical readings do not create an artificial temperature gradient. Unknowns remain unknown.

For automatic palette choice only, [Open-Meteo forecast documentation](https://open-meteo.com/en/docs) supplies `daily=temperature_2m_mean`, seven days, timezone Europe/Zurich at fixed Basel city coordinates. [Terms](https://open-meteo.com/en/terms) admit the free API for this noncommercial prototype; weather data is CC BY 4.0 with attribution **Weather data by Open-Meteo**. Commercial API use requires a suitable subscription. The dated daily city forecast was fetched and its unit/date payload verified locally. No personal location or route is sent. One-hour cache/retry limits, 6-second timeout and 64KiB response bound prevent repeated unbounded calls; offline serving makes no requests. Retrieval time is not model issue time. A forecast is never represented as a measured route temperature, and a saved forecast remains labelled saved offline. The user requested the summer/winter colours; automatic winter below 15°C is a documented display convention with manual override.

## Supermarket schedules and display projections — 2026-10-04

A fresh fixed-canton Swiss Overpass acquisition contains 2,237 clipped bench/park/supermarket candidates, including 95 supermarkets with 87 opening_hours tags. **© OpenStreetMap contributors / ODbL 1.0** remains the source/licence. Generic supermarket or allowlisted chain names and opening_hours are retained; raw name/contact fields are discarded. The previous acquisition count remains historical. The conservative client evaluates weekly schedules in Europe/Zurich at the selected departure, withholds missing/complex/overnight hours and unknown calendar years, and withholds all listed public holidays. The [official Basel-Stadt holiday calendar](https://www.bs.ch/themen/arbeit-und-steuern/feiertage-im-kanton-basel-stadt) supplies the nine 2026 dates in config/route-stops.json. These are mapped schedules, not live operation, accessibility or cooling evidence. The prior Theater foyer candidate is no longer part of Interior space. All serving remains local.

Route stop display coordinates are now projections onto the walking line. Source coordinates remain unchanged and inspectable; this visual projection is not a verified entrance or accessible detour. Planned rest prompts follow the user-requested 15 walking-minute interval and are not source-backed benches. Fast route means lowest estimated walking time; Recommended is withheld unless the existing eligible comparison supplies a winner. Shading repair is explicitly deferred. All source descriptions/limits appear under Information sources, separately from title-only controls.

### Route stop icons

Lucide `droplets`, `rocking-chair` and `clock-fading` SVGs are served locally. The latter two were retrieved on 2026-10-04 from the [official Lucide icon repository](https://github.com/lucide-icons/lucide/tree/main/icons). Licence: ISC; retained in `src/icons/LICENSE.txt`. Icons and screen-distance grouping describe stop types and visual proximity, not verified accessibility.
