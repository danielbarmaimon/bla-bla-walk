"""Information loss must remain visible before admitting compact receivers."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from audit_compact_receivers import audit_heights  # noqa: E402


def test_encoding_erases_inversions_and_creates_false_ground_equality():
    surface = np.array([[99.4, 100.4, 104, np.nan]])
    terrain = np.array([[100.1, 100.1, 100, 100]])
    report = audit_heights(surface, terrain, 2)
    assert report["valid_pairs"] == 3
    assert report["missing_pairs"] == 1
    assert report["source_below_terrain"] == 1
    assert report["erased_below_terrain"] == 1
    assert report["encoded_equal_but_source_unequal"] == 2


def test_masked_nodata_and_real_equality_do_not_count_as_encoding_loss():
    values = np.ma.array([[100.0, -9999]], mask=[[False, True]])
    report = audit_heights(values, values, 2)
    assert report["encoded_equal_pairs"] == 1
    assert report["encoded_equal_but_source_unequal"] == 0
    assert report["missing_pairs"] == 1
    assert report["surface_max_encoding_error_metres"] == 0


def test_all_missing_has_no_measured_error():
    report = audit_heights(np.full((2, 2), np.nan), np.zeros((2, 2)), 2)
    assert report["valid_pairs"] == 0
    assert report["surface_max_encoding_error_metres"] is None


@pytest.mark.parametrize("step", [0, -2, float("nan")])
def test_invalid_encoding_step_rejected(step):
    with pytest.raises(ValueError):
        audit_heights(np.zeros((2, 2)), np.zeros((2, 2)), step)
