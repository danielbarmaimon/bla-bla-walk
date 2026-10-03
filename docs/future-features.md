# Future features

## Phone access for people without a smartphone or internet

**Status:** Deferred until the core web-app demo is ready.

### Goal

Let people using a basic phone or landline access the same route-planning help as the map: routes that consider shade, confirmed construction closures, and other known risks. The service must never claim that a route is safe when that has not been verified. It must state clearly when route information is missing or uncertain.

### Agreed demo direction

Use a scripted call simulation, not a live phone number. The caller chooses from prepared Basel locations, receives a route recommendation and directions, and can request a map for later. Map delivery is the priority extension: the caller can choose postal delivery to their home or an email to a neighbour who can print it. For the demo, show a confirmation only. Do not ask for or store a real home address or email, and do not actually send a map.

Use the same route scenario and evidence as the web demo. Label simulated or unverified data. The call must explain missing information and avoid presenting the recommendation as a guarantee of safety.

### Infrastructure notes for a later implementation

A call simulation can be demonstrated inside the web app without buying a phone number. Open-source [Asterisk](https://www.asterisk.org/products/software/) is free phone-server software, but reaching ordinary phone networks still requires a provider, number, and call service. As checked on 2026-10-03, [Twilio's Switzerland pricing](https://www.twilio.com/en-us/voice/pricing/ch) lists a local number at $1.15/month and incoming calls at $0.01/minute; its [free trial restrictions](https://help.twilio.com/hc/en-us/articles/360036052753-Twilio-Free-Trial-Limitations) limit calls to verified numbers, so a trial is for testing rather than a public service. Recheck costs and availability before a pilot. Postal delivery also has per-item costs and operational work.

### Human-centred route instructions: landmarks and barriers

Kevin Lynch's *The Image of the City* describes how people form mental images of a city through five elements: **paths** (routes people travel), **edges** (perceived boundaries), **districts** (areas with a recognizable character), **nodes** (junctions or gathering points), and **landmarks** (distinctive reference points). For phone directions, this is a useful way to organize what callers may recognize. A Lynch edge is a perceived boundary, though; it is not proof that a path is physically blocked or unsafe. [Lynch, MIT Press](https://mitpress.mit.edu/9780262620017/the-image-of-the-city/)

Research on spoken directions supports combining a broad orientation cue with a nearby landmark and the actual maneuver. Landmark-based instructions can be easier to remember than street names alone, while global landmarks help people keep track of where they are in the wider city. These findings are design guidance, not a guarantee that every caller knows the same landmarks. [Anacta et al., 2016](https://link.springer.com/article/10.1007/s10708-016-9703-5); [Tom, 2004](https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1045); [landmark review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8324579/)

For a phone conversation, the later feature should:

- Start with a broad orientation cue the caller can check, then give one maneuver at a time: for example, “Keep the Rhine on your left. At the next confirmed crossing, turn toward [verified landmark].” Add the street name as a second cue when available.
- Prefer distinctive, visible, pronounceable landmarks near a decision point. Give a fallback such as the street name or the next recognizable stop if the landmark is hidden, unfamiliar, or ambiguous.
- Offer repeat, slower delivery, and a chance to say where the caller is now. Avoid stacking several turns into one long spoken instruction.
- Describe barriers separately from orientation boundaries. State what is known, when it was checked, and what remains unknown; never turn incomplete evidence into a claim that the route is safe or passable.

To build a Basel-Stadt mental map, collect more than map features. In walk-alongs with intended users, ask people to sketch or describe the route in their own words, point out landmarks they use to orient themselves, and identify confusing crossings, detours, and barriers. Repeat with different people and access needs: a familiar tram stop may help one caller but mean nothing to another. Treat each sketch as one person's perspective, not a universal map. Record findings without names or contact details.

For each candidate landmark, record its location, type (global orientation cue or local decision cue), whether it is visible from the approach, how people describe it, and whether participants recognize it. For each candidate barrier, record the affected path, who or what it affects, whether it is temporary, the evidence and source, when it was checked, and a confidence/unknown status. Validate temporary closures and passability against current evidence before using them in a route. A construction notice by itself is not proof that a pedestrian path is closed.

Basel-specific starting points for research—not yet user-validated landmarks—could include the Rhine as a broad orientation feature and recognizable bridges, major squares, Basel SBB, and tram stops as possible local cues. The official street-name dataset can support spoken street-name fallbacks; the canton also publishes a Basel Info map with sights and tram stops. The official construction feed is limited: its inspected schema has no geometry or structured pedestrian-closure field, so it cannot alone establish where a walking barrier is or whether a route is blocked. See the data limits in [Sources](SOURCES.md#basel-wayfinding-research-checked-2026-10-03).

Before using any of these cues in the demo, test a short scripted route with people who know Basel and people who do not. Mark sample data as simulated, ask whether the directions were understandable, and preserve explicit unknowns. This research informs a future phone prototype; it does not change the agreed scripted-demo scope.
### Before building a live service

- Verify that the web demo's route data and missing-data behavior can be reused by the phone flow.
- Check Swiss phone-number availability, provider costs, and call reliability.
- Decide supported languages and how callers can repeat or slow down directions.
- Define a privacy-conscious process for handling a postal address or a neighbour's email, including consent, retention, and deletion.
- Confirm who would prepare and send printed maps and how delivery timing is represented.

The first demo only shows the scripted interaction and simulated map-request confirmation. Live calls and actual map delivery remain future work.

## Physically verified city-wide shade

The completed T10 route approximation covers building-cast shadows only. Before
expanding it into a physical city-wide shade model, independently check walking
ground, canopy/bridge/tunnel receivers, building/survey alignment, tree behavior,
terrain relief and a proven horizon extent. Validate shade boundaries against
observations and route-metre sensitivity, then benchmark full-city coverage and
low-sun halos. The finite building approximation is not that acceptance evidence.
