import select
from unittest.mock import call

import espnow
import pytest

from esp_now_hub.hub.esp_now import ESPNow


@pytest.fixture
def poll(mocker):
    return mocker.Mock()


@pytest.fixture
def esp_now(mocker):
    e = mocker.Mock()
    mocker.patch.object(espnow, "ESPNow", return_value=e)
    return e


@pytest.fixture
def devices():
    return (
        {
            "address": "00:00:00:00:00:01",
            "components": {"sensor1": {"pressure"}},
            "send_signal_strength_threshold": -80,
        },
        {
            "address": "00:00:00:00:00:02",
            "components": {"sensor2": {"temperature"}},
        },
    )


@pytest.fixture
def client(poll, esp_now, devices):
    return ESPNow(poll, devices)


def test_setup(poll, esp_now, client):
    with client:
        poll.register.assert_called_once_with(esp_now, select.POLLIN)
        assert esp_now.active.call_args == call(True)
        esp_now.active.reset_mock()
    poll.unregister.assert_called_once_with(esp_now)
    assert esp_now.active.call_args == call(False)


def test_receive(esp_now, client):
    address = b"\x00\x00\x00\x00\x00\x01"
    esp_now.recv.return_value = (
        address,
        b'{"sensor1":{"pressure":1.002,"temperature":10.2}}',
    )
    esp_now.peers_table = {address: [-90, 0]}

    with client:
        assert client.receive(select.POLLIN) == (
            "000000000001",
            {"sensor1_pressure": 1.002, "_signal": -90},
        )


def test_receive_empty(esp_now, client):
    address = b"\x00\x00\x00\x00\x00\x02"
    esp_now.recv.return_value = (
        address,
        b'{"sensor2":{"pressure":1.002}}',
    )
    esp_now.peers_table = {address: [-90, 0]}

    with client:
        assert client.receive(select.POLLIN) == ("000000000002", {})
