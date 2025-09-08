import json
import time

import umqtt.simple


def get_status_topic(topic_prefix, device_id):
    return f"{topic_prefix}/status/{device_id}"


def get_state_topic(topic_prefix, device_id):
    return f"{topic_prefix}/get/{device_id}"


class MQTTClient:
    def __init__(
        self,
        topic_prefix,
        server,
        port=1883,
        user=None,
        password=None,
        keepalive=0,
    ):
        self._status_topic = get_status_topic(topic_prefix, "hub")
        self._client = umqtt.simple.MQTTClient(
            topic_prefix,
            server,
            port=port,
            user=user,
            password=password,
            keepalive=keepalive,
        )
        self._client.set_last_will(self._status_topic, b"offline", retain=True)
        self.ping_interval = self._client.keepalive / 2 or 30

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.publish(self._status_topic, b"offline", retain=True)
        self._client.disconnect()

    def _connect(self, clean_session=True):
        self._client.connect(clean_session)
        self._client.publish(self._status_topic, b"online", retain=True)
        print("connected to MQTT")

    def _reconnect(self, attempts):
        i = 0
        while i < attempts:
            if i:
                time.sleep(min(i, 30))
            try:
                self._connect(False)
                return True
            except OSError:
                i += 1
        return False

    def ping(self):
        try:
            self._client.ping()
        except OSError:
            self._reconnect(1)

    def publish(self, topic, data, retain=False, keep_trying=False, encode=False):
        """Retry indefinitely if keep_trying or just once otherwise."""
        retried = False
        while True:
            try:
                self._client.publish(
                    topic.encode("utf-8"),
                    json.dumps(data).encode("utf-8") if encode else data,
                    retain=retain,
                )
                return True
            except OSError:
                if keep_trying:
                    self._reconnect(1000)
                elif retried:
                    return False
                else:
                    retried = True
                    if not self._reconnect(1):
                        return False


_SENT_DISCOVERIES = set()  # sensor_id, property
_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "pressure": "bar",
}
_ICONS = {
    "temperature": "mdi:thermometer",
    "humidity": "mdi:percent",
    "pressure": "mdi:speedometer",
}


def send(client, topic_prefix, device_id, device_name, data):
    status_topic = get_status_topic(topic_prefix, device_id)
    state_topic = get_state_topic(topic_prefix, device_id)
    state = {}
    for sensor_id, sensor_data in data.items():
        for prop, datum in sensor_data.items():
            if (sensor_id, prop) not in _SENT_DISCOVERIES:
                client.publish(
                    f"{topic_prefix}/sensor/{device_id}/{sensor_id}-{prop}/config",
                    {
                        "state_topic": state_topic,
                        "value_template": "{{ value_json.%s_%s }}" % (sensor_id, prop),
                        "state_class": "measurement",
                        "device": {
                            "identifiers": [f"{topic_prefix}-{device_id}"],
                            "manufacturer": "Wemos",
                            "model": "ESP32 S2 Mini",
                            "name": device_name,
                        },
                        "availability": [
                            {"topic": status_topic},
                            {"topic": get_status_topic(topic_prefix, "hub")},
                        ],
                        "availability_mode": "all",
                        "unique_id": f"{topic_prefix}-{device_id}-{sensor_id}-{prop}",
                        "name": f"{sensor_id} {prop}",
                        "unit_of_measurement": _UNITS[prop],
                        "device_class": prop,
                        "icon": _ICONS[prop],
                    },
                    retain=True,
                    keep_trying=True,
                    encode=True,
                )
                _SENT_DISCOVERIES.add((sensor_id, prop))
            state[f"{sensor_id}_{prop}"] = datum
    client.publish(status_topic, b"online", retain=True)
    client.publish(state_topic, state, encode=True)
    client.publish(status_topic, b"offline", retain=True)
