import json
import select
import time

import umqtt.simple


class MQTTClient:
    def __init__(
        self,
        poll,
        topic_prefix,
        devices,
        keepalive,
        server,
        port=1883,
        user=None,
        password=None,
    ):
        self._poll = poll
        self._topic_prefix = topic_prefix
        self._devices = devices
        self._device_keepalive = {}
        self._last_receive_ticks = {}
        self._last_broker_tick = None
        self._last_ping_tick = None
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

    def __enter__(self):
        self._connect()
        self._send_discovery()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._poll.unregister(self._client.sock)
        self._client.publish(self._status_topic, b"offline", retain=True)
        self._client.disconnect()

    def _get_status_topic(self, device_id):
        return f"{self._topic_prefix}/status/{device_id}".encode("utf-8")

    def _get_state_topic(self, device_id):
        return f"{self._topic_prefix}/get/{device_id}".encode("utf-8")

    def _connect(self, clean_session=True):
        self._client.connect(clean_session)
        self._last_broker_tick = self._last_ping_tick = time.ticks_ms()  # type: ignore[attr-defined]
        self._client.publish(self._status_topic, b"online", retain=True)
        self._poll.register(self._client.sock, select.POLLIN)
        print("connected to MQTT")

    def _reconnect(self, attempts=None):
        self._poll.unregister(self._client.sock)
        i = 0
        while attempts is None or i < attempts:
            if i:
                time.sleep(min(i, 30))
            try:
                self._connect(False)
                return True
            except OSError:
                i += 1
        return False

    def wants(self, obj):
        return obj is self._client.sock

    def receive(self, event):
        if event & select.POLLERR or event & select.POLLHUP:
            self._reconnect()
        elif event & select.POLLIN:
            # Consume messages.
            self._client.check_msg()
            self._last_broker_tick = time.ticks_ms()  # type: ignore[attr-defined]

    def ping(self):
        keepalive = self._client.keepalive * 1000
        now = time.ticks_ms()  # type: ignore[attr-defined]
        # Check if we need to ping.
        next_ping = max(
            0,
            keepalive - time.ticks_diff(now, self._last_ping_tick),  # type: ignore[attr-defined]
        )
        if next_ping > 0:
            return next_ping
        # Check last message received from broker (at least ping responses).
        if (
            self._last_broker_tick is not None
            and time.ticks_diff(now, self._last_broker_tick) > keepalive  # type: ignore[attr-defined]
        ):
            self._reconnect()
        # Ping broker.
        try:
            self._client.ping()
            self._last_ping_tick = time.ticks_ms()  # type: ignore[attr-defined]
        except OSError:
            self._reconnect()
        # Check if wee need to put some devices offline.
        for device_id, dev_keepalive in self._device_keepalive.items():
            ticks = self._last_receive_ticks.get(device_id)
            if (
                ticks is not None
                and time.ticks_diff(time.ticks_ms(), ticks) > dev_keepalive  # type: ignore[attr-defined]
            ):
                self._publish(
                    self._get_status_topic(device_id),
                    b"offline",
                    retain=True,
                )
                del self._last_receive_ticks[device_id]
        return keepalive

    def _send_discovery(self):
        for device in self._devices:
            device_id = device["address"].replace(":", "")
            # Store in ms and allow a bit more.
            self._device_keepalive[device_id] = device["keepalive"] * 1500
            status_topic = self._get_status_topic(device_id)
            state_topic = self._get_state_topic(device_id)
            device_discovery = {
                "identifiers": [f"{self._topic_prefix}-{device_id}"],
                "manufacturer": device.get("manufacturer", ""),
                "model": device.get("model", ""),
                "name": device["name"],
            }
            availability = [
                {"topic": status_topic.decode("utf-8")},
                {"topic": self._status_topic.decode("utf-8")},
            ]
            for sensor_id, components in device["components"].items():
                for component in components:
                    self._publish(
                        f"{self._topic_prefix}/sensor/{device_id}/{sensor_id}-{component}/config",
                        {
                            "state_topic": state_topic.decode("utf-8"),
                            "value_template": "{{ value_json.%s_%s }}"
                            % (sensor_id, component),
                            "state_class": "measurement",
                            "device": device_discovery,
                            "availability": availability,
                            "availability_mode": "all",
                            "unique_id": f"{self._topic_prefix}-{device_id}-{sensor_id}-{component}",
                            "name": f"{sensor_id} {component}",
                            "unit_of_measurement": _UNITS[component],
                            "device_class": component,
                            "icon": _ICONS[component],
                        },
                        retain=True,
                        keep_trying=True,
                        encode=True,
                    )
            self._publish(status_topic, b"offline", retain=True)

    def send(self, device_id, data):
        if device_id not in self._last_receive_ticks:
            self._publish(self._get_status_topic(device_id), b"online", retain=True)
        self._last_receive_ticks[device_id] = time.ticks_ms()  # type: ignore[attr-defined]
        if data:
            self._publish(self._get_state_topic(device_id), data, encode=True)

    def _publish(self, topic, data, retain=False, keep_trying=False, encode=False):
        """Retry indefinitely if keep_trying or just once otherwise."""
        retried = False
        while True:
            try:
                self._client.publish(
                    topic,
                    json.dumps(data).encode("utf-8") if encode else data,
                    retain=retain,
                )
                return True
            except OSError:
                if keep_trying:
                    self._reconnect()
                elif retried:
                    return False
                else:
                    retried = True
                    if not self._reconnect(1):
                        return False


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
