"""API validation, conservative compact evidence and local-only geometry checks."""

import base64
import json

import numpy as np
import pytest
import rasterio
from bla_bla_walk import main
from bla_bla_walk.geometry import sha256_file
from bla_bla_walk.interfaces import ShadeRequest, ShadeResponse
from bla_bla_walk.shade_geometry import corridor_cells, load_metre_grids
from bla_bla_walk.shade_service import ROOT, ShadeService, solar_location
from fastapi.testclient import TestClient
from rasterio.transform import from_origin


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    directory = tmp_path / "data/geometry"
    directory.mkdir(parents=True)
    (tmp_path / "config").mkdir()
    for name in ("shade.json", "shade-service.json"):
        settings = json.loads((ROOT / "config" / name).read_text())
        if name == "shade-service.json":
            settings["halo_metres"] = 2
        (tmp_path / "config" / name).write_text(json.dumps(settings))
    boundary = {
        "type": "Polygon",
        "coordinates": [
            [
                [2610000, 1266000],
                [2611000, 1266000],
                [2611000, 1267000],
                [2610000, 1267000],
                [2610000, 1266000],
            ]
        ],
    }
    (tmp_path / "data/tile-inventory.json").write_text(
        json.dumps({"boundary": {"geometry": boundary}})
    )
    assets = {}
    for kind in ("surface", "terrain"):
        path = directory / f"2610-1266-{kind}.tif"
        values = np.full((1000, 1000), 150, dtype="int16")
        values[499, 500] = -32768
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=1000,
            width=1000,
            count=1,
            dtype="int16",
            crs="EPSG:2056",
            nodata=-32768,
            transform=from_origin(2610000, 1267000, 1, 1),
            compress="DEFLATE",
        ) as dataset:
            dataset.write(values, 1)
            dataset.scales = (2,)
        assets[f"2610-1266-{kind}"] = {
            "file": path.name,
            "tile": "2610-1266",
            "kind": kind,
            "shape": [1000, 1000],
            "sha256": sha256_file(path),
        }
    manifest = {
        "assets": assets,
        "preparation_version": "test-version",
        "settings": {
            "cell_size_metres": 1,
            "height_step_metres": 2,
            "nodata_code": -32768,
        },
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    service = ShadeService(tmp_path)
    monkeypatch.setattr(main, "shade_service", service)
    return service, manifest


def request(**updates):
    value = {
        "bounds": [2610498, 1266498, 2610502, 1266502],
        "requested_time": "2026-06-21T12:00:00Z",
    }
    value.update(updates)
    return value


def test_scaled_windows_and_missing_halo_are_not_filled(prepared):
    service, manifest = prepared
    surface, terrain = load_metre_grids(
        service.root / "data/geometry", manifest, (2610498, 1266498, 2610502, 1266502)
    )
    assert surface[0, 0] == terrain[0, 0] == 300
    assert np.isnan(surface[1, 2])
    absent, _ = load_metre_grids(
        service.root / "data/geometry", manifest, (2609998, 1266998, 2610002, 1267002)
    )
    assert np.isnan(absent[:2]).all()


def test_api_unknown_cache_timezones_and_no_external_calls(prepared, monkeypatch):
    import ipaddress
    import socket

    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("Network")
    )
    original_connect = socket.socket.connect

    def local_connect(sock, address):
        # Windows asyncio uses a loopback socket pair for its own event loop.
        if (
            not isinstance(address, tuple)
            or not ipaddress.ip_address(address[0]).is_loopback
        ):
            pytest.fail("External network")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", local_connect)
    client = TestClient(main.app)
    first = client.post("/api/shade", json=request())
    assert first.status_code == 200
    body = ShadeResponse.model_validate(first.json())
    assert body.counts.model_dump() == {
        "unknown": 16,
        "sunlit": 0,
        "shaded": 0,
        "night": 0,
    }
    assert base64.b64decode(body.states) == bytes(16)
    assert body.availability == "unknown"
    assert "validation" in body.explanation
    assert first.headers["x-shade-cache"] == "MISS"
    assert client.post("/api/shade", json=request()).headers["x-shade-cache"] == "HIT"
    same_time = client.post(
        "/api/shade", json=request(requested_time="2026-06-21T14:00:00+02:00")
    )
    assert same_time.headers["x-shade-cache"] == "HIT"
    assert same_time.json()["shade"]["requested_time"].endswith("+02:00")
    changed_time = client.post(
        "/api/shade", json=request(requested_time="2026-06-21T12:01:00Z")
    )
    assert changed_time.headers["x-shade-cache"] == "MISS"


@pytest.mark.parametrize(
    "change",
    [
        {"bounds": [1, 2, 1, 3]},
        {"requested_time": "2026-01-01T12:00:00"},
        {"corridor": [[0, 0], [1, 1]]},
        {"extra": True},
        {"corridor_width_m": 0},
        {"bounds": [1, 2, "NaN", 4]},
    ],
)
def test_invalid_api_requests_are_rejected(prepared, change):
    assert (
        TestClient(main.app).post("/api/shade", json=request(**change)).status_code
        == 422
    )


def test_oversize_missing_corrupt_and_outside_inputs(prepared):
    service, _ = prepared
    client = TestClient(main.app)
    assert (
        client.post(
            "/api/shade", json=request(bounds=[2610000, 1266000, 2611001, 1267000])
        ).status_code
        == 413
    )
    outside = client.post(
        "/api/shade", json=request(bounds=[2612000, 1266000, 2612002, 1266002])
    )
    assert outside.json()["availability"] == "unsupported"
    # Missing geometry stays unknown and invalidates the prior file-stamp key.
    path = service.root / "data/geometry/2610-1266-surface.tif"
    content = path.read_bytes()
    path.unlink()
    missing = client.post("/api/shade", json=request())
    assert missing.status_code == 200
    assert missing.json()["counts"]["unknown"] == 16
    path.write_bytes(content + b"corrupted")
    assert client.post("/api/shade", json=request()).status_code == 503
    path.write_bytes(content)
    assert client.post("/api/shade", json=request()).status_code == 200
    (service.root / "data/geometry/manifest.json").unlink()
    assert client.post("/api/shade", json=request()).status_code == 503


def test_cache_version_settings_corridor_and_file_state_invalidation(prepared):
    service, manifest = prepared
    model = ShadeRequest.model_validate(request())
    original = service.context(model)[0]
    manifest["preparation_version"] = "new-version"
    (service.root / "data/geometry/manifest.json").write_text(json.dumps(manifest))
    assert service.context(model)[0] != original
    corridor = model.model_copy(
        update={"corridor": [(2610498, 1266500), (2610502, 1266500)]}
    )
    assert service.context(model)[0] != service.context(corridor)[0]


def test_corridor_selection_and_lv95_rotation():
    model = ShadeRequest.model_validate(
        request(corridor=[[2610498, 1266500], [2610502, 1266500]], corridor_width_m=1)
    )
    selected = corridor_cells(model, model.bounds, 1)
    assert selected.sum() == 8
    latitude, longitude, rotation = solar_location(model.bounds)
    assert latitude == pytest.approx(47.55, abs=0.01)
    assert longitude == pytest.approx(7.59, abs=0.02)
    assert rotation == pytest.approx(0.10, abs=0.02)


def test_service_busy_maps_to_retryable_503(prepared, monkeypatch):
    from bla_bla_walk.shade_cache import ShadeBusy

    def busy(*args):
        raise ShadeBusy("Busy")

    monkeypatch.setattr(prepared[0], "respond", busy)
    result = TestClient(main.app).post("/api/shade", json=request())
    assert result.status_code == 503
    assert result.headers["retry-after"] == "1"
