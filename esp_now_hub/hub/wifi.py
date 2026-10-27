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
    def __init__(
        self,
        debug,
        ssid: str,
        password: str,
        ifconfig: tuple[str, str, str, str] | None,
    ):
        self._debug = debug
        self._ssid = ssid
        self._password = password
        self._ifconfig = ifconfig
        self._wlan = network.WLAN(network.STA_IF)

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self._debug("error in tear down:", exc_type)
            self._debug(exc_tb)
        self._disconnect()

    def _connect(self) -> None:
        while True:
            self._disconnect()
            self._wlan.active(True)
            self._wlan.config(pm=self._wlan.PM_NONE)
            if self._ifconfig:
                self._wlan.ifconfig(self._ifconfig)
            self._wlan.connect(self._ssid, self._password)
            i = 0
            while i < 100 and self._wlan.status() in {
                network.STAT_CONNECTING,
                network.STAT_IDLE,
            }:
                time.sleep(0.1)
                i += 1
            if self._wlan.status() == network.STAT_GOT_IP and self._wlan.isconnected():
                self._debug("connected")
                return
            self._disconnect()
            raise RuntimeError(
                f"could not connect, status: {STATUSES.get(self._wlan.status())}"
            )

    def _disconnect(self) -> None:
        if self._wlan.isconnected():
            self._wlan.disconnect()
        self._wlan.active(False)
