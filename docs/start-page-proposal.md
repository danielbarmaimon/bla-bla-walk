# Start-page UI proposal

Approved by @ltorrecilla on 2026-10-04 ("go for it"). Scope: T27 start page. T30 owns results/map integration separately. Retain the existing visual theme and Lucide icons.

## Chosen layout: form beside map on desktop

The owner chose a desktop layout with the form on the left and the map beside it on the right. Keep the form readable and the map large enough to inspect selected endpoints. Before calculation, the map shows Basel and selected pins; it never shows old routes as new results. Map-pin selection remains available. On mobile, show the full-width form first and open the map for pin selection or after route selection.

Desktop: form left, map right; the outline below shows the form contents.

```text
Bla Bla Walk                         [Information]

Where are you going?

Start
[ Current location or Basel address      ]
[Use my location]  [Choose on map]

Destination
[ Search a Basel street and number       ]
[Choose on map]

Departure
[Now]  [Choose date and time]

[              Calculate               ]

One tap away
[Nearby supermarket] [Nearby fountain] …

[Try SBB → Marktplatz example]

▸ Information sources
```

## Content and interactions

1. **Start:** do not silently treat Basel SBB as the user's location. Begin unselected, retain a user's explicitly selected start when returning from the map, and request GPS only after Use my location. Permission refusal offers address search/map pin. The explicit example button fills the saved pair.
2. **Destination:** keep official address suggestions and keyboard selection. Free typed text is not a selected address. Show one short error if an endpoint is missing or outside supported Basel coverage. Do not calculate while the person is still typing.
3. **Departure:** move time out of the hidden journey card into the main form. Default to Now; reveal date/time only when requested. Use the existing timezone behavior and make the chosen time clear. Return from the map without losing it.
4. **Calculate:** one full-width primary action. Validate start/destination, then launch existing route work once. Disable duplicate submissions while pending, show real status, allow Cancel/Retry, and invalidate old results if inputs change. Preparation tips remain T30 work. No invented percentage or promise of a quick finish.
5. **Nearby shortcuts:** place below the primary action. Use actual available place records around the selected start; show concise name/category/distance when known. Tapping fills Destination, then Calculate is the single calculation action. If only illustrative sample places exist, label them Sample places; never display them as actual nearest places. Limit visible cards to a small, readable set.
6. **After calculation:** hand off to T30's Fast/Recommended selection. No preference selector, Balanced sliders, detour controls or route cards before the first calculation. Both supported roles use the same calculation; one/no candidate and unsupported recommendation remain explicit. Selecting a role then opens its map and matching steps.
7. **Information:** move provider/method explanations, mode-specific notes and advanced weights into the collapsed Information sources/advanced disclosure. Keep required map/data attribution visible where used. Show Example/Offline status briefly when relevant; keep online mode-switch controls out of the main form's visual hierarchy.

## States to review

| State | What the user sees |
|---|---|
| Initial | Empty start/destination, Now, nearby section asks for a start |
| Address lookup | Suggestions and a short Searching… message |
| Ready | Selected endpoints; enabled Calculate |
| Calculating | Finding routes… / actual comparison status, Cancel |
| No route/provider failure | Short explanation, Calculate retries; change endpoints if needed |
| Saved example/offline | Explicit saved/example label; pins/sample fallback if new routing is unavailable |
| Returning from map | Previous selected endpoints and departure retained |

## Remove or move from the start page

Remove the repeated introduction/prototype paragraphs, provider explanation paragraphs, initial What matters most? selector and the second See route and evidence action. Move advanced comparison settings to results/Information sources. Keep the desktop map beside the form; omit journey steps from the initial view. Successful basemap status, compact map badges and turn-step placement remain T30 work.

## Check before implementation is accepted

On mobile and desktop: select two real Basel addresses, choose Now or a later departure, and start with one action. GPS denial and keyboard-only address selection work. Changing a field clears stale results; duplicate clicks do not duplicate route requests. An explicitly labelled example still works. Loading/error/empty-nearby states remain short and usable. Keep all visual values in the existing theme file. No new backend, external deployment or claims of shade/closure support.

## Review decision

Layout decision: desktop form left / map right, confirmed by the owner. Mobile stays form-first. Owner subsequently approved implementation. The T27 checkpoint retains the existing route cards and Show on map actions; full Fast/Recommended selection and preparation tips remain T30.
