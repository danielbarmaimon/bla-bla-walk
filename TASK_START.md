# Pick a task and start

**Tomorrow's short plan and copyable prompts are below: one or two tasks per account, plus your five-minute storytelling prompt.**

This is the team's task launcher. Read [HACKAMRHEIN.md](HACKAMRHEIN.md) for first-time setup. [ROADMAP.md](ROADMAP.md) shows the sequence and dependencies. [docs/plan.md](docs/plan.md) is the source of truth for each task's acceptance check. [TEAM.md](TEAM.md) maps **slots** (work areas) to GitHub usernames.

Open this repository in Codex. Start one fresh chat per task. Choose the suggested model and effort under the message box; use **Advanced** when needed and keep **Fast mode off**. Copy one prompt below into that chat. Codex handles branching, checks, handoff and the pull request.

The settings follow the local [HackAmRhein model guide](.agents/skills/hack-models/SKILL.md) and [official OpenAI model guidance](https://developers.openai.com/api/docs/guides/model-selection). Luna handles scoped work. Sol handles complex decisions and integrations. These are starting settings; the model picker controls availability.

## How task IDs, plan chunks and team slots fit together

- **Task IDs** such as T13 name a piece of work. Use the matching task in `docs/plan.md` for its files, dependencies and “Done when” check.
- **Plan chunks** (A–J) group tasks by when they can run. Their letters are only plan labels.
- **Team slots** (A–F) are work areas in `TEAM.md`; their letters do not refer to plan chunks. Slot owners are still TBD until the team assigns them.
- A prompt is ready only when its mandatory `Needs` have passed acceptance and are merged into `main`. A merged checkpoint does not complete its parent task. Conditional transit dependencies apply only after source admission. Check `handoff/` and the latest `main` first; this launcher does not override either.

## Shared metaprompt

Each launch prompt invokes these instructions:

> Read AGENTS.md and HACKAMRHEIN.md. Read TEAM.md, ROADMAP.md and docs/plan.md. Apply my local profile. Use the named task skill. Check the task's Needs against merged main. Check handoff/ for active ownership. If blocked, name the exact dependency. Start my selected task when ready. Work in my own clone. Create a task branch from current main. Respect listed file ownership. Follow the task's Done when. Work one checkable step first. Save handoff before changing chats. Run relevant checks and the privacy guard. Commit and push completed checkpoints. Open a pull request after completion. Ask before merging that pull request. Keep replies brief.

For a long task, complete one checkpoint. Save its state in handoff/. Continue in a fresh chat. For shared T10 and T6, complete only your assigned portion. Open a PR for that portion. Merge it before the next portion. Mark the parent task done after its full acceptance check passes.

## Tomorrow: short four-account plan

**Start here. At most two tasks each.** Assign A–D tomorrow. These are account lanes, distinct from older A–F team slots. The feature stack and plan are merged on main at or after `1554167`; no T20 setup task is needed. Use a separate clone and fresh chat for each task. Keep Fast mode off; select the model/effort below before pasting. Model availability is checked by the local picker; Light means Low.

| Account | Start now | Second task | Settings |
|---|---|---|---|
| A | P0 T22 — real route-specific steps | P2 T21 — landmarks, optional | Sol Medium → Luna High |
| B | P0 T23 — existing shade diagnosis/repair | P2 T24 — actual shadow-area overlay, optional | Sol High → Sol Medium |
| C | P1 T25 — construction evidence/capability check | P0 T31 — joined-flow checks and saved fallback | Luna High → Luna High |
| D | P0 T27 — concise start form/one Calculate | P0 T30 — route choice/map/steps/loading integration | Sol Medium → Sol Medium |

“Sol” = **GPT-6.1 Sol** (`gpt-6.1-sol`); “Luna” = **GPT-6 Luna** (`gpt-6-luna`). A/B second tasks are optional; protect D's integration and C's fallback first. Current main and relevant handoffs determine readiness. [M6 in the plan](docs/plan.md#m6-next-session-priority--complete-the-address-to-journey-experience) owns acceptance and exact file lists.

### Short-session metaprompt

Every prompt below includes this metaprompt by reference:

> Read AGENTS.md and my local profile, then TEAM.md, M6 in docs/plan.md and my task's handoff. Follow TASK_START.md's shared metaprompt using the short-session M6 queue, which replaces the old T20–T31 launch sequence. In my own clone, update from current merged main and create a task branch. Verify Needs; PRs #43–#49 are already merged. Respect A/B/C/D file ownership: A owns maneuver backend/necessary additive contracts; B owns shade; C owns construction audit/acceptance docs; D alone edits shared browser entry points and CSS. Reuse current APIs and code. Do one checkable checkpoint first, with no broad redesign or extra task. Keep missing/stale/unsupported states truthful. Coordinate required shared-contract changes through A and regenerate with a decision line. Save a handoff with exact integration hooks and evidence. Run relevant checks, doc check and privacy guard; commit/push, open a reviewed PR, and ask before merging unless that PR already has explicit approval. Never deploy externally. Stop optional scope if essential integration/fallback is unfinished. Keep replies brief and show the working result.

### A — journey steps first

**Model:** GPT-6.1 Sol · **Effort:** Medium.

```text
Start T22 for account A. Use $hack-build and $hack-interface only if an additive contract change is needed. Follow TASK_START.md's short-session metaprompt. Read M6/T22 in docs/plan.md. Request and normalize actual walking-provider maneuvers, tied to the selected route ID/geometry, and export the journey renderer for D. Check two Basel address pairs and route switching; never invent turns or reuse demo destination text. Do not edit D's main/map/index/CSS. Reuse the current API; provide D one checked payload and clear mount/update hooks. Complete only this checkpoint.
```

**Optional second task:** GPT-6 Luna · High.

```text
Start T21 for account A only after T22 is ready and merged. Use $hack-build. Follow TASK_START.md's short-session metaprompt and M6/T21. Restore route-near landmark candidates without a demo-route-a special case, reusing admitted saved places first. Export markers for D, preserve source positions/dates and unknown visibility. Keep coverage limitations explicit. Skip if steps or integration are unfinished.
```

### B — shade diagnosis first

**Model:** GPT-6.1 Sol · **Effort:** High.

```text
Start T23 for account B. Use $hack-build and $hack-unstuck. Follow TASK_START.md's short-session metaprompt and M6/T23. Trace the existing real building-shadow model from prepared inputs through shade API, saved-route samples and ranking. Reproduce two daylight times, night and missing data; repair only a demonstrated defect. Supply D checked evidence and layer/progress hooks. Preserve unknown coverage/access, exact effective time and building-only limits. No new shade engine, tree/terrain promises, full-city recomputation or edits to D's browser files. Complete a bounded verified checkpoint.
```

**Optional second task:** GPT-6.1 Sol · Medium.

```text
Start T24 for account B only after T23 is ready and merged. Use $hack-build. Follow TASK_START.md's short-session metaprompt and M6/T24. Export an isolated OpenLayers area overlay from actual existing ShadeResponse cells; verify alignment and time replacement in one supported viewport. Distinguish shade/unknown/night and supply D mount/update/dispose hooks. No fabricated shadow patches or city-wide expansion. Skip if pipeline repair or integration is unfinished.
```

### C — construction evidence, then verification/fallback

**Model:** GPT-6 Luna · **Effort:** High. If source semantics defeat this checkpoint, escalate to GPT-6.1 Sol Medium.

```text
Start T25 for account C. Use $hack-build. Follow TASK_START.md's short-session metaprompt and M6/T25. Verify current official construction data for reusable spatial geometry, active dates, freshness and confirmed pedestrian-closure meaning. Recheck the known 100335 gap and whether the current router can avoid closed edges. Supply D a concise truthful construction status and record the next action if evidence is unavailable. No invented coordinates, blanket blockage rules, rerouting engine or shared app-file edits. Save source/licence evidence for T31.
```

**Second task, protect this:** GPT-6 Luna · High.

```text
Start T31 for account C. Use $hack-build, $hack-review and $hack-demo. Follow TASK_START.md's short-session metaprompt and M6/T31. Prepare smoke checks while A/B/D work; final acceptance waits for merged T22/T23/T25/T30. Test saved and arbitrary address pairs, route-specific steps, selection, changed time, mobile/keyboard flow, source/calculation failures and truthful unavailable states. Include optional landmarks/area shadows only if ready. Consolidate source/limit docs and test a local dated fallback explicitly labelled saved, never live. Do not add features or deploy externally. Record actual build/latency and remaining gaps.
```

### D — concise start, then finish the journey

**Model:** GPT-6.1 Sol · **Effort:** Medium for both tasks.

```text
Start T27 for account D. Use $hack-build and $hack-design. Follow TASK_START.md's short-session metaprompt and M6/T27. Simplify the current start page to Start, Destination, Departure/Now, existing nearby-place shortcuts and one Calculate action. Reuse address lookup/GPS/map pins and existing APIs; clear stale results on changes and avoid duplicate route fetches. Own shared browser entry points/CSS exclusively. Keep arbitrary-route shade/access unknowns. Save a working checkpoint, then continue T30 in a fresh chat after merge.
```

```text
Start T30 for account D after T27 merges. Use $hack-build. Follow TASK_START.md's short-session metaprompt and M6/T30. Finish Fast (Lucide fast-forward) and Recommended (trees) choice, both distinct supported paths on the map and selected-route steps below. Integrate A's maneuver renderer and B's checked shade evidence using their handoffs; fixtures allow UI work while waiting, but final acceptance requires real integration. Make badges smaller, centred and without underline while retaining focus/pressed state; remove the successful basemap-status sentence and keep actual errors/attribution. Show real calculation status plus 3–4 concise officially sourced preparation tips. Keep details in Information sources. One available route, same-route roles and unsupported recommendation must be honest. Integrate optional landmarks/shadow areas only if ready; do not wait for them or start a new backend orchestrator. Hand off to C for T31.
```

### Presenter — five-minute storytelling pitch

This is your separate presentation chat, **not an extra engineering task for A–D**. English. **Model:** GPT-6.1 Sol · **Effort:** Low (Light). Select it, then paste:

```text
Help me prepare and deliver Bla Bla Walk's English five-minute pitch. Use $hack-demo and $hack-build for the presentation deliverables, not new product features. Follow TASK_START.md's shared metaprompt, read AGENTS.md, my local profile, docs/design.md, docs/pitch.md, docs/demo.md, docs/SOURCES.md and the latest merged handoffs. Check what actually works in the current local app; do not pitch tomorrow's planned features as delivered. Respect local-only delivery.

Focus on storytelling and follow these seven beats in this exact order. The five-minute solution pitch totals 300 seconds:
Storytelling Point | Pacing | Recommended Time % | What Is Needed (Description)
1. Create Curiosity | Moderate | 15% / 45s / 0:00–0:45 | Hold back key information.
2. Create Tension | Slow | 15% / 45s / 0:45–1:30 | Make stakes feel important.
3. Specific Moment | Slow | 30% / 90s / 1:30–3:00 | Use vivid, tangible details.
4. Change Pace | Variable | 10% / 30s / 3:00–3:30 | Slow for emotion, speed setup.
5. Unexpected Twist | Quick | 10% / 30s / 3:30–4:00 | Surprise audience with turns.
6. Personal Story | Slow | 10% / 30s / 4:00–4:30 | Show humanity, build connection.
7. Land Takeaway | Punchy | 10% / 30s / 4:30–5:00 | Make the message clear.

Start with one concise question about a true experience I can tell and who speaks/clicks; draft the rest while waiting. Do not invent my personal story, user testimony, field validation or statistics. If no true story is available, label an illustrative scenario clearly and leave a private presenter fill-in. No real names, health details or personal data in committed material. Curiosity may delay the solution reveal; it must not conceal important limitations.

Use one concrete Basel walking situation to connect all beats. Let the 90-second Specific Moment contain the verified demo or a dated saved fallback. Cover the problem, what we built, how it works and why it is interesting through the story. Make the twist a truthful insight about the limits of distance-only planning or what the team actually discovered; do not invent a shade benefit or closure detour. Keep plain English, human stakes, crisp transitions, intentional pauses and one memorable takeaway. Sources/licences, AI assistance and limitations must stay concise and visible, including measured vs interpolated/synthetic/saved/unavailable and the building-only shadow approximation where relevant. Prepare likely jury questions with short evidence-based answers and a short route if a live source fails.

Write the timed script and speaker/click cues in docs/pitch.md, with a minimal slide outline; update docs/demo.md with setup, exact demo actions, timing, fallback and likely jury answers. Offer a realistic word budget for each beat, then adjust for my measured speaking speed and click delays. Test the local fallback and label dated output saved, never live.

After the five-minute solution pitch, preserve the separately required 42-second HackAmRhein reflection at 5:00–5:42 about what we learned, what surprised us, what broke or what we will remember. Keep it outside the seven percentages. Rehearse the full 5:42 twice with a timer and trim after run one without changing the beat order or 300-second solution budget. A human rehearsal is not completed until I actually perform it; record measured times, never simulated timing as a rehearsal. Keep the event submission/venue instructions already recorded in docs/demo.md, and do not claim form submission without evidence. Commit/push checked deliverables through the privacy guard, open a reviewed PR and ask before merging unless explicitly approved.
```

## Core demo work queue

T0, T1, T2, T3, T4 and T9 are marked complete in `docs/plan.md`; do not start them again unless the plan or handoff says otherwise. Remaining core tasks and their current slot suggestions:

| Slot | Work queue | Suggested allowance | Start condition |
|---|---|---:|---|
| A | Core source/adapters work complete | — | Support source follow-up only when agreed |
| B | T5 · route comparison | 5–8 h | T10, T9 and T2 merged |
| C | Core design/routes work complete | — | Support T6 using the accepted guide and checked routes |
| D | T6 · comparison screen | part of 5–8 h | T4, T5 and T3 merged |
| E | T8 · city geometry; T10 · shade calculation | 12–22 h combined | T8: T1 plus T0 boundary/inventory; T10: T8 |
| F | T10 · cache/API; T6 · integration; T7 · demo | 7–13 h combined | Respect each task's dependencies and E/D handoffs |

The hours are original roadmap estimates, not remaining-work estimates or deadlines; T8 ingestion is already merged. T10 and T6 each have one acceptance check in the plan but are shared across two slots in sequence. The first portion must hand off its result; the second portion completes the parent task's full check. T8 still needs spatial/scene/bridge validation; T4 and T9 are complete. Reuse merged implementations and handoffs.

## Core task prompts

T3 and T4 have no new-work prompts. Reuse [the accepted screen guide](docs/style-guide.md), [T3 handoff](handoff/T3.md) and [T4 handoff](handoff/t4-observations-fountains.md); provider-mode API wiring is also merged. T6 screen and journey integration are merged; the [acceptance record](handoff/t6-integration.md) tracks the remaining check.

### E · T8 · City geometry

**Start:** after T1 and T0's boundary and inventory merge. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

Read [the compact preparation handoff](handoff/data-compact-offline.md) first: ingestion and offline resources already exist. Continue the remaining T8 spatial/scene/bridge checks using the configured encoding; do not repeat source downloads when matching prepared files can be verified and reused.

```text
Start T8 for Slot E. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T8 in docs/plan.md. Verify T1 and the T0 boundary and inventory are merged. Read handoff/data-compact-offline.md, reuse verified prepared geometry, and finish the remaining spatial/scene/bridge checks in T8's Done when.
```

### E · T10 · Shade calculation

**Start:** after T8 merges. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Start T10 calculation for Slot E. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T10 in docs/plan.md. Implement and validate shade calculation only, then write a handoff for Slot F's cache/API portion. Do not mark T10 done until the complete T10 acceptance check passes.
```

### F · T10 · Cache, API and performance

**Start:** after E's calculation portion merges. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Continue T10 cache/API for Slot F. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T10 and E's handoff. Complete caching, API connection and performance checks, then verify the entire T10 Done when before marking the parent task done.
```

### B · T5 · Eligible trip comparison

**Start:** after T10 passes full acceptance and merges, with T9 and T2 complete; include T18/T19 only if transit sources are admitted. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Start T5 for Slot B. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T5 in docs/plan.md. Verify T10, T9 and T2 are merged, then implement and check T5's acceptance criteria. Read the current routing proposal; preserve baseline weight, tie and unknown-evidence rules. Include transit only after T18/T19 admission and approval.
```

### D · T6 · Comparison screen

The screen is merged. Reuse its implementation and the [historical screen
handoff](handoff/t6-screen.md); current acceptance belongs in the
[T6 acceptance record](handoff/t6-integration.md).

### F · T6 · External-server acceptance

**Start:** screen and local journey integration are merged. A deployment URL and
prepared datasets on that server are needed. **Suggested model:** GPT-6.1 Sol.
**Effort:** Medium.

```text
Continue T6 external-server acceptance. Read handoff/t6-integration.md and T6 in docs/plan.md. Reuse the merged comparison API and screen. Obtain the deployment URL and verify the complete online journey with its prepared datasets, including source/calculation failures, polling, departure changes, cached rescoring, eligibility, layers and missing resources. Record evidence in the acceptance handoff. Keep unknown access/water and unavailable transit explicit; mark T6 complete only after its remaining criterion passes.
```

### F · T7 · Demo and fallback

**Start:** after T6 fully merges. **Suggested model:** GPT-6.1 Sol. **Effort:** Light. The team submission form is due before the Sunday 4 October 2026 build cutoff at 14:59.

```text
Start T7 for Slot F. Use $hack-demo and $hack-build. Follow TASK_START.md's shared metaprompt. Read T7 in docs/plan.md and build the deliverables in docs/pitch.md and docs/demo.md. Write in the presenters' chosen language. Prepare exactly five minutes for the solution followed by exactly 42 seconds about what the team learned, what surprised them, what broke, or what they will remember from HackAmRhein. Cover the problem, what we built, how it works, what is interesting, and a live demo if possible; include concise sources/licences, AI assistance, limitations and likely jury answers. Rehearse the full 5:42 twice with a timer and trim after the first run. Prepare and test a fallback; label dated saved output as saved, never live. Remind the team to complete its submission form before 14:59 on Sunday 4 October 2026. Arrive at FHNW Dreispitz, Dornacherstrasse 394. Doors open 13:30; building stops at 14:59; the introduction is 15:00–15:30; presentations begin at 15:30 in random order.
```

## Conditional transit proposal prompts

T18/T19 are proposals outside the core effort estimate. Slot suggestions are proposals, not assignments. Coordinate edits to shared routing, style and source documents before starting. Walking comparison remains usable when transit is unavailable; T18 also resolves the proposed route modes and detour option.

### A/B/C · T18 · Review modes and admit transit evidence

**Start:** after the T0 source follow-up and T2 routing proposal are available for review.

```text
Start T18. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T18 in docs/plan.md and coordinate shared-file ownership. Agree route-mode ranking and the detour option with the team. Verify timetable and alert access, terms, coverage and freshness separately; keep scheduled evidence distinct from live status. Keep keys local. Record admission or gaps and meet T18's Done when before transit integration.
```

### E/F · T19 · Transit-assisted candidate

**Start:** after T18 admits the required data; T1, T2 and T9 are complete.

```text
Start T19 only if its required transit inputs are admitted. Use $hack-build and $hack-interface when a contract change is needed. Follow TASK_START.md's shared metaprompt. Read T19 in docs/plan.md. Preserve checked walking legs, wait/ride/transfer durations, access evidence, freshness and scheduled/live labels. Keep waiting shade unknown without evidence. If admission fails, record transit unavailable and retain walking comparison. Meet T19's Done when and include a decision line with contract changes.
```

## Phone-access prompts (M4)

M4 follows the core demo (M3). It is a **simulated call**, with no live phone number and no real postal or email delivery. Keep route uncertainty visible; never claim a route is safe or passable without evidence. The slot suggestions below are proposals based on `TEAM.md` work areas, not assignments.

### C · T11 · Landmarks and barriers

**Start:** after T7 and T9 merge. **Suggested model:** GPT-6 Luna. **Effort:** Medium.

```text
Start T11 for Slot C. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T11 in docs/plan.md. Review the checked demo route, then document a privacy-preserving wayfinding check and record evidence-backed familiar landmarks, confusing points and barriers. Keep unknowns explicit and meet T11's Done when.
```

### B · T12 · Spoken instruction format

**Start:** after T11 merges. **Suggested model:** GPT-6 Luna. **Effort:** Light.

```text
Start T12 for Slot B. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T12 in docs/plan.md and use T11's findings. Agree and document the spoken-step format and examples, including missing or uncertain information. Never promise safety or passability without evidence; meet T12's Done when.
```

### E · T13 · Backend spoken directions

**Start:** after T12, T5 and T9 merge. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Start T13 for Slot E. Use $hack-build and $hack-interface. Follow TASK_START.md's shared metaprompt. Read T13 in docs/plan.md and the agreed T12 format. Generate structured spoken steps from the same checked route and evidence as the map; preserve source freshness and unknowns. If the shared contract changes, add its decision line in the same change. Meet T13's Done when.
```

### F · T14 · Simulated call and map request

**Start:** after T13, T6 and T7 merge. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Start T14 for Slot F. Use $hack-build and $hack-demo. Follow TASK_START.md's shared metaprompt. Read T14 in docs/plan.md and verify T13, T6 and T7 are merged. Build the scripted call with accessible transcript and simulated map-request confirmation. Never collect real contact details or send anything. Preserve missing and unverified route information, then meet T14's Done when.
```

## Shared-report prompts (M5)

M5 follows the phone-access prototype in the team's priority order. The `Needs` lines in `docs/plan.md` remain the actual technical dependencies. These slot suggestions are proposals, not assignments.

### B · T15 · Shared-report rules

**Start:** after T1 and T2 merge. **Suggested model:** GPT-6 Luna. **Effort:** Medium.

```text
Start T15 for Slot B. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T15 in docs/plan.md. Agree the report categories, privacy defaults, moderation, expiry, rate limits and storage approach with the team; document the decision and examples. Keep reports distinct from verified safe-stop data and meet T15's Done when.
```

### F · T16 · Store and serve reports

**Start:** after T15 and T1 merge. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Start T16 for Slot F. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T16 in docs/plan.md and follow the approved T15 rules. Implement persistent report storage and API behaviour, validation, expiry, moderation actions and agreed rate limits. Do not collect reporter identity by default. Meet T16's Done when.
```

### D · T17 · Show reports on the map

**Start:** after T16 and T6 merge. **Suggested model:** GPT-6 Luna. **Effort:** Medium.

```text
Start T17 for Slot D. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T17 in docs/plan.md and verify T16 and T6 are merged. Add map report submission and display with age and status, plus confirmation, resolution and flagging. Clearly show reports as unverified reports, never as proof a place is safe. Meet T17's Done when.
```

## When a task is blocked

Wait for its named prerequisites. Check whether they are merged into `main` and whether a handoff already exists. Review active pull requests and coordinate with the task owner. After a dependency merges, recheck `main` and start the next task whose `Needs` are all met.
