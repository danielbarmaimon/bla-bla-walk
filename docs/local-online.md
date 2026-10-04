# Run locally with external sources

The plain root URL defaults to online mode. Use Python 3.12 or newer and keep
internet connected. No Node.js, API key, account or `.env` configuration is
required for the currently integrated public sources.

## Start with one command

From the repository root, on Windows (PowerShell or Command Prompt):

```powershell
.\scripts\run-windows.cmd
```

On Linux:

```sh
bash scripts/run-linux.sh
```

Open [the online app](http://127.0.0.1:8000/). Keep the terminal open and press
Ctrl+C to stop. Both commands create or reuse the project `.venv`, install the
pinned requirements, verify/download browser assets, install missing committed
shade inputs, validate the saved building cache and download missing rest stops.
Prepared local inputs are preserved. Later runs reuse cached browser/data files;
requirements are checked again to pick up repository updates. Generated shared
contracts are committed and do not need regeneration to start the app.

To use another port, append it: `.\scripts\run-windows.cmd 8001` or
`bash scripts/run-linux.sh 8001`. FastAPI serves the page and API from that same
address. Do not open the HTML file directly. Explicit `?mode=offline` and
`?mode=fixture` URLs remain available for their separate use cases.

Run the launcher/server with outbound network access. A server started in a
network-restricted coding-tool sandbox can return 503 for address search and
walking routes even when your browser has internet. If asked, allow network
access for this session, then restart the server using the same launcher. The
launcher reports preparation failures and stops before starting a partial setup.

## Refresh or recover prepared data

The launchers download rest stops only when their cache is absent. For a newer
acquisition, stop the server and run the project Python with
`scripts/prepare_rest_stops.py --download`, then restart the launcher. The Python
path is `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` on Linux.

If shade installation reports differing local inputs, it preserves them. Review
[snapshot replacement instructions](../data/prepared/README.md) before choosing
to replace them. Validate existing buildings with the project Python and
`scripts/prepare_building_shade.py --offline`; this does not change the webapp's
online mode. Preparation happens before the server starts.

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

1. Open the root URL or explicitly use `/?mode=online`. The first provider load can
   take longer than later loads.
2. Under **More**, enable **Weather stations**. Select a station to inspect its
   reading, observation time, age and source. Open **Information sources** for
   the layer status and limitations.
3. Search and select a start and destination, then press **Calculate**. The
   **Temperature** route layer estimates temperatures from nearby admitted sensor
   readings; unsupported sections stay unknown. Enable **Fountains** or **Water**
   to inspect provider water locations and route stops.
4. Enable **Heatmap** to check the historical WMS layer. The old saved-pair example
   shortcut is hidden. Prepared shade for the saved
   pair remains available through the comparison API and its validation tools.
   **Shading** shows calculated evidence when supported. A cold saved-route comparison can take around
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
| Address or walking-route provider fails | Restart the launcher with outbound HTTPS allowed, then retry. Map pins can replace address search; new routes still require the routing provider. |
| Port 8000 is already in use | Stop the previous app server, or append another port to the launcher command and use that port in the browser URL. |

Full basemap downloads and city-wide geometry preparation are not prerequisites
for this local online setup. For disconnected use, follow
[the README's offline preparation](../README.md#download-data-before-offline-use).
