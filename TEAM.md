# Bla Bla Walk team

Challenge: heat-aware walking in Basel · Repository: [bla-bla-walk](https://github.com/danielbarmaimon/bla-bla-walk)

## People and proposed work areas

Replace each `TBD` with the contributor's GitHub username after the team chooses the role. See [ROADMAP.md](ROADMAP.md) for task dependencies, file ownership, and effort estimates. [TASK_START.md](TASK_START.md) gives copyable prompts and model settings. The task acceptance checks remain in [docs/plan.md](docs/plan.md).

| Slot | GitHub username | Work area |
|---|---|---|
| A | TBD | T18 source follow-up · Transit access, terms and freshness review (conditional) |
| B | TBD | T5, T12, T15 · Route evaluation, spoken format and report rules |
| C | TBD | T11 · Landmark and barrier validation |
| D | TBD | T6 screen, T17 · Comparison screen and report display |
| E | @danielbarmaimon | T8 validation, T10 calculation, T13 · Geometry, shade and spoken steps |
| F | TBD | T10 cache/API, T6 integration, T7, T14, T16 · Journey, demo, call and report API |

Core implementation tasks T0–T4 and T9 are merged; T8 ingestion and online/offline data modes are also available. Slot suggestions below describe remaining proposals, not assignments. Demo and end-to-end integration owner: TBD (slot F). Timekeeper: the team can assign one if useful.

## Working rules

- Keep one shared repository. Each contributor works in their own clone, on a branch named for the task, never directly on `main`.
- Follow the file ownership in the roadmap. Ask the owner before changing their files, and agree on a handoff when the work depends on their result.
- Open a pull request when a task is ready. At least one teammate reviews it; merge only after the contributor explicitly approves.
- Keep `main` runnable. Share progress and blockers with the team regularly; there are no fixed sync times.
- Run `bash scripts/hack-guard.sh` before commits and pushes. Never bypass the privacy check.
- Record team-wide choices in `docs/decisions.md`. Keep task status in the relevant `handoff/` file.

## Next-session four-account lanes

Assign usernames tomorrow. Temporary A–D labels are distinct from the older six work-area slots. Each account has one primary task and at most one second task, using its own clone. [M6](docs/plan.md#m6-next-session-priority--complete-the-address-to-journey-experience) owns exact acceptance/file lists; TASK_START.md provides model settings and ready prompts.

| Lane | Username | Primary → second | Exclusive shared ownership |
|---|---|---|---|
| A | TBD | T22 steps → optional T21 landmarks | Walking adapter/maneuvers and necessary additive canonical contract |
| B | TBD | T23 shade repair → optional T24 area overlay | Shade implementation; isolated overlay module |
| C | TBD | T25 construction audit → T31 verification/fallback | Construction evidence and final source/runbook docs |
| D | TBD | T27 concise form → T30 integrated choice/map/steps | Shared browser entry points and CSS |

Start all four primary tasks together from merged main at or after 1554167; no T20 prerequisite. Protect integration/fallback before optional features. A/B provide modules and evidence to D; C verifies the merged result. Required contract additions go through A. No shared working directory and no external deployment.

T27 start-page UI is claimed by @ltorrecilla; its approved proposal is in docs/start-page-proposal.md and state in handoff/T27.md. T30 map/results integration ownership remains to be assigned.
