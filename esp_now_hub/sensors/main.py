import binascii
import json
import time

import espnow
import machine
import network
from config import CONFIG
from setup import setup_sensors


def run():
    data_getters = setup_sensors(
        CONFIG,
        initialize=machine.reset_cause() == machine.PWRON_RESET,
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
                e.send(
                    hub_address,
                    json.dumps(
                        {
                            sensor_id: getter()
                            for sensor_id, getter in data_getters.items()
                        }
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

    machine.deepsleep(int(CONFIG["interval"] * 1000))


while True:
    try:
        run()
    except Exception as exc:
        print("error running sensor:", exc)
        # Wait for a 10th of an interval.
        if CONFIG.get("deepsleep"):
            machine.deepsleep(int(CONFIG["interval"] * 1000 / 10))
        time.sleep(CONFIG["interval"] / 10)
