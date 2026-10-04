@echo off
setlocal
cd /d "%~dp0.." || exit /b 1
set "APP_PORT=%~1"
if not defined APP_PORT set "APP_PORT=8000"

if exist ".venv\Scripts\python.exe" goto environment_ready
set "BOOTSTRAP_PYTHON=python"
where py >nul 2>nul
if not errorlevel 1 set "BOOTSTRAP_PYTHON=py -3"
%BOOTSTRAP_PYTHON% -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12 or newer is required'" || exit /b 1
%BOOTSTRAP_PYTHON% -m venv .venv || exit /b 1

:environment_ready
set "APP_PYTHON=%CD%\.venv\Scripts\python.exe"
"%APP_PYTHON%" -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12 or newer is required'; assert 1 <= int(sys.argv[1]) <= 65535, 'Use a port from 1 to 65535'" "%APP_PORT%" || exit /b 1
echo Preparing the project environment and browser assets...
"%APP_PYTHON%" -m pip install --disable-pip-version-check --quiet -r backend\requirements.txt || exit /b 1
"%APP_PYTHON%" scripts/fetch_browser_assets.py || exit /b 1
if not exist "data\geometry\manifest.json" goto install_shade
if exist ".cache\buildings\manifest.json" goto shade_ready
:install_shade
"%APP_PYTHON%" scripts/install_shade_snapshot.py || exit /b 1
:shade_ready
"%APP_PYTHON%" scripts/prepare_building_shade.py --offline || exit /b 1
if exist ".cache\rest-stops.json" goto server_ready
"%APP_PYTHON%" scripts/prepare_rest_stops.py --download || exit /b 1
:server_ready
echo Open http://127.0.0.1:%APP_PORT%/ - online mode is the default.
echo Keep this terminal open. Press Ctrl+C to stop.
echo Address search and routing need outbound HTTPS. Allow network access if your coding tool asks.
"%APP_PYTHON%" -m uvicorn bla_bla_walk.main:app --app-dir backend --host 127.0.0.1 --port "%APP_PORT%"
exit /b %errorlevel%
