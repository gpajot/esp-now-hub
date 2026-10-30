import json
import os
import select
import time

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

import umqtt.simple

if TYPE_CHECKING:
    from .config import Device
else:
    Device = ...
try:
    from .version import VERSION
except ImportError:
    from version import VERSION  # ty: ignore[unresolved-import]

_VERSION_INFO = f"{VERSION} ({os.uname().release})"


class MQTTClient:
    def __init__(
        self,
        debug,
        poll: select.poll,
        topic_prefix: str,
        devices: list[Device],
        keepalive: int,
        server: str,
        port: int = 1883,
        user: str | None = None,
        password: str | None = None,
    ):
        self._debug = debug
        self._poll = poll
        self._topic_prefix = topic_prefix
        self._devices: dict[str, Device] = {
            d["address"].replace(":", ""): d for d in devices
        }
        self._broker_keepalive = keepalive
        self._device_keepalive: dict[str, float] = {}
        self._last_device_seen_times: dict[str, float] = {}
        self._last_ping_time: float = 0
        self._status_topic = self._get_status_topic("hub")
        self._client = umqtt.simple.MQTTClient(
            topic_prefix,
            server,
            port=port,
            user=user,
            password=password,
            keepalive=keepalive,
        )
        self._client.set_last_will(self._status_topic, b"offline", retain=True)
        self._discovery_sent: dict[
            str, dict[str, str]
        ] = {}  # address -> extra device info

    def __enter__(self):
        while True:
            try:
                self._connect()
                break
            except OSError:
                time.sleep(1)
        for device_id, device in self._devices.items():
            # Allow a bit more.
            self._device_keepalive[device_id] = device["keepalive"] * 1.5
            self._publish(self._get_status_topic(device_id), b"offline", retain=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self._debug("error in tear down:", exc_type)
            self._debug(exc_tb)
        self._poll.unregister(self._client.sock)
        self._client.publish(self._status_topic, b"offline", retain=True)
        self._client.disconnect()

    def _get_status_topic(self, device_id: str) -> bytes:
        return f"{self._topic_prefix}/status/{device_id}".encode()

    def _get_state_topic(self, device_id: str) -> bytes:
        return f"{self._topic_prefix}/get/{device_id}".encode()

    def _connect(self) -> None:
        self._client.connect()
        self._last_ping_time = time.time()
        self._client.publish(self._status_topic, b"online", retain=True)
        self._poll.register(self._client.sock, select.POLLIN)
        self._debug("connected")

    def _reconnect(self, attempts: int | None = None) -> bool:
        self._debug("reconnecting")
        self._poll.unregister(self._client.sock)
        i = 0
        while attempts is None or i < attempts:
            if i:
                time.sleep(min(i, 30))
            try:
                self._connect()
                return True
            except OSError as exc:
                self._debug("error trying to connect", exc)
                i += 1
        self._debug("stopping connection attempts")
        return False

    def wants(self, obj) -> bool:
        return obj is self._client.sock

    def receive(self, event: int) -> None:
        if event & select.POLLERR or event & select.POLLHUP:
            self._debug("error from poller")
            self._reconnect()
        elif event & select.POLLIN:
            # Consume messages.
            try:
                self._client.check_msg()
            except OSError:
                self._debug("received empty message")
                self._reconnect()

    def ping(self) -> float:
        # Check if wee need to put some devices offline.
        for device_id, dev_keepalive in self._device_keepalive.items():
            last_time = self._last_device_seen_times.get(device_id)
            if last_time is not None and (time.time() - last_time) > dev_keepalive:
                self._debug(f"device {device_id} offline")
                self._publish(
                    self._get_status_topic(device_id),
                    b"offline",
                    retain=True,
                )
                del self._last_device_seen_times[device_id]
        # Check if we need to ping.
        next_ping = max(
            0,
            self._broker_keepalive * 0.9 - (time.time() - self._last_ping_time),
        )
        if next_ping > 0:
            self._debug(f"next ping in: {next_ping}s")
            return next_ping
        # Ping broker.
        try:
            self._debug("pinging broker")
            self._client.ping()
            self._last_ping_time = time.time()
        except OSError:
            self._reconnect()
        return self._broker_keepalive * 0.9

    def _send_discovery(self, device_id: str, extra_dev_info: dict[str, str]) -> None:
        device = self._devices[device_id]
        self._publish(
            f"{self._topic_prefix}/device/{device_id}/config".encode(),
            {
                "device": dict(
                    {
                        "ids": f"{self._topic_prefix}-{device_id}",
                        "name": device["name"],
                    },
                    **extra_dev_info
                ),
                "origin": {
                    "name": "esp-now-hub",
                    "sw": _VERSION_INFO,
                    "url": "https://github.com/gpajot/esp-now-hub",
                },
                "availability": [
                    {"topic": self._status_topic.decode("utf-8")},
                    {"topic": self._get_status_topic(device_id).decode("utf-8")},
                ],
                "availability_mode": "all",
                "state_topic": self._get_state_topic(device_id).decode("utf-8"),
                "components": {
                    f"{sensor_id}_{component}": {
                        "unique_id": f"{self._topic_prefix}-{device_id}-{sensor_id}-{component}",
                        "platform": "sensor",
                        "device_class": component,
                        "state_class": "measurement",
                        "unit_of_measurement": _UNITS[component],
                        "value_template": "{{ value_json.%s_%s }}"  # noqa: UP031
                        % (sensor_id, component),
                        "name": f"{sensor_id} {component}",
                        "icon": _ICONS[component],
                    }
                    for sensor_id, components in device["components"].items()
                    for component in components
                },
            },
            retain=True,
            keep_trying=True,
            encode=True,
        )  # fmt: skip

    def send(self, device_id: str, data) -> None:
        if device_id not in self._last_device_seen_times:
            self._debug(f"device {device_id} back online")
            self._publish(self._get_status_topic(device_id), b"online", retain=True)
        self._last_device_seen_times[device_id] = time.time()
        extra_dev_info = data.pop("d", {})
        if extra_dev_info != self._discovery_sent.get(device_id):
            self._send_discovery(device_id, extra_dev_info)
            self._discovery_sent[device_id] = extra_dev_info
        if data:
            self._publish(self._get_state_topic(device_id), data, encode=True)

    def _publish(
        self,
        topic: bytes,
        data,
        *,
        retain: bool = False,
        keep_trying: bool = False,
        encode: bool = False,
    ) -> None:
        """Retry indefinitely if keep_trying or just once otherwise."""
        retried = False
        while True:
            try:
                self._client.publish(
                    topic,
                    json.dumps(data).encode("utf-8") if encode else data,
                    retain=retain,
                )
                return
            except OSError:
                if keep_trying:
                    self._reconnect()
                elif retried:
                    self._debug(f"did not publish message to topic {topic}: {data}")
                    return
                else:
                    retried = True
                    if not self._reconnect(1):
                        self._debug(f"did not publish message to topic {topic}: {data}")
                        return


_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "pressure": "bar",
}
_ICONS = {
    "temperature": "mdi:thermometer",
    "humidity": "mdi:water-percent",
    "pressure": "mdi:speedometer",
}
