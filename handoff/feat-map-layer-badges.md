# Map layer badges and rest planning

Status: done and verified locally; merge pending. Branch feat/map-layer-badges, stacked on temperature PR #46. Prior #43–46 remain unmerged.

## Done

- Equal title-only aria-pressed tap badges; six active defaults and six inactive controls under collapsed More. Collapsed Information sources footer holds metadata/methods/limits.
- Independent fastest and supported-winner route visibility. Default selected route is fastest so its temperature gradient/markers match the drawn line. Unsupported recommendations stay withheld; shading repair deferred.
- Project route stop display onto walking geometry without modifying source coordinates. Rest planning prompts every15 walking minutes before arrival; seating/stop duration not invented.
- Canonical optional opening_hours, regenerated contracts/decision line, sanitized OSM supermarket preparation. Acquisition2237 candidates includes95 supermarkets,87 with hours. Conservative Zurich-local weekly hours and official2026 holiday calendar; unknown/complex/overnight hours withheld.
- Targeted badge/layout/keyboard/mobile and role/rest/hour checks passed. Ten supermarkets have supported schedules open at the checked Sunday-noon departure; the separate Interior space layer/list uses original source positions across Basel. Existing temperature click check adapted to respect foreground stop markers. Local server port8007 (8006 was already occupied and left alone).

## Next

All292 regression checks passed. Six focused browser checks passed after the final supermarket-list change, plus preparation checks. Review the stacked PR based on #46; merge only with explicit authorization. No external deployment. Presenter rehearsals/submission remain pending in T7.
