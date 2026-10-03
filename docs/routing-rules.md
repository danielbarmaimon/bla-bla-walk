# Walking and multimodal comparison rules

T2 baseline specification for T9, T5 and T6. The multimodal section is a
follow-up proposal for T18, T19, T5 and T6. The demo walk and defaults were
selected under the user's 2026-10-03 instruction to continue until T2 is
finished. The workaround is an explicit demo assumption, not a participant
interview. All numerical examples are synthetic; no shade cooling degrees or
health thresholds are asserted. Task status belongs in [the handoff](../handoff/t2-walk-rules.md).

## Demo walk and current workaround

Use **Basel SBB, Centralbahnplatz → Marktplatz**, in Basel city centre, for a
walk from the railway station to the city market. The baseline workaround is
to use a shortest-walk navigator and manually check shade and water along the
way. The app brings those tradeoffs into one comparison, retaining manual choice.

The [SBB station plan](https://company.sbb.ch/content/dam/infrastruktur/trafimage/bahnhofplaene/plan-basel-sbb-a4.pdf)
identifies the station and Centralbahnplatz. The
[cantonal city-market page](https://www.bs.ch/en/verwaltung/prasidialdepartement/amter-und-bereiche/external-affairs-and-marketing/fairs-and-markets/basel-markets/basel-city-market)
identifies the market at Marktplatz and describes construction at the tram stop
and a reduced market area from June 2026. These references were inspected on
2026-10-03. They establish the public places and the construction caution;
they do not establish licensed walking geometry, actual pedestrian closures,
shade or drinking-water availability. T0 owns source admission. T9 must pin
the exact public endpoint coordinates and two checked, licensed walking routes.

The domain pitfall is confusing a construction site with a closed path. Only
authoritative, segment-specific closure evidence blocks a path. A caution does
not itself establish a closure or prove that a path is open. Checked access is
required independently. A shaded route or a mapped fountain also does not prove
that water or shade will be available at the person's arrival time.

## User-facing route choice proposal

The intended journey is an older person going to a grocery store, such as a
selected Migros. The person chooses the destination, then chooses between
**Fastest overall** and **More shade**. Keep the route cards and final choice
with the person. The current checked example remains Centralbahnplatz to
Marktplatz; a specific Migros and its checked routes have not been selected.

- **Fastest overall** compares eligible walking and transit candidates by
  door-to-door duration. Include walking access and egress, waiting, riding,
  transfers and planned stops. Do not estimate transit riding time using the
  configured walking speed. If required time evidence is missing, label the
  estimate incomplete and withhold a fastest recommendation.
- **More shade** prioritizes measured shade on outdoor walking segments. Show
  total duration, exposed and unknown metres, benches, water opportunities,
  construction cautions and evidence status. Do not treat a transit ride as
  measured shade. A transit candidate can be described as reducing outdoor
  walking only when its walking legs are known and comparable. Time spent
  waiting outdoors remains unknown unless stop shade or shelter is evidenced.
- Offer a selectable **five-minute extra-time limit** for the shadier option.
  This is a user preference, not a health threshold. The configured 30% distance
  and 10-minute duration limits remain absolute prototype limits; the person's
  selected limit can make them stricter.
- A confirmed pedestrian closure remains ineligible in every mode. Unknown
  access remains unverified. A construction caution is not a confirmed closure.
  A confirmed stop closure or service cancellation makes that transit itinerary
  ineligible. Transit stop access and service status need their own evidence.
- Avoid the label **Safe route**. Show measured shade, known closures, stop
  status and uncertainty. These data cannot establish overall or personal
  safety.

Public transport is not yet admitted for application use. T0 records that GTFS
coverage and access, plus GTFS-RT alert access, still need verification. A
verified timetable can support a **scheduled** estimate; it must not appear as
live service status. Show live disruption information only after its source,
coverage and freshness are verified. If admission fails, retain walking-only
comparison and say transit data are unavailable.

## Defaults and adjustable assumptions

[Production config](../config/routing-rules.json) is the home for numeric
defaults. [The scenario file](../data/scenarios.json) pins T2's acceptance
examples and original policy for regression checks. Config defines speed, stop duration, detour limits,
fixed benefit ranges, default weights, completeness, water freshness/proximity
and arithmetic/tie tolerances. These are editable prototype settings.

- Assume a constant positive walking speed, with no stops by default. Report
  moving minutes separately from total estimated duration, which adds planned
  stops. A selected water stop uses the configured stop duration unless edited.
- Include every planned diversion and return in route distance. A water stop
  adds its time before calculating subsequent shade sample times. Merely passing
  a fountain does not automatically add a stop or assume the person drinks.
- Evaluate shade at departure plus cumulative moving and stop time. Effective
  calculation times and geometry versions must match the request. A cached
  historical calculation for the requested historical departure is valid;
  cache age alone does not make it stale. T10 defines supported time precision.
- Sensor observations retain their source times. Changing departure time does
  not rewrite observations or turn them into a forecast.
- Detour limits are explicit adjustable constraints, outside preference weights.
  Neither walking speed nor a detour setting represents a health prescription.

## Eligibility before scoring

Apply these checks before preference scoring, in this order:

1. Reject invalid metrics: route length must be positive, lengths and stop time
   finite/nonnegative, and shaded + unshaded + unknown metres must equal route
   metres within the arithmetic tolerance. Invalid input stays visible as invalid.
2. A confirmed blocked segment makes the route ineligible. Unknown access means
   needs verification. No preference weight or manual choice overrides either.
   A worksite caution is displayed separately from the checked access state.
3. A route outside supported calculation coverage is unsupported for this
   comparison. Gaps inside coverage remain unknown rather than sunlit.
4. Fix the reference as the shortest checked-open route within supported coverage,
   before detour filtering, evidence-completeness filtering or scoring. Include
   its planned stops in the reference duration. Never change the reference when
   preference weights change. Among equal shortest distances, use the smaller
   total duration as the reference; any remaining ties have identical reference
   metrics. Route order must not change detour eligibility or the winner.
5. A candidate must satisfy both configured limits: extra distance divided by
   reference distance, and extra total duration above reference duration.
   Values at the limits pass; arithmetic tolerance handles rounding only.

If none remain, show no eligible route and each reason. Manual selection is
available only among eligible routes. People can edit their stated assumptions
or detour limits and recompute eligibility; closures remain outside their control.

## Metrics and denominators

Show both cards with distance, moving time, planned stop time, total duration,
shaded/unshaded/unknown metres and percentages, water evidence and eligibility.
Keep source/snapshot times, requested/effective shade times, geometry versions
and relevant cautions visible. Scores supplement those metrics.

All length percentages use the **full route length** as denominator. Known
shade coverage is (shaded + unshaded) / total. Never remove unknown cells from
the denominator, convert them to exposed cells, or let them imply cooling.
Unsupported, stale and failed calculations remain labelled; stale historical
metrics may be shown separately but cannot earn current shade credit.

## Fixed normalization and adjustable recommendation

The criteria are shade fraction, total estimated duration and a qualifying
water opportunity. Distance remains visible and constrains detours; scoring it
again would duplicate walking effort under the constant-speed assumption.

| Criterion | Benefit, from the fixed ranges in the scenario file |
|---|---|
| Shade | Current shaded metres / full route metres; unknown earns no credit |
| Duration | clamp(1 - (total minutes - range minimum) / range span, 0, 1) |
| Water | Binary benefit for at least one qualifying opportunity; counts do not stack |

Ranges stay fixed when the route pair or weights change; do not normalize by
the better/worse value in the current pair. Normalize finite, nonnegative
weights by their sum. Each contribution is normalized weight × benefit;
the total score is their sum. Explain every contribution and any excluded route.
Reject negative, missing, extra or nonfinite weights. If all weights are zero,
return no preferences with zero contributions and no winner; retain both cards.

Recommend the highest-scoring eligible route only when the evidence check below
passes. A score gap within the configured tie tolerance is a tie: show both
without choosing by ID or input order. If only one eligible route remains, it
still needs adequate evidence for active criteria. Manual choice remains
available when eligible, including ties and withheld recommendations.

Weight changes rescore cached metrics and reevaluate active evidence requirements;
they do not trigger new shadow calculations. Departure, route, speed or stop
changes require time-dependent metrics to be recalculated.

## Water, unknown and stale evidence

A qualifying water opportunity needs fresh, complete evidence of drinking type,
pedestrian access and operation, no applicable confirmed closure/broken status,
and a checked network diversion within the configured extra-distance limit.
The full diversion must already be counted in route distance. Straight-line
proximity is insufficient. Record source and evidence time; a recently fetched
static record is not proof of current physical operation.

The configured water evidence age is a demo validity window, not a claim about
a source's update frequency. T0/T4 must retain source cadence and actual evidence
times. If operation or corridor inventory completeness cannot be established,
use unknown. A fresh, complete search with no qualifying opportunity is known
absence and earns zero. A known broken, non-drinking, inaccessible or overly
distant opportunity earns zero. Unknown/stale water earns zero too, but remains
a different state and may withhold a recommendation.

Check **every eligible route** for every criterion with positive weight:

- Shade needs matching effective time and geometry, a current calculation and
  at least the configured known-length fraction. Even within the allowed gap,
  the score is a lower bound based only on confirmed shade over total length.
- Water needs fresh, complete evidence, including a verified absence where
  appropriate. Partial inventories or unknown operation cannot become absence.
- Duration needs validated geometry, positive speed and accounted-for stops.

If any eligible route fails an active criterion, show insufficient evidence and
withhold the winner for the pair. Scores may be shown as incomplete lower-bound
estimates, with the missing evidence identified. An inactive criterion earns
zero contribution and does not veto ranking, while its unknown state stays
visible. This never bypasses access or coverage constraints.

## Acceptance examples and ownership

The scenario file contains the selected rules, two reusable synthetic base
routes and cases with explicit expected statuses, metrics, contributions and
winners. The cases cover shade versus distance, weight changes and scaling,
water access/absence/broken/type/proximity, stops/diversions, blocked/unknown
access, construction cautions, unsupported coverage, unknown denominators,
stale water/shade, time/version mismatches, insufficient evidence, inactive
criteria, ties, zero/invalid weights, detour boundaries and invalid metrics.

Run `node scripts/check-routing-scenarios.mjs` to check their arithmetic and
expected outcomes. Add `--format` to format the JSON. This is a dependency-free
T2 acceptance checker. T5's production evaluator is
[evaluation.py](../backend/bla_bla_walk/evaluation.py), with all cases ported to
[production tests](../backend/tests/test_evaluation.py); the shared contract
remains canonical in the interface file.
No real Basel route distances, shade values or fountains are asserted here.

## T5 approximation and integration boundary

[Route sampling](../backend/bla_bla_walk/route_shade.py) estimates shaded,
unshaded and unknown route metres from the user-approved T10 building model.
It partitions full source route length along projected geometry, preserves
bends and stop boundaries, and uses interval midpoints at departure plus
cumulative walking and stop time. The maximum interval and sample budget live
in production config. This numerical approximation can miss changes inside an
interval; it is neither exact cell intersection nor observed physical shade.
Night contributes to unknown for baseline scoring but retains its own sample
state. Unknown, failed, unsupported or mismatched responses cannot earn credit.
Samples retain exact requested/effective times, geometry version, model and
source explanations; the original route provenance remains attached.

`compare_routes` only consumes cached evidence: weight changes make zero shade
calls. `compare_choices` additionally exposes walking-only Fastest overall and
More shade views used by T6, without replacing the approved baseline or
admitting the multimodal proposal. Fastest compares complete total minutes
directly, avoiding duration-normalization saturation. More shade uses current
shade over full route length and the same eligibility/completeness rules.
The optional user time limit only tightens the absolute limit; five minutes is
not imposed by default. Both keep manual choice among eligible routes. Transit
is explicitly unavailable pending T18/T19 admission and approval.

The saved T9 routes' access remains unknown and current fountain records do not
establish operation. They can display metrics but receive no recommendation.
T6 API/browser wiring reuses these contracts and functions and keeps approximate
model and missing-evidence explanations visible. Journey acceptance is tracked
in the [T6 acceptance record](../handoff/t6-integration.md).
