import sys
from unittest.mock import Mock

import pytest

sys.modules["esp32"] = Mock()
sys.modules["espnow"] = Mock()
sys.modules["machine"] = Mock()
sys.modules["micropython"] = Mock()
sys.modules["time"] = Mock()
sys.modules["umqtt"] = Mock()
sys.modules["umqtt.simple"] = Mock()


@pytest.fixture
def nvs(mocker):
    nvs_ = mocker.Mock()
    mocker.patch.object(sys.modules["esp32"], "NVS", return_value=nvs_)
    return nvs_


@pytest.fixture(autouse=True)
def _const(mocker):
    mocker.patch.object(sys.modules["micropython"], "const", new=lambda e: e)


@pytest.fixture
def ticks_ms(mocker):
    return mocker.patch.object(sys.modules["time"], "ticks_ms")


@pytest.fixture(autouse=True)
def _ticks_diff(mocker):
    mocker.patch.object(sys.modules["time"], "ticks_diff", new=lambda a, b: a - b)
