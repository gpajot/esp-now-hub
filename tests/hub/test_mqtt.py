import json
import select
from unittest.mock import call

import pytest
import umqtt.simple

from esp_now_hub.hub.config import Device
from esp_now_hub.hub.mqtt import MQTTClient


@pytest.fixture
def poll(mocker):
    return mocker.Mock()


@pytest.fixture
def mqtt_socket(mocker):
    return mocker.Mock()


@pytest.fixture
def mqtt_client(mocker, mqtt_socket):
    m = mocker.Mock()
    m.sock = mqtt_socket
    mocker.patch.object(umqtt.simple, "MQTTClient", return_value=m)
    return m


@pytest.fixture
def devices() -> list[Device]:
    return [
        {
            "address": "00:00:00:00:00:01",
            "name": "dev1",
            "keepalive": 5,
            "components": {"sensor1": ["pressure"]},
        },
        {
            "address": "00:00:00:00:00:02",
            "name": "dev2",
            "keepalive": 5,
            "components": {"sensor2": ["temperature"]},
        },
    ]


@pytest.fixture
def client(poll, mqtt_client, devices):
    return MQTTClient(lambda *_: None, poll, "topic", devices, 10, "host")


def test_setup(client, poll, mqtt_client, mqtt_socket):
    with client:
        poll.register.assert_called_once_with(mqtt_socket, select.POLLIN)
        # 2 dev statuses, 1 hub status
        assert mqtt_client.publish.call_count == 3
        mqtt_client.publish.reset_mock()
    poll.unregister.assert_called_once_with(mqtt_socket)
    assert mqtt_client.publish.call_count == 1


def test_receive(client, mqtt_client):
    with client:
        client.receive(select.POLLIN)
    mqtt_client.check_msg.assert_called_once()


def test_ping_wait(client, mqtt_client, time_mock):
    time_mock.return_value = 1000
    with client:
        time_mock.return_value = 1005
        assert client.ping() == 4


def test_ping_ping(client, mqtt_client, time_mock):
    time_mock.return_value = 1000
    with client:
        time_mock.return_value = 1011
        mqtt_client.ping.reset_mock()
        assert client.ping() == 9
        mqtt_client.ping.assert_called_once()


def test_ping_devices(client, mqtt_client, time_mock):
    time_mock.return_value = 1000
    with client:
        time_mock.return_value = 1008
        client._last_device_seen_times = {
            "000000000001": 1000,
        }
        mqtt_client.publish.reset_mock()
        assert client.ping() == 1
        assert mqtt_client.publish.call_args_list == [
            call(b"topic/status/000000000001", b"offline", retain=True),
        ]
    assert client._last_device_seen_times == {}


def test_send(client, mqtt_client, time_mock, mocker):
    mocker.patch("esp_now_hub.hub.mqtt._VERSION_INFO", new="version")
    time_mock.return_value = 1000
    with client:
        assert client._last_device_seen_times == {}
        mqtt_client.publish.reset_mock()
        client.send("000000000001", {"some": "data", "d": {"extra": "device property"}})
        assert mqtt_client.publish.call_args_list == [
            call(b"topic/status/000000000001", b"online", retain=True),
            call(
                b"topic/device/000000000001/config",
                json.dumps(
                    {
                        "device": {
                            "ids": "topic-000000000001",
                            "name": "dev1",
                            "extra": "device property",
                        },
                        "origin": {
                            "name": "esp-now-hub",
                            "sw": "version",
                            "url": "https://github.com/gpajot/esp-now-hub",
                        },
                        "availability": [
                            {"topic": "topic/status/hub"},
                            {"topic": "topic/status/000000000001"},
                        ],
                        "availability_mode": "all",
                        "state_topic": "topic/get/000000000001",
                        "components": {
                            "sensor1_pressure": {
                                "unique_id": "topic-000000000001-sensor1-pressure",
                                "platform": "sensor",
                                "device_class": "pressure",
                                "state_class": "measurement",
                                "unit_of_measurement": "bar",
                                "value_template": "{{ value_json.sensor1_pressure }}",
                                "name": "sensor1 pressure",
                                "icon": "mdi:speedometer",
                            }
                        },
                    }
                ).encode(),
                retain=True,
            ),
            call(b"topic/get/000000000001", b'{"some": "data"}', retain=False),
        ]
        assert client._last_device_seen_times == {"000000000001": 1000}

        # Send again, should only send the data.
        mqtt_client.publish.reset_mock()
        client.send("000000000001", {"some": "data", "d": {"extra": "device property"}})
        assert mqtt_client.publish.call_args_list == [
            call(b"topic/get/000000000001", b'{"some": "data"}', retain=False),
        ]
        assert client._last_device_seen_times == {"000000000001": 1000}
