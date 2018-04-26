from config.cst import CONFIG_ENABLED_OPTION, CONFIG_DATA_COLLECTOR


class DataCollector:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def enabled(config):
        return CONFIG_DATA_COLLECTOR in config and config[CONFIG_DATA_COLLECTOR][CONFIG_ENABLED_OPTION]