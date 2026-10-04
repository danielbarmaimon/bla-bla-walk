"""Saved data must keep its time, unknowns and identity during offline use."""

import pytest
from bla_bla_walk import main, snapshots
from bla_bla_walk.demo_fixture import fixture_snapshot
from bla_bla_walk.main import app
from fastapi.testclient import TestClient


def provider_example():
    payload = fixture_snapshot().model_dump(mode="json")
    payload["mode"] = "online"
    for layer in payload["layers"]:
        layer["availability"] = "current"
        for feature in layer["features"]:
            feature["provenance"]["fixture"] = False
    payload["layers"][0]["features"][0]["availability"] = "current"
    return payload


def test_offline_preserves_saved_time_and_unknowns_without_network(
    tmp_path, monkeypatch
):
    def no_network():
        raise AssertionError("Offline mode contacted a provider")

    monkeypatch.setattr(snapshots.TEMPERATURE, "get_layer", no_network)
    monkeypatch.setattr(snapshots.FOUNTAINS, "get_layer", no_network)
    path = tmp_path / "snapshot.json"
    original = snapshots.MapSnapshot.model_validate(provider_example())
    path.write_text(original.model_dump_json(), encoding="utf-8")
    saved = snapshots.offline_snapshot(path)
    assert saved.mode == "offline"
    assert saved.generated_at == original.generated_at
    assert saved.layers[0].availability == "stale"
    assert [feature.availability for feature in saved.layers[0].features] == [
        "stale",
        "missing",
    ]
    assert saved.layers[1].features[0].availability == "unknown"
    assert saved.layers[0].features[0].value == original.layers[0].features[0].value
    assert "no refresh" in saved.layers[0].features[0].explanation


def test_offline_rejects_fixtures(tmp_path):
    path = tmp_path / "snapshot.json"
    path.write_text(fixture_snapshot().model_dump_json(), encoding="utf-8")
    with pytest.raises(ValueError, match="synthetic"):
        snapshots.offline_snapshot(path)


def test_modes_and_missing_offline_snapshot(monkeypatch):
    client = TestClient(app)
    expected = snapshots.MapSnapshot.model_validate(provider_example())
    monkeypatch.setattr(main, "online_snapshot", lambda: expected)
    assert client.get("/api/map").json()["mode"] == "online"
    assert client.get("/api/map?mode=online").json()["mode"] == "online"
    assert client.get("/api/map?mode=fixture").json()["mode"] == "fixture"
    assert client.get("/api/map?mode=invalid").status_code == 422

    def absent():
        raise FileNotFoundError("No prepared snapshot")

    monkeypatch.setattr(main, "offline_snapshot", absent)
    assert client.get("/api/map?mode=offline").status_code == 503


def test_failed_preparation_does_not_replace_saved_snapshot(tmp_path, monkeypatch):
    snapshot = snapshots.MapSnapshot.model_validate(provider_example())
    snapshot.layers[0].availability = "missing"
    monkeypatch.setattr(snapshots, "online_snapshot", lambda: snapshot)
    path = tmp_path / "snapshot.json"
    path.write_text("last successful snapshot")
    with pytest.raises(ValueError, match="retained"):
        snapshots.save_provider_snapshot(path)
    assert path.read_text() == "last successful snapshot"
