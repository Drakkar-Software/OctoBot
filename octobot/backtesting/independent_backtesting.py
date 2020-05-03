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
import asyncio
from copy import deepcopy
from os import path

from octobot.backtesting.octobot_backtesting import OctoBotBacktesting
from octobot_backtesting.constants import CONFIG_BACKTESTING, BACKTESTING_FILE_PATH, BACKTESTING_DEFAULT_JOIN_TIMEOUT
from octobot_backtesting.data.data_file_manager import get_file_description
from octobot_backtesting.enums import DataFormatKeys
from octobot_commons.constants import CONFIG_ENABLED_OPTION, CONFIG_CRYPTO_CURRENCIES, CONFIG_CRYPTO_PAIRS
from octobot_commons.enums import PriceIndexes
from octobot_commons.errors import ConfigTradingError
from octobot_commons.logging.logging_util import get_logger, get_backtesting_errors_count, \
    reset_backtesting_errors, set_error_publication_enabled
from octobot_commons.symbol_util import split_symbol
from octobot_commons.time_frame_manager import find_min_time_frame
from octobot_evaluators.constants import CONFIG_FORCED_TIME_FRAME
from octobot_trading.api.exchange import get_exchange_manager_from_exchange_id, get_exchange_name, \
    get_watched_timeframes
from octobot_trading.api.modes import get_activated_trading_mode
from octobot_trading.api.portfolio import get_portfolio, get_origin_portfolio
from octobot_trading.api.profitability import get_profitability_stats, get_reference_market
from octobot_trading.api.symbol_data import get_symbol_data, get_symbol_historical_candles
from octobot_trading.constants import CONFIG_TRADER_RISK, CONFIG_TRADING, CONFIG_SIMULATOR, \
    CONFIG_STARTING_PORTFOLIO, CONFIG_SIMULATOR_FEES, CONFIG_EXCHANGES, CONFIG_TRADER, CONFIG_TRADER_REFERENCE_MARKET


class IndependentBacktesting:
    def __init__(self, config, tentacles_setup_config, backtesting_files, data_file_path=BACKTESTING_FILE_PATH):
        self.octobot_origin_config = config
        self.tentacles_setup_config = tentacles_setup_config
        self.backtesting_config = {}
        self.backtesting_files = backtesting_files
        self.logger = get_logger(self.__class__.__name__)
        self.data_file_path = data_file_path
        self.symbols_to_create_exchange_classes = {}
        self.risk = 0.1
        self.starting_portfolio = {}
        self.fees_config = {}
        self.forced_time_frames = []
        self._init_default_config_values()
        self.octobot_backtesting = OctoBotBacktesting(self.backtesting_config,
                                                      self.tentacles_setup_config,
                                                      self.symbols_to_create_exchange_classes,
                                                      self.backtesting_files)

    async def initialize_and_run(self, log_errors=True):
        try:
            await self.initialize_config()
            self._add_crypto_currencies_config()
            await self.octobot_backtesting.initialize_and_run()
            self._block_errors_publish_till_end_of_backtesting()
        except Exception as e:
            if log_errors:
                self.logger.exception(e, True, f"Error when running backtesting: {e}")
            raise e

    async def initialize_config(self):
        await self._register_available_data()
        self._adapt_config()
        return self.backtesting_config

    async def join(self, timeout):
        await asyncio.wait_for(self.octobot_backtesting.backtesting.time_updater.finished_event.wait(), timeout)

    async def stop(self):
        await self.octobot_backtesting.stop()

    def is_in_progress(self):
        if self.octobot_backtesting.backtesting:
            return self.octobot_backtesting.backtesting.is_in_progress()
        else:
            return False

    def get_progress(self):
        if self.octobot_backtesting.backtesting:
            return self.octobot_backtesting.backtesting.get_progress()
        else:
            return 0

    def _block_errors_publish_till_end_of_backtesting(self):
        reset_backtesting_errors()
        set_error_publication_enabled(False)
        asyncio.create_task(self._re_enable_logs_after_backtesting())

    async def _re_enable_logs_after_backtesting(self):
        await self.join(timeout=BACKTESTING_DEFAULT_JOIN_TIMEOUT)
        set_error_publication_enabled(True)

    @staticmethod
    def _get_market_delta(symbol, exchange_manager, min_timeframe):
        market_data = get_symbol_historical_candles(get_symbol_data(exchange_manager, symbol), min_timeframe)
        market_begin = market_data[PriceIndexes.IND_PRICE_CLOSE.value][0]
        market_end = market_data[PriceIndexes.IND_PRICE_CLOSE.value][-1]

        if market_begin and market_end and market_begin > 0:
            market_delta = market_end / market_begin - 1 if market_end >= market_begin \
                else 1 - market_begin / market_end
        else:
            market_delta = 0

        return market_delta

    async def _register_available_data(self):
        for data_file in self.backtesting_files:
            description = await get_file_description(path.join(self.data_file_path, data_file))
            exchange_name = description[DataFormatKeys.EXCHANGE.value]
            if exchange_name not in self.symbols_to_create_exchange_classes:
                self.symbols_to_create_exchange_classes[exchange_name] = []
            for symbol in description[DataFormatKeys.SYMBOLS.value]:
                self.symbols_to_create_exchange_classes[exchange_name].append(symbol)

    def _init_default_config_values(self):
        self.risk = deepcopy(self.octobot_origin_config[CONFIG_TRADING][CONFIG_TRADER_RISK])
        self.starting_portfolio = deepcopy(self.octobot_origin_config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO])
        self.fees_config = deepcopy(self.octobot_origin_config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES])
        if CONFIG_FORCED_TIME_FRAME in self.octobot_origin_config:
            self.forced_time_frames = deepcopy(self.octobot_origin_config[CONFIG_FORCED_TIME_FRAME])
        self.backtesting_config = {
            CONFIG_BACKTESTING: {},
            CONFIG_CRYPTO_CURRENCIES: {},
            CONFIG_EXCHANGES: {},
            CONFIG_TRADER: {},
            CONFIG_SIMULATOR: {},
            CONFIG_TRADING: {},
        }

    async def get_dict_formatted_report(self):
        reference_market = get_reference_market(self.backtesting_config)
        try:
            trading_mode = get_activated_trading_mode(self.backtesting_config, self.tentacles_setup_config).get_name()
        except ConfigTradingError as e:
            self.logger.error(e)
            trading_mode = "Error when reading trading mode"
        for exchange_id in self.octobot_backtesting.exchange_manager_ids:
            report = self._get_exchange_report(exchange_id, reference_market, trading_mode)
            # TODO: handle multi exchange reports
            return report

    def _get_exchange_report(self, exchange_id, reference_market, trading_mode):
        SYMBOL_REPORT = "symbol_report"
        BOT_REPORT = "bot_report"
        CHART_IDENTIFIERS = "chart_identifiers"
        ERRORS_COUNT = "errors_count"
        report = {
            SYMBOL_REPORT: [],
            BOT_REPORT: {},
            CHART_IDENTIFIERS: [],
            ERRORS_COUNT: get_backtesting_errors_count()
        }
        exchange_manager = get_exchange_manager_from_exchange_id(exchange_id)
        _, profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
        min_timeframe = find_min_time_frame(get_watched_timeframes(exchange_manager))
        exchange_name = get_exchange_name(exchange_manager)
        for symbol in self.symbols_to_create_exchange_classes[exchange_name]:
            market_delta = self._get_market_delta(symbol, exchange_manager, min_timeframe)
            report[SYMBOL_REPORT].append({symbol: market_delta * 100})
            report[CHART_IDENTIFIERS].append({
                "symbol": symbol,
                "exchange_id": exchange_id,
                "exchange_name": exchange_name,
                "time_frame": min_timeframe.value
            })

        report[BOT_REPORT] = {
            "profitability": profitability,
            "market_average_profitability": market_average_profitability,
            "reference_market": reference_market,
            "end_portfolio": get_portfolio(exchange_manager),
            "starting_portfolio": get_origin_portfolio(exchange_manager),
            "trading_mode": trading_mode
        }
        return report

    def _adapt_config(self):
        self.backtesting_config[CONFIG_TRADING][CONFIG_TRADER_RISK] = self.risk
        self.backtesting_config[CONFIG_TRADING][CONFIG_TRADER_REFERENCE_MARKET] = self._find_reference_market()
        self.backtesting_config[CONFIG_SIMULATOR][CONFIG_STARTING_PORTFOLIO] = self.starting_portfolio
        self.backtesting_config[CONFIG_SIMULATOR][CONFIG_SIMULATOR_FEES] = self.fees_config
        if self.forced_time_frames:
            self.backtesting_config[CONFIG_FORCED_TIME_FRAME] = self.forced_time_frames
        self._add_config_default_backtesting_values()

    def _find_reference_market(self):
        ref_market_candidate = None
        ref_market_candidates = {}
        for pairs in self.symbols_to_create_exchange_classes.values():
            for pair in pairs:
                base = split_symbol(pair)[1]
                if ref_market_candidate is None:
                    ref_market_candidate = base
                if base in ref_market_candidates:
                    ref_market_candidates[base] += 1
                else:
                    ref_market_candidates[base] = 1
                if ref_market_candidate != base and \
                   ref_market_candidates[ref_market_candidate] < ref_market_candidates[base]:
                    ref_market_candidate = base
        return ref_market_candidate

    def _add_config_default_backtesting_values(self):
        if CONFIG_BACKTESTING not in self.backtesting_config:
            self.backtesting_config[CONFIG_BACKTESTING] = {}
        self.backtesting_config[CONFIG_BACKTESTING][CONFIG_ENABLED_OPTION] = True
        self.backtesting_config[CONFIG_TRADER][CONFIG_ENABLED_OPTION] = False
        self.backtesting_config[CONFIG_SIMULATOR][CONFIG_ENABLED_OPTION] = True

    def _add_crypto_currencies_config(self):
        for pairs in self.symbols_to_create_exchange_classes.values():
            for pair in pairs:
                if pair not in self.backtesting_config[CONFIG_CRYPTO_CURRENCIES]:
                    self.backtesting_config[CONFIG_CRYPTO_CURRENCIES][pair] = {
                        CONFIG_CRYPTO_PAIRS: []
                    }
                    self.backtesting_config[CONFIG_CRYPTO_CURRENCIES][pair][CONFIG_CRYPTO_PAIRS] = [pair]
