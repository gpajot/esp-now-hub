#!/bin/bash
set -o errexit

mkdir flash

python -m mpy-cross -o flash/config.mpy config.py
if grep -q 'AHT20' config.py; then
  python -m mpy-cross -o flash/aht20.mpy esp_now_hub/sensors/aht20.py
fi
if grep -q 'BMP280' config.py; then
  python -m mpy-cross -o flash/bmp280.mpy esp_now_hub/sensors/bmp280.py
fi
if grep -q 'MS5540C' config.py; then
  python -m mpy-cross -o flash/ms5540c.mpy esp_now_hub/sensors/ms5540c.py
fi
if test "$1" = 'hub'; then
  echo "setting up hub"
  python -m mpy-cross -o flash/wifi.mpy esp_now_hub/hub/wifi.py
  mkdir flash/umqtt
  python -m mpy-cross -o flash/umqtt/simple.mpy esp_now_hub/hub/umqtt/simple.py
  python -m mpy-cross -o flash/mqtt.mpy esp_now_hub/hub/mqtt.py
  python -m mpy-cross -o flash/boot.mpy esp_now_hub/hub/boot.py
elif test "$1" = 'test'; then
  echo "setting up sensor in test mode"
  python -m mpy-cross -o flash/boot.mpy esp_now_hub/sensors/boot_test.py
else
  echo "setting up sensor"
  python -m mpy-cross -o flash/boot.mpy esp_now_hub/sensors/boot.py
fi

echo "Preparing to flash device, connect and put it in boot mode."
echo "Press any key to continue..."
read -r
python -m esptool write-flash --erase-all 0x1000 "$2"
python -m rshell cp -r flash... .

rm -rf flash
