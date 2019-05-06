#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

from tools.logging.logging_util import get_logger
import os
import time

from config import CONFIG_ANALYSIS_ENABLED_OPTION, CONFIG_BACKTESTING, PriceIndexes, CONFIG_CRYPTO_CURRENCIES, \
    CONFIG_CRYPTO_PAIRS
from tools.pretty_printer import PrettyPrinter


class Backtesting:
    def __init__(self, config, exchange_simulator, exit_at_end=True):
        self.config = config
        self.begin_time = time.time()
        self.force_exit_at_end = exit_at_end
        self.exchange_simulator = exchange_simulator
        self.logger = get_logger(self.__class__.__name__)
        self.ended_symbols = set()
        self.symbols_to_test = set()
        self.init_symbols_to_test()

    def get_is_finished(self, symbols=None):
        if symbols is None:
            return len(self.ended_symbols) == len(self.symbols_to_test)
        else:
            return all(symbol in self.ended_symbols for symbol in symbols)

    async def end(self, symbol):
        self.ended_symbols.add(symbol)
        if self.get_is_finished():
            try:
                self.logger.info(" **** Backtesting report ****")
                self.logger.info(" ========= Trades =========")
                self.print_trades_history()

                self.logger.info(" ========= Symbols price evolution =========")
                for symbol_to_test in self.symbols_to_test:
                    await self.print_symbol_report(symbol_to_test)

                self.logger.info(" ========= Octobot end state =========")
                await self.print_global_report()
            except AttributeError:
                self.logger.info(" *** Backtesting ended ****")

            if self.force_exit_at_end:
                if self.analysis_enabled(self.config):
                    self.logger.info(" *** OctoBot will now keep working for analysis purposes because of the '-ba' "
                                     "(--backtesting_analysis) argument. To stop it, use CTRL+C or 'STOP OCTOBOT' "
                                     "from the web interface. ***")
                else:
                    os._exit(0)

    def print_trades_history(self):
        trader = self.get_trader()
        trades_history = trader.get_trades_manager().get_trade_history()
        trades_history_string = ""
        for trade in trades_history:
            trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + "\n"
        self.logger.info(trades_history_string.strip())

    async def print_global_report(self):
        try:
            trader = self.get_trader()

            profitability, market_average_profitability = await self.get_profitability(trader)
            reference_market = self.get_reference_market(trader)
            end_portfolio = self.get_portfolio(trader)
            starting_portfolio = self.get_origin_portfolio(trader)

            self.logger.info(f"End portfolio: "
                             f"{PrettyPrinter.global_portfolio_pretty_print(end_portfolio,' | ')}")

            self.logger.info(f"Starting portfolio: "
                             f"{PrettyPrinter.global_portfolio_pretty_print(starting_portfolio,' | ')}")

            self.logger.info(f"Global market profitability (vs {reference_market}) : "
                             f"{market_average_profitability}% | Octobot : {profitability}%")

            backtesting_time = time.time() - self.begin_time
            self.logger.info(f"Simulation lasted {backtesting_time} sec")
        except Exception as e:
            self.logger.exception(e)

    async def _get_symbol_report(self, symbol, trader):
        market_data = self.exchange_simulator.get_ohlcv(symbol)[self.exchange_simulator.MIN_ENABLED_TIME_FRAME.value]

        # profitability
        total_profitability = 0
        _, profitability, _, _, _ = await trader.get_trades_manager().get_profitability()
        total_profitability += profitability

        # vs market
        return self.get_market_delta(market_data)

    async def print_symbol_report(self, symbol):
        symbol_report = await self._get_symbol_report(symbol, self.get_trader())
        self.logger.info(f"{symbol} Profitability : Market {symbol_report * 100}%")

    async def get_dict_formatted_report(self):
        SYMBOL_REPORT = "symbol_report"
        BOT_REPORT = "bot_report"
        SYMBOLS_WITH_TF = "symbols_with_time_frames_frames"
        report = {
            SYMBOL_REPORT: [],
            BOT_REPORT: {},
            SYMBOLS_WITH_TF: {}
        }

        trader = self.get_trader()

        profitability, market_average_profitability = await self.get_profitability(trader)

        for symbol in self.symbols_to_test:
            symbol_report = await self._get_symbol_report(symbol, trader)
            report[SYMBOL_REPORT].append({symbol: symbol_report * 100})
            report[SYMBOLS_WITH_TF][symbol] = self.exchange_simulator.get_min_time_frame(symbol)

        report[BOT_REPORT] = {
            "profitability": profitability,
            "market_average_profitability": market_average_profitability,
            "reference_market": self.get_reference_market(trader),
            "end_portfolio": self.get_portfolio(trader),
            "starting_portfolio": self.get_origin_portfolio(trader),
            "trading_mode": ",".join([t.get_name() for t in trader.trading_modes])
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
    def get_origin_portfolio(trader):
        return trader.get_trades_manager().get_origin_portfolio()

    @staticmethod
    async def get_profitability(trader):
        trade_manager = trader.get_trades_manager()
        _, profitability, _, market_average_profitability, _ = await trade_manager.get_profitability(True)
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
    def analysis_enabled(config):
        return CONFIG_BACKTESTING in config and config[CONFIG_BACKTESTING][CONFIG_ANALYSIS_ENABLED_OPTION]
