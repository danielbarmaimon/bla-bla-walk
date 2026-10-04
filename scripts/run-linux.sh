#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
app_port="${1:-8000}"

if [[ ! -x .venv/bin/python ]]; then
  python3 -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12 or newer is required'"
  python3 -m venv .venv
fi
app_python="$PWD/.venv/bin/python"
"$app_python" -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12 or newer is required'; assert 1 <= int(sys.argv[1]) <= 65535, 'Use a port from 1 to 65535'" "$app_port"
printf '%s\n' 'Preparing the project environment and browser assets...'
"$app_python" -m pip install --disable-pip-version-check --quiet -r backend/requirements.txt
"$app_python" scripts/fetch_browser_assets.py
if [[ ! -f data/geometry/manifest.json || ! -f .cache/buildings/manifest.json ]]; then
  "$app_python" scripts/install_shade_snapshot.py
fi
"$app_python" scripts/prepare_building_shade.py --offline
if [[ ! -f .cache/rest-stops.json ]]; then
  "$app_python" scripts/prepare_rest_stops.py --download
fi
printf '%s\n' "Open http://127.0.0.1:$app_port/ - online mode is the default." \
  'Keep this terminal open. Press Ctrl+C to stop.' \
  'Address search and routing need outbound HTTPS. Allow network access if your coding tool asks.'
exec "$app_python" -m uvicorn bla_bla_walk.main:app --app-dir backend --host 127.0.0.1 --port "$app_port"
