import logging
import os
import time

from backtesting import get_bot
from config.cst import *
from tools.pretty_printer import PrettyPrinter


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

            self.logger.info(" **** Backtesting report ****")
            self.logger.info(" ========= Trades =========")
            self.print_trades_history()

            self.logger.info(" ========= Symbols price evolution =========")
            for symbol_to_test in self.symbols_to_test:
                self.print_symbol_report(symbol_to_test)

            self.logger.info(" ========= Octobot end state =========")
            self.print_global_report()

            if self.force_exit_at_end:
                os._exit(0)

    def print_trades_history(self):
        trader = next(iter(get_bot().get_exchange_trader_simulators().values()))
        trades_history = trader.get_trades_manager().get_trade_history()
        trades_history_string = ""
        for trade in trades_history:
            trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + "\n"
        self.logger.info(trades_history_string.strip())

    def print_global_report(self):
        trader = next(iter(get_bot().get_exchange_trader_simulators().values()))
        trade_manager = trader.get_trades_manager()
        _, profitability, _, market_average_profitability = trade_manager.get_profitability(True)
        reference_market = trade_manager.get_reference()
        portfolio = trader.get_portfolio()
        accuracy_info = "" if len(self.symbols_to_test) < 2 else "\nPlease note that multi symbol backtesting is " \
                                                                 "slightly random due to Octbot's multithreaded " \
                                                                 "architecture used to process all symbols as fast as" \
                                                                 " possible. This randomness is kept for backtesting " \
                                                                 "in order to be as close as possible from reality. " \
                                                                 "Single symbol backtesting is 100% determinist."

        self.logger.info(f"End portfolio: "
                         f"{PrettyPrinter.global_portfolio_pretty_print(portfolio.get_portfolio(),' | ')}")

        self.logger.info(f"Global market profitability (vs {reference_market}) : "
                         f"{market_average_profitability}% | Octobot : {profitability}%{accuracy_info}")

        backtesting_time = time.time() - self.begin_time
        self.logger.info(f"Simulation lasted {backtesting_time} sec")

    def print_symbol_report(self, symbol):
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
        self.logger.info(f"{symbol} Profitability : Market {market_delta * 100}%")

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
