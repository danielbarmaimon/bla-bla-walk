"""Live and saved provider layers, with explicit offline freshness."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from .adapters.fountains import FountainAdapter
from .adapters.pet import add_pet_route_metrics
from .adapters.routes import load_demo_routes
from .adapters.temperature import TemperatureAdapter
from .interfaces import MapSnapshot

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / ".cache/provider-snapshot.json"
TEMPERATURE = TemperatureAdapter()
FOUNTAINS = FountainAdapter()
SNAPSHOT_LOCK = Lock()


def online_snapshot() -> MapSnapshot:
    """Refresh independent layers concurrently, respecting each adapter's cadence."""
    with SNAPSHOT_LOCK, ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(adapter.get_layer) for adapter in (TEMPERATURE, FOUNTAINS)
        ]
        routes = add_pet_route_metrics(load_demo_routes())
        return MapSnapshot(
            mode="online",
            generated_at=datetime.now(UTC),
            layers=[future.result() for future in futures] + [routes],
        )


def save_provider_snapshot(path: Path = SNAPSHOT_PATH) -> MapSnapshot:
    """Save sanitized provider output; retain the previous file on missing layers."""
    snapshot = online_snapshot()
    if any(layer.availability == "missing" for layer in snapshot.layers):
        raise ValueError(
            "Provider preparation failed; previous offline snapshot retained"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return snapshot


def offline_snapshot(path: Path = SNAPSHOT_PATH) -> MapSnapshot:
    """Read local bytes only; retain unknowns and label saved current data as stale."""
    snapshot = MapSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    if any(
        feature.provenance.fixture
        for layer in snapshot.layers
        for feature in layer.features
    ):
        raise ValueError("Expected provider snapshot, received synthetic fixture")
    saved = snapshot.generated_at.isoformat()
    layers = []
    for layer in snapshot.layers:
        features = [
            feature.model_copy(
                update={
                    "availability": "stale"
                    if feature.availability == "current"
                    else feature.availability,
                    "explanation": (
                        f"Saved offline snapshot {saved}; no refresh. "
                        f"{feature.explanation}"
                    ),
                    "pet": feature.pet.model_copy(update={"availability": "stale"})
                    if feature.pet and feature.pet.availability == "current"
                    else feature.pet,
                }
            )
            for feature in layer.features
        ]
        layers.append(
            layer.model_copy(
                update={
                    "availability": "stale"
                    if layer.availability == "current"
                    else layer.availability,
                    "explanation": (
                        f"Saved offline snapshot {saved}; no refresh. "
                        f"{layer.explanation}"
                    ),
                    "features": features,
                }
            )
        )
    return snapshot.model_copy(update={"mode": "offline", "layers": layers})
