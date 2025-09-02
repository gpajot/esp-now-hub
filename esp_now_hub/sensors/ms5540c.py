import time

import machine


class MS5540C:
    """Waterproof pressure and temperature sensor.
    See hhttps://www.te.com/commerce/DocumentDelivery/DDEController?Action=showdoc&DocId=Data+Sheet%7FMS5540C%7FB3%7Fpdf%7FEnglish%7FENG_DS_MS5540C_B3.pdf%7FCAT-BLPS0033
    """

    MCLK_FREQ = 32768  # Hz, 50% duty cycle at this frequency.
    SCLK_FREQ = 500000  # Hz
    CONVERSION_DURATION = 0.035  # Sensor requires 35ms to convert readings.
    # Commands: 3 high start bits, command bits, 3 low stop bits.
    # Leading zeros are added to have multiples of 8.
    # Pressure and temperature require 2 additional clock ticks at the end.
    # Words require 1 additional clock ticks at the end.
    READ_PRESSURE = b"\x0f\x40"  # 111 1010 000 00
    READ_TEMPERATURE = b"\x0f\x20"  # 111 1001 000 00
    READ_WORD1 = b"\x1d\x50"  # 111 010101 000 0
    READ_WORD2 = b"\x1d\x60"  # 111 010110 000 0
    READ_WORD3 = b"\x1d\x90"  # 111 011001 000 0
    READ_WORD4 = b"\x1d\xa0"  # 111 011010 000 0
    RESET = b"\x15\x55\x40"  # 101010101010101000000
    CALIBRATION_CACHE = "ms5540c-calibration.txt"

    def __init__(self, sclk, din, dout, mclk, calibration_cache_prefix=None):
        self._spi_params = {
            "baudrate": self.SCLK_FREQ,
            "sck": machine.Pin(sclk),
            "mosi": machine.Pin(din),
            "miso": machine.Pin(dout),
        }
        self._spi = machine.SoftSPI(**self._spi_params)
        self._pwm_params = {
            "freq": self.MCLK_FREQ,
            "duty_u16": 32768,
        }
        self._pwm = machine.PWM(machine.Pin(mclk), **self._pwm_params)
        self._calibration_coefficients = self._get_calibration_coefficients(
            calibration_cache_prefix
        )

    def deinit(self):
        self._spi.deinit()
        self._pwm.deinit()

    def _write(self, data):
        self._spi.init(phase=0, **self._spi_params)  # Rising edge.
        self._spi.write(data)

    def _read(self):
        self._spi.init(phase=1, **self._spi_params)  # Falling edge.
        # Always read 2 bytes.
        return int.from_bytes(self._spi.read(2))

    def _get_word(self, command):
        self._write(command)
        return self._read()

    def _get_measure(self, command):
        self._write(command)
        time.sleep(self.CONVERSION_DURATION)
        return self._read()

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
        self._write(self.RESET)
        coefficients = _get_coefficients(
            self._get_word(self.READ_WORD1),
            self._get_word(self.READ_WORD2),
            self._get_word(self.READ_WORD3),
            self._get_word(self.READ_WORD4),
        )
        with open(cache, "w") as f:
            f.write(",".join(map(str, coefficients)))
        self.deinit()
        return coefficients

    def get_measure(self):
        """Return pressure (bar), temperature (Celsius)."""
        self._pwm.init(**self._pwm_params)
        self._write(self.RESET)
        d1 = self._get_measure(self.READ_PRESSURE)
        d2 = self._get_measure(self.READ_TEMPERATURE)
        pres, temp = _compute(d1, d2, *self._calibration_coefficients)
        self.deinit()
        return {"pressure": pres, "temperature": temp}


def _get_coefficients(w1, w2, w3, w4):
    """Get coefficients as per bit-pattern."""
    return (
        w1 >> 1,
        ((w3 & 0x3F) << 6) | (w4 & 0x3F),
        w4 >> 6,
        w3 >> 6,
        ((w1 & 0x1) << 10) | w2 >> 6,
        w2 & 0x3F,
    )


def _compute(d1, d2, c1, c2, c3, c4, c5, c6):
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
