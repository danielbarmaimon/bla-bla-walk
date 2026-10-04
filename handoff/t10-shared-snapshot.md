# T10 shared prepared-data snapshot

State: done; versioned, offline-installable snapshot prepared on
`data/t10-shared-shade-snapshot` and included in PR #56 with the regional fix.

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
(one repeat, engineering smoke measurements). 69 focused/contract tests passed;
changed-file Ruff checks pass. Existing missing local demo/rest-stop outputs
remain outside this task, as recorded by the preparation-fix handoff.

Next: approve and merge updated PR #56, then teammates can pull and run
`python scripts/install_shade_snapshot.py` followed by
`python scripts/prepare_building_shade.py --offline`. Restart a running server
after installation. The preparation fix is included because regional coverage
constraints require the corrected loader. No merge has been authorized. T23's
full 248-sample journey comparison remains the next separate acceptance task.
