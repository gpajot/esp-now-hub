import time

import esp32


def process_sensor_data(
    sensor_id: str,
    data: dict[str, float],
    send_configs: dict[str, dict[str, float]],
    *,
    ignore_stored_value: bool = False,
) -> dict[str, float]:
    if not send_configs:
        return data
    nvs = esp32.NVS(sensor_id)
    data_to_send = {}
    for prop, value in data.items():
        send_config = send_configs.get(prop)
        if not send_config or ignore_stored_value:
            data_to_send[prop] = value
            continue
        last_value, last_time = _get(nvs, prop)
        if (
            last_value is None
            or last_time is None
            or round(abs(value - last_value), 10) >= send_config["diff"]
            or time.time() < last_time
            or time.time() - last_time >= send_config["time"]
        ):
            data_to_send[prop] = value

    return data_to_send


def store_sensor_data(sensor_id: str, data: dict[str, float], send_configs) -> None:
    if not send_configs:
        return
    nvs = esp32.NVS(sensor_id)
    for prop, value in data.items():
        send_config = send_configs.get(prop)
        if not send_config:
            continue
        _set(nvs, prop, value)


def _get(nvs: esp32.NVS, prop: str) -> tuple[float | None, int | None]:
    buf = bytearray(100)
    try:
        nvs.get_blob(prop, buf)
    except OSError:
        return None, None
    val, tm = buf.replace(b"\x00", b"").decode("utf-8").split(",")
    return float(val), int(tm)


def _set(nvs: esp32.NVS, prop: str, value: float) -> None:
    nvs.set_blob(prop, f"{value},{time.time()}".encode())
    nvs.commit()
