"""Saved building reuse, acquisition provenance and failure preservation."""

import hashlib
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def preparation(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "building_preparation", ROOT / "scripts/prepare_building_shade.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for name in (
        "config/building-shade.json",
        "data/routes/demo.geojson",
        "data/tile-inventory.json",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    return module


def response_data():
    return {
        "osm3s": {"timestamp_osm_base": "2026-10-03T12:00:00Z"},
        "elements": [
            {
                "type": "way",
                "id": 123,
                "geometry": [
                    {"lon": 7.59, "lat": 47.55},
                    {"lon": 7.591, "lat": 47.55},
                    {"lon": 7.591, "lat": 47.551},
                    {"lon": 7.59, "lat": 47.55},
                ],
                "tags": {"building": "yes", "height": "12 m", "name": "Unused label"},
            }
        ],
    }


def transport(preparation, monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        preparation.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    return original


def test_default_reuses_cache_offline_and_preserves_source_dates(
    preparation, monkeypatch
):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=response_data())

    transport(preparation, monkeypatch, handle)
    first = preparation.prepare(endpoint="https://example.org/api/interpreter")
    second = preparation.prepare()
    third = preparation.prepare(offline=True)
    assert first == second == third
    assert len(requests) == first["query_count"]
    assert "bla-bla-walk" in requests[0].headers["user-agent"]
    assert first["endpoint"] == "https://example.org/api/interpreter"
    path = preparation.ROOT / ".cache/buildings" / first["file"]
    content = path.read_bytes()
    assert hashlib.sha256(content).hexdigest() == first["sha256"]
    assert b"Unused label" not in content


def test_failed_refresh_preserves_the_previous_good_cache(preparation, monkeypatch):
    def handle(request):
        return httpx.Response(200, json=response_data())

    client_type = transport(preparation, monkeypatch, handle)
    first = preparation.prepare()
    directory = preparation.ROOT / ".cache/buildings"
    before = (directory / "manifest.json").read_bytes()

    def unavailable(request):
        raise httpx.ReadTimeout("Provider unavailable", request=request)

    # Replace the transport factory directly, keeping the actual original class.
    monkeypatch.setattr(
        preparation.httpx,
        "Client",
        lambda **kwargs: client_type(
            transport=httpx.MockTransport(unavailable), **kwargs
        ),
    )
    with pytest.raises(httpx.ReadTimeout):
        preparation.prepare(refresh=True)
    assert (directory / "manifest.json").read_bytes() == before
    assert preparation.prepare(offline=True) == first


def test_corrupt_changed_coverage_and_unsanitized_caches_are_rejected(
    preparation, monkeypatch
):
    transport(
        preparation,
        monkeypatch,
        lambda request: httpx.Response(200, json=response_data()),
    )
    metadata = preparation.prepare()
    directory = preparation.ROOT / ".cache/buildings"
    polygon = metadata["coverage"]
    assert preparation.cached_buildings(directory, {"type": "Polygon"}) is None
    path = directory / metadata["file"]
    content = path.read_bytes()
    path.write_bytes(content + b"corrupt")
    assert preparation.cached_buildings(directory, polygon) is None
    with pytest.raises(ValueError, match="No verified"):
        preparation.prepare(offline=True)
    features = json.loads(content)
    features[0]["name"] = "Unneeded field"
    altered = json.dumps(features).encode()
    path.write_bytes(altered)
    metadata.update(sha256=hashlib.sha256(altered).hexdigest())
    metadata["version"] = metadata["sha256"]
    (directory / "manifest.json").write_text(json.dumps(metadata))
    assert preparation.cached_buildings(directory, polygon) is None


def test_offline_without_inputs_makes_no_requests(preparation, monkeypatch):
    transport(preparation, monkeypatch, lambda request: pytest.fail("Network request"))
    with pytest.raises(ValueError, match="No verified"):
        preparation.prepare(offline=True)


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://example.org/api",
        "https://user:password@example.org/api",
        "https://example.org/api?key=example",
        "https://example.org/api#fragment",
    ],
)
def test_endpoint_rejects_credentials_and_non_https(preparation, endpoint):
    with pytest.raises(ValueError, match="public HTTPS"):
        preparation.download_buildings(endpoint, "query", {}, preparation.ROOT)


def test_partial_or_inconsistent_batches_do_not_publish(preparation, monkeypatch):
    directory = preparation.ROOT / ".cache/buildings"
    calls = []

    def handle(request):
        calls.append(request)
        data = response_data()
        if len(calls) == 2:
            data["remark"] = "Query interrupted"
        return httpx.Response(200, json=data)

    transport(preparation, monkeypatch, handle)
    with pytest.raises(ValueError, match="incomplete"):
        preparation.prepare()
    assert not (directory / "manifest.json").exists()


def test_queries_cover_the_full_rectangle_with_bounded_cells(preparation):
    import re

    bounds = (47.55, 7.58, 47.573, 7.603)
    queries = preparation.building_queries(bounds, 0.01)
    assert len(queries) == 9
    rectangles = [
        tuple(map(float, re.search(r'way\["building"\]\(([^)]+)', query)[1].split(",")))
        for query in queries
    ]
    assert min(box[0] for box in rectangles) == bounds[0]
    assert min(box[1] for box in rectangles) == bounds[1]
    assert max(box[2] for box in rectangles) == bounds[2]
    assert max(box[3] for box in rectangles) == bounds[3]
    assert all(
        box[2] - box[0] <= 0.01 and box[3] - box[1] <= 0.01 for box in rectangles
    )


def test_acquisition_resumes_validated_batches(preparation, monkeypatch):
    directory = preparation.ROOT / ".cache/buildings"
    original = httpx.Client
    calls = []

    def handle(request):
        calls.append(request.content)
        if request.content.endswith(b"second") and len(calls) == 2:
            return httpx.Response(504)
        return httpx.Response(200, json=response_data())

    monkeypatch.setattr(
        preparation.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs),
    )
    with pytest.raises(httpx.HTTPStatusError):
        preparation.download_buildings(
            "https://example.org/api", ["first", "second"], {}, directory
        )
    assert not (directory / "manifest.json").exists()
    assert len(list((directory / ".batches").glob("*.json"))) == 1
    metadata = preparation.download_buildings(
        "https://example.org/api", ["first", "second"], {}, directory
    )
    assert calls == [b"data=first", b"data=second", b"data=second"]
    assert metadata["feature_count"] == 1
    assert metadata["query_count"] == 2


def test_inconsistent_duplicates_do_not_publish(preparation, monkeypatch):
    calls = []

    def handle(request):
        calls.append(request)
        data = response_data()
        if len(calls) == 2:
            data["elements"][0]["tags"]["height"] = "18 m"
        return httpx.Response(200, json=data)

    transport(preparation, monkeypatch, handle)
    directory = preparation.ROOT / ".cache/buildings"
    with pytest.raises(ValueError, match="changed between"):
        preparation.download_buildings(
            "https://example.org/api", ["first", "second"], {}, directory
        )
    assert not (directory / "manifest.json").exists()
