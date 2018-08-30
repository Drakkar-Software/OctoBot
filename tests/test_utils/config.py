from config.config import load_config
from config.cst import CONFIG_EVALUATOR, CONFIG_TRADING_TENTACLES, TimeFrames, CONFIG_TIME_FRAME


def init_config_time_frame_for_tests(config):
    result = []
    for time_frame in config[CONFIG_TIME_FRAME]:
        result.append(TimeFrames(time_frame))
    config[CONFIG_TIME_FRAME] = result


def load_test_config():
    config = load_config("tests/static/config.json")
    config[CONFIG_EVALUATOR] = load_config("tests/static/evaluator_config.json", False)
    config[CONFIG_TRADING_TENTACLES] = load_config("tests/static/trading_config.json", False)
    init_config_time_frame_for_tests(config)
    return config
