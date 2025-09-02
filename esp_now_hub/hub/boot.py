import json

import espnow
import mqtt
import ubinascii
import wifi

# Load config.
with open("config.json", "r") as f:
    config = json.loads(f.read())


topic_prefix = config["topic_prefix"]
with wifi.WLan(**config["wifi"]):
    with mqtt.MQTTClient(topic_prefix, **config["mqtt"]) as mqtt_client:
        e = espnow.ESPNow()
        e.active(True)
        e.set_pmk(config["primary_master_key"])
        for device in config["devices"]:
            e.add_peer(
                ubinascii.unhexlify(device["address"].replace(":", "").encode("utf-8")),
                lmk=device["local_master_key"],
            )
        print("waiting for messages...")
        for address, payload in e:
            mqtt.send(
                mqtt_client,
                topic_prefix,
                address.hex(),
                json.loads(payload.decode("utf-8")),
            )
