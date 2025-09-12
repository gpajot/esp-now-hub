def setup_sensors(config, initialize):
    data_getters = {}
    excluded_components_by_id = {}
    for cfg in config["sensors"]:
        sensor_id = cfg.pop("id")
        sensor_type = cfg.pop("type")
        excluded_components_by_id[sensor_id] = (
            cfg.pop("excluded_components", None) or set()
        )
        if sensor_type == "MS5540C":
            from ms5540c import MS5540C

            data_getters[sensor_id] = MS5540C(
                calibration_cache_prefix=sensor_id,
                **cfg
            ).get_measure  # fmt: skip
        elif sensor_type == "BMP280":
            from bmp280 import BMP280

            data_getters[sensor_id] = BMP280(
                initialize=initialize,
                calibration_cache_prefix=sensor_id,
                **cfg
            ).get_measure  # fmt: skip
        elif sensor_type == "AHT20":
            from aht20 import AHT20

            data_getters[sensor_id] = AHT20(initialize=initialize, **cfg).get_measure
        elif sensor_type == "MS5803":
            from ms5803 import MS5803

            data_getters[sensor_id] = MS5803(
                initialize=initialize,
                calibration_cache_prefix=sensor_id,
                **cfg
            ).get_measure  # fmt: skip
    return data_getters, excluded_components_by_id
