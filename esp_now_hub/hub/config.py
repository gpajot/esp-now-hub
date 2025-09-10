from typing import NotRequired, TypedDict


class Wifi(TypedDict):
    ssid: str
    password: str
    ifconfig: NotRequired[tuple[str, str, str, str]]


class MQTT(TypedDict):
    server: str
    port: NotRequired[int]
    user: NotRequired[str]
    password: NotRequired[str]
    keepalive: NotRequired[int]


class Device(TypedDict):
    address: str
    local_master_key: NotRequired[str]
    name: str


class Config(TypedDict):
    topic_prefix: str
    primary_master_key: NotRequired[str]
    wifi: Wifi
    mqtt: MQTT
    devices: list[Device]


CONFIG: Config
