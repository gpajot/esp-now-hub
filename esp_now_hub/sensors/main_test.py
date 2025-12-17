import sys
import time

from config import CONFIG  # ty: ignore[unresolved-import]
from setup import setup_sensors  # ty: ignore[unresolved-import]
from value_cache import (  # ty: ignore[unresolved-import]
    process_sensor_data,
    store_sensor_data,
)


def run():
    data_getters, send_configs = setup_sensors(CONFIG, initialize=True)
    while True:
        for sensor_id, getter in data_getters.items():
            sensor_data = process_sensor_data(
                sensor_id, getter(), send_configs[sensor_id]
            )
            print(sensor_id, sensor_data)
            store_sensor_data(sensor_id, sensor_data, send_configs[sensor_id])
        time.sleep(CONFIG["interval"])


while True:
    try:
        run()
    except Exception as exc:
        print("error running sensor:")
        sys.print_exception(exc)  # ty: ignore[unresolved-attribute]
        # Wait for a 10th of an interval.
        time.sleep(CONFIG["interval"] / 10)
