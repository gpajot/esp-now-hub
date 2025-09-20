import time

import esp32


def process_sensor_data(sensor_id, data, send_configs):
    if not send_configs:
        return data
    nvs = esp32.NVS(sensor_id)
    data_to_send = {}
    for prop, value in data.items():
        send_config = send_configs.get(prop)
        if not send_config:
            data_to_send[prop] = value
            continue
        last_value, last_time = _get(nvs, prop)
        if (
            last_value is None
            or last_time is None
            or round(abs(value - last_value), 10) >= send_config["diff"]
            or time.ticks_diff(time.ticks_ms(), last_time) >= send_config["time"] * 1000  # type: ignore[attr-defined]
        ):
            _set(nvs, prop, value)
            data_to_send[prop] = value

    return data_to_send


def _get(nvs, prop):
    buf = bytearray()
    try:
        nvs.get_blob(prop, buf)
    except OSError:
        return None, None
    val, tm = buf.decode("utf-8").split(",")
    return float(val), int(tm)


def _set(nvs, prop, value):
    nvs.set_blob(prop, f"{value},{time.ticks_ms()}".encode("utf-8"))  # type: ignore[attr-defined]
    nvs.commit()
