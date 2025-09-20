from typing import Collection, NotRequired, TypedDict


class SendConfig(TypedDict):
    diff: float
    seconds: float


class Sensor(TypedDict):
    id: str
    type: str
    send_configs: NotRequired[dict[str, SendConfig]]


class Config(TypedDict):
    deepsleep: NotRequired[bool]
    interval: float
    wifi_channel: int
    hub_address: str
    primary_master_key: NotRequired[str]
    local_master_key: NotRequired[str]
    sensors: Collection[Sensor]


CONFIG: Config
