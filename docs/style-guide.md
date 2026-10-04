# Map and comparison screen

**Status:** T3 accepted by the team on 2026-10-03; visual direction A selected by Slot C.
**Theme values:** `src/theme.css` (created by T1). Keep visual values there; this guide describes their roles.

## Screen at a glance

```text
┌ Basel walk                                      [Now ▾] [Layers ▾] ┐
│ Depart now · shade calculated for 14:32 · Updated 14:31           │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  MAP                                                              │
│  [temperature] [fountains] [shade]     Legend: shade / unknown     │
│                                                                   │
│  ┄ ┄ Basel coverage boundary ┄ ┄                                 │
│  Route A ─────────────── Route B ══════════════                    │
│                                                                   │
├───────────────────────────────────────────────────────────────────┤
│ Destination [Migros search]  [Fastest overall] [More shade]       │
│ ┌ Walk · [door-to-door time] ┐ ┌ Transit + walk · [time] ───────┐ │
│ │ Shade · exposed · unknown  │ │ Walk · wait · ride · transfer │ │
│ │ Bench · fountain · works   │ │ Stops · alerts · evidence     │ │
│ │ [Show on map] [Choose]     │ │ [Show on map] [Choose]        │ │
│ └────────────────────────────┘  └────────────────────────────┘      │
│ Data status: shade incomplete near boundary · fountain data current│
└───────────────────────────────────────────────────────────────────┘
```

The T27 start page supersedes the initial layout above: desktop form left, map right; mobile form first, with the map opened for pin selection or a selected route. Start and destination begin empty. Departure defaults to Now; Choose time reveals the local date/time. One Calculate action starts work, and route cards appear only after submission. Nearby destination shortcuts follow the primary action. Provider explanations and advanced settings live in Information sources. See [the approved start-page proposal](start-page-proposal.md). Map labels and controls must not cover route endpoints or the coverage edge. Show a transit card only when its source passes admission.

## Three visual directions

| Direction | Feel | Strength | Tradeoff |
|---|---|---|---|
| **A · Calm civic (selected)** | Quiet blue/teal accents, pale neutral surfaces, clear spacing | Keeps the map and evidence easy to scan | Less compact on a small screen |
| **B · Map-first utility** | Neutral panels, compact controls, strong route line patterns | Leaves more room for the map | Denser cards need careful type sizing |
| **C · Warm outdoor** | Warm neutral surfaces, leaf/sky accents, softer card corners | Feels approachable for a walking tool | Accent colours need strict separation from status meanings |

The structure above works with all three directions. Slot C selected A: use a restrained civic palette, with blue/teal reserved for navigation and route identity, and status colours kept distinct. The actual colour and spacing values belong in `src/theme.css` as created by T1.

### Additional visual direction proposed by the user

Use a white background, gray-950 primary buttons, sharp corners, and Teal-600
accents. Use Lucide for every interface icon. Keep this as a proposal until Slot C reviews it against
the selected calm-civic direction. Use Teal-600 for icons, outlines and
highlights; check contrast before using it for text. Keep icon labels visible.
Use large, clearly separated touch controls for the grocery trip and route
choice.

The root route screen now carries the reviewed planning flow into the main
application. It uses `src/theme.css` tokens, large labelled controls, and
Lucide icons. The SBB → Marktplatz options come from the saved pedestrian
geometry and current route contract. Rest and pause are example cues; nearby
fountains and sensors come from the selected provider snapshot. Route-specific
steps may add source-backed mapped references, always marked visibility
unverified; the optional landmark overlay is not part of the accepted flow.
Historical PET classes are displayed with their source status. Synthetic
temperature ramps and example shadows from `/poc` stay out of the main map so
they cannot be mistaken for measured heat or calculated shade.

## Principles

1. **The map is the shared reference.** Toggling a layer changes the map and its legend together.
2. **Show evidence beside the claim.** Every feature and route metric exposes its source, observation or calculation time, and coverage status.
3. **Unknown stays visible.** Missing, stale, unsupported, and outside-coverage data never looks like confirmed sun, shade, water, or access.

## Visual roles

- **Colour:** `surface` and `surface-raised` for panels; `text-primary` and `text-muted` for type; `accent` for selected controls; separate `route-a` and `route-b` tokens for route identity; `shade`, `exposed`, and `unknown` for layer meaning; `status-current`, `status-stale`, and `status-missing` for data state. Statuses always include words or symbols as well as colour.
- **Type:** use the system sans-serif stack. `text-body` for controls and metrics, `text-label` for compact metadata, and `text-heading` for screen and card headings. Keep route metrics tabular and aligned.
- **Spacing and shape:** use the shared spacing scale (`space-1` through `space-6`); reserve `radius-card` for cards and `radius-control` for buttons and inputs. Controls need touch-sized targets on mobile.
- **Theme home:** `src/theme.css`; components must use its tokens rather than local colour, type, or spacing values.

## Components and behaviour

- **Layer controls:** labelled toggles for temperature, fountains, and calculated shade. Each toggle exposes its state to assistive technology. A control has a visible focus ring.
- **Legend:** labels every line, fill, and symbol, including `Unknown / not calculated` and the dashed Basel coverage boundary. Route A and Route B differ by both colour and line pattern/label.
- **Time control:** `Now` is a direct action and the default; use the current instant when Calculate is pressed. A departure date/time control states the selected local time and the effective shade calculation time; stale saved calculations retain their original time.
- **Route choices:** offer `Fastest overall` and `More shade`; retain manual selection. Show the extra-time cap, including the proposed five-minute choice.
- **Walking card:** show door-to-door time, distance, shaded/exposed/unknown metres, bench and fountain opportunities, construction cautions and evidence status.
- **Transit card:** when admitted, show access/egress walking, wait, ride and transfer time separately. Mark wait shade unknown without stop evidence. Label scheduled versus live data and disclose stale or unavailable service status.
- **Route selection:** `Show on map` focuses the option; `Choose route` is explicit and keyboard reachable. Never label an option `Safe route`.
- **Provenance:** feature details show source name, observed/calculated time, freshness, and source link or attribution. Put a short status on the map/card and full details in a keyboard-accessible disclosure.
- **Coverage and data states:** outline the supported Basel boundary on the map. Inside gaps use `Unknown`; outside the boundary use `Outside coverage`. Stale values show `Stale · [time]`; absent values show `Unavailable`; never silently reuse old values as current.

## Accessibility and language

- Meet WCAG AA contrast: at least 4.5:1 for normal text and 3:1 for large text and meaningful graphical controls. Check the actual token pairs in `src/theme.css` as created by T1.
- Never use colour alone: pair shade/exposure with text or patterns; pair freshness colours with labels and icons; distinguish routes with names and line styles.
- All actions work with Tab, Shift+Tab, Enter/Space, and arrow keys where the control pattern calls for them. Keep focus visible and in a predictable order: start, destination, departure, Calculate, nearby shortcuts, then map/results controls. The map must have equivalent keyboard-accessible layer and route controls outside the map canvas.
- Use short, factual labels: “Shade calculated 14:32”, “Stale · 13:50”, “Unknown · no coverage”, “Outside Basel coverage”. Avoid “safe”, “cool”, or “best” unless the data and agreed rules support that claim.

## Reference images

No visual references were supplied for this draft. If the team adds examples later, use cropped, non-personal images; record the specific element to borrow and do not copy a whole branded interface.

## Map badge update — 2026-10-04

The user chose equal-size title-only tap buttons, no layer checkboxes. Six active primary badges: Temperature, Fast route, Recommended, Water, Bench, Rest. More starts collapsed; Landmarks is active initially and its other five optional badges are inactive. Native buttons expose aria-pressed, support keyboard activation and retain a focus outline; active backgrounds and lower borders distinguish state without underlining text. Theme tokens and badge sizing live in src/theme.css. Keep badge text free of source metadata. Information sources is a collapsed footer containing all provider/method/limit details; the map keeps concise journey instructions. Stop markers project onto the route without moving their source records; planned rest labels include walking-minute milestones.

Route stop circles use droplets, rocking-chair and clock-fading, with no permanent word labels. Same-type stops cluster within 38 screen pixels; a count indicates multiple members. Tap to inspect members; zoom to separate them. Keep clusters anchored on an actual route member. Other optional markers retain their labels.
