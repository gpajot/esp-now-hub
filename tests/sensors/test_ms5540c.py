import sys
from unittest.mock import Mock

import pytest

sys.modules["machine"] = Mock()
sys.modules["micropython"] = Mock()
sys.modules["micropython"].const = lambda e: e  # type: ignore[attr-defined]
from esp_now_hub.sensors.ms5540c import _compute, _get_coefficients  # noqa: E402


@pytest.fixture(scope="session")
def coefficients():
    return (
        23470,
        1324,
        737,
        393,
        628,
        25,
    )


def test_get_coefficients(coefficients):
    assert _get_coefficients(46940, 40217, 25172, 47212) == coefficients


def test_compute(coefficients):
    assert _compute(16460, 27856, *coefficients) == (0.9717, 39.1)
