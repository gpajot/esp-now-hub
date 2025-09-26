# esp-now-hub

[![tests](https://github.com/gpajot/esp-now-hub/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/esp-now-hub/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)

ESP-NOW proxy to gather data collected by sensors and send them to MQTT.

Compatible with [MQTT Discovery](https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery).

I had a lot of WI-FI connection issues coming out of deepsleep, hence this project.
The sensor devices will send data through ESP-Now to the hub, which will act as a proxy to MQTT.
One of the advantages is that [it consumes much less energy than connecting to WI-FI](https://github.com/glenn20/upy-esp32-experiments), making it better for battery operated devices.

## Setup
1. Run `uv sync`
2. Copy [umqtt.simple](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py) into `esp_now_hub/hub/umqtt/simple.py`.

## Flash a device
A device is either a sensor or the hub. A test mode is available to display real time sensor data.

1. Set up `config.py` (see below for structure) in root project folder.
2. Flash the device with micropython firmware: `python -m esptool write-flash --erase-all 0x1000 $FIRMWARE_PATH`. 
3. Deploy the code to the device: `./deploy.bash hub|sensor|test`. 

> [!NOTE]
> If using ESPNow encryption, generate keys with `openssl rand -hex 8`.
> Otherwise remove the properties in configurations.

> [!TIP]
> For test mode run `mpremote exec "import main"` to see sensor output.

### Hub config

See [configuration definition](esp_now_hub/hub/config.py).

### Sensor config

See [configuration definition](esp_now_hub/sensors/config.py).

> [!NOTE]
> Check below to view sensor types and arguments to supply.

### Test config

Keep only the sensors used on the device to test.

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
      "address": 0x76,
      "pressure_resolution": 1024,
      "temperature_resolution": 256,
    },
  ],
}
```


