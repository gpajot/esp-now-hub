import sys
from unittest.mock import Mock

import pytest

sys.modules["esp32"] = Mock()
sys.modules["espnow"] = Mock()
sys.modules["machine"] = Mock()
sys.modules["micropython"] = Mock()
sys.modules["micropython"].const = lambda e: e
sys.modules["umqtt"] = Mock()
sys.modules["umqtt.simple"] = Mock()


@pytest.fixture
def nvs(mocker):
    nvs_ = mocker.Mock()
    mocker.patch.object(sys.modules["esp32"], "NVS", return_value=nvs_)
    return nvs_


@pytest.fixture
def time_mock(mocker):
    return mocker.patch.object(sys.modules["time"], "time")
