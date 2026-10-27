import sys
import time

try:
    from .config import CONFIG
    from .setup import setup_sensors
    from .value_cache import process_sensor_data, store_sensor_data
except ImportError:
    from config import CONFIG  # ty: ignore[unresolved-import]
    from setup import setup_sensors  # ty: ignore[unresolved-import]
    from value_cache import process_sensor_data, store_sensor_data  # ty: ignore[unresolved-import]


def run() -> None:
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
        # Wait for an interval.
        time.sleep(CONFIG["interval"])
