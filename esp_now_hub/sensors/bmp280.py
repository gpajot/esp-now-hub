import struct
import time

import machine


class BMP280:
    """Atmospheric pressure and temperature sensor.
    See https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf
    """

    CONFIG_REGISTER = 0xF5  # 3 bits: standby duration, 3 bits: IIR filter time, 1 bit: nothing, 1 bit: spi
    CONFIG_VALUE = b"\x00"  # 000 000 0 0
    CTRL_MEASURE_REGISTER = (
        0xF4  # 3 bits: temp oversampling, 3 bits: press oversampling, 2 bits: mode
    )
    CTRL_MEASURE_VALUES = {
        "ultra-low-power": b"\x25",  # 001 001 01
        "low-power": b"\x29",  # 001 010 01
        "standard-resolution": b"\x2d",  # 001 011 01
        "high-resolution": b"\x31",  # 001 100 01
        "ultra-high-resolution": b"\x55",  # 010 101 01
    }
    MEASURE_REGISTER = 0xF7
    MEASURE_DURATIONS = {
        "ultra-low-power": 0.0064,
        "low-power": 0.0087,
        "standard-resolution": 0.0133,
        "high-resolution": 0.0225,
        "ultra-high-resolution": 0.0432,
    }
    CALIBRATION_REGISTER = 0x88  # 24 bytes.
    CALIBRATION_STRUCT = "<H2hH8h"  # dig_T1 -> dig_T3, dig_P1 -> dig_P9
    CALIBRATION_CACHE = "bmp280-calibration.txt"

    def __init__(
        self,
        scl,
        sda,
        address=0x77,
        mode="ultra-low-power",
        initialize=True,
        calibration_cache_prefix=None,
    ):
        self._i2c = machine.SoftI2C(scl=machine.Pin(scl), sda=machine.Pin(sda))
        self._address = address
        self._mode = mode
        if initialize:
            self._i2c.writeto_mem(
                self._address, self.CONFIG_REGISTER, self.CONFIG_VALUE
            )
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
        data = self._i2c.readfrom_mem(
            self._address,
            self.CALIBRATION_REGISTER,
            struct.calcsize(self.CALIBRATION_STRUCT),
        )
        coefficients = struct.unpack(self.CALIBRATION_STRUCT, data)
        with open(cache, "w") as f:
            f.write(",".join(map(str, coefficients)))
        return coefficients

    def get_measure(self):
        """Return pressure (bar), temperature (Celsius)."""
        # Set forced mode to trigger measure.
        self._i2c.writeto_mem(
            self._address,
            self.CTRL_MEASURE_REGISTER,
            self.CTRL_MEASURE_VALUES[self._mode],
        )
        # Wait for measurements to complete.
        time.sleep(self.MEASURE_DURATIONS[self._mode])
        data = self._i2c.readfrom_mem(
            self._address,
            self.MEASURE_REGISTER,
            6,
        )
        p = (data[0] << 16 | data[1] << 8 | data[2]) >> 4
        t = (data[3] << 16 | data[4] << 8 | data[5]) >> 4
        pres, temp = _compute(t, p, *self._calibration_coefficients)
        return {"pressure": pres, "temperature": temp}


def _compute(
    adc_t,
    adc_p,
    dig_t1,
    dig_t2,
    dig_t3,
    dig_p1,
    dig_p2,
    dig_p3,
    dig_p4,
    dig_p5,
    dig_p6,
    dig_p7,
    dig_p8,
    dig_p9,
):
    # Temperature.
    var1 = (adc_t / 16384.0 - dig_t1 / 1024.0) * dig_t2
    var2 = (adc_t / 131072.0 - dig_t1 / 8192.0) ** 2 * dig_t3
    t_fine = var1 + var2
    t = t_fine / 5120
    # Pressure.
    var1 = t_fine / 2 - 64000
    var2 = var1**2 * dig_p6 / 32768.0
    var2 = var2 + var1 * dig_p5 * 2
    var2 = var2 / 4 + dig_p4 * 65536.0
    var1 = (dig_p3 * var1**2 / 524288 + dig_p2 * var1) / 524288
    var1 = (1.0 + var1 / 32768) * dig_p1
    p = (1048576.0 - adc_p - var2 / 4096) * 6250 / var1
    var1 = dig_p9 * p**2 / 2147483648
    var2 = p * dig_p8 / 32768
    p = p + (var1 + var2 + dig_p7) / 16
    return round(p / 100000, 4), round(t, 1)
