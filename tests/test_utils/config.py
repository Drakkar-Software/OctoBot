from config.config import load_config


def load_test_config():
    return load_config("tests/static/config.json")
