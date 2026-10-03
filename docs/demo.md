# Slot F — local demonstration runbook

English; 5:00 solution followed by 0:42 reflection. The team authorized a local
presentation without an external deployment. T6's external-server criterion remains
unverified; it does not block this local preparation checkpoint. T7 is not fully
accepted until the presenters rehearse and the submission is confirmed.

## Presentation and backup

Source script: [pitch.md](pitch.md). Generate the local distribution from the
repository root with the existing project Python:

```powershell
.venv\Scripts\python.exe scripts/build_demo_distribution.py
```

Final presentation file: `dist/t7/index.html`; speaker notes: `dist/t7/pitch.md`;
runbook: `dist/t7/demo.md`; source register: `dist/t7/SOURCES.md`.
Backup: `dist/t7-backup/index.html` and its companion files. Both folders are
local and ignored by Git. Copy the whole backup folder to the presenting team's
chosen removable drive before leaving; do not copy private profiles or credentials.
This is a presentation/fallback distribution, not a portable installation of the app.
The local app continues to use this checkout, virtual environment and prepared caches.

The standalone HTML contains the slide outline, real dated result table, source
credits, limitations and an elapsed-time display. It opens directly from disk
without a server or internet. It includes the original saved JSON and its checksum.
No screenshots or recording are necessary for the primary fallback.

## Before going on stage

1. Assign speaker and clicker using GitHub usernames; assignments are pending.
2. Confirm the reflection describes the team's actual experience.
3. Run the documented [local startup](../README.md), open the map, select offline
   provider mode using the app's mode link, and use only SBB → Marktplatz.
4. Pre-open `dist/t7/index.html` and backup. Set browser zoom to 125%; use the
   projector resolution. Keep source times readable. Avoid historical PET's
   online-only overlay in the disconnected demo.
5. Precheck local geometry/buildings and saved provider/basemap resources. The
   existing [T6 evidence](../handoff/t6-integration.md) records the real offline
   journey. A new cold calculation cannot fit this presentation; do it before
   the session if desired, and label its time accurately.
   New-address street routing is online-only and has no current-departure shade
   comparison. Keep the saved pair for this offline presentation.
6. Start the presentation timer. Follow pitch.md's section boundaries; switch
   from the local map to the saved fallback by 2:10. At 5:00 start reflection;
   stop at 5:42. Manual slide switching remains possible after a timer boundary.

## Failure procedure — spend at most ten seconds recovering

If startup, map loading, a source, calculation or projector internet fails,
open `dist/t7/index.html` directly. Say: “The local app is unavailable. This is
saved output for 3 October 2026, 14:00 Basel time, not a live calculation.”
Show the two route rows, large unknown distances and withheld recommendation.
Keep the planned timing; replace app clicks with table inspection.
If the primary file is unavailable, open the backup index file. If neither
computer display works, read the saved-result numbers from the printed pitch
and describe the outcome. Do not relabel saved or synthetic evidence as live.

Saved calculation provenance: `.hack/t6-merged-real-journey.json`, departure
2026-10-03 12:00 UTC (14:00 Europe/Paris); 248 samples; prior recorded runtime
827.833 seconds; zero outbound HTTP attempts. “Saved 2026-10-03” describes the
existing recorded artifact, not the moment a new calculation was run.
Source observations retain their own timestamps in that JSON. No eligible route:
access unknown. Water availability unknown. Original JSON stays local.

## Two spoken rehearsals — required, not yet performed

Technical fallback test on 2026-10-03: Chrome opened both primary and backup
directly from disk, displayed the real route rows and opened only local resources.
All companion links existed; no browser errors or external requests occurred.
Timer start/reset and simulated elapsed-time boundaries at 5:00 and 5:42 passed.
Both HTML copies matched byte for byte. These checks are not spoken rehearsals.

Use the distribution timer and actual presenters, clicker and screen. A browser
timer test is not a spoken rehearsal. Exact timing cannot be certified by word count.

| Run | Solution | Reflection | Full duration | Changes / confirmation |
|---|---|---|---|---|
| 1 | Pending: target 5:00 | Pending: target 0:42 | Pending: target 5:42 | Note slow clicks and overruns; trim after this run. |
| 2 | Pending: target 5:00 | Pending: target 0:42 | Pending: target 5:42 | Verify the trimmed script and fallback with the same presenters. |

After run 1, remove about 20% of optional explanation if needed: shorten the
workaround paragraph, remove the rescoring explanation and compress source speech
while leaving the source slide visible. Never cut saved/live disclosure, unknown
access, model limits or the reflection. Use regained time for clicks and pauses.
Edit pitch.md, regenerate both folders, then run 2. Record measured times here
and confirm exactly 5:00 + 0:42 before calling the presentation ready.

## Sources and limits on screen

Concise credits appear in the distribution; [SOURCES.md](SOURCES.md) owns detailed
terms and versions. Basel-Stadt/meteoblue: CC BY 4.0; IWB: noncommercial with
attribution; OSM contributors: ODbL 1.0, routing by OSRM/FOSSGIS; survey heights:
swisstopo open-data terms. OpenLayers BSD-2-Clause, FastAPI MIT, Rasterio BSD-3-Clause,
AJV MIT; keep upstream notices. Codex assisted code, tests, documentation and pitch.
Its assistance does not validate the data or assign team contributions.

Distinguish measured observations, numerical model output, dated saved results,
synthetic fixtures, unavailable transit and unvalidated physical behaviour.
No cooling degrees, medical advice, overall safety or verified drinking water.
Building-only flat-ground shadows omit tree casting and terrain relief; historical
PET is a fixed summer scenario. See pitch.md for short jury answers.

## Sunday 4 October 2026 — team action

Complete the team submission form **before 14:59**; confirmation is pending.
The team must provide its form link and check the completion receipt. Do not
claim submission based on this reminder.

Arrive at **FHNW Dreispitz, Dornacherstrasse 394, Basel**. Doors open **13:30**;
building stops **14:59**; introduction **15:00–15:30**; presentations begin
**15:30 in random order**. These are the event details supplied for this task.
Keep the app and fallback ready throughout the presentation session.

## Route-stop demonstration

On the local app, select an address, show the calculated route, and enable Route stops. WATER uses saved IWB fountains; BENCH and REST use saved OSM seating/park candidates, with optional sourced indoor candidates. Open Route stops or select a marker to show provenance. Describe these as mapped candidates within 50m, with drinking, operation, access and cooling unknown. A dated saved acquisition is never a live condition report. The static T7 fallback retains its labelled saved result and does not claim this new interactive feature.

## Sensor route-temperature demonstration

Use the local **Online** mode, select a route, and enable Sensor-based route temperature. The selected line uses real station-based estimates with an actual °C range, coverage and time/source details. Click a coloured section for its contributing observations. Summer is green–amber–rose; winter is cyan–indigo. Automatic uses current sensor temperature, then the departure day's city forecast to choose the palette. Forecast never fills route gaps. Disable temperature to inspect shade strokes. Example/offline uses saved readings and explicitly says SAVED / STALE. This feature is exploratory and does not establish street-level cooling or safety; the static T7 fallback remains its older labelled saved result.

## Simplified map controls

The local app now starts with Temperature, Fast route, Recommended, Water, Bench and Rest active. Tap badges to toggle them; open More for Heatmap, Shading, Weather stations, Fountains, Landmarks and Interior space. Recommended may have no supported route; do not call an arbitrary alternative recommended. Stops are displayed on the walking line, with rest planning prompts at 15 walking-minute intervals. Sources and actual off-route positions are under Information sources. Interior space filters mapped supermarkets by supported scheduled hours at the selected departure. Shading repair remains deferred. The static fallback still reflects its dated earlier saved output.
