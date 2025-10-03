import pytest

from esp_now_hub.sensors.ms5803 import _compute


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
