import json
import logging

from config.cst import CONFIG_FILE


def load_config(config_file=CONFIG_FILE, error=True):
    logger = logging.getLogger("CONFIG LOADER")
    basic_error = "Error when load config"
    try:
        with open(config_file) as json_data_file:
            config = json.load(json_data_file)
        return config
    except ValueError as e:
        error_str = "{0} : json decoding failed ({1})".format(basic_error, e)
        if error:
            raise Exception(error_str)
        else:
            logger.error(error_str)

    except IOError as e:
        error_str = "{0} : file opening failed ({1})".format(basic_error, e)
        if error:
            raise Exception(error_str)
        else:
            logger.error(error_str)
    except Exception as e:
        error_str = "{0} : {1}".format(basic_error, e)
        if error:
            raise Exception(error_str)
        else:
            logger.error(error_str)
    return None
