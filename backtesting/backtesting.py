import logging
import os
import time

from backtesting import get_bot
from config.cst import *


class Backtesting:
    def __init__(self, config, exchange_simulator, exit_at_end=True):
        self.config = config
        self.begin_time = time.time()
        self.time_delta = 0
        self.force_exit_at_end = exit_at_end
        self.exchange_simulator = exchange_simulator
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ended_symbols = set()
        self.symbols_to_test = set()
        self.init_symbols_to_test()

    def end(self, symbol):
        self.ended_symbols.add(symbol)
        if len(self.ended_symbols) == len(self.symbols_to_test):

            for symbol in self.exchange_simulator.get_symbols():
                self.report(symbol)

            backtesting_time = time.time() - self.begin_time
            self.logger.info("Simulation lasted {0} sec".format(backtesting_time))
            if self.force_exit_at_end:
                os._exit(0)

    def report(self, symbol):
        market_data = self.exchange_simulator.get_data()[symbol][self.exchange_simulator.MIN_ENABLED_TIME_FRAME.value]

        self.time_delta = self.begin_time - market_data[0][PriceIndexes.IND_PRICE_TIME.value] / 1000

        # profitability
        total_profitability = 0
        for trader in get_bot().get_exchange_trader_simulators().values():
            _, profitability, _, _ = trader.get_trades_manager().get_profitability()
            total_profitability += profitability

        # vs market
        market_delta = self.get_market_delta(market_data)

        # log
        self.logger.info(f"{symbol} Profitability : Market {market_delta * 100}% | OctoBot : {total_profitability}%")

    def init_symbols_to_test(self):
        for crypto_currency_data in self.config[CONFIG_CRYPTO_CURRENCIES].values():
            for symbol in crypto_currency_data[CONFIG_CRYPTO_PAIRS]:
                if symbol in self.exchange_simulator.get_symbols():
                    self.symbols_to_test.add(symbol)

    @staticmethod
    def get_market_delta(market_data):
        market_begin = market_data[0][PriceIndexes.IND_PRICE_CLOSE.value]
        market_end = market_data[-1][PriceIndexes.IND_PRICE_CLOSE.value]

        if market_begin and market_end and market_begin > 0:
            market_delta = market_end / market_begin - 1 if market_end >= market_begin else market_end / market_begin - 1
        else:
            market_delta = 0

        return market_delta

    @staticmethod
    def enabled(config):
        return CONFIG_BACKTESTING in config and config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION]


class BacktestingEndedException(Exception):
    def __init__(self, symbol=""):
        self.msg = f"Backtesting finished for {symbol}."
        super().__init__(self.msg)
