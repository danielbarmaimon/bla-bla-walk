# T10 shared prepared-data snapshot

State: done; versioned, offline-installable snapshot prepared on
`data/t10-shared-shade-snapshot` in PR #59. It includes the regional fix from
PR #56, so the combined PR supersedes that preparation-only PR.

Done: committed archive is 41,938,457 bytes (41.9MB), expanding to 71,265,138
bytes across 254 files: the 17,432 building footprints, building manifest and tile
selection, 225 survey grids, 25 flags and geometry manifest. Acquisition batch
duplicates and unrelated caches are excluded. Source notices document separate
OSM/ODbL and swisstopo terms; original freshness and coverage limits remain intact.

Installer verifies archive, file and canonical JSON configuration hashes, restores
existing local paths, and preserves differing local data unless explicitly
replaced. Canonical input hashes tolerate Windows/Unix checkout line endings.

Validation: expanded JSON passed the privacy guard using a separate temporary Git
index before packaging. Building features were checked against the exact caster
field allowlist, numeric coordinates and source-ID grammar. All survey artifacts
match their recorded hashes. A cache-free checkout installed the snapshot,
passed offline building preparation and real full-polyline shade API validation
with zero external HTTP requests, consistent seams, concurrent requests and night
states. Cold p95 4.351007s; warm p95 0.148067s; peak process 584,613,888 bytes
(one repeat, engineering smoke measurements). After incorporating the latest
main's walking-directions changes, 84 focused/contract/instruction tests passed;
changed-file Ruff checks pass. Existing missing local demo/rest-stop outputs
remain outside this task, as recorded by the preparation-fix handoff.

Next: approve and merge the combined snapshot PR, then teammates can pull and run
`python scripts/install_shade_snapshot.py` followed by
`python scripts/prepare_building_shade.py --offline`. Restart a running server
after installation. The preparation fix is included because regional coverage
constraints require the corrected loader. No merge has been authorized. T23's
full 248-sample journey comparison remains the next separate acceptance task.

Sharing note: updating the old PR branch was blocked by the push guard because
its update range included a pre-existing upstream web merge carrying a real-name
attribution. Publishing this new branch passed the unchanged guard: its range
excludes commits already on remote branches and checks the new local commits.
No upstream history was rewritten and no guard was bypassed.

PR synchronization: locally merged the latest main (T30 integration,
`e018435`) into #59; the merge drivers preserved all decision-log additions and
there were no unresolved paths. PR #56's exact remote head `087ab52` is an ancestor
of #59, so #56 has no separate changes to merge and needs no separate conflict
repair. Formal GitHub approval requires another account: the connected account
is also the author of both PRs. Conflict repair/review is authorized; no merge
has been requested in this synchronization step.
