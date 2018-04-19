import json

from config.cst import CONFIG_FILE


def load_config(config_file=CONFIG_FILE):
    try:
        with open(config_file) as json_data_file:
            config = json.load(json_data_file)
        return config
    except Exception:
        raise Exception("Error when load config")
