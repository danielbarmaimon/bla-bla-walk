# Interactive route screen PoC

Status: done; updated street-route preview awaiting team visual review.

## Goal
Preview a simple trip flow for older travellers on phone and desktop.

## Done
- Added isolated `/poc` screen with GPS fallback, manual and map-pinned starts, destination search and map pinning.
- Added six quick destination categories. Each chooses the closest entry in a small, explicit sample catalog.
- Added Fastest/More shade controls and a map view with labelled example steps.
- Reused the current Basel basemap and local OpenLayers assets, including downloaded tiles in `?mode=offline`. All UI icons are bundled Lucide SVGs with their ISC licence.
- Replaced the schematic connector with the saved SBB → Marktplatz pedestrian street path. Other destination pairs show no invented route.
- Added a 50 m fountain buffer and 250 m sensor buffer from the admitted provider layers, with a dated saved snapshot fallback.
- Added an illustrative temperature gradient using the user-supplied ramp, plus accent Lucide icons for rest, pause and water steps.
- Marked rest, water and pause directly on the route in both map modes, with labelled icon badges and details.
- Added OSM node/landmark cues, a public cooling-place candidate, and map layer switches. AC, hours and landmark visibility remain unverified.
- Added example area heat, example shadow patches, reversed heat colours, and a plain teal route in area-heat view. These are display examples, not measured heat or calculated shade.
- Manually checked the route line, map source markers, legend and step display in the browser.

## Next
- Review the screen with the team and older users.
- Decide which elements enter T6 after real route and shade data exist.
- Add arbitrary A → B routing and route-backed turn instructions in T6.
- Validate any future sensor-derived temperature interpolation before use.

## Resume
Open `/poc`, inspect the phone and desktop flows, then record the team’s chosen UX changes before T6 integration.
