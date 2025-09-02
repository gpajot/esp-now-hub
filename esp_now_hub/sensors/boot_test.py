import json
import time

# Load config.
with open("config.json", "r") as f:
    config = json.loads(f.read())

# Create sensors.
data_getters = {}
for cfg in config["sensors"]:
    sensor_id = cfg.pop("id")
    sensor_type = cfg.pop("type")
    if sensor_type == "MS5540C":
        from .ms5540c import MS5540C

        data_getters[sensor_id] = MS5540C(
            calibration_cache_prefix=sensor_id,
            **cfg
        ).get_measure  # fmt: skip
    elif sensor_type == "BMP280":
        from .bmp280 import BMP280

        data_getters[sensor_id] = BMP280(
            initialize=True,
            calibration_cache_prefix=sensor_id,
            **cfg
        ).get_measure  # fmt: skip
    elif sensor_type == "AHT20":
        from .aht20 import AHT20

        data_getters[sensor_id] = AHT20(initialize=True, **cfg).get_measure

# Show data.
while True:
    for sensor_id, getter in data_getters:
        print(sensor_id, getter())
    time.sleep(config["interval"])
