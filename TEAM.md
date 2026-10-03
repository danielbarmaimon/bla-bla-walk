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

The team will assign usernames tomorrow. These temporary A–D lane labels are separate from the existing six A–F work-area slots above. Each account uses its own clone; no four chats share a working directory. Task acceptance and exact files live only in [M6 in docs/plan.md](docs/plan.md#m6-next-session-priority--complete-the-address-to-journey-experience).

| Temporary lane | GitHub username | Queue | Ownership |
|---|---|---|---|
| A | TBD | T21, T22 | Route landmarks and maneuver directions |
| B | TBD | T23, T24 | Shade diagnosis, corridor evidence and shadow overlay module |
| C | TBD | T25, T26, T29 | Construction admission, avoidance policy and backend integration |
| D | TBD | T20, T27, T28, T30, T31 | Common contract checkpoint, concise UX and browser integration/acceptance |

D coordinates T20 before the parallel wave; C and D own shared backend/browser entry points respectively. Other lanes export modules with frozen contract fixtures and do not edit those shared files. Assign usernames and claim handoffs at the start; assistants must not infer that temporary lane letters are people.
