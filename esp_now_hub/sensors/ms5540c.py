import time

import esp32
import machine
from micropython import const

_PWM_FREQ = const(32768)  # Hz.
_PWM_DUTY = const(32768)  # 50% duty cycle.
_SCLK_FREQ = const(500000)  # Hz
_CONV_TIME = const(0.035)  # Sensor requires 35ms to convert readings.
# Commands: 3 high start bits, command bits, 3 low stop bits.
# Leading zeros are added to have multiples of 8.
# Pressure and temperature require 2 additional clock ticks at the end.
# Words require 1 additional clock ticks at the end.
_MEASURE_PRES_CMD = const(b"\x0f\x40")  # 111 1010 000 00
_MEASURE_TEMP_CMD = const(b"\x0f\x20")  # 111 1001 000 00
_READ_WORD1_CMD = const(b"\x1d\x50")  # 111 010101 000 0
_READ_WORD2_CMD = const(b"\x1d\x60")  # 111 010110 000 0
_READ_WORD3_CMD = const(b"\x1d\x90")  # 111 011001 000 0
_READ_WORD4_CMD = const(b"\x1d\xa0")  # 111 011010 000 0
_RESET_CMD = const(b"\x15\x55\x40")  # 101010101010101000000
_CALIB_CACHE = const("calibration")
type CalibrationCoefficients = tuple[int, int, int, int, int, int]


class MS5540C:
    """Waterproof pressure and temperature sensor.
    See https://www.te.com/commerce/DocumentDelivery/DDEController?Action=showdoc&DocId=Data+Sheet%7FMS5540C%7FB3%7Fpdf%7FEnglish%7FENG_DS_MS5540C_B3.pdf%7FCAT-BLPS0033
    """

    def __init__(
        self,
        calibration_cache_namespace: str,
        sclk: int,
        din: int,
        dout: int,
        mclk: int,
    ):
        self._spi_params = {
            "baudrate": _SCLK_FREQ,
            "sck": machine.Pin(sclk),
            "mosi": machine.Pin(din),
            "miso": machine.Pin(dout),
        }
        self._spi = machine.SoftSPI(**self._spi_params)
        self._pwm = machine.PWM(machine.Pin(mclk), freq=_PWM_FREQ, duty_u16=_PWM_DUTY)
        self._calibration_coefficients = self._get_calibration_coefficients(
            calibration_cache_namespace
        )

    def deinit(self) -> None:
        self._spi.deinit()
        self._pwm.deinit()

    def _write(self, data: bytes) -> None:
        self._spi.init(phase=0, **self._spi_params)  # Rising edge.
        self._spi.write(data)

    def _read(self) -> int:
        self._spi.init(phase=1, **self._spi_params)  # Falling edge.
        # Always read 2 bytes.
        return int.from_bytes(self._spi.read(2))

    def _get_word(self, command: bytes) -> int:
        self._write(command)
        return self._read()

    def _get_measure(self, command: bytes) -> int:
        self._write(command)
        time.sleep(_CONV_TIME)
        return self._read()

    def _get_calibration_coefficients(self, namespace: str) -> CalibrationCoefficients:
        nvs = esp32.NVS(namespace)
        try:
            buf = bytearray(100)
            nvs.get_blob(_CALIB_CACHE, buf)
            return tuple(
                map(
                    int,
                    buf.replace(b"\x00", b"").decode("utf-8").strip().split(","),
                )
            )  # ty: ignore[invalid-return-type]
        except OSError:
            pass
        self._write(_RESET_CMD)
        coefficients = _get_coefficients(
            self._get_word(_READ_WORD1_CMD),
            self._get_word(_READ_WORD2_CMD),
            self._get_word(_READ_WORD3_CMD),
            self._get_word(_READ_WORD4_CMD),
        )
        nvs.set_blob(_CALIB_CACHE, ",".join(map(str, coefficients)).encode("utf-8"))
        nvs.commit()
        self.deinit()
        return coefficients

    def get_measure(self) -> dict[str, float]:
        """Return pressure (bar), temperature (Celsius)."""
        self._pwm.init(freq=_PWM_FREQ, duty_u16=_PWM_DUTY)
        self._write(_RESET_CMD)
        d1 = self._get_measure(_MEASURE_PRES_CMD)
        d2 = self._get_measure(_MEASURE_TEMP_CMD)
        if not d1 or not d2:
            raise ValueError("could not fetch value from sensor")
        pres, temp = _compute(d1, d2, *self._calibration_coefficients)
        self.deinit()
        return {"pressure": pres, "temperature": temp}


def _get_coefficients(w1: int, w2: int, w3: int, w4: int) -> CalibrationCoefficients:
    """Get coefficients as per bit-pattern."""
    return (
        w1 >> 1,
        ((w3 & 0x3F) << 6) | (w4 & 0x3F),
        w4 >> 6,
        w3 >> 6,
        ((w1 & 0x1) << 10) | w2 >> 6,
        w2 & 0x3F,
    )


def _compute(
    d1: int, d2: int, c1: int, c2: int, c3: int, c4: int, c5: int, c6: int
) -> tuple[float, float]:
    # Temperature.
    ut1 = 8 * c5 + 20224
    dt = d2 - ut1
    temp = 200 + dt * (c6 + 50) / 2**10
    # Pressure.
    off = c2 * 4 + ((c4 - 512) * dt) / 2**12
    sens = c1 + (c3 * dt) / 2**10 + 24576
    x = (sens * (d1 - 7168)) / 2**14 - off
    p = x * 10 / 2**5 + 250 * 10
    # Second order compensation.
    if temp < 200:
        t2 = 11 * (c6 + 24) * (200 - temp) * (200 - temp) / 2**20
        p2 = 3 * t2 * (p - 3500) / 2**14
        temp -= t2
        p -= p2
    elif temp > 450:
        t2 = 3 * (c6 + 24) * (450 - temp) * (450 - temp) / 2**20
        p2 = t2 * (p - 10000) / 2**13
        temp -= t2
        p -= p2
    return (
        round(p / 10000, 4),
        round(temp / 10, 1),
    )


def setup(sensor_id: str, initialize: bool, **kwargs):
    return MS5540C(calibration_cache_namespace=sensor_id, **kwargs).get_measure
