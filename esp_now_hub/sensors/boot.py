import json
import time

import espnow
import machine
import network
import ubinascii

initialize = machine.reset_cause() == machine.PWRON_RESET

# Load config.
with open("config.json", "r") as f:
    config = json.loads(f.read())
deepsleep = config.get("deepsleep")


# Create sensors.
data_getters = {}
for cfg in config["sensors"]:
    sensor_id = cfg.pop("id")
    sensor_type = cfg.pop("type")
    if sensor_type == "MS5540C":
        from .ms5540c import MS5540C

        data_getters[sensor_id] = MS5540C(
            calibration_cache_prefix=sensor_id,
            **cfg
        ).get_measure  # fmt: skip
    elif sensor_type == "BMP280":
        from .bmp280 import BMP280

        data_getters[sensor_id] = BMP280(
            initialize=initialize,
            calibration_cache_prefix=sensor_id,
            **cfg
        ).get_measure  # fmt: skip
    elif sensor_type == "AHT20":
        from .aht20 import AHT20

        data_getters[sensor_id] = AHT20(initialize=initialize, **cfg).get_measure

# Send data.
wlan = network.WLAN(network.WLAN.IF_STA)
wlan.active(True)
wlan.config(channel=config["wifi_channel"])
try:
    e = espnow.ESPNow()
    e.set_pmk(config["primary_master_key"])
    e.active(True)
    try:
        hub_address = ubinascii.unhexlify(
            config["hub_address"].replace(":", "").encode("utf-8")
        )
        e.add_peer(hub_address, lmk=config["local_master_key"])
        while True:
            e.send(
                hub_address,
                json.dumps(
                    {sensor_id: getter() for sensor_id, getter in data_getters.items()}
                ),
            )
            if deepsleep:
                break
            else:
                time.sleep(config["interval"])
    finally:
        e.active(False)
finally:
    wlan.active(False)

if deepsleep:
    machine.deepsleep(config["interval"] * 1000)
