# Handoff: online defaults and running server

Status: done · Updated: 2026-10-04 · Branch: fix/map-badge-controls · Last owner: @ltorrecilla

## Goal
Restore live address lookup and routing, and make online mode the default.

## State
Both requests failed because the prior preview server had restricted outbound sockets (WinError 10013). Restarted on port 8001 with network access; official address search and walking routes now return HTTP 200. Browser/API defaults changed to online; explicit offline/fixture behavior is retained. A real browser selected Centralbahnplatz 1 and a returned Marktplatz address and displayed a 1208 m / 20 min provider walking route with no browser errors. 25 focused checks passed; formatting, lint and whitespace checks passed.

## Done
- Reproduced both 503 errors and traced the blocked provider connections.
- Restarted the local server with outbound network access.
- Updated frontend/API defaults, docs and explicit fixture test URLs.

## Next
No implementation work remains. Keep the network-enabled local server running on port 8001. Explicit fixture/offline URLs remain opt-in.

## Resume prompt
Continue the online-mode fix using this handoff. Verify the server at http://127.0.0.1:8001/ and finish Next.
