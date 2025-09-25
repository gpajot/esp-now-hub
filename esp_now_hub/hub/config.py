from typing import Collection, NotRequired, TypedDict


class Wifi(TypedDict):
    ssid: str
    password: str
    # ip, subnet, gateway, dns
    ifconfig: NotRequired[tuple[str, str, str, str]]


class MQTT(TypedDict):
    server: str
    port: NotRequired[int]
    user: NotRequired[str]
    password: NotRequired[str]


class Device(TypedDict):
    # Mac address, eg. 00:00:00:00:00:00
    address: str
    local_master_key: NotRequired[str]
    manufacturer: NotRequired[str]
    model: NotRequired[str]
    name: str
    # Device will be put offline if nothing received in 1.5 * keepalive period.
    keepalive: int
    # sensor_id -> included components (temperature, pressure, etc...).
    components: dict[str, Collection[str]]


class Config(TypedDict):
    topic_prefix: str
    primary_master_key: NotRequired[str]
    # The hub will ping MQTT every interval, so this will be the keepalive of the connection.
    interval: int
    wifi: Wifi
    mqtt: MQTT
    devices: Collection[Device]


CONFIG: Config
