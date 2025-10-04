import struct
import time

import esp32
import machine
from micropython import const

_MODES = [
    const("ultra-low-power"),
    const("low-power"),
    const("standard-resolution"),
    const("high-resolution"),
    const("ultra-high-resolution"),
]
# 3 bits: standby duration, 3 bits: IIR filter time, 1 bit: nothing, 1 bit: spi
_CONFIG_REG = const(0xF5)
_CONFIG_VAL = const(b"\x00")  # 000 000 0 0
# 3 bits: temp oversampling, 3 bits: press oversampling, 2 bits: mode
_CTRL_MEASURE_REG = const(0xF4)
_CTRL_MEASURE_VALS = [
    const(b"\x25"),  # 001 001 01
    const(b"\x29"),  # 001 010 01
    const(b"\x2d"),  # 001 011 01
    const(b"\x31"),  # 001 100 01
    const(b"\x55"),  # 010 101 01
]
_MEASURE_REG = const(0xF7)
_CONV_TIMES = [
    const(0.0064),
    const(0.0087),
    const(0.0133),
    const(0.0225),
    const(0.0432),
]
_CALIB_REG = const(0x88)  # 24 bytes.
_CALIB_STRUCT = const("<H2hH8h")  # dig_T1 -> dig_T3, dig_P1 -> dig_P9
_CALIB_CACHE = const("calibration")


class BMP280:
    """Atmospheric pressure and temperature sensor.
    See https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf
    """

    def __init__(
        self,
        calibration_cache_namespace,
        scl,
        sda,
        address=0x77,
        mode="ultra-low-power",
        initialize=True,
    ):
        self._i2c = machine.SoftI2C(scl=machine.Pin(scl), sda=machine.Pin(sda))
        self._address = address
        self._mode_idx = _MODES.index(mode)
        if initialize:
            self._i2c.writeto_mem(self._address, _CONFIG_REG, _CONFIG_VAL)
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
        data = self._i2c.readfrom_mem(
            self._address,
            _CALIB_REG,
            struct.calcsize(_CALIB_STRUCT),
        )
        coefficients = struct.unpack(_CALIB_STRUCT, data)
        nvs.set_blob(_CALIB_CACHE, ",".join(map(str, coefficients)).encode("utf-8"))
        nvs.commit()
        return coefficients

    def get_measure(self):
        """Return pressure (bar), temperature (Celsius)."""
        # Set forced mode to trigger measure.
        self._i2c.writeto_mem(
            self._address,
            _CTRL_MEASURE_REG,
            _CTRL_MEASURE_VALS[self._mode_idx],
        )
        # Wait for measurements to complete.
        time.sleep(_CONV_TIMES[self._mode_idx])
        data = self._i2c.readfrom_mem(self._address, _MEASURE_REG, 6)
        p = (data[0] << 16 | data[1] << 8 | data[2]) >> 4
        t = (data[3] << 16 | data[4] << 8 | data[5]) >> 4
        if not p or not t:
            raise ValueError("could not fetch value from sensor")
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


def setup(sensor_id, initialize, **kwargs):
    return BMP280(
        calibration_cache_namespace=sensor_id,
        initialize=initialize,
        **kwargs
    ).get_measure  # fmt: skip
