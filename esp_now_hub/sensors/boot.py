import json
import time

import espnow
import machine
import network
import ubinascii
from config import CONFIG

initialize = machine.reset_cause() == machine.PWRON_RESET

# Create sensors.
data_getters = {}
for cfg in CONFIG["sensors"]:
    sensor_id = cfg.pop("id")
    sensor_type = cfg.pop("type")
    if sensor_type == "MS5540C":
        from ms5540c import MS5540C

        data_getters[sensor_id] = MS5540C(
            calibration_cache_prefix=sensor_id,
            **cfg
        ).get_measure  # fmt: skip
    elif sensor_type == "BMP280":
        from bmp280 import BMP280

        data_getters[sensor_id] = BMP280(
            initialize=initialize,
            calibration_cache_prefix=sensor_id,
            **cfg
        ).get_measure  # fmt: skip
    elif sensor_type == "AHT20":
        from aht20 import AHT20

        data_getters[sensor_id] = AHT20(initialize=initialize, **cfg).get_measure

# Send data.
wlan = network.WLAN(network.WLAN.IF_STA)
wlan.active(True)
wlan.config(channel=CONFIG["wifi_channel"])
try:
    e = espnow.ESPNow()
    e.active(True)
    if CONFIG.get("primary_master_key"):
        e.set_pmk(CONFIG["primary_master_key"])
    try:
        hub_address = ubinascii.unhexlify(
            CONFIG["hub_address"].replace(":", "").encode("utf-8")
        )
        e.add_peer(hub_address, lmk=CONFIG.get("local_master_key"))
        while True:
            e.send(
                hub_address,
                json.dumps(
                    {sensor_id: getter() for sensor_id, getter in data_getters.items()}
                ),
            )
            if CONFIG.get("deepsleep"):
                break
            else:
                time.sleep(CONFIG["interval"])
    finally:
        e.active(False)
finally:
    wlan.active(False)

if CONFIG.get("deepsleep"):
    machine.deepsleep(CONFIG["interval"] * 1000)
