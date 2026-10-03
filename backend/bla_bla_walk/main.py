"""Small foundation API; feature owners add their adapters after T1 merges."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from rasterio.warp import transform_geom

from .adapters.addresses import search_addresses
from .adapters.rest_stops import rest_stops
from .adapters.routes import load_demo_routes
from .adapters.walking import walking_routes as provider_walking_routes
from .basemap import tile_path
from .comparison_service import ComparisonService
from .demo_fixture import fixture_snapshot
from .interfaces import (
    AddressSearchRequest,
    AddressSearchResponse,
    ComparisonJob,
    ComparisonPreferences,
    ComparisonRequest,
    MapLayer,
    MapSnapshot,
    PolygonGeometry,
    RouteAmenities,
    ShadeRequest,
    ShadeResponse,
    WalkingRouteRequest,
)
from .shade_cache import ShadeBusy
from .shade_service import ShadeService
from .snapshots import FOUNTAINS, offline_snapshot, online_snapshot


@asynccontextmanager
async def lifespan(app):
    yield
    comparison_service.close()


app = FastAPI(title="Bla Bla Walk", version="0.1.0", lifespan=lifespan)
ROOT = Path(__file__).resolve().parents[2]
shade_service = ShadeService()
comparison_service = ComparisonService(shade_service)
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
    return FileResponse(
        ROOT / "data/routes/demo.geojson", media_type="application/geo+json"
    )


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


@app.post("/api/addresses", response_model=AddressSearchResponse)
def address_search(request: AddressSearchRequest, response: Response):
    """Keep typed addresses out of access-log URLs and persistent caches."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return search_addresses(request.query, request.mode)
    except ValueError as error:
        raise HTTPException(422, "Enter a valid address query") from error
    except (httpx.HTTPError, OSError, KeyError, TypeError) as error:
        raise HTTPException(
            503, "Address search unavailable; try again or pin on map"
        ) from error


@app.post("/api/shade", response_model=ShadeResponse)
def shade_snapshot(request: ShadeRequest, response: Response) -> ShadeResponse:
    """Local exact-time calculation; unknown compact acceptance stays explicit."""
    try:
        result, hit = shade_service.respond(request)
    except ShadeBusy as error:
        raise HTTPException(503, str(error), headers={"Retry-After": "1"}) from error
    except OverflowError as error:
        raise HTTPException(413, str(error)) from error
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(
            503, "Prepared shade inputs unavailable or invalid; verify local geometry"
        ) from error
    response.headers["X-Shade-Cache"] = "HIT" if hit else "MISS"
    response.headers["Cache-Control"] = "no-store"
    return result


@app.get("/api/route-amenities", response_model=RouteAmenities)
def route_amenities(mode: Literal["fixture", "online", "offline"] = "offline"):
    """Real stop evidence independently of illustrative sensor mode."""
    if mode == "online":
        fountains = FOUNTAINS.get_layer()
    else:
        try:
            fountains = next(
                layer for layer in offline_snapshot().layers if layer.kind == "fountain"
            )
        except (OSError, ValueError, StopIteration):
            fountains = MapLayer(
                id="route-fountains",
                label="IWB fountains",
                kind="fountain",
                availability="missing",
                features=[],
                explanation="Saved IWB fountain data unavailable.",
            )
    return RouteAmenities(fountains=fountains, rest_stops=rest_stops())


@app.post("/api/walking-routes", response_model=MapLayer)
def selected_walking_routes(request: WalkingRouteRequest, response: Response):
    """Resolve ephemeral endpoints; never reuse the demo line for another pair."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return provider_walking_routes(request)
    except OverflowError as error:
        raise HTTPException(429, str(error), headers={"Retry-After": "1"}) from error
    except ValueError as error:
        raise HTTPException(
            422, "Select different endpoints within Basel-Stadt"
        ) from error
    except (httpx.HTTPError, OSError, KeyError, TypeError) as error:
        raise HTTPException(
            503, "Walking route unavailable; retry or use saved example"
        ) from error


@app.get("/api/walking-routes", response_model=MapLayer)
def walking_routes() -> MapLayer:
    """The saved checked pair, also usable beside synthetic source layers."""
    return load_demo_routes()


@app.post("/api/comparison", response_model=ComparisonJob, status_code=202)
def start_comparison(request: ComparisonRequest, response: Response):
    """Admit one background journey; preparation is strictly local."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return comparison_service.start(request)
    except ShadeBusy as error:
        raise HTTPException(503, str(error), headers={"Retry-After": "5"}) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except (OSError, KeyError, OverflowError) as error:
        raise HTTPException(
            503,
            "Prepared shade inputs unavailable; run local "
            "geometry and building preparation",
        ) from error


@app.get("/api/comparison/{job_id}", response_model=ComparisonJob)
def comparison_result(job_id: str, response: Response):
    """Polling never starts shade work or contacts an external provider."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return comparison_service.get(job_id)
    except KeyError as error:
        raise HTTPException(404, "Calculation expired; start again") from error


@app.post("/api/comparison/{job_id}/rescore", response_model=ComparisonJob)
def rescore_comparison(
    job_id: str, preferences: ComparisonPreferences, response: Response
):
    """Rescore weights/detour settings with zero new shade calls."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return comparison_service.get(job_id, preferences)
    except KeyError as error:
        raise HTTPException(404, "Calculation expired; start again") from error


@app.get("/tiles/{zoom}/{x}/{y}.png", include_in_schema=False)
def offline_basemap(zoom: int, x: int, y: int) -> FileResponse:
    """Serve downloaded imagery only; a miss never makes an external request."""
    path = tile_path(zoom, x, y)
    if path is None or not path.is_file():
        raise HTTPException(404, "Tile not downloaded or outside offline coverage")
    return FileResponse(path, media_type="image/png")


@app.get("/api/coverage", response_model=list[PolygonGeometry])
def calculation_boundary():
    """Pinned city boundary; it does not certify prepared inputs inside it."""
    boundary = json.loads((ROOT / "data/tile-inventory.json").read_text())["boundary"]
    geometry = transform_geom(boundary["crs"], "EPSG:4326", boundary["geometry"])
    polygons = (
        geometry["coordinates"]
        if geometry["type"] == "MultiPolygon"
        else [geometry["coordinates"]]
    )
    return [
        PolygonGeometry(type="Polygon", coordinates=coordinates)
        for coordinates in polygons
    ]


@app.delete("/api/comparison/{job_id}", status_code=204)
def cancel_comparison(job_id: str):
    """Cancel a superseded departure after the current bounded sample."""
    try:
        comparison_service.cancel(job_id)
    except KeyError as error:
        raise HTTPException(404, "Calculation expired") from error
