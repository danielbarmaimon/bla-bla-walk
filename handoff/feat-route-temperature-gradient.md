# Sensor route temperature gradient

Status: done and verified locally; merge pending. Branch feat/route-temperature-gradient, stacked on route-stop PR #45 (which depends on #44 and #43). No new merges authorized.

## Done

- Bounded real sensor API uses the existing canonical MapLayer; example/offline use saved real data independently of synthetic global overlays.
- Time-aligned exploratory IDW selected-route estimates, 25m nominal segments, at least two of three nearest sensors within 1km. Unknowns grey, saved values labelled, no shade/PET offsets.
- Exact user colours, minimum 2°C relative span, explicit numeric range, sources/timestamps, coverage and withheld-station check. Map section clicks show supporting readings; off toggle restores shade display.
- User confirmed automatic sensor-first palette with expected day weather fallback. Canonical PaletteForecast contract and regenerated TS, decision line; fixed city Open-Meteo daily mean API, bounded/hourly cached and offline saved. Forecast only chooses palette; manual override available.
- Seven targeted checks passed. Real online SBB–Marktplatz estimate 16.3–18.1°C, seven stations, full coverage. Saved public-address route 17.3–19.7°C, twelve stations, full coverage. Saved withheld-station MAE0.758°C on65/79 stations; not street-level validation. Screenshot stays local.
- README, source register and demo notes updated. All 289 regression checks passed, including real gradient rendering, section click, off toggle, palettes, temporal/coverage withholding and zero-external offline checks. Lint, formatting and documentation checks passed. The click test waits for the map fit animation before computing screen pixels.

## Next

Review the feature PR stacked on #45 and merge only after explicit authorization. Privacy checks run on commit and push. Updated local server is port8005. Prior PRs remain unmerged. Presenter timing rehearsals and submission receipt remain pending in T7.
