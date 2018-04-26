from config.cst import CONFIG_BACKTESTING, CONFIG_ENABLED_OPTION


class Backtesting:
    @staticmethod
    def enabled(config):
        return CONFIG_BACKTESTING in config and config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION]
