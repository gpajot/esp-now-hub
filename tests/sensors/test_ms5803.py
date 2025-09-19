import sys
from unittest.mock import Mock

import pytest

sys.modules["machine"] = Mock()
sys.modules["micropython"] = Mock()
sys.modules["micropython"].const = lambda e: e  # type: ignore[attr-defined]
from esp_now_hub.sensors.ms5803 import _compute  # noqa: E402


@pytest.fixture(scope="session")
def coefficients():
    return (
        46546,
        42845,
        29751,
        29457,
        32745,
        29059,
    )


def test_compute(coefficients):
    assert _compute(4311550, 8387300, *coefficients) == (1.0005, 20.1)
