import logging
import os
import time

from config.cst import *
from tools.pretty_printer import PrettyPrinter


class Backtesting:
    def __init__(self, config, exchange_simulator, exit_at_end=True):
        self.config = config
        self.begin_time = time.time()
        self.force_exit_at_end = exit_at_end
        self.exchange_simulator = exchange_simulator
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ended_symbols = set()
        self.symbols_to_test = set()
        self.init_symbols_to_test()

    def get_is_finished(self):
        return len(self.ended_symbols) == len(self.symbols_to_test)

    def end(self, symbol):
        self.ended_symbols.add(symbol)
        if self.get_is_finished():
            try:
                self.logger.info(" **** Backtesting report ****")
                self.logger.info(" ========= Trades =========")
                self.print_trades_history()

                self.logger.info(" ========= Symbols price evolution =========")
                for symbol_to_test in self.symbols_to_test:
                    self.print_symbol_report(symbol_to_test)

                self.logger.info(" ========= Octobot end state =========")
                self.print_global_report()
            except AttributeError:
                self.logger.info(" *** Backtesting ended ****")

            if self.force_exit_at_end:
                os._exit(0)

    def print_trades_history(self):
        trader = self.get_trader()
        trades_history = trader.get_trades_manager().get_trade_history()
        trades_history_string = ""
        for trade in trades_history:
            trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + "\n"
        self.logger.info(trades_history_string.strip())

    def print_global_report(self):
        try:
            trader = self.get_trader()

            profitability, market_average_profitability = self.get_profitability(trader)
            reference_market = self.get_reference_market(trader)
            portfolio = self.get_portfolio(trader)
            accuracy_info = "" if len(self.symbols_to_test) < 2 else \
                "\nPlease note that multi symbol backtesting is slightly random due to Octbot's multithreaded " \
                "architecture used to process all symbols as fast as possible. This randomness is kept for " \
                "backtesting in order to be as close as possible from reality. Single symbol backtesting is " \
                "100% determinist."

            self.logger.info(f"End portfolio: "
                             f"{PrettyPrinter.global_portfolio_pretty_print(portfolio,' | ')}")

            self.logger.info(f"Global market profitability (vs {reference_market}) : "
                             f"{market_average_profitability}% | Octobot : {profitability}%{accuracy_info}")

            backtesting_time = time.time() - self.begin_time
            self.logger.info(f"Simulation lasted {backtesting_time} sec")
        except Exception as e:
            logging.exception(e)

    def _get_symbol_report(self, symbol, trader):
        market_data = self.exchange_simulator.get_data()[symbol][self.exchange_simulator.MIN_ENABLED_TIME_FRAME.value]

        # profitability
        total_profitability = 0
        _, profitability, _, _ = trader.get_trades_manager().get_profitability()
        total_profitability += profitability

        # vs market
        return self.get_market_delta(market_data)

    def print_symbol_report(self, symbol):
        self.logger.info(f"{symbol} Profitability : Market {self._get_symbol_report(symbol, self.get_trader()) * 100}%")

    def get_dict_formatted_report(self):
        SYMBOL_REPORT = "symbol_report"
        BOT_REPORT = "bot_report"
        report = {
            SYMBOL_REPORT: [],
            BOT_REPORT: {}
        }

        trader = self.get_trader()

        profitability, market_average_profitability = self.get_profitability(trader)

        for symbol in self.symbols_to_test:
            report[SYMBOL_REPORT].append({symbol: self._get_symbol_report(symbol, trader) * 100})

        report[BOT_REPORT] = {
            "profitability": profitability,
            "market_average_profitability": market_average_profitability,
            "reference_market": self.get_reference_market(trader),
            "end_portfolio": self.get_portfolio(trader)
        }
        return report

    def get_trader(self):
        return self.exchange_simulator.get_exchange_manager().get_trader()

    @staticmethod
    def get_reference_market(trader):
        return trader.get_trades_manager().get_reference()

    @staticmethod
    def get_portfolio(trader):
        return trader.get_portfolio().get_portfolio()

    @staticmethod
    def get_profitability(trader):
        trade_manager = trader.get_trades_manager()
        _, profitability, _, market_average_profitability = trade_manager.get_profitability(True)
        return profitability, market_average_profitability

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
            market_delta = market_end / market_begin - 1 if market_end >= market_begin \
                else 1 - market_begin / market_end
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
