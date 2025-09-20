import time

import esp32
import machine
from micropython import const

_OSRS = [const(256), const(512), const(1024), const(2048), const(4096)]
_MEASURE_PRES_CMD = const(0x40)
_MEASURE_TEMP_CMD = const(0x50)
# I found max conversion times from the datasheet are too low,
# as device will often report busy or return 0.
_CONV_TIMES = [const(0.004), const(0.006), const(0.007), const(0.010), const(0.015)]
_READ_MEASURE_CMD = const(b"\x00")
_READ_CALIB_COEF_CMD = const(0xA2)
_CALIB_CACHE = const("calibration")


class MS5803:
    """Waterproof pressure and temperature sensor.
    See https://www.te.com/commerce/DocumentDelivery/DDEController?Action=showdoc&DocId=Data+Sheet%7FMS5803-14BA%7FB3%7Fpdf%7FEnglish%7FENG_DS_MS5803-14BA_B3.pdf%7FCAT-BLPS0013
    """

    def __init__(
        self,
        calibration_cache_namespace,
        scl,
        sda,
        address=0x76,
        pressure_resolution=1024,
        temperature_resolution=256,
    ):
        self._i2c = machine.SoftI2C(scl=machine.Pin(scl), sda=machine.Pin(sda))
        self._address = address
        self._p_res_idx = _OSRS.index(pressure_resolution)
        self._t_res_idx = _OSRS.index(temperature_resolution)
        self._calibration_coefficients = self._get_calibration_coefficients(
            calibration_cache_namespace
        )

    def _get_calibration_coefficients(self, namespace):
        nvs = esp32.NVS(namespace)
        try:
            buf = bytearray(100)
            nvs.get_blob(_CALIB_CACHE, buf)
            return tuple(
                map(int, buf.replace(b"\x00", b"").decode("utf-8").strip().split(","))
            )
        except OSError:
            pass
        coefficients = tuple(
            self._get_calibration_coefficient(
                (_READ_CALIB_COEF_CMD + 0x02 * i).to_bytes(1),
            )
            for i in range(6)
        )
        nvs.set_blob(_CALIB_CACHE, ",".join(map(str, coefficients)).encode("utf-8"))
        nvs.commit()
        return coefficients

    def _get_calibration_coefficient(self, cmd):
        self._i2c.writeto(self._address, cmd)
        return int.from_bytes(self._i2c.readfrom(self._address, 2), "big")

    def _get_measure(self, cmd, wait_time):
        self._i2c.writeto(self._address, cmd)
        time.sleep(wait_time)
        self._i2c.writeto(self._address, _READ_MEASURE_CMD)
        return int.from_bytes(self._i2c.readfrom(self._address, 3), "big")

    def get_measure(self):
        """Return pressure (bar), temperature (Celsius)."""
        d1 = self._get_measure(
            (_MEASURE_PRES_CMD + 0x02 * self._p_res_idx).to_bytes(1),
            _CONV_TIMES[self._p_res_idx],
        )
        d2 = self._get_measure(
            (_MEASURE_TEMP_CMD + 0x02 * self._t_res_idx).to_bytes(1),
            _CONV_TIMES[self._t_res_idx],
        )
        if not d1 or not d2:
            raise ValueError("could not fetch value from sensor")
        pres, temp = _compute(d1, d2, *self._calibration_coefficients)
        return {"pressure": pres, "temperature": temp}


def _compute(d1, d2, c1, c2, c3, c4, c5, c6):
    # Temperature.
    dt = d2 - c5 * 2**8
    temp = 2000 + (dt * c6) // 2**23
    # Pressure.
    off = c2 * 2**16 + (c4 * dt) // 2**7
    sens = c1 * 2**15 + (c3 * dt) // 2**8
    # Second order compensation.
    if temp < 2000:
        t2 = (3 * dt**2) // 2**33
        off2 = (3 * (temp - 2000) ** 2) // 2**1
        sens2 = (5 * (temp - 2000) ** 2) // 2**3
        if temp < -1500:
            off2 += 7 * (temp + 1500) ** 2
            sens2 += 4 * (temp + 1500) ** 2
    else:
        t2 = (7 * dt**2) // 2**37
        off2 = (temp - 2000) ** 2 // 2**4
        sens2 = 0
    temp -= t2
    off -= off2
    sens -= sens2
    p = ((d1 * sens) // 2**21 - off) // 2**15
    return round(p / 10000, 4), round(temp / 100, 1)
