import math
import time

import machine
from micropython import const

_VCC_RAMP_UP_TIME = const(
    0.01
)  # Must be > RC, this should be enough for most use cases.
_MEASURE_INTERVAL = const(0.0001)
_T0 = const(273.15)  # 0 degrees Celsius in Kelvin.
_T25 = const(298.15)  # 25 degrees Celsius in Kelvin.
_ATTENUATION_MAP = {
    const(0): machine.ADC.ATTN_0DB,
    const(2.5): machine.ADC.ATTN_2_5DB,
    const(6): machine.ADC.ATTN_6DB,
    const(11): machine.ADC.ATTN_11DB,
}


class NTCThermistor:
    """NTC Thermistor temperature sensor.
    Circuit:
                 __ 0.1 uF electrolytic capacitor __
                /                                   \
        gnd pin -- NTC -- adc pin -- divider R ------ vcc pin

    The capacitor is here to smooth out VCC noise.

    The divider resistance value should be close or above the NTC resistance.
    Having one above allows going deeper in the negatives while still staying in the ADC linear range.
    See https://docs.micropython.org/en/latest/esp32/quickref.html#ADC.

    Note: a separate pin is used to avoid heating the NTC when not measuring.
    """

    def __init__(
        self,
        adc_pin,
        vcc_pin=None,
        beta=3590,
        vcc=3.3,
        resistance_ntc=10000,
        resistance_divider=10000,
        adc_attenuation=11,
    ):
        self._adc = machine.ADC(
            machine.Pin(adc_pin),
            atten=_ATTENUATION_MAP[adc_attenuation],
        )
        self._vcc_pin = machine.Pin(vcc_pin, machine.Pin.OUT) if vcc_pin else None
        self._beta = beta
        self._vcc = vcc
        self._resistance_ntc = resistance_ntc
        self._resistance_divider = resistance_divider

    def _measure_one(self):
        rt = self._resistance_divider / (self._vcc / self._adc.read_uv() * 1e6 - 1)
        print(rt)
        return 1 / (1 / _T25 + math.log(rt / self._resistance_ntc) / self._beta) - _T0

    def _measure(self):
        measures = []
        for _ in range(20):
            temp = self._measure_one()
            # Extremes will mean that value is outside linear measurement range
            # or indicate an issue with wiring.
            if -20 < temp < 60:
                measures.append(temp)
        if not measures:
            raise ValueError("could not measure temperature")
        return sum(measures) / len(measures)

    def get_measure(self):
        """Return temperature (Celsius)."""
        if self._vcc_pin is not None:
            self._vcc_pin.value(1)
            time.sleep(_VCC_RAMP_UP_TIME)
        temp = self._measure()
        if self._vcc_pin is not None:
            self._vcc_pin.value(0)
        return {
            "temperature": round(temp, 1),
        }


def setup(sensor_id, initialize, **kwargs):
    return NTCThermistor(**kwargs).get_measure
