from typing import Collection, NotRequired, TypedDict


class SendConfig(TypedDict):
    # Send if difference from current and last sent is greater or equal to this value.
    diff: float
    # Send if not sent since this number of seconds.
    seconds: float


class Sensor(TypedDict):
    id: str
    type: str
    # Key is component (temperature, etc..)
    send_configs: NotRequired[dict[str, SendConfig]]
    # Sensor kwargs should go here.


class Config(TypedDict):
    deepsleep: NotRequired[bool]
    # Get a measure every interval.
    interval: float
    # This should be the WI-FI channel of the access point the hub is connected to.
    wifi_channel: int
    # Mac address of the hub, eg. 00:00:00:00:00:00
    hub_address: str
    primary_master_key: NotRequired[str]
    local_master_key: NotRequired[str]
    sensors: Collection[Sensor]


CONFIG: Config
