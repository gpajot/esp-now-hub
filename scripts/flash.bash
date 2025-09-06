#!/bin/bash
set -o errexit

rm -rf flash
mkdir flash

if test "$1" = 'hub'; then
  echo "setting up hub..."
  mpy-cross -o flash/wifi.mpy esp_now_hub/hub/wifi.py
  mkdir flash/umqtt
  mpy-cross -o flash/umqtt/simple.mpy esp_now_hub/hub/umqtt/simple.py
  mpy-cross -o flash/mqtt.mpy esp_now_hub/hub/mqtt.py
  mpy-cross -o flash/main.mpy esp_now_hub/hub/main.py
else
  if test "$1" = 'test'; then
    echo "setting up sensor in test mode..."
    mpy-cross -o flash/main.mpy esp_now_hub/sensors/main_test.py
  else
    echo "setting up sensor..."
    mpy-cross -o flash/main.mpy esp_now_hub/sensors/main.py
  fi
  mpy-cross -o flash/setup.mpy esp_now_hub/sensors/setup.py
  if grep -q 'AHT20' config.py; then
    mpy-cross -o flash/aht20.mpy esp_now_hub/sensors/aht20.py
  fi
  if grep -q 'BMP280' config.py; then
    mpy-cross -o flash/bmp280.mpy esp_now_hub/sensors/bmp280.py
  fi
  if grep -q 'MS5540C' config.py; then
    mpy-cross -o flash/ms5540c.mpy esp_now_hub/sensors/ms5540c.py
  fi
fi
mpy-cross -o flash/config.mpy config.py

echo "Preparing to flash device, connect and put it in boot mode."
echo "Press any key to continue..."
read -r
python -m esptool write-flash --erase-all 0x1000 "$2"
sleep 1
mpremote cp -r flash/* :.
rm -rf flash

if test "$1" = 'test'; then
  mpremote exec "import main"
fi
