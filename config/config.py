import json

from config.cst import CONFIG_FILE


def load_config(config_file=CONFIG_FILE, error=True):
    try:
        with open(config_file) as json_data_file:
            config = json.load(json_data_file)
        return config
    except Exception:
        if error:
            raise Exception("Error when load config")
        else:
            return None
