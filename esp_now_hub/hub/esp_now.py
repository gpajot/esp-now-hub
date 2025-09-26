import binascii
import json
import select

import espnow


class ESPNow:
    def __init__(self, poll, devices, pmk=None):
        self._poll = poll
        self._devices = devices
        self._pmk = pmk
        self._esp_now = espnow.ESPNow()
        self._included_components = {}
        self._signal_thresholds = {}

    def __enter__(self):
        self._esp_now.active(False)
        self._esp_now.active(True)
        if self._pmk:
            self._esp_now.set_pmk(self._pmk)
        for device in self._devices:
            address = binascii.unhexlify(
                device["address"].replace(":", "").encode("utf-8")
            )
            if device.get("local_master_key"):
                self._esp_now.add_peer(address, lmk=device["local_master_key"])
            self._included_components[address] = device["components"]
            self._signal_thresholds[address] = (
                device.get("send_signal_strength_threshold") or -127
            )
        self._poll.register(self._esp_now, select.POLLIN)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._poll.unregister(self._esp_now)
        self._esp_now.active(False)

    def wants(self, obj):
        return obj is self._esp_now

    def receive(self, event):
        if event & select.POLLERR or event & select.POLLHUP:
            raise RuntimeError("error event received for ESP-Now")
        if event & select.POLLIN:
            address, payload = self._esp_now.recv(0)
            if address and payload:
                components = self._included_components.get(address)
                if components:
                    data = {}
                    for sensor_id, sensor_data in json.loads(
                        payload.decode("utf-8")
                    ).items():
                        if sensor_id not in components:
                            continue
                        for prop, datum in sensor_data.items():
                            if prop in components[sensor_id]:
                                data[f"{sensor_id}_{prop}"] = datum
                    # Send the signal strength if below threshold.
                    peer_stats = self._esp_now.peers_table.get(address)
                    if peer_stats and peer_stats[0] <= self._signal_thresholds[address]:
                        data["_signal"] = f"{peer_stats[0]}dBm"
                    return address.hex(), data
        return None, None
