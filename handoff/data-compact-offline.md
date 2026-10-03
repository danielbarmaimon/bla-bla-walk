# Compact geometry and offline/online modes

Status: done

## Goal
Prepare 1m horizontal cells and 2m elevation steps, download the Basel geometry and offline map resources, and document local offline and external-server online operation.

## Done
- Downloaded and prepared all 225 available city/buffer assets (129 surface, 96 terrain). Prepared rasters occupy 37,652,574 bytes; unique native input sizes total 1,824,802,732 bytes. Catalogue SHA-256 checks, resumable transfers and output checksums passed. Verified temporary sources are discarded. All 65 receiver tiles have both outputs; 53 missing buffer assets remain explicit.
- Downloaded and verified all 4,418 basemap images at zoom 12–17 (57,026,146 bytes), checksum-pinned browser libraries, and a sanitized provider snapshot: 177 observation points and 305 fountains. Local manifests/snapshot remain ignored.
- Added explicit API/browser fixture, online and offline modes. Online uses the existing T4 adapters; offline reads saved bytes only and marks previously current data stale. Missing tiles/snapshots do not trigger external requests. Browser inspection loaded all 482 provider features in both modes; offline loaded with HTTPS requests blocked. Bounded the feature list so the full source set does not overwhelm the map page.
- Verified every prepared raster's hash, shape, bounds, CRS, scale and NoData count, plus all image hashes. Five surface cells remain unknown; this is not a count of shadow coverage gaps. Shareable evidence is in data/preparation-summary.json. Reuse preparation passed without source re-downloads; bounded Windows checkpoint-replace retries address transient file locks.
- 47 API/contract/geometry/snapshot/download/browser checks passed, plus 39 T2 rule cases. Python/browser formatting, lint and strict doc checks passed before final save. Reviewed changes and updated README, source register, design, tasks and launch guidance.
- Updated from main after the transit proposal and T3 acceptance merged. Preserved trip-option and offline requirements in T6 and assigned the new transit proposals T18/T19 to avoid the existing phone/report task IDs. The original PR #23 is superseded by the fresh feat/compact-geometry-offline-ready branch.
- Updating the old branch hit the local identity guard on metadata already published on remote main. Publishing a fresh branch uses the guard's existing new-branch range, which checks only commits absent from remote refs; the only new commits have the repository's GitHub username/noreply identity. Guard rules and shared history are unchanged.

## Next
PR #24 is merged into main. Continue T8 spatial/scene/bridge acceptance, then T10 shadow accuracy/performance and T5/T6 journey integration. Use README's local offline/external-server instructions; large data must be prepared or copied separately in another clone/server.

## Limits
This is T8 ingestion and operating-mode preparation. T8 scene/bridge validation, T10 shade and T5 route metrics remain unfinished. The original inventory records native 0.5m pins; the preparation manifest records the selected 2m terrain source separately. Missing buffer geometry remains unknown.

## Resume
Read this handoff and the remaining T8 acceptance checks. Reuse the compact preparation scripts/manifests, verify local resources, and finish scene/bridge validation without treating successful ingestion as accepted shade accuracy.
