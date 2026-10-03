# Bla Bla Walk

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

Bla Bla Walk is a proposed heat-aware walking route planner for Basel. It aims to help people who are more affected by heat, and their caregivers, compare routes using shade, drinking water, cooler places, and known obstacles.

## The problem

The shortest walk may involve exposed streets, few places to rest, or inaccessible crossings. The project explores how public environmental and map data could make those tradeoffs visible when planning a walk.

## Project status

The map supports online provider observations/fountain locations, a historical PET heat layer with route-class distances, downloaded offline maps and saved provider snapshots, and separate synthetic fixtures. The PET map overlay needs internet; saved route classes remain visible offline with a stale label. PET describes a fixed 14:00 summer scenario. FastAPI serves the browser and API; no JavaScript package manager or build step is required. Compact city geometry preparation is available. Current-time shade and the full weighted route comparison remain later tasks; downloading heights does not enable those features by itself. See the [current preparation handoff](handoff/data-compact-offline.md). T8 also keeps a native 0.5 m preparation for geometry validation; see [T8's handoff](handoff/t8.md).

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

Use Python 3.12 or newer. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python scripts/fetch_browser_assets.py
python backend/export_contract.py
python -m uvicorn bla_bla_walk.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [the local map](http://127.0.0.1:8000). On Windows, use `python -m venv .venv` and run the Activate.ps1 script inside the environment's Scripts folder in PowerShell instead of the first two commands.

The browser assets are pinned by URL and SHA-256 in [config/browser-assets.json](config/browser-assets.json). The setup script downloads them into an ignored local cache, verifies their bytes and retains licence notices. Subsequent setup runs reuse matching files. Initial installation and downloads need internet. The root URL selects synthetic fixtures; use the links in the app to choose a mode.

## Download data before offline use

With the project environment active and internet available, run from the repository root:

```sh
python scripts/fetch_browser_assets.py
python scripts/prepare_geometry.py --workers 2
python scripts/prepare_offline.py --workers 4
python scripts/verify_prepared_data.py
```

Geometry preparation downloads all available pinned city/buffer assets, verifies catalogue SHA-256 checksums, and writes compressed 1m grids with 2m height steps into ignored `data/geometry/`. It keeps native 0.5m surface detail until max aggregation and uses the smaller native 2m terrain sources. Verified temporary source downloads are discarded after conversion. The local manifest records source URLs/checksums, preparation version, output checksums and coverage gaps. Run the same command again to resume; `--limit 2` is a small validation batch, not full preparation. Encoding and accuracy limitations live in [the source register](docs/SOURCES.md#compact-geometry-and-offline-preparation).

Offline preparation saves sanitized observation/fountain layers, any available route PET class summary, and all basemap tiles in the finite advertised Basel rectangle at zooms 12–17. Saved PET route summaries are labelled stale; the PET map overlay itself requires internet. It retains source attribution and saved timestamps. Basemap downloads resume from checksum-verified files. Inspect .cache/basemap/manifest.json (generated locally by offline preparation) for `complete: true` and data/geometry/manifest.json (generated locally by geometry preparation) for `complete_available_inventory: true`; the latter means all available assets, not that the buffer gaps disappeared. Large downloads stay on this computer and are not included in a Git clone.

## Use offline

Keep the local server running with the Run locally command and open [offline mode](http://127.0.0.1:8000/?mode=offline). Internet is no longer required: browser libraries, basemap images, saved provider layers and prepared heights are local. Saved observations are historical and visibly labelled; fountain operation/drinking status remains unknown. Missing saved tiles and missing snapshots are explicit errors and never trigger external requests. Pan/zoom coverage is limited to the downloaded rectangle and zoom range. This is a local-server app, not an installed phone/PWA application; the server must remain reachable.

## Use online or on an external server

Open [online mode](http://127.0.0.1:8000/?mode=online) to request provider observations, fountain locations, the two checked walking routes, and PET-class distances through the API. The historical PET map is served by the canton WMS. PET is modelled for a clear summer high-pressure day at 14:00; it is not current weather. Source attribution, route class distances and unknown coverage remain visible. The first provider load may take longer; later requests follow the observation/fountain adapters' hourly/daily caches.

To run on an external server, install the same pinned environment and browser assets there. Prepare geometry there for the future shade worker, or copy the prepared geometry together with its manifest and config. Run:

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

Slot E's T10 calculation checkpoint has analytic and independent numerical checks; see [its handoff](handoff/t10-shade-calculation.md) for remaining T10 acceptance work. To reproduce the small real-raster spot check, supply the native source pair for tile 2610-1266 from [the pinned inventory](data/tile-inventory.json), saved locally as .hack/t10/surface.tif and .hack/t10/terrain.tif. The validator verifies both catalogue checksums and does not download files:

```sh
python scripts/validate_shade_sample.py --surface .hack/t10/surface.tif --terrain .hack/t10/terrain.tif --output .hack/t10/shade-validation.json
```

To reproduce the compact sensitivity check, supply the same pinned surface/native-0.5m terrain pair plus the matching native 2m terrain asset (same tile/year, replace `_0.5_2056_` with `_2_2056_` in its URL). The 2m SHA-256 pins for all three checked tiles are recorded in [compact validation evidence](data/fixtures/compact-shade-validation.json). The script makes no external requests, writes scaled compact rasters and compressed pre-encoding receiver evidence to the local work directory, and checks both representations independently:

```sh
python scripts/validate_compact_shade.py --surface .hack/t10/surface.tif --terrain .hack/t10/terrain.tif --terrain-2m .hack/t10/terrain-2m.tif --work-directory .hack/t10/compact --output .hack/t10/compact-validation.json
```

Repeat for route tiles 2611-1266 and 2611-1267 using `--tile` and `--terrain-2m-sha256` from the evidence, with their matching source paths and separate work/output paths. Each per-tile report uses the full route denominator and marks outside-tile samples unknown. Across these disjoint receiver tiles, sum shaded/changed-state metres; aggregate unknown metres equal the full route length minus summed shaded metres. The preserved-evidence case retains source flags and numerical ground candidates; it does not certify walking surfaces. Existing compact height files alone cannot reconstruct this evidence. Slot F must version and verify the companion files before cache/API use; see the handoff.

Activate the environment and run from the repository root:

```sh
python backend/export_contract.py
python -m pytest -c backend/pyproject.toml backend/tests
python -m ruff check --config backend/pyproject.toml backend scripts/fetch_browser_assets.py scripts/format_browser.py scripts/prepare_geometry.py scripts/prepare_offline.py scripts/verify_prepared_data.py
python -m ruff format --check --config backend/pyproject.toml backend scripts/fetch_browser_assets.py scripts/format_browser.py scripts/prepare_geometry.py scripts/prepare_offline.py scripts/verify_prepared_data.py
python scripts/format_browser.py --check
bash scripts/doc-check.sh --strict
```

Browser checks use an installed Chromium; set `CHROMIUM_PATH` to its executable if it is not on PATH. These checks skip with a visible reason when no browser is available. Offline browser integration checks also need the saved provider snapshot and basemap from offline preparation. Run only the API/model checks with `python -m pytest -c backend/pyproject.toml backend/tests -m 'not browser'`. No Node.js installation is required.

Format Python with `python -m ruff format backend scripts/fetch_browser_assets.py scripts/format_browser.py` and browser code with `python scripts/format_browser.py`. [backend/bla_bla_walk/interfaces.py](backend/bla_bla_walk/interfaces.py) is canonical; regeneration writes [src/interfaces.ts](src/interfaces.ts) for editor/JSDoc use and the browser validation schema. Include a decision line with model changes and never edit generated files by hand. Consumer ownership is listed in [ROADMAP.md](ROADMAP.md); the map modules now use .js filenames.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Fixture mode uses invented overlays. Online/offline provider modes use admitted sources with timestamps and uncertainty; offline data never claims a live refresh. Prepared geometry has coverage gaps and mismatched survey years; 1m grid spacing does not make native 2m terrain more detailed, and 2m elevation quantization can change shadows. Shade accuracy/performance and route comparison are not established. Scope, unknowns, and demo fallback are documented in the [design brief](docs/design.md).

## Team

The six-person work split is proposed in [ROADMAP.md](ROADMAP.md). Contributors still need to choose role slots and add their GitHub usernames in [TEAM.md](TEAM.md).
