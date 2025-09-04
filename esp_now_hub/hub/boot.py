import json

import espnow
import mqtt
import ubinascii
import wifi
from config import CONFIG

topic_prefix = CONFIG["topic_prefix"]
with wifi.WLan(**CONFIG["wifi"]):
    with mqtt.MQTTClient(topic_prefix, **CONFIG["mqtt"]) as mqtt_client:
        e = espnow.ESPNow()
        e.active(True)
        if CONFIG.get("primary_master_key"):
            e.set_pmk(CONFIG["primary_master_key"])
        all_addresses = set()
        for device in CONFIG["devices"]:
            address = ubinascii.unhexlify(
                device["address"].replace(":", "").encode("utf-8")
            )
            if device.get("local_master_key"):
                e.add_peer(address, lmk=device["local_master_key"])
            all_addresses.add(address)
        print("waiting for messages...")
        for address, payload in e:
            if address not in all_addresses:
                continue
            mqtt.send(
                mqtt_client,
                topic_prefix,
                address.hex(),
                json.loads(payload.decode("utf-8")),
            )
