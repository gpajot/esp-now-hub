import select
import sys
import time

import machine

try:
    from . import esp_now, mqtt, wifi
    from .config import CONFIG
except ImportError:
    import esp_now  # ty: ignore[unresolved-import]
    import mqtt  # ty: ignore[unresolved-import]
    import wifi  # ty: ignore[unresolved-import]
    from config import CONFIG  # ty: ignore[unresolved-import]

_log_to_file = CONFIG.get("debug_to")
_log_to_stdout = _log_to_file == "stdout"


def _debug(source: str, msg: str, exc_info: Exception | None = None) -> None:
    if _log_to_stdout:
        print(time.time(), source, msg)
        if exc_info:
            sys.print_exception(exc_info)  # ty: ignore[unresolved-attribute]
    elif _log_to_file:
        with open(_log_to_file, "a") as f:
            f.write(f"{time.time()} - {source}: {msg}\n")
            if exc_info:
                f.write(f"{type(exc_info)}: {exc_info}\n")


def _get_debug(source: str):
    def _d(msg: str, exc_info: Exception | None = None) -> None:
        _debug(source, msg, exc_info)

    return _d


def run() -> None:
    _debug("main", "starting...")
    interval = CONFIG["interval"]
    poll = select.poll()
    with wifi.WLan(_get_debug("wifi"), **CONFIG["wifi"]):
        with mqtt.MQTTClient(
            _get_debug("mqtt"),
            poll,
            CONFIG["topic_prefix"],
            CONFIG["devices"],
            interval,
            **CONFIG["mqtt"]
        ) as mqtt_client:  # fmt: skip
            with esp_now.ESPNow(
                _get_debug("esp-now"),
                poll,
                CONFIG["devices"],
                CONFIG.get("primary_master_key"),
            ) as esp_now_client:
                _debug("main", "waiting for messages...")
                next_ping = mqtt_client.ping()
                while True:
                    for event in poll.poll(int(next_ping * 1000)):
                        if mqtt_client.wants(event[0]):
                            mqtt_client.receive(event[1])
                        elif esp_now_client.wants(event[0]):
                            device_id, data = esp_now_client.receive(event[1])
                            if device_id and data is not None:
                                mqtt_client.send(device_id, data)
                        else:
                            raise RuntimeError(f"unknown poll event {event}")
                    next_ping = mqtt_client.ping()


while True:
    try:
        run()
    except Exception as exc:
        _debug("main", "error running hub:", exc)
        # Wait for a quarter of interval.
        time.sleep(CONFIG["interval"] / 4)
        _debug("main", "resetting...")
        machine.reset()
