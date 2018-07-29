import json
import logging

from cryptography.fernet import Fernet, InvalidToken

from config.cst import CONFIG_FILE, OCTOBOT_KEY


def load_config(config_file=CONFIG_FILE, error=True):
    logger = logging.getLogger("CONFIG LOADER")
    basic_error = "Error when load config file {0}".format(config_file)
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


def encrypt(data):
    try:
        return Fernet(OCTOBOT_KEY).encrypt(data.encode())
    except Exception as e:
        logging.getLogger().error(f"Failed to encrypt : {data}")
        raise e


def decrypt(data, silent_on_invalid_token=False):
    try:
        return Fernet(OCTOBOT_KEY).decrypt(data.encode()).decode()
    except InvalidToken as e:
        if not silent_on_invalid_token:
            logging.getLogger().error(f"Failed to decrypt : {data} ({e})")
        raise e
    except Exception as e:
        logging.getLogger().error(f"Failed to decrypt : {data} ({e})")
        raise e
