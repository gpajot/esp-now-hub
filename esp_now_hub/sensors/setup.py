def setup_sensors(config, initialize):
    data_getters = {}
    send_configs = {}
    for cfg in config["sensors"]:
        sensor_id = cfg["id"]
        sensor_type = cfg["type"]
        send_configs[sensor_id] = cfg.get("send_config") or {}
        kw = {k: v for k, v in cfg.items() if k not in {"id", "type", "send_config"}}
        if sensor_type == "MS5540C":
            from ms5540c import MS5540C

            data_getters[sensor_id] = MS5540C(
                calibration_cache_namespace=sensor_id,
                **kw
            ).get_measure  # fmt: skip
        elif sensor_type == "BMP280":
            from bmp280 import BMP280

            data_getters[sensor_id] = BMP280(
                calibration_cache_namespace=sensor_id,
                initialize=initialize,
                **kw
            ).get_measure  # fmt: skip
        elif sensor_type == "AHT20":
            from aht20 import AHT20

            data_getters[sensor_id] = AHT20(initialize=initialize, **kw).get_measure
        elif sensor_type == "MS5803":
            from ms5803 import MS5803

            data_getters[sensor_id] = MS5803(
                calibration_cache_namespace=sensor_id,
                **kw
            ).get_measure  # fmt: skip
    return data_getters, send_configs
