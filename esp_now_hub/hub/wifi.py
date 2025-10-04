import time

import machine
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
    def __init__(self, ssid, password, ifconfig):
        self._ssid = ssid
        self._password = password
        self._ifconfig = ifconfig
        self._wlan = network.WLAN(network.STA_IF)

    def __enter__(self):
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
                print("connected to wifi")
                return self
            self._disconnect()
            print(
                f"could not connect to wifi! status: {STATUSES.get(self._wlan.status())}, wait for 10s"
            )
            self._disconnect()
            machine.lightsleep(10000)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._disconnect()

    def _disconnect(self):
        if self._wlan.isconnected():
            self._wlan.disconnect()
        self._wlan.active(False)
