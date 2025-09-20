import sys
from unittest.mock import Mock

import pytest

sys.modules["esp32"] = Mock()
sys.modules["machine"] = Mock()
sys.modules["micropython"] = Mock()
sys.modules["micropython"].const = lambda e: e  # type: ignore[attr-defined]
from esp_now_hub.sensors.bmp280 import _compute  # noqa: E402


@pytest.fixture(scope="session")
def coefficients():
    return (
        27504,
        26435,
        -1000,
        36477,
        -10685,
        3024,
        2855,
        140,
        -7,
        15500,
        -14600,
        6000,
    )


def test_compute(coefficients):
    assert _compute(519888, 415148, *coefficients) == (1.0065, 25.1)
