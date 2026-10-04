"""T23 file-to-API-to-route diagnostics; the building scene is synthetic."""

import json
from datetime import datetime

import numpy as np
import pytest
import rasterio
from bla_bla_walk import main
from bla_bla_walk.adapters.routes import load_demo_routes
from bla_bla_walk.comparison_service import ComparisonService
from bla_bla_walk.evaluation import compare_choices
from bla_bla_walk.geometry import sha256_file
from bla_bla_walk.interfaces import ShadeRequest, ShadeResponse, ShadeState
from bla_bla_walk.route_shade import calculate_walking_evidence
from bla_bla_walk.shade_service import ROOT, ShadeService
from fastapi.testclient import TestClient
from rasterio.transform import from_origin

BOUNDS = (2611490, 1266490, 2611520, 1266520)
DAYLIGHT = ("2026-06-21T08:00:00+02:00", "2026-06-21T14:00:00+02:00")
NIGHT = "2026-06-21T00:00:00+02:00"


def polygon(west, south, east, north):
    return {
        "type": "Polygon",
        "coordinates": [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


@pytest.fixture
def scene(tmp_path, monkeypatch):
    """One verified compact tile and known 12m building; reduced test-only reach."""

    def reject_network(*args, **kwargs):
        raise AssertionError("Shade diagnostics must not contact providers")

    monkeypatch.setattr("httpx.HTTPTransport.handle_request", reject_network)
    geometry = tmp_path / "data/geometry"
    buildings = tmp_path / ".cache/buildings"
    geometry.mkdir(parents=True)
    buildings.mkdir(parents=True)
    (tmp_path / "config").mkdir()
    for name in ("shade-service.json", "shade.json", "building-shade.json"):
        settings = json.loads((ROOT / "config" / name).read_text())
        if name == "shade-service.json":
            settings["halo_metres"] = 40
        else:
            settings["maximum_ray_distance_metres"] = 40
        (tmp_path / "config" / name).write_text(json.dumps(settings))
    coverage = polygon(2611000, 1266000, 2612000, 1267000)
    (tmp_path / "data/tile-inventory.json").write_text(
        json.dumps({"boundary": {"geometry": coverage}})
    )
    manifest = {
        "preparation_version": "synthetic-t23",
        "settings": {
            "cell_size_metres": 1,
            "height_step_metres": 2,
            "nodata_code": -32768,
        },
        "assets": {},
        "pair_flags": {},
    }
    for kind in ("surface", "terrain"):
        path = geometry / f"2611-1266-{kind}.tif"
        values = np.full((1000, 1000), 150, dtype="int16")
        if kind == "surface":
            values[495:500, 500:505] = 156  # 12m above the flat 300m datum
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
            transform=from_origin(2611000, 1267000, 1, 1),
            compress="DEFLATE",
        ) as dataset:
            dataset.write(values, 1)
            dataset.scales = (2,)
        manifest["assets"][f"2611-1266-{kind}"] = {
            "file": path.name,
            "tile": "2611-1266",
            "kind": kind,
            "shape": [1000, 1000],
            "sha256": sha256_file(path),
        }
    flags = geometry / "flags.npy"
    np.save(flags, np.ones((1000, 1000), dtype="uint8"))
    manifest["pair_flags"]["2611-1266"] = {
        "file": flags.name,
        "sha256": sha256_file(flags),
        "preparation_version": manifest["preparation_version"],
    }
    (geometry / "manifest.json").write_text(json.dumps(manifest))
    footprint = buildings / "footprints.json"
    footprint.write_text(
        json.dumps(
            [{"geometry": polygon(2611500, 1266500, 2611505, 1266505), "height_m": 12}]
        )
    )
    (buildings / "manifest.json").write_text(
        json.dumps(
            {
                "file": footprint.name,
                "sha256": sha256_file(footprint),
                "coverage": coverage,
                "attribution": "Synthetic T23 test scene only",
            }
        )
    )
    service = ShadeService(tmp_path)
    monkeypatch.setattr(main, "shade_service", service)
    return service


def snapshot(client, moment):
    return client.post(
        "/api/shade",
        json={
            "bounds": BOUNDS,
            "requested_time": moment,
        },
    )


def test_known_building_two_daylight_times_exact_time_and_warm_cache(scene):
    client = TestClient(main.app)
    states = []
    for moment in DAYLIGHT:
        cold = snapshot(client, moment)
        assert cold.status_code == 200
        assert cold.headers["X-Shade-Cache"] == "MISS"
        value = ShadeResponse.model_validate(cold.json())
        assert value.availability == "approximate"
        assert value.model == "building-shadow-approximation"
        assert value.counts.shaded > 0 and value.counts.sunlit > 0
        assert value.counts.unknown > 0  # building interiors are not receivers
        assert value.shade.effective_time == datetime.fromisoformat(moment)
        assert value.shade.requested_time == value.shade.effective_time
        assert "synthetic-t23;buildings=" in value.shade.geometry_version
        warm = snapshot(client, moment)
        assert warm.headers["X-Shade-Cache"] == "HIT"
        assert warm.json() == cold.json()
        states.append(value.states)
    assert states[0] != states[1]  # departure changes the actual cast-shadow grid


def test_night_is_separate_from_shade_and_invalid_receivers(scene):
    value = ShadeResponse.model_validate(snapshot(TestClient(main.app), NIGHT).json())
    assert value.counts.night > 0
    assert value.counts.shaded == value.counts.sunlit == 0
    assert value.counts.unknown == 25  # no night credit for building interiors


@pytest.mark.parametrize("missing", ["flags", "surface", "terrain"])
def test_missing_receiver_inputs_invalidate_cached_credit(scene, missing):
    client = TestClient(main.app)
    assert snapshot(client, DAYLIGHT[0]).json()["counts"]["shaded"] > 0
    name = "flags.npy" if missing == "flags" else f"2611-1266-{missing}.tif"
    (scene.root / "data/geometry" / name).unlink()
    response = snapshot(client, DAYLIGHT[0])
    assert response.status_code == 200
    assert response.headers["X-Shade-Cache"] == "MISS"
    assert response.json()["counts"] == {
        "unknown": 900,
        "sunlit": 0,
        "shaded": 0,
        "night": 0,
    }
    assert response.json()["availability"] == "unknown"


def test_absent_building_manifest_blocks_saved_pair_and_shade(scene, monkeypatch):
    (scene.root / ".cache/buildings/manifest.json").unlink()
    comparison = ComparisonService(scene)
    monkeypatch.setattr(main, "comparison_service", comparison)
    try:
        client = TestClient(main.app)
        assert snapshot(client, DAYLIGHT[0]).status_code == 503
        result = client.post("/api/comparison", json={"departure_time": DAYLIGHT[0]})
        assert result.status_code == 503
        assert "Prepared shade inputs unavailable" in result.json()["detail"]
    finally:
        comparison.close()


def test_saved_route_sampling_preserves_unknowns_times_and_eligibility(scene):
    """Real saved lines over a synthetic single-tile scene; never live evidence."""
    client = TestClient(main.app)
    responses = []

    def calculate(request):
        result = client.post("/api/shade", json=request.model_dump(mode="json"))
        assert result.status_code == 200
        value = ShadeResponse.model_validate(result.json())
        responses.append(value)
        return value

    evidence = [
        calculate_walking_evidence(
            route,
            datetime.fromisoformat(DAYLIGHT[1]),
            calculate,
        )
        for route in load_demo_routes().features
    ]
    assert len(evidence) == 2 and responses
    for route in evidence:
        assert (
            route.shaded_metres + route.unshaded_metres + route.unknown_metres
            == pytest.approx(route.distance_metres)
        )
        assert route.unknown_metres > 0  # single tile cannot cover the saved pair
        assert all(
            sample.metadata.effective_time == sample.requested_time
            for sample in route.samples
        )
        assert all(
            sample.state == ShadeState.UNKNOWN
            for sample in route.samples
            if sample.explanation.startswith("Requested cells are outside")
        )
    choices = compare_choices(evidence)
    assert all(choice.winner is None for choice in choices.values())
    assert all(route.access_state == "unknown" for route in evidence)


def test_corrupt_footprints_cannot_reuse_a_cached_shadow(scene):
    request = ShadeRequest(bounds=BOUNDS, requested_time=DAYLIGHT[0])
    scene.respond(request)
    (scene.root / ".cache/buildings/footprints.json").write_text("[]")
    with pytest.raises(ValueError, match="checksum"):
        scene.respond(request)
