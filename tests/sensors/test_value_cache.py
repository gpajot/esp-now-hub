import sys
from unittest.mock import Mock

import pytest

sys.modules["time"] = Mock()
sys.modules["esp32"] = Mock()
from esp_now_hub.sensors.value_cache import (  # noqa: E402
    _get,
    _set,
    process_sensor_data,
    store_sensor_data,
)


def test_get_not_found(mocker):
    nvs_ = mocker.Mock()
    nvs_.get_blob.side_effect = OSError
    assert _get(nvs_, "prop") == (None, None)


def test_get(mocker):
    nvs_ = mocker.Mock()

    def _get_blob(_, buf):
        buf += bytearray(b"21.2,3000")

    nvs_.get_blob = _get_blob
    assert _get(nvs_, "prop") == (21.2, 3000)


def test_set(mocker):
    nvs_ = mocker.Mock()
    mocker.patch.object(sys.modules["time"], "ticks_ms", return_value=3000)
    _set(nvs_, "prop", 21.2)
    nvs_.set_blob.assert_called_once_with("prop", b"21.2,3000")
    nvs_.commit.assert_called_once()


@pytest.fixture
def nvs_get(mocker):
    return mocker.patch("esp_now_hub.sensors.value_cache._get")


@pytest.fixture
def ticks_ms(mocker):
    return mocker.patch.object(sys.modules["time"], "ticks_ms")


@pytest.fixture
def _ticks_diff(mocker):
    mocker.patch.object(sys.modules["time"], "ticks_diff", new=lambda a, b: a - b)


def test_process_sensor_no_config():
    assert process_sensor_data("id", {"temp": 21.2}, {}) == {"temp": 21.2}


def test_process_sensor_data_no_cache(nvs_get):
    nvs_get.return_value = (None, None)
    assert process_sensor_data(
        "id",
        {"temp": 21.2},
        {"temp": {"diff": 0.2, "time": 5}},
    ) == {"temp": 21.2}


@pytest.mark.usefixtures("_ticks_diff")
def test_process_sensor_data_should_not_send(nvs_get, ticks_ms):
    nvs_get.return_value = (21.2, 3000)
    ticks_ms.return_value = 6000
    assert (
        process_sensor_data(
            "id",
            {"temp": 21.3},
            {"temp": {"diff": 0.2, "time": 5}},
        )
        == {}
    )


@pytest.mark.usefixtures("_ticks_diff")
def test_process_sensor_data_send_for_diff(nvs_get, ticks_ms):
    nvs_get.return_value = (21.2, 3000)
    ticks_ms.return_value = 6000
    assert process_sensor_data(
        "id",
        {"temp": 21.4},
        {"temp": {"diff": 0.2, "time": 5}},
    ) == {"temp": 21.4}


@pytest.mark.usefixtures("_ticks_diff")
def test_process_sensor_data_send_for_time(nvs_get, ticks_ms):
    nvs_get.return_value = (21.2, 3000)
    ticks_ms.return_value = 10000
    assert process_sensor_data(
        "id",
        {"temp": 21.3},
        {"temp": {"diff": 0.2, "time": 5}},
    ) == {"temp": 21.3}


@pytest.fixture
def nvs(mocker):
    nvs_ = mocker.Mock()
    mocker.patch.object(sys.modules["esp32"], "NVS", return_value=nvs_)
    return nvs_


@pytest.fixture
def nvs_set(mocker):
    return mocker.patch("esp_now_hub.sensors.value_cache._set")


def test_store_sensor_data(nvs, nvs_set):
    store_sensor_data(
        "id",
        {"temp": 21.3, "no_config": 10},
        {"temp": 1, "not_sent": 1},
    )
    nvs_set.assert_called_once_with(nvs, "temp", 21.3)
