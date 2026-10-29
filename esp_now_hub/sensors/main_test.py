import os
import sys
import time

try:
    from .config import CONFIG
    from .setup import setup_sensors
    from .value_cache import process_sensor_data, store_sensor_data
    from .version import VERSION
except ImportError:
    from config import CONFIG  # ty: ignore[unresolved-import]
    from setup import setup_sensors  # ty: ignore[unresolved-import]
    from value_cache import process_sensor_data, store_sensor_data  # ty: ignore[unresolved-import]
    from version import VERSION  # ty: ignore[unresolved-import]

_OS_STATS = os.uname()
_VERSION_INFO = f"{VERSION} ({_OS_STATS.release}) - {_OS_STATS.sysname}"


def run() -> None:
    print(_VERSION_INFO)
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
