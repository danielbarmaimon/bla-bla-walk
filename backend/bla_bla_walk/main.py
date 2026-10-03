"""Small foundation API; feature owners add their adapters after T1 merges."""

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .basemap import tile_path
from .demo_fixture import fixture_snapshot
from .interfaces import MapSnapshot
from .snapshots import offline_snapshot, online_snapshot

app = FastAPI(title="Bla Bla Walk", version="0.1.0")
ROOT = Path(__file__).resolve().parents[2]
app.mount("/src", StaticFiles(directory=ROOT / "src"), name="browser")
app.mount("/config", StaticFiles(directory=ROOT / "config"), name="configuration")
app.mount("/poc-assets", StaticFiles(directory=ROOT / "poc"), name="route-poc-assets")
app.mount(
    "/vendor",
    StaticFiles(directory=ROOT / ".cache/browser-assets", check_dir=False),
    name="browser-assets",
)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Serve the map and API from one origin, without a JavaScript build step."""
    return FileResponse(ROOT / "index.html")


@app.get("/poc", include_in_schema=False)
def route_poc() -> FileResponse:
    """Show an isolated, interactive route design preview."""
    return FileResponse(ROOT / "poc/index.html")


@app.get("/api/poc-route", include_in_schema=False)
def poc_route() -> FileResponse:
    """Serve the checked SBB to Marktplatz pedestrian route example."""
    return FileResponse(ROOT / "data/routes/demo.geojson", media_type="application/geo+json")


@app.get("/api/map", response_model=MapSnapshot)
def map_snapshot(
    mode: Literal["fixture", "online", "offline"] = "fixture",
) -> MapSnapshot:
    """Serve explicit fixture/live/saved modes; offline never contacts providers."""
    if mode == "online":
        return online_snapshot()
    if mode == "offline":
        try:
            return offline_snapshot()
        except (OSError, ValueError) as error:
            raise HTTPException(
                503, "Saved provider snapshot unavailable; run offline preparation"
            ) from error
    return fixture_snapshot()


@app.get("/tiles/{zoom}/{x}/{y}.png", include_in_schema=False)
def offline_basemap(zoom: int, x: int, y: int) -> FileResponse:
    """Serve downloaded imagery only; a miss never makes an external request."""
    path = tile_path(zoom, x, y)
    if path is None or not path.is_file():
        raise HTTPException(404, "Tile not downloaded or outside offline coverage")
    return FileResponse(path, media_type="image/png")
