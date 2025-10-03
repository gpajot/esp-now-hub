import select
from unittest.mock import call

import pytest
import umqtt.simple

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
def devices():
    return (
        {
            "address": "00:00:00:00:00:01",
            "keepalive": 5,
            "name": "dev1",
            "components": {"sensor1": {"pressure"}},
        },
        {
            "address": "00:00:00:00:00:02",
            "keepalive": 5,
            "name": "dev2",
            "components": {"sensor2": {"temperature"}},
        },
    )


@pytest.fixture
def client(poll, mqtt_client, devices):
    return MQTTClient(poll, "topic", devices, 10, "host")


def test_setup(client, poll, mqtt_client, mqtt_socket):
    with client:
        poll.register.assert_called_once_with(mqtt_socket, select.POLLIN)
        # 2 discovery, 2 dev statuses, 1 hub status
        assert mqtt_client.publish.call_count == 5
        mqtt_client.publish.reset_mock()
    poll.unregister.assert_called_once_with(mqtt_socket)
    assert mqtt_client.publish.call_count == 1


def test_receive(client, mqtt_client):
    with client:
        client.receive(select.POLLIN)
    mqtt_client.check_msg.assert_called_once()


def test_ping_wait(client, mqtt_client, ticks_ms):
    ticks_ms.return_value = 1000
    mqtt_client.keepalive = 10
    with client:
        ticks_ms.return_value = 2000
        assert client.ping() == 9000


def test_ping_reconnect(client, mqtt_client, ticks_ms):
    ticks_ms.return_value = 1000
    mqtt_client.keepalive = 10
    with client:
        ticks_ms.return_value = 12000
        mqtt_client.connect.reset_mock()
        mqtt_client.publish.reset_mock()
        assert client.ping() == 10000
        assert mqtt_client.publish.call_args_list == [
            call(b"topic/status/hub", b"online", retain=True),
        ]
    mqtt_client.connect.assert_called_once()


def test_ping_devices(client, mqtt_client, ticks_ms):
    ticks_ms.return_value = 1000
    mqtt_client.keepalive = 10
    with client:
        ticks_ms.return_value = 12000
        client._last_receive_ticks = {
            "000000000001": 1000,
        }
        mqtt_client.publish.reset_mock()
        assert client.ping() == 10000
        assert mqtt_client.publish.call_args_list == [
            call(b"topic/status/hub", b"online", retain=True),
            call(b"topic/status/000000000001", b"offline", retain=True),
        ]
    assert client._last_receive_ticks == {}


def test_send(client, mqtt_client, ticks_ms):
    ticks_ms.return_value = 1000
    with client:
        assert client._last_receive_ticks == {}
        mqtt_client.publish.reset_mock()
        client.send("000000000001", {"some": "data"})
        assert mqtt_client.publish.call_args_list == [
            call(b"topic/status/000000000001", b"online", retain=True),
            call(b"topic/get/000000000001", b'{"some": "data"}', retain=False),
        ]
        assert client._last_receive_ticks == {"000000000001": 1000}
