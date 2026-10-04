# Run locally with external sources

Run the Python server on your computer and open **http://127.0.0.1:8000/?mode=online**.
The `mode=online` part enables provider sensor readings and online data adapters.
Opening the plain root URL uses synthetic example layers. Keep internet connected
and the server terminal open while using the app.

## First-time setup

Use Python 3.12 or newer. Run these commands from the repository root.
No Node.js, npm build, API key, account or `.env` configuration is required for
the currently integrated public sources.

On Windows, in PowerShell:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
& ./.venv/Scripts/python.exe scripts/fetch_browser_assets.py
& ./.venv/Scripts/python.exe backend/export_contract.py
& ./.venv/Scripts/python.exe scripts/install_shade_snapshot.py
& ./.venv/Scripts/python.exe scripts/prepare_building_shade.py --offline
& ./.venv/Scripts/python.exe scripts/prepare_rest_stops.py --download
```

These commands use the environment's Python directly, so PowerShell activation
and execution-policy changes are unnecessary. Reuse an existing `.venv` if it
already contains the project dependencies.

On macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python scripts/fetch_browser_assets.py
python backend/export_contract.py
python scripts/install_shade_snapshot.py
python scripts/prepare_building_shade.py --offline
python scripts/prepare_rest_stops.py --download
```

Dependency installation, browser-library downloads and rest-stop acquisition
need internet. Shade installation restores the committed, checksum-verified
prepared data locally. The `--offline` command validates the building cache;
it does not switch the webapp to offline mode. Do this preparation before
starting the server. If installation reports differing local shade inputs,
it preserves them; see [snapshot replacement instructions](../data/prepared/README.md).

## Start and open the app

Windows PowerShell, from the repository root:

```powershell
& ./.venv/Scripts/python.exe -m uvicorn bla_bla_walk.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

macOS/Linux, with the project environment active:

```sh
python -m uvicorn bla_bla_walk.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open [the local online app](http://127.0.0.1:8000/?mode=online).
FastAPI serves both the page and API; no separate frontend server, API URL or
CORS configuration is needed. Do not open the HTML file directly. Press Ctrl+C
in the terminal to stop the server. On subsequent runs, just start the server
and open the same online URL; repeat rest-stop preparation when you want a newer
saved acquisition.

## Which connections are used

| Feature | Source and connection | What to expect |
|---|---|---|
| Weather stations and route temperature | Server → `data.bs.ch`, meteoblue observations dataset 100009 and station catalogue 100082 | Latest available raw readings, with observation times. Sensor cache refreshes on requests after one hour; readings older than 90 minutes are stale. |
| Fountains and route water stops | Server → `data.bs.ch`, IWB dataset 100008 | Provider locations, cached for 24 hours. Current operation and drinking-water status remain unknown. |
| Street-address search | Server → `api3.geo.admin.ch` | Type at least three characters and select a result inside Basel-Stadt, Riehen or Bettingen. |
| New walking routes | Server → `routing.openstreetmap.de` | Select two endpoints and press Calculate. The provider receives their coordinates. |
| Basel street map | Browser → `wmts.geo.bs.ch` | Online map tiles; browser internet access is required. |
| Heatmap and saved-route PET classes | Browser/server → `wms.geo.bs.ch` | Historical PET for a fixed summer scenario at 14:00; this is separate from current sensors. |
| Automatic temperature palette | Server → `api.open-meteo.com` | Seven daily mean forecasts for a fixed Basel point, cached for one hour. Used for colours, not measured route temperatures. |
| Benches, parks and supermarkets | Preparation → `overpass.osm.ch`; serving reads the local saved cache | Run rest-stop preparation above. Mapped weekly supermarket hours are interpreted locally; they are not live opening or cooling checks. |
| Exact-time shade for the saved demo | Local prepared buildings, survey grids and solar calculation | Install the shade snapshot above. Online mode does not download shade inputs automatically. |

Allow outbound HTTPS to these hosts from the relevant browser/server. Initial
browser-library preparation also uses GitHub and jsDelivr, as pinned in
[the asset configuration](../config/browser-assets.json). Data dates, attribution
and limitations are recorded in [the source register](SOURCES.md).

## Check that the data is showing

1. Confirm the address bar ends in `/?mode=online`. The first provider load can
   take longer than later loads.
2. Under **More**, enable **Weather stations**. Select a station to inspect its
   reading, observation time, age and source. Open **Information sources** for
   the layer status and limitations.
3. Search and select a start and destination, then press **Calculate**. The
   **Temperature** route layer estimates temperatures from nearby admitted sensor
   readings; unsupported sections stay unknown. Enable **Fountains** or **Water**
   to inspect provider water locations and route stops.
4. Enable **Heatmap** to check the historical WMS layer. To inspect prepared
   shade, use **Try SBB → Marktplatz example**, choose a departure and Calculate,
   then enable **Shading**. A cold saved-route comparison can take around
   20 minutes; the screen shows background progress.

The saved SBB → Marktplatz pair has shade comparison support. Newly selected
address pairs have online walking geometry and sensor estimates, but their
shade and access remain unknown. Unknown access can also withhold a recommended
journey for the saved pair. Enabling sources does not remove these limits.

For a direct API check, open [the online snapshot](http://127.0.0.1:8000/api/map?mode=online).
It should report `"mode": "online"`. Inspect layer `availability`, `features` and
their provenance; a successful HTTP response alone does not prove all providers
returned data. Additional checks:

- [Sensor layer](http://127.0.0.1:8000/api/route-temperatures?mode=online)
- [Fountains and saved rest stops](http://127.0.0.1:8000/api/route-amenities?mode=online)
- [Palette forecast](http://127.0.0.1:8000/api/palette-forecast?mode=online)
- [Interactive API documentation](http://127.0.0.1:8000/docs)

## If something is missing

| Symptom | Action |
|---|---|
| Example sensors | Open the explicit online URL above. |
| Page fails to initialize or `/vendor` files return 404 | Rerun browser-asset preparation and reload the page. |
| Sensor layer is stale or missing | Check observation timestamps and outbound access to `data.bs.ch`. Reload to request data; the server respects its cache and retry intervals. The browser does not continuously poll sensors. A restart clears the in-memory sensor/fountain caches, but cannot make the provider's readings newer. |
| No benches or interior-space candidates | Run rest-stop preparation, then reload. Candidates may also be outside the route buffer or withheld because their schedules cannot be interpreted. |
| Shade/comparison returns 503 | Stop the server, install and validate the shade snapshot, then restart. Check the server error and snapshot notes if validation fails. |
| Map tiles or Heatmap are blank | Check browser access to the WMTS/WMS hosts, including any browser/network blocking. |
| Address or walking-route provider fails | Check server internet access. Retry Calculate or use the saved example; map pins can replace address search. |
| Port 8000 is already in use | Stop the previous app server, or choose another port and use that port in the browser URL. |

Full basemap downloads and city-wide geometry preparation are not prerequisites
for this local online setup. For disconnected use, follow
[the README's offline preparation](../README.md#download-data-before-offline-use).
