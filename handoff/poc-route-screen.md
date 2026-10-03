# Interactive route screen PoC

Status: done; awaiting team visual review.

## Goal
Preview a simple trip flow for older travellers on phone and desktop.

## Done
- Added isolated `/poc` screen with GPS fallback, manual and map-pinned starts, destination search and map pinning.
- Added six quick destination categories. Each chooses the closest entry in a small, explicit sample catalog.
- Added Fastest/More shade controls and a map view with labelled example steps, including a sample tram and optional rest stop.
- Reused the current Basel basemap and local OpenLayers assets, including downloaded tiles in `?mode=offline`. All UI icons are bundled Lucide SVGs with their ISC licence.
- Kept route geometry schematic and marked unverified shade, transit, places, and stops visibly.
- Manually checked search, preference switching, map pinning and step display in the browser, plus narrow-screen layout.

## Next
- Review the screen with the team and older users.
- Decide which elements enter T6 after real route and shade data exist.
- Replace sample destinations and steps with admitted provider data and route-backed instructions.

## Resume
Open `/poc`, inspect the phone and desktop flows, then record the team’s chosen UX changes before T6 integration.
