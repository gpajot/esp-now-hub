def setup_sensors(config, initialize):
    data_getters = {}
    send_configs = {}
    for cfg in config["sensors"]:
        sensor_id = cfg["id"]
        sensor_type = cfg["type"]
        send_configs[sensor_id] = cfg.get("send_configs") or {}
        kw = {k: v for k, v in cfg.items() if k not in {"id", "type", "send_configs"}}
        setup_func = __import__(sensor_type).setup
        data_getters[sensor_id] = setup_func(sensor_id, initialize, **kw)
    return data_getters, send_configs
