# Bla Bla Walk — English presenter script

Target: exactly **5:00 solution + 0:42 HackAmRhein reflection**. Use the timer in
the local distribution described in [the runbook](demo.md). The timetable is a
delivery target, not proof of spoken duration. Presenter rehearsals remain pending.
Speaker and clicker: team to assign by GitHub username; one person may do both.

## 0:00–0:45 — The moment it hurts

Imagine planning a walk through Basel on a hot day. You want to reach the market,
but the shortest route does not tell you how exposed the walk is, where you might
refill water, or what information is missing. This matters particularly for people
affected by heat and the people helping them plan.

Our example is Basel SBB to Marktplatz. The assumed workaround is a normal walking
navigator plus separate checks for shade and water. This is our demo scenario,
not a claim that we interviewed users. Bla Bla Walk brings those tradeoffs together.

## 0:45–1:25 — What we built

We built a browser map served by a Python backend. It brings together timestamped
temperature observations, fountain locations, two saved walking alternatives,
and a time-dependent building-shadow approximation.

The comparison has Fastest overall, More shade and manual inspection. A five-minute
extra-time limit expresses a preference. It does not establish a health threshold.
We keep distance, time, shaded metres and unknown metres visible. The most useful
result can be an honest refusal to recommend a route when the evidence is incomplete.

## 1:25–3:05 — Demonstration

Clicker: open the local offline map, already at 125% zoom. Show SBB to Marktplatz,
inspect one source timestamp and one fountain's unknown operational status. Do not
start a cold calculation on stage. At 2:10 switch to the saved-result page.

This map is running on this computer. Offline provider observations are saved;
they are not live measurements. Here is the source time, and here is what we do
not know about the fountain. A point on the map does not prove drinking water is
available when someone arrives.

Now we are showing **saved output**, calculated for 3 October 2026 at 14:00 Basel
time. This page is not recalculating shade. Both alternatives contain substantial
unknown distance. Route A has about 158 metres of modelled building shade and
1,152 metres unknown; route B has about 108 metres modelled shade and 1,197 metres
unknown. Unknown is not sunlight, shade or safe access.

Both routes have unknown access, so the system withholds a recommendation. We can
inspect their evidence, but cannot present either as an eligible verified journey.
Changing departure time in the app requests a new calculation; it does not update
this saved page. A cold calculation took about fourteen minutes in our recorded
local run, so this dated fallback protects the presentation from that delay.

If the app fails: use the same saved page immediately and say, “The local app is
unavailable. This is dated saved output, not a live calculation.”

## 3:05–4:00 — How it works and what is interesting

The backend samples the saved route at the time a walker is expected to reach each
point. Local solar calculations and prepared building geometry estimate shadows.
This is a flat-ground building approximation: trees and terrain relief do not
cast shadows in this model. Missing inputs stay unknown.

Completed evidence can be rescored without repeating the shadow calculations.
Restrictions remain outside preference weights. You cannot make an unknown-access
route eligible simply by giving shade a higher weight.

Our interesting design choice is preserving different kinds of evidence:
an observed temperature, a historical summer heat scenario, an approximate shadow,
and an unknown access condition are different things. Combining them on a map
must not make them look equally certain.

## 4:00–5:00 — Sources, limits and next step

Basel-Stadt data uses CC BY attribution; observations credit meteoblue, and
fountain locations credit IWB under noncommercial terms. Walking geometry and
building footprints credit OpenStreetMap contributors under ODbL and OSRM routing.
Survey heights credit swisstopo under its open-data terms. Our source register
contains the detailed versions and obligations.

OpenLayers, FastAPI and Rasterio support the implementation. Codex assisted with
code, tests, documentation and this script. Numerical and browser checks establish
software behaviour, not measured cooling, physical shade accuracy or route safety.

Transit, arbitrary-destination routing and the proposed phone service are not
available here. The PET layer is a historical scenario, not current temperature.
Our next step is field validation of shade and access, followed by user testing
and performance work. Today we demonstrate transparent evidence and uncertainty,
not a finished navigation or health service.

At 5:00 stop the solution, even if a sentence was skipped; move to reflection.

## 5:00–5:42 — Team reflection draft: confirm before presenting

The following reflects documented technical work. The team must confirm it matches
their experience or replace it with their own lesson; do not invent personal feelings.

“One lesson from building Bla Bla Walk was that getting data onto a map is only
the beginning. We had to ask what each source actually proves. A fountain location
does not prove usable water, and a shadow calculation does not prove a safe walk.
The calculation time also changed our demo plan: we needed an honest saved fallback.
What we want to remember is that making uncertainty visible is itself useful.
That is a principle we want to carry into the next version.”

Aim for approximately 124 words per minute during reflection; use pauses and stop
at 5:42. Only timed spoken rehearsal can establish the final delivery duration.

## Jury answers — outside the 5:42

| Question | Short evidence-based answer |
|---|---|
| Who is it for; what do they do now? | People affected by heat and caregivers; separate navigation and water/shade checks are our scenario assumption, awaiting interviews. |
| What is real, saved or synthetic? | Admitted provider data and saved OSM routes are real inputs; this fallback is a dated real calculation. Fixture mode is synthetic and must be labelled. |
| What did you fake? | We did not verify access or physical shade. Phone service and transit are proposals, not working services. |
| Can you use the data? | See the source register: CC BY, ODbL, swisstopo terms and IWB noncommercial restrictions; commercial fountain reuse needs permission. |
| Why no winning route? | Unknown access makes both routes ineligible; preferences cannot override missing access evidence. |
| Does more shade mean cooler or safe? | We have no measured cooling or personalised safety validation; it is a bounded building-shadow approximation. |
| Does it work offline? | A recorded local run completed 248 samples with zero external HTTP attempts; missing downloads remain explicit. External hosting is untested. |
| What would production take or cost? | Field and user validation, access evidence, service operations and performance budgets; production cost has not been established. |
| What was technically difficult? | Preserving unknowns and source/model times across geometry, scoring and the screen; cold route calculation remains slow. |
| What did each person contribute? | Each contributor answers for themselves using their GitHub username and actual work; do not assign contributions from slot suggestions. |

See [SOURCES.md](SOURCES.md) for licences and provenance; see [demo.md](demo.md)
for rehearsal records, local files, fallback checks and event logistics.
