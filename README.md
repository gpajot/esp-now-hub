# esp-now-hub

[![tests](https://github.com/gpajot/esp-now-hub/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/esp-now-hub/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)

ESP-NOW proxy to gather data collected by sensors and send them to MQTT.

## Setup
1. Run `uv sync`
2. Copy [umqtt.simple](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py) into `esp_now_hub/hub/umqtt/simple.py`.

## Flash a device
A device is either a sensor or the hub. A test mode is available to display real time sensor data.

1. Set up `config.py` (see below for structure) in root project folder.
2.
   - Run `python -m esptool write-flash --erase-all 0x1000 PATH_TO_MICROPYTHON_FIRMWARE_BINARY` to flash the device
   - Run `./deploy.bash hub|sensor|test` to flash the device

> [!NOTE]
> If using ESPNow encryption, generate keys with `openssl rand -hex 8`.
> Otherwise remove the properties in configurations.

> [!TIP]
> For test mode run `mpremote exec "import main"` to see sensor output.

### Hub config
```python
CONFIG = {
  "topic_prefix": "esp-now-hub",
  "primary_master_key": "...",
  "wifi": {
    "ssid":  "...",
    "password": "...",
  },
  "mqtt": {
    "server": "192.168.1.X",
    "port": 1883,
    "user": "...",
    "password": "...",
    "keepalive": 60,
  },
  "devices": [
    {
      "address": "00:00:00:00:00:00",
      "local_master_key": "...",
      "name": "Device",
    },
  ],
}
```
> [!NOTE]
> Remove MQTT `user` and `password` if not using them.

### Sensor config
```python
CONFIG = {
  "deepsleep": True,
  "interval": 300,
  "wifi_channel": 6,
  "hub_address": "00:00:00:00:00:00",
  "primary_master_key": "...",
  "local_master_key": "...",
  "sensors": [
    {
      "id": "...",
    },
  ],
}
```
> [!NOTE]
> Check test config to view sensor types and arguments to supply.

### Test config
```python
CONFIG = {
  "interval": 2,
  "sensors": [
    {
      "id": "...",
      "type": "MS5540C",
      "sclk": 36,
      "din": 35,
      "dout": 37,
      "mclk": 38,
    },
    {
      "id": "...",
      "type": "BMP280",
      "scl": 9,
      "sda": 8,
      "address": 0x77,
      "mode": "ultra-low-power",
    },
    {
      "id": "...",
      "type": "AHT20",
      "scl": 9,
      "sda": 8,
      "address": 0x38,
    },
    {
      "id": "...",
      "type": "MS5803",
      "scl": 9,
      "sda": 8,
      "address": 0x77,
      "pressure_resolution": 256,
      "temperature_resolution": 256,
    },
  ],
}
```


