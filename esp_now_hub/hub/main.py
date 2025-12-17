import select
import sys
import time

import esp_now  # ty: ignore[unresolved-import]
import mqtt  # ty: ignore[unresolved-import]
import wifi  # ty: ignore[unresolved-import]
from config import CONFIG  # ty: ignore[unresolved-import]


def run():
    interval = CONFIG["interval"]
    poll = select.poll()
    with wifi.WLan(**CONFIG["wifi"]):
        with mqtt.MQTTClient(
            poll,
            CONFIG["topic_prefix"],
            CONFIG["devices"],
            interval,
            **CONFIG["mqtt"]
        ) as mqtt_client:  # fmt: skip
            with esp_now.ESPNow(
                poll,
                CONFIG["devices"],
                CONFIG.get("primary_master_key"),
            ) as esp_now_client:
                print("waiting for messages...")
                next_ping = interval * 1000
                while True:
                    for event in poll.poll(next_ping):
                        if mqtt_client.wants(event[0]):
                            mqtt_client.receive(event[1])
                        elif esp_now_client.wants(event[0]):
                            device_id, data = esp_now_client.receive(event[1])
                            if device_id and data is not None:
                                mqtt_client.send(device_id, data)
                        else:
                            raise RuntimeError(f"unknown poll event {event}")
                    next_ping = mqtt_client.ping()


while True:
    try:
        run()
    except Exception as exc:
        print("error running hub:")
        sys.print_exception(exc)  # ty: ignore[unresolved-attribute]
        time.sleep(CONFIG["interval"] / 10)
