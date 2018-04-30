import time

from config.cst import *


class Backtesting:
    def __init__(self, config):
        self.config = config
        self.begin_time = time.time()

    def end(self):
        # TODO : temp
        raise Exception("End of simulation in {0} sec".format(time.time() - self.begin_time))

    @staticmethod
    def enabled(config):
        return CONFIG_BACKTESTING in config and config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION]

    # uses symbol lists in exchanges in exchange_list to keep only symbols that have available data, removed others
    # from configuration to avoid useless computations
    @staticmethod
    def update_config_crypto_currencies(config, exchange_list):
        supported_symbols = [symbol for exchange in exchange_list for symbol in exchange.symbols]
        to_delete_crypto_currencies = []
        for crypto_currency, crypto_currency_data in config[CONFIG_CRYPTO_CURRENCIES].items():
            to_delete_symbol = []
            for symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]:
                if symbol not in supported_symbols:
                    to_delete_symbol.append(symbol)
            if len(to_delete_symbol) == len(crypto_currency_data[CONFIG_CRYPTO_PAIRS]):
                to_delete_crypto_currencies.append(crypto_currency)
            else:
                for symbol in to_delete_symbol:
                    config[CONFIG_CRYPTO_CURRENCIES][crypto_currency][CONFIG_CRYPTO_PAIRS].remove(symbol)
        for crypto_currency in to_delete_crypto_currencies:
            del config[CONFIG_CRYPTO_CURRENCIES][crypto_currency]
