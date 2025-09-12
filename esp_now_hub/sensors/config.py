from typing import Collection, NotRequired, TypedDict


class Sensor(TypedDict):
    id: str
    type: str
    excluded_components: NotRequired[Collection[str]]


class Config(TypedDict):
    deepsleep: NotRequired[bool]
    interval: float
    wifi_channel: int
    hub_address: str
    primary_master_key: NotRequired[str]
    local_master_key: NotRequired[str]
    sensors: Collection[Sensor]


CONFIG: Config
