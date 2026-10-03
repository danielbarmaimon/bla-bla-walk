"""Package the English T7 presentation and dated real evidence for local use."""

import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    """Require the recorded result; generate two self-contained offline copies."""
    source = ROOT / ".hack/t6-merged-real-journey.json"
    raw = source.read_bytes()
    result = json.loads(raw)
    if result["status"] != "ready" or result["completed_samples"] != 248:
        raise ValueError("Expected the recorded complete T6 result")
    if result["departure_time"] != "2026-10-03T12:00:00Z":
        raise ValueError("Presentation date differs from recorded evidence")
    if any(view["winner"] is not None for view in result["choices"].values()):
        raise ValueError("Recheck script: recorded result has a recommendation")
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in values) + "</tr>"
        for route in result["evidence"]
        for values in [
            [
                route["id"],
                f"{route['distance_metres']:.1f}",
                f"{route['shaded_metres']:.1f}",
                f"{route['unshaded_metres']:.1f}",
                f"{route['unknown_metres']:.1f}",
                route["access_state"],
            ]
        ]
    )
    page = """<!doctype html>
<html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bla Bla Walk — local presentation and saved fallback</title>
<style>
body{font:22px system-ui;background:#f4f5ee;color:#183d34;margin:2rem;max-width:1200px}
h1{font-size:2.2rem}h2{font-size:1.6rem}section{border-top:2px solid #183d34;padding:1rem 0}
button{font:inherit;padding:.5rem 1rem;margin:.3rem;cursor:pointer}
header{position:sticky;top:0;background:#f4f5ee;padding:.5rem;border:2px solid #183d34}
table{border-collapse:collapse;width:100%;font-size:1.05rem}td,th{padding:.6rem;border:1px solid #183d34}
.notice{font-weight:bold;background:#fff0bd;padding:1rem}a{color:#164f80}
@media print{header button{display:none}header{position:static}section{break-inside:avoid}}
</style>
<header><strong id="timer" aria-live="off">0:00 / 5:42</strong>
<span id="phase">Solution</span><button id="start">Start timer</button>
<button id="reset">Reset timer</button></header>
<h1>Bla Bla Walk</h1><p>Heat-aware walking in Basel: make the tradeoffs and unknowns visible.</p>
<p class="notice">SAVED OUTPUT · 3 October 2026 · departure 14:00 Basel time (12:00 UTC).
This presentation makes no live calculations or provider requests.</p>
<section id="problem"><h2>0:00 — The problem</h2><p>The shortest walk does not tell you
how exposed it is, where water is available, or what evidence is missing.</p>
<p>Demo scenario: Basel SBB → Marktplatz. Users affected by heat and caregivers.
The assumed workaround awaits user interviews.</p></section>
<section id="built"><h2>0:45 — What we built</h2><p>A local browser map, timestamped
observations, fountain locations, saved walking routes and approximate building shadows.</p>
<p>Fastest overall · More shade · manual inspection · five-minute extra-time preference.</p></section>
<section id="demo"><h2>1:25 — Demonstration / saved fallback</h2>
<p>Inspect the local offline app first if available. At 2:10 use this dated saved table.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Route</th><th>Distance m</th>
<th>Modelled shade m</th><th>Modelled sun m</th><th>Unknown m</th><th>Access</th></tr></thead>
<tbody>ROWS</tbody></table></div>
<p class="notice">No eligible route: access unknown. Unknown distance receives no shade credit.
Fountain drinking-water, operational and access status remain unknown.</p>
<p>248 exact-time samples. Previously recorded local runtime: 827.833 seconds.
Zero external HTTP attempts in that validation. This is historical test evidence.</p>
<a href="saved-result.json">Original saved result</a></section>
<section id="works"><h2>3:05 — How it works / what is interesting</h2>
<p>Expected arrival at each route sample → local solar geometry → building-shadow approximation
→ explicit shade, sunlight or unknown → eligibility before preference scoring.</p>
<p>Rescore cached evidence without repeating shade calculations. Restrictions cannot be outweighed.</p>
<p>Building-only, flat-ground model; finite ray reach. Trees and terrain relief omitted.
Physical shade accuracy, cooling and overall safety are unvalidated.</p></section>
<section id="limits"><h2>4:00 — Sources, limits and next step</h2>
<p>Basel-Stadt geodata / meteoblue: CC BY 4.0. IWB fountains: noncommercial,
attribute IWB Industrielle Werke Basel. © OpenStreetMap contributors: ODbL 1.0;
routing by OSRM (FOSSGIS). Survey heights: © swisstopo, open-data terms.</p>
<p>OpenLayers BSD-2-Clause · FastAPI MIT · Rasterio BSD-3-Clause · AJV MIT.
Codex assisted code, tests, documentation and the pitch.</p>
<p>Saved observations are not live; historical PET is not current temperature.
Fixture mode is synthetic. Transit and phone service unavailable. Only the saved endpoint pair
has checked route geometry; pedestrian access remains unknown. External hosting untested.</p>
<p>Next: field validation of shade/access, user tests and performance work.</p>
<a href="SOURCES.md">Detailed source register</a></section>
<section id="reflection"><h2>5:00–5:42 — HackAmRhein reflection</h2>
<p>Draft for team confirmation: data on a map is only the beginning. What does each
source prove? The cold calculation changed the demo plan. Making uncertainty visible
is useful. Use the confirmed spoken reflection in the speaker notes.</p></section>
<p><a href="pitch.md">English speaker notes and jury answers</a> ·
<a href="demo.md">Runbook and rehearsal log</a></p>
<p>Submission before 14:59 Sunday 4 October 2026. FHNW Dreispitz, Dornacherstrasse 394.
Doors 13:30; build cutoff 14:59; introduction 15:00–15:30; presentations 15:30, random order.</p>
<script>
let started = null;
const boundaries = [[0,'problem'],[45,'built'],[85,'demo'],[185,'works'],[240,'limits'],[300,'reflection']];
let section = '';
function tick(){
 const seconds = started === null ? 0 : Math.min(342,Math.floor((performance.now()-started)/1000));
 document.querySelector('#timer').textContent = Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0')+' / 5:42';
 document.querySelector('#phase').textContent = seconds < 300 ? 'Solution' : seconds < 342 ? 'Reflection' : 'STOP — 5:42';
 const current = boundaries.filter(([time])=>time<=seconds).at(-1)[1];
 if(started !== null && current !== section){document.getElementById(current).scrollIntoView({block:'center'});section=current;}
}
document.querySelector('#start').onclick=()=>{if(started===null){started=performance.now();section='';tick();}};
document.querySelector('#reset').onclick=()=>{started=null;section='';tick();};
setInterval(tick,100);
</script></html>""".replace("ROWS", rows)
    for folder in ("t7", "t7-backup"):
        target = ROOT / "dist" / folder
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(page, encoding="utf-8")
        (target / "saved-result.json").write_bytes(raw)
        for name in ("pitch.md", "demo.md", "SOURCES.md"):
            shutil.copyfile(ROOT / "docs" / name, target / name)
        (target / "manifest.json").write_text(
            json.dumps(
                {
                    "label": "Saved output, not live",
                    "departure_time": result["departure_time"],
                    "saved_result_sha256": hashlib.sha256(raw).hexdigest(),
                    "presentation_seconds": 300,
                    "reflection_seconds": 42,
                    "spoken_rehearsals": "pending",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(target)


if __name__ == "__main__":
    build()
