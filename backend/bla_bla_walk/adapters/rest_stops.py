"""Local sanitized bench/park candidates; serving never downloads OSM data."""

from ..interfaces import MapLayer
from .addresses import ROOT

PATH = ROOT / ".cache/rest-stops.json"


def rest_stops(path=PATH):
    """Return explicitly dated mapped candidates or an explicit missing layer."""
    try:
        layer = MapLayer.model_validate_json(path.read_text(encoding="utf-8"))
        if layer.kind != "rest" or any(
            item.provenance.fixture for item in layer.features
        ):
            raise ValueError("Expected real rest candidates")
        return layer
    except (OSError, ValueError):
        return MapLayer(
            id="rest-stops",
            label="Benches and rest candidates",
            kind="rest",
            availability="missing",
            features=[],
            explanation="Saved bench/park data unavailable; run rest-stop preparation.",
        )
