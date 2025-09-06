import json

import espnow
import mqtt
import ubinascii
import wifi
from config import CONFIG


def run():
    topic_prefix = CONFIG["topic_prefix"]
    with wifi.WLan(**CONFIG["wifi"]):
        with mqtt.MQTTClient(topic_prefix, **CONFIG["mqtt"]) as mqtt_client:
            e = espnow.ESPNow()
            e.active(True)
            if CONFIG.get("primary_master_key"):
                e.set_pmk(CONFIG["primary_master_key"])
            name_by_address = {}
            for device in CONFIG["devices"]:
                address = ubinascii.unhexlify(
                    device["address"].replace(":", "").encode("utf-8")
                )
                if device.get("local_master_key"):
                    e.add_peer(address, lmk=device["local_master_key"])
                name_by_address[address] = device["name"]
            print("waiting for messages...")
            for address, payload in e:
                name = name_by_address.get(address)
                if not name:
                    continue
                mqtt.send(
                    mqtt_client,
                    topic_prefix,
                    address.hex(),
                    name,
                    json.loads(payload.decode("utf-8")),
                )


run()
