from config.config import load_config
from config.cst import CONFIG_EVALUATOR, CONFIG_EVALUATOR_FILE


def load_test_config():
    config = load_config("tests/static/config.json")
    config[CONFIG_EVALUATOR] = load_config("tests/static/evaluator_config.json", False)
    return config
