import pytest

from esp_now_hub.sensors.ntc_thermistor import NTCThermistor


@pytest.fixture
def adc(mocker):
    return mocker.Mock()


@pytest.fixture
def ntc(adc):
    ntc = NTCThermistor(1)
    ntc._adc = adc
    return ntc


@pytest.mark.parametrize(
    ("r_ntc", "r_divider", "uv", "expected"),
    [
        (10000, 10000, 150000, 126),
        (10000, 10000, 2450000, 1),
        (15000, 22000, 150000, 110),
        (15000, 22000, 2450000, -7),
    ],
)
def test_measure_one(r_ntc, r_divider, uv, expected, ntc, adc):
    ntc._resistance_ntc = r_ntc
    ntc._resistance_divider = r_divider
    adc.read_uv.return_value = uv
    assert round(ntc._measure_one()) == expected
