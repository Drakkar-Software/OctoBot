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

    def end(self):
        self.logger.warning("Current backtesting version has a 2% precision error rate.")

        for symbol in self.exchange_simulator.get_symbols():
            self.report(symbol)

        # make sure to wait the end of threads process
        backtesting_time = time.time() - self.begin_time
        time.sleep(5)
        self.logger.info("Simulation lasted {0} sec".format(backtesting_time))
        if self.force_exit_at_end:
            os._exit(0)

    def report(self, symbol):
        market_data = self.exchange_simulator.get_data()[symbol][self.exchange_simulator.MIN_ENABLED_TIME_FRAME.value]

        self.time_delta = self.begin_time - market_data[0][PriceIndexes.IND_PRICE_TIME.value] / 1000

        # profitability
        total_profitability = 0
        for trader in get_bot().get_exchange_trader_simulators().values():
            _, profitability, _ = trader.get_trades_manager().get_profitability()
            total_profitability += profitability

        # vs market
        market_delta = self.get_market_delta(market_data)

        # log
        self.logger.info(
            "Profitability : Market {0}% | OctoBot : {1}%".format(market_delta * 100, total_profitability))

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
