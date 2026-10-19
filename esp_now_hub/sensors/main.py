import binascii
import json
import time

import espnow
import machine
import network
from config import CONFIG  # ty: ignore[unresolved-import]
from setup import setup_sensors  # ty: ignore[unresolved-import]
from value_cache import (  # ty: ignore[unresolved-import]
    process_sensor_data,
    store_sensor_data,
)

_first_run = machine.reset_cause() != machine.DEEPSLEEP_RESET


def run() -> None:
    global _first_run
    data_getters, send_configs = setup_sensors(
        CONFIG,
        initialize=_first_run,
    )

    wlan = network.WLAN(network.WLAN.IF_STA)
    wlan.active(True)
    wlan.config(channel=CONFIG["wifi_channel"])
    try:
        e = espnow.ESPNow()
        e.active(False)
        e.active(True)
        if CONFIG.get("primary_master_key"):
            e.set_pmk(CONFIG["primary_master_key"])
        try:
            hub_address = binascii.unhexlify(
                CONFIG["hub_address"].replace(":", "").encode("utf-8")
            )
            e.add_peer(hub_address, lmk=CONFIG.get("local_master_key"))
            while True:
                data = {}
                for sensor_id, getter in data_getters.items():
                    sensor_data = process_sensor_data(
                        sensor_id,
                        getter(),
                        send_configs[sensor_id],
                        ignore_stored_value=_first_run,
                    )
                    if sensor_data:
                        data[sensor_id] = sensor_data
                if e.send(hub_address, json.dumps(data)):
                    for sensor_id, sensor_data in data.items():
                        store_sensor_data(
                            sensor_id, sensor_data, send_configs[sensor_id]
                        )
                if CONFIG.get("deepsleep"):
                    break
                else:
                    _first_run = False
                    time.sleep(CONFIG["interval"])
        finally:
            e.active(False)
    finally:
        wlan.active(False)

    machine.deepsleep(int(CONFIG["interval"] * 1000))


while True:
    try:
        run()
    except Exception as exc:
        print("error running sensor:", exc)
        # Wait for an interval.
        time.sleep(CONFIG["interval"])
        machine.reset()
