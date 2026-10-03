# Route planner integration

Status: done — route planner integration merged in PR #33; T6 continuation is tracked separately.

## State

- Moved the route planning flow to `/`: sample-place search and shortcuts, GPS/map-pinned start, destination pinning, Fastest/More shade choices, route cards, route steps and nearby source details.
- Route geometry and PET summaries come from the canonical map snapshot. Fixture, online and offline modes remain explicit; offline still uses local tiles and saved provider layers.
- At this integration checkpoint, shade was not calculated and More shade was a manual preference. See the [T6 continuation](t6-journey-integration.md) for current behavior. Non-SBB → Marktplatz pairs do not show invented route lines.
- Main map controls retain provider layers and PET WMS status. Wayfinding/indoor-place cues stay explicitly unverified.
- Synthetic route-temperature ramps and sample shadow patches remain available only under `/poc`.

## Done

- Root route screen and map now share the planner interaction flow.
- Reused current API contracts for provider freshness, source detail, PET summaries and route options.
- Updated README, style guide and decision log.

## Next

- Review the integrated screen visually, especially narrow layout and route-card/map interaction.
- Follow [T6 journey integration](t6-journey-integration.md) for calculation wiring and remaining prepared-data/external-server acceptance.
