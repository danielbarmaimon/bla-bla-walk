# Handoff: one-command app launchers

Status: done · Updated: 2026-10-04 · Branch: fix/map-badge-controls · Last owner: @ltorrecilla

## Goal
Provide one-command Windows/Linux startup and document the working online setup.

## State
Latest team main integrated cleanly. scripts/run-windows.cmd and scripts/run-linux.sh prepare isolated dependencies/assets/missing data and start the online app. Existing prepared inputs are preserved. Windows startup was verified natively; the Bash startup flow was verified with the Windows project interpreter, because native Linux/WSL is unavailable here.

## Done
- Windows launcher served the online app on port 8000; Bash launcher served it on port 8002 during its smoke check.
- 308 backend/contract checks and 60 browser checks passed; three browser checks skipped for unavailable local fixtures/native assumptions.
- Platform browser checks use pytest temporary paths, recognize the intentionally hidden successful basemap status and explicitly skip absent local fallback artifacts.
- Updated run instructions and reviewed the full UI/online/startup diff. Formatter, lint and whitespace checks pass.

## Next
Run the operating-system launcher from the repository root; open http://127.0.0.1:8000/ and keep the terminal open. Allow outbound HTTPS for provider search/routing. Native Linux dependency installation still needs verification on a Linux machine.

## Files
- scripts/run-windows.cmd, scripts/run-linux.sh: one-command setup and startup.
- README.md, docs/local-online.md: commands, network requirements and source limits.
