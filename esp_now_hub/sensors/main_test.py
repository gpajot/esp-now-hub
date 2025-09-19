import sys
import time

from config import CONFIG
from setup import setup_sensors


def run():
    data_getters = setup_sensors(CONFIG, initialize=True)
    while True:
        for sensor_id, getter in data_getters.items():
            print(sensor_id, getter())
        time.sleep(CONFIG["interval"])


while True:
    try:
        run()
    except Exception as exc:
        print("error running sensor:")
        sys.print_exception(exc)  # type: ignore[attr-defined]
        # Wait for a 10th of an interval.
        time.sleep(CONFIG["interval"] / 10)
