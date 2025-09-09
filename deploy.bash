#!/bin/bash
set -o errexit

rm -rf data
mkdir data

if test "$1" = 'hub'; then
  echo "setting up hub..."
  mpy-cross -o data/wifi.mpy esp_now_hub/hub/wifi.py
  mkdir data/umqtt
  mpy-cross -o data/umqtt/simple.mpy esp_now_hub/hub/umqtt/simple.py
  mpy-cross -o data/mqtt.mpy esp_now_hub/hub/mqtt.py
  mpy-cross -o data/esp_now.mpy esp_now_hub/hub/esp_now.py
  mpy-cross -o data/main.mpy esp_now_hub/hub/main.py
  printf "import main\n" > data/boot.py
else
  if test "$1" = 'test'; then
    echo "setting up sensor in test mode..."
    mpy-cross -o data/main.mpy esp_now_hub/sensors/main_test.py
  else
    echo "setting up sensor..."
    mpy-cross -o data/main.mpy esp_now_hub/sensors/main.py
    printf "import main\n" > data/boot.py
  fi
  mpy-cross -o data/setup.mpy esp_now_hub/sensors/setup.py
  if grep -q 'AHT20' config.py; then
    mpy-cross -o data/aht20.mpy esp_now_hub/sensors/aht20.py
  fi
  if grep -q 'BMP280' config.py; then
    mpy-cross -o data/bmp280.mpy esp_now_hub/sensors/bmp280.py
  fi
  if grep -q 'MS5540C' config.py; then
    mpy-cross -o data/ms5540c.mpy esp_now_hub/sensors/ms5540c.py
  fi
  if grep -q 'MS5803' config.py; then
    mpy-cross -o data/ms5803.mpy esp_now_hub/sensors/ms5803.py
  fi
fi
mpy-cross -o data/config.mpy config.py

mpremote cp -r data/* :.

rm -rf data
