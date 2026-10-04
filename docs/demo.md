# Bla Bla Walk — five-minute pitch runbook

English: exactly 5:00 for the seven-beat solution pitch, followed by a separate 0:42 HackAmRhein reflection. No external deployment. Use the speaker script in [pitch.md](pitch.md); the demo plan below is based on what this checkout could actually load on 2026-10-04.

## Verified local state — 2026-10-04

- The FastAPI root page returned HTTP 200 and contains the route form. This checks the app shell, not provider-backed operation.
- The explicit fixture map endpoint returned HTTP 200 with two synthetic observation features and one synthetic fountain feature. It is useful only as a visibly synthetic UI check.
- The offline map endpoint returned HTTP 503: the saved provider snapshot is missing in this checkout. Do not claim a working offline app on this machine.
- The dated T31 fallback and T7 distribution were absent at session start; the original `.hack/t6-merged-real-journey.json` was also absent. A local-only saved-summary fallback was reconstructed from the exact figures in the merged `handoff/t6-integration.md`. It is labelled **SAVED FALLBACK SUMMARY · 3 October 2026 · departure 14:00 Basel time · not live**, states that the raw JSON is absent, and makes no requests.
- Existing browser acceptance check for that fallback passed: two route rows, saved/not-live wording, zero external requests. A browser attempt before localhost permission failed at sandbox socket setup; the approved rerun passed. This is a page check, not a spoken rehearsal.

## Guaranteed setup

1. From the project root, open `.hack/t31-fallback/index.html` directly in a browser. It needs no server or internet. It is local-only and ignored by Git.
2. Set browser zoom to 125% and size the window so both route rows and the saved/not-live notice fit. Keep the table visible before starting.
3. Assign speaker and clicker. Use GitHub usernames in team records. One person may do both.
4. Start the page timer with the first word. Reset only before a run. The page timer is a pacing aid, not proof of a timed human rehearsal.
5. Keep the full source register in `docs/SOURCES.md` available locally. Credits and limits are summarized on the fallback page and in the script.

The online app can be started with the existing Linux launcher `bash scripts/run-linux.sh` or Windows launcher `scripts\\run-windows.cmd`, as documented in `README.md`. These prepare dependencies and data and require internet. This checkout's offline snapshot is missing, so use the standalone fallback as the guaranteed presentation path. Do not switch to fixture mode as route evidence; fixtures are synthetic.

## Exact five-minute actions

| Time | Beat / screen action |
|---|---|
| 0:00–0:45 | Create Curiosity. Start timer; keep the fallback title and saved label visible. No click. |
| 0:45–1:30 | Create Tension. Hold the question; no result reveal and no click. |
| 1:30–3:00 | Specific Moment. Point to the date and **not live** notice. Point to Route A, then Route B. End on **Access: Unknown** and the sentence explaining why no route is eligible. Allow 20–25 seconds for the audience to read; do not calculate or open another route. |
| 3:00–3:30 | Change Pace. Keep the table still; pause on the unknown column. |
| 3:30–4:00 | Unexpected Twist. No click. State that neither route is eligible because access is unknown. |
| 4:00–4:30 | Personal Story. Use one true, non-identifying personal sentence only if the speaker supplies it. Otherwise use the explicitly illustrative line in `pitch.md`. |
| 4:30–5:00 | Land Takeaway. Look up; deliver the final sentence. At 5:00 move to reflection. |
| 5:00–5:42 | HackAmRhein reflection. Keep this separate from the solution timing. Stop at 5:42. |

Do not imply the fallback is the interactive app. It presents a summary of a saved run. The source values are exact in the merged T6 acceptance handoff: Route A 158.475 m modelled shade / 1,151.620 m unknown; Route B 107.680 m modelled shade / 1,196.889 m unknown; 248 exact-time samples; recorded runtime 827.833 s; zero outbound HTTP attempts; access unknown for both. The browser page transcribes the summary; it does not contain the missing raw JSON.

## Failure route

There is no recovery delay: open the standalone page directly. Say: “The local offline snapshot is missing here, so this is a dated saved summary from the recorded 3 October run, not live output.” Use the table and proceed on the planned timing. If the local page cannot open, read its two route values from the speaker script and name the source as the merged T6 acceptance record. Never call the summary a fresh calculation, measured shade, live observation or verified safe route.

## Word budget and rehearsal record

Word budgets, pause cues and beat order are in [pitch.md](pitch.md). The working estimate is about 474 spoken words plus 30–40 seconds for pauses and demo actions for the 300-second solution, and about 70 words for the 42-second reflection. The presenter’s speaking rate and click delays are not measured.

| Run | Solution | Reflection | Full duration | Changes / confirmation |
|---|---|---|---|---|
| 1 | Pending — human timed run | Pending — human timed run | Pending | Record actual start/end times, speaker pace and slow clicks. Trim after this run while preserving beat order and 300 seconds. |
| 2 | Pending — human timed run | Pending — human timed run | Pending | Rehearse the revised script with the same speaker/clicker and fallback. Record measured times; do not use simulated timing. |

No spoken human rehearsal has been completed. Browser acceptance and page-timer behavior do not count as rehearsals. The presenters must perform both full 5:42 runs before marking presentation acceptance complete.

## Likely jury answers

| Question | Short answer |
|---|---|
| Who is it for; what do they do today? | People planning walks around heat and caregivers are the intended users. Separate navigation and shade/water checks are an assumption awaiting user interviews. |
| What is measured, estimated, saved or synthetic? | Station readings are measurements at stations; route temperature colours are interpolated estimates. The shown route comparison is a dated saved model output. Fixture data is synthetic. |
| What did you fake? | Nothing in the shown summary is a live calculation. Physical shade, water operation, pedestrian access and safety are not verified. |
| Where does the data come from, and may it be reused? | `docs/SOURCES.md` lists attribution and terms: Basel-Stadt/meteoblue CC BY 4.0, OSM ODbL 1.0, IWB noncommercial terms and swisstopo open-data terms. |
| Why no winning route? | Access is unknown for both saved routes, so neither is eligible. A preference cannot turn unknown evidence into known access. |
| Is more shade cooler or safer? | No such claim is validated. The model approximates building shadows on flat ground and omits trees and terrain relief. |
| What would it take to run for real? | Field validation of shade/access, user testing, source operations and performance work. Cost and regulatory requirements have not been assessed. |
| What broke or was hardest? | The cold route calculation is slow, and this checkout lacks the saved offline provider snapshot. We preserve those gaps instead of presenting synthetic or stale data as live. |
| What did each person contribute? | Each person answers for themselves with their GitHub username and actual work. |

## Sources and limits on screen

Keep the fallback's concise credits visible and point to `docs/SOURCES.md` for exact versions and licence obligations. Codex assisted with code, checks, documentation and the pitch. The prototype does not prove measured cooling, physical shade accuracy, verified water/access, route safety or a live closure detour. No transit service is available. Historical PET is a fixed summer scenario, not current weather. The shadow model is a building-only flat-ground approximation.

## Sunday 4 October 2026 — team action

Complete the team submission form **before 14:59**; confirmation is pending.
The team must provide its form link and check the completion receipt. Do not
claim submission based on this reminder.

Arrive at **FHNW Dreispitz, Dornacherstrasse 394, Basel**. Doors open **13:30**;
building stops **14:59**; introduction **15:00–15:30**; presentations begin
**15:30 in random order**. These are the event details supplied for this task.
Keep the app and fallback ready throughout the presentation session.

## Optional interactive app tour — only after the pitch

The merged local app code supports online address search and walking geometry, route steps, sensor-based route estimates, route-stop candidates and a saved-pair shade comparison. Provider-dependent operation needs outbound HTTPS and prepared local data. This checkout's offline provider snapshot returned 503, so do not add these live actions to the guaranteed five-minute route. If an online source fails, show the saved summary and describe what it contains; do not use fixture values as real evidence.
