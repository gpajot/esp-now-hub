import esp_now
import machine
import mqtt
import wifi
from config import CONFIG


def run():
    topic_prefix = CONFIG["topic_prefix"]
    with wifi.WLan(**CONFIG["wifi"]):
        with mqtt.MQTTClient(topic_prefix, **CONFIG["mqtt"]) as mqtt_client:
            with esp_now.ESPNow(
                CONFIG["devices"], CONFIG.get("primary_master_key")
            ) as esp_now_client:
                print("waiting for messages...")
                while True:
                    mqtt_client.ping()
                    message = esp_now_client.receive(
                        int(mqtt_client.ping_interval * 1000)
                    )
                    if not message:
                        continue
                    mqtt.send(mqtt_client, topic_prefix, *message)


try:
    run()
except Exception as e:
    print("error running hub:", e)
    machine.reset()
