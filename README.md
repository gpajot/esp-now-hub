# esp-now-hub

[![tests](https://github.com/gpajot/esp-now-hub/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/gpajot/esp-now-hub/actions/workflows/test.yml?query=branch%3Amain+event%3Apush)

ESP-NOW proxy to gather data collected by sensors and send them to MQTT.

## Setup
`poetry install --with dev`

Copy [umqtt.simple](https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py) into `esp_now_hub/hub/umqtt/simple.py`.
