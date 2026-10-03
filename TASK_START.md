# Pick a task and start

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

T3 and T4 have no new-work prompts. Reuse [the accepted screen guide](docs/style-guide.md), [T3 handoff](handoff/T3.md) and [T4 handoff](handoff/t4-observations-fountains.md); provider-mode API wiring is also merged. T6 completes the route/shade journey.

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

**Start:** after T5 passes acceptance and merges; T4 and T3 are complete. T19 is conditional on transit admission. **Suggested model:** GPT-6 Luna. **Effort:** Medium.

```text
Start T6 screen work for Slot D. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T6 in docs/plan.md. Build the screen portion only, then hand it off to Slot F. Do not mark T6 done until its full acceptance check passes.
```

### F · T6 · Journey integration

**Start:** after D's screen portion merges. **Suggested model:** GPT-6.1 Sol. **Effort:** Medium.

```text
Continue T6 integration for Slot F. Use $hack-build. Follow TASK_START.md's shared metaprompt. Read T6 and D's handoff. Reuse the merged provider/offline modes. Connect shade, trip comparison and time controls, then verify all T6 criteria in online and local offline modes. Offline must make zero external requests; missing resources and unavailable transit stay explicit.
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
