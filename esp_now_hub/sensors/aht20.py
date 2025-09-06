import time

import machine


class AHT20:
    """Atmospheric humidity and temperature sensor.
    See https://asairsensors.com/wp-content/uploads/2021/09/Data-Sheet-AHT20-Humidity-and-Temperature-Sensor-ASAIR-V1.0.03.pdf
    """

    SETUP_TIME = 0.1  # Needs 100ms after power up.
    STATUS_CMD = b"\x71"
    INIT_CMD = b"\xbe\x08\x00"
    INIT_TIME = 0.01
    MEASURE_CMD = b"\xac\x33\x00"
    MEASURE_TIME = 0.08

    def __init__(self, scl, sda, address=0x38, initialize=True):
        self._i2c = machine.SoftI2C(scl=machine.Pin(scl), sda=machine.Pin(sda))
        self._address = address
        if initialize:
            time.sleep(self.SETUP_TIME)
            if not self._get_status() & 0x08:
                self._i2c.writeto(self._address, self.INIT_CMD)
                time.sleep(self.INIT_TIME)

    def _get_status(self):
        self._i2c.writeto(self._address, self.STATUS_CMD)
        return self._i2c.readfrom(self._address, 1)[0]

    def get_measure(self):
        """Return humidity (0-100), temperature (Celsius)."""
        self._i2c.writeto(self._address, self.MEASURE_CMD)
        time.sleep(self.MEASURE_TIME)
        while self._get_status() & 0x80:
            time.sleep(0.01)
        data = self._i2c.readfrom(self._address, 6)
        h = data[1] << 12 | data[2] << 4 | data[3] >> 4
        t = (data[3] & 0x0F) << 16 | data[4] << 8 | data[5]
        return {
            "humidity": int(round(h / 2**20 * 100, 0)),
            "temperature": round(t / 2**20 * 200 - 50, 1),
        }
