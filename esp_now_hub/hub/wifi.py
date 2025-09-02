import time

import network

STATUSES = {
    network.STAT_IDLE: "idle",
    network.STAT_CONNECTING: "connecting",
    network.STAT_WRONG_PASSWORD: "wrong password",
    network.STAT_NO_AP_FOUND: "no ap found",
    network.STAT_CONNECT_FAIL: "connect failed",
    network.STAT_GOT_IP: "got ip",
}


class WLan:
    def __init__(self, ssid, password):
        self._ssid = ssid
        self._password = password
        self._wlan = network.WLAN(network.STA_IF)

    def __enter__(self):
        while True:
            self._disconnect()
            self._wlan.active(True)
            self._wlan.connect(self._ssid, self._password)
            while self._wlan.status() in {
                network.STAT_CONNECTING,
                network.STAT_IDLE,
            }:
                time.sleep(0.1)
            if self._wlan.status() == network.STAT_GOT_IP:
                return self
            print(
                f"could not connect to wifi! status: {STATUSES.get(self._wlan.status())}, wait for 5s"
            )
            time.sleep(5)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()

    def _disconnect(self):
        if self._wlan.isconnected():
            self._wlan.disconnect()
        self._wlan.active(False)
