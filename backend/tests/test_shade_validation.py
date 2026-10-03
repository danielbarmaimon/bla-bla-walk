"""Checks for the reproducible numerical validation harness."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).parents[2] / "scripts/validate_compact_shade.py"
spec = importlib.util.spec_from_file_location("compact_validation", SCRIPT)
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def test_route_sample_weights_and_elapsed_time_preserve_saved_route():
    route = {
        "geometry": {"coordinates": [[7.59, 47.55], [7.5901, 47.5501]]},
        "properties": {"routing_duration_s": 30},
    }
    samples, total = validation.route_samples(route)
    assert sum(sample[1] for sample in samples) == pytest.approx(total)
    assert all(0 < sample[1] <= 2 for sample in samples)
    assert all(0 < sample[2] < 30 for sample in samples)
    assert np.all(np.diff([sample[2] for sample in samples]) > 0)


def test_scene_without_supported_receivers_is_recorded_without_matches():
    surface = np.ones((2000, 2000), dtype="float32")
    terrain = np.zeros_like(surface)
    checks = validation.scene_check(
        surface, terrain, surface[::2, ::2], terrain[::2, ::2]
    )
    assert len(checks) == 18
    assert all(check["points"] == [] for check in checks)
