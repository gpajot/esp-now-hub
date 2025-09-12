import json

import espnow
import ubinascii


class ESPNow:
    def __init__(self, devices, pmk=None):
        self._devices = devices
        self._pmk = pmk
        self._esp_now = espnow.ESPNow()
        self._name_by_address = {}

    def __enter__(self):
        self._esp_now.active(False)
        self._esp_now.active(True)
        if self._pmk:
            self._esp_now.set_pmk(self._pmk)
        for device in self._devices:
            address = ubinascii.unhexlify(
                device["address"].replace(":", "").encode("utf-8")
            )
            if device.get("local_master_key"):
                self._esp_now.add_peer(address, lmk=device["local_master_key"])
            self._name_by_address[address] = device.get("name") or device["address"]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._esp_now.active(False)

    def receive(self, timeout):
        address, payload = self._esp_now.recv(timeout)
        if address and payload:
            name = self._name_by_address.get(address)
            if name:
                return (
                    address.hex(),
                    name,
                    json.loads(payload.decode("utf-8")),
                )
        return None
