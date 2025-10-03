import pytest

from esp_now_hub.sensors.bmp280 import _compute


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
