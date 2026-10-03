# Walking routes between Basel addresses

Status: done; publication in progress. Branch: feat/address-walking-routes.

## State

Follow-up to unmerged address-search PR #43, whose changes are the branch base.
User reported that address pins work but geometry/calculation does not.
Cause: frontend and comparison API only support saved SBB–Marktplatz geometry.

## Done

- Typed endpoint API, bounded foot-provider replies, one-request-per-second throttle,
  endpoint boundary checks and rejection of snaps over 100m; no persisted queries.
- Endpoint changes clear old lines, cancel superseded browser work and draw actual
  network geometry. Cards and layer controls now use the selected route layer.
- Distance/time estimates, retry button and explicit offline/failure states;
  new shade/access/ranking remain unknown; saved shade comparison preserved.
- Live Chrome test: venue route had 118 vertices; changed start had 213 vertices.
  The line followed streets on visual inspection; no page errors.
- 281 regression checks passed, including old journey, route geometry replacement,
  late-response rejection and offline no-provider behaviour. Lint/format passed.
- Source register, README, design and T7 presentation limits updated. Regenerated
  presentation and backup both passed their offline Chrome checks again.

## Next

Finish doc/privacy checks and publish a PR against the address-search branch.
Merge requires separate approval for #43 and this follow-up. Local updated app:
http://127.0.0.1:8003. Offline new-pair routing and new-pair shade remain future work.
