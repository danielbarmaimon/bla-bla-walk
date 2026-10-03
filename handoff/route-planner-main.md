# Route planner integration

Status: integrated on `feat/poc-route-screen-integration`; local review pending.

## State

- Moved the route planning flow to `/`: sample-place search and shortcuts, GPS/map-pinned start, destination pinning, Fastest/More shade choices, route cards, route steps and nearby source details.
- Route geometry and PET summaries come from the canonical map snapshot. Fixture, online and offline modes remain explicit; offline still uses local tiles and saved provider layers.
- Current shade is not calculated, so More shade remains a manual comparison preference. Non-SBB → Marktplatz pairs do not show invented route lines.
- Main map controls retain provider layers and PET WMS status. Wayfinding/indoor-place cues stay explicitly unverified.
- Synthetic route-temperature ramps and sample shadow patches remain available only under `/poc`.

## Done

- Root route screen and map now share the planner interaction flow.
- Reused current API contracts for provider freshness, source detail, PET summaries and route options.
- Updated README, style guide and decision log.

## Next

- Review the integrated screen visually, especially narrow layout and route-card/map interaction.
- T6 still needs current shade calculation, time controls, route eligibility/ranking, coverage behavior, and full external-server/offline acceptance.
