import time

import machine


class MS5803:
    """Waterproof pressure and temperature sensor.
    See https://www.te.com/commerce/DocumentDelivery/DDEController?Action=showdoc&DocId=Data+Sheet%7FMS5803-14BA%7FB3%7Fpdf%7FEnglish%7FENG_DS_MS5803-14BA_B3.pdf%7FCAT-BLPS0013
    """

    RESET_CMD = b"\x1e"
    RESET_TIME = 0.005
    READ_PRESSURE_CMDS = {
        256: b"\x40",
        512: b"\x42",
        1024: b"\x44",
        2048: b"\x46",
        4096: b"\x48",
    }
    READ_TEMPERATURE_CMDS = {
        256: b"\x50",
        512: b"\x52",
        1024: b"\x54",
        2048: b"\x56",
        4096: b"\x58",
    }
    CONVERTION_TIMES = {
        256: 0.0006,
        512: 0.00117,
        1024: 0.00228,
        2048: 0.00454,
        4096: 0.00904,
    }
    READ_MEASURE_CMD = b"\x00"
    CALIBRATION_COEFFICIENT_CMDS = (
        b"\xa2",
        b"\xa4",
        b"\xa6",
        b"\xa8",
        b"\xaa",
        b"\xac",
    )
    CALIBRATION_CACHE = "ms5803-calibration.txt"

    def __init__(
        self,
        scl,
        sda,
        address=0x77,
        pressure_resolution=256,
        temperature_resolution=256,
        initialize=True,
        calibration_cache_prefix=None,
    ):
        self._i2c = machine.SoftI2C(scl=machine.Pin(scl), sda=machine.Pin(sda))
        self._address = address
        self._pressure_resolution = pressure_resolution
        self._temperature_resolution = temperature_resolution
        if initialize:
            self._i2c.writeto(self._address, self.RESET_CMD)
            time.sleep(self.RESET_TIME)
        self._calibration_coefficients = self._get_calibration_coefficients(
            calibration_cache_prefix
        )

    def _get_calibration_coefficients(self, cache_prefix):
        cache = (
            "-".join((cache_prefix, self.CALIBRATION_CACHE))
            if cache_prefix
            else self.CALIBRATION_CACHE
        )
        try:
            with open(cache, "r") as f:
                return tuple(map(int, f.read().strip().split(",")))
        except Exception:
            pass
        coefficients = tuple(
            self._get_calibration_coefficient(self.CALIBRATION_COEFFICIENT_CMDS[i])
            for i in range(6)
        )
        with open(cache, "w") as f:
            f.write(",".join(map(str, coefficients)))
        return coefficients

    def _get_calibration_coefficient(self, cmd):
        self._i2c.writeto(self._address, cmd)
        return int.from_bytes(self._i2c.readfrom(self._address, 2), byteorder="big")

    def _get_measure(self, cmd, wait_time):
        self._i2c.writeto(self._address, cmd)
        time.sleep(wait_time)
        return int.from_bytes(self._i2c.readfrom(self._address, 3), byteorder="big")

    def get_measure(self):
        """Return pressure (bar), temperature (Celsius)."""
        d1 = self._get_measure(
            self.READ_PRESSURE_CMDS[self._pressure_resolution],
            self.CONVERTION_TIMES[self._pressure_resolution],
        )
        d2 = self._get_measure(
            self.READ_TEMPERATURE_CMDS[self._temperature_resolution],
            self.CONVERTION_TIMES[self._temperature_resolution],
        )
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
