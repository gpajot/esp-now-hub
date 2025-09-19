from typing import Collection, NotRequired, TypedDict


class Wifi(TypedDict):
    ssid: str
    password: str
    ifconfig: NotRequired[tuple[str, str, str, str]]


class MQTT(TypedDict):
    server: str
    port: NotRequired[int]
    user: NotRequired[str]
    password: NotRequired[str]


class Device(TypedDict):
    address: str
    local_master_key: NotRequired[str]
    manufacturer: NotRequired[str]
    model: NotRequired[str]
    name: str
    keepalive: int
    # sensor_id -> properties.
    components: dict[str, Collection[str]]


class Config(TypedDict):
    topic_prefix: str
    primary_master_key: NotRequired[str]
    interval: int
    wifi: Wifi
    mqtt: MQTT
    devices: Collection[Device]


CONFIG: Config
