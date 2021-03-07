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
import copy
import os.path as path

import octobot_commons.constants as common_constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.logging as logging
import octobot_commons.pretty_printer as pretty_printer
import octobot_commons.symbol_util as symbol_util
import octobot_commons.time_frame_manager as time_frame_manager

import octobot.backtesting as backtesting
import octobot_backtesting.api as backtesting_api
import octobot_backtesting.constants as backtesting_constants
import octobot_backtesting.enums as backtesting_enums
import octobot_backtesting.data as backtesting_data

import octobot_evaluators.constants as evaluator_constants

import octobot_trading.api as trading_api


class IndependentBacktesting:
    def __init__(self, config,
                 tentacles_setup_config,
                 backtesting_files,
                 data_file_path=backtesting_constants.BACKTESTING_FILE_PATH,
                 run_on_common_part_only=True,
                 join_backtesting_timeout=backtesting_constants.BACKTESTING_DEFAULT_JOIN_TIMEOUT):
        self.octobot_origin_config = config
        self.tentacles_setup_config = tentacles_setup_config
        self.backtesting_config = {}
        self.backtesting_files = backtesting_files
        self.logger = logging.get_logger(self.__class__.__name__)
        self.data_file_path = data_file_path
        self.symbols_to_create_exchange_classes = {}
        self.risk = 0.1
        self.starting_portfolio = {}
        self.fees_config = {}
        self.forced_time_frames = []
        self._init_default_config_values()
        self.stopped = False
        self.post_backtesting_task = None
        self.join_backtesting_timeout = join_backtesting_timeout
        self.octobot_backtesting = backtesting.OctoBotBacktesting(self.backtesting_config,
                                                                  self.tentacles_setup_config,
                                                                  self.symbols_to_create_exchange_classes,
                                                                  self.backtesting_files,
                                                                  run_on_common_part_only)

    async def initialize_and_run(self, log_errors=True):
        try:
            await self.initialize_config()
            self._add_crypto_currencies_config()
            await self.octobot_backtesting.initialize_and_run()
            self._post_backtesting_start()
        except RuntimeError as e:
            self.logger.error(f"{e} ({e.__class__.__name__})")
            await self.stop()
        except Exception as e:
            if log_errors:
                self.logger.exception(e, True, f"Error when running backtesting: {e}")
            raise e

    async def initialize_config(self):
        await self._register_available_data()
        self._adapt_config()
        return self.backtesting_config

    async def join_backtesting_updater(self, timeout=None):
        if self.octobot_backtesting.backtesting is not None:
            await asyncio.wait_for(self.octobot_backtesting.backtesting.time_updater.finished_event.wait(), timeout)

    async def stop(self, memory_check=False, should_raise=False):
        try:
            if not self.stopped:
                await self.octobot_backtesting.stop(memory_check=memory_check, should_raise=should_raise)
        finally:
            self.stopped = True

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

    def _post_backtesting_start(self):
        logging.reset_backtesting_errors()
        logging.set_error_publication_enabled(False)
        self.post_backtesting_task = asyncio.create_task(self._register_post_backtesting_end_callback())

    async def _register_post_backtesting_end_callback(self):
        await self.join_backtesting_updater(timeout=self.join_backtesting_timeout)
        await self._post_backtesting_end_callback()

    async def _post_backtesting_end_callback(self):
        # re enable logs
        logging.set_error_publication_enabled(True)
        # stop backtesting importers to release database files
        await self.octobot_backtesting.stop_importers()

    @staticmethod
    def _get_market_delta(symbol, exchange_manager, min_timeframe):
        market_data = trading_api.get_symbol_historical_candles(
            trading_api.get_symbol_data(exchange_manager, symbol), min_timeframe)
        market_begin = market_data[enums.PriceIndexes.IND_PRICE_CLOSE.value][0]
        market_end = market_data[enums.PriceIndexes.IND_PRICE_CLOSE.value][-1]

        if market_begin and market_end and market_begin > 0:
            market_delta = market_end / market_begin - 1 if market_end >= market_begin \
                else -1 * (1 - market_end / market_begin)
        else:
            market_delta = 0

        return market_delta

    async def _register_available_data(self):
        for data_file in self.backtesting_files:
            description = await backtesting_data.get_file_description(path.join(self.data_file_path, data_file))
            if description is None:
                raise RuntimeError(f"Impossible to start backtesting: missing or invalid data file: {data_file}")
            exchange_name = description[backtesting_enums.DataFormatKeys.EXCHANGE.value]
            if exchange_name not in self.symbols_to_create_exchange_classes:
                self.symbols_to_create_exchange_classes[exchange_name] = []
            for symbol in description[backtesting_enums.DataFormatKeys.SYMBOLS.value]:
                self.symbols_to_create_exchange_classes[exchange_name].append(symbol)

    def _init_default_config_values(self):
        self.risk = copy.deepcopy(self.octobot_origin_config[common_constants.CONFIG_TRADING][
                                      common_constants.CONFIG_TRADER_RISK])
        self.starting_portfolio = copy.deepcopy(self.octobot_origin_config[common_constants.CONFIG_SIMULATOR][
                                                    common_constants.CONFIG_STARTING_PORTFOLIO])
        self.fees_config = copy.deepcopy(self.octobot_origin_config[common_constants.CONFIG_SIMULATOR][
                                             common_constants.CONFIG_SIMULATOR_FEES])
        if evaluator_constants.CONFIG_FORCED_TIME_FRAME in self.octobot_origin_config:
            self.forced_time_frames = copy.deepcopy(self.octobot_origin_config[
                                                        evaluator_constants.CONFIG_FORCED_TIME_FRAME])
        self.backtesting_config = {
            backtesting_constants.CONFIG_BACKTESTING: {},
            common_constants.CONFIG_CRYPTO_CURRENCIES: {},
            common_constants.CONFIG_EXCHANGES: {},
            common_constants.CONFIG_TRADER: {},
            common_constants.CONFIG_SIMULATOR: {},
            common_constants.CONFIG_TRADING: {},
        }

    async def get_dict_formatted_report(self):
        reference_market = trading_api.get_reference_market(self.backtesting_config)
        try:
            trading_mode = trading_api.get_activated_trading_mode(self.tentacles_setup_config).get_name()
        except errors.ConfigTradingError as e:
            self.logger.error(e)
            trading_mode = "Error when reading trading mode"
        report = self._get_exchanges_report(reference_market, trading_mode)
        return report

    def _get_exchanges_report(self, reference_market, trading_mode):
        SYMBOL_REPORT = "symbol_report"
        BOT_REPORT = "bot_report"
        CHART_IDENTIFIERS = "chart_identifiers"
        ERRORS_COUNT = "errors_count"
        report = {
            SYMBOL_REPORT: [],
            BOT_REPORT: {},
            CHART_IDENTIFIERS: [],
            ERRORS_COUNT: logging.get_backtesting_errors_count()
        }
        profitabilities = {}
        market_average_profitabilities = {}
        starting_portfolios = {}
        end_portfolios = {}
        for exchange_id in self.octobot_backtesting.exchange_manager_ids:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            _, profitability, _, market_average_profitability, _ = trading_api.get_profitability_stats(exchange_manager)
            min_timeframe = time_frame_manager.find_min_time_frame(trading_api.get_watched_timeframes(exchange_manager))
            exchange_name = trading_api.get_exchange_name(exchange_manager)
            for symbol in self.symbols_to_create_exchange_classes[exchange_name]:
                market_delta = self._get_market_delta(symbol, exchange_manager, min_timeframe)
                report[SYMBOL_REPORT].append({symbol: market_delta * 100})
                report[CHART_IDENTIFIERS].append({
                    "symbol": symbol,
                    "exchange_id": exchange_id,
                    "exchange_name": exchange_name,
                    "time_frame": min_timeframe.value
                })
            profitabilities[exchange_name] = profitability
            market_average_profitabilities[exchange_name] = market_average_profitability
            starting_portfolios[exchange_name] = trading_api.get_origin_portfolio(exchange_manager)
            end_portfolios[exchange_name] = trading_api.get_portfolio(exchange_manager)

        report[BOT_REPORT] = {
            "profitability": profitabilities,
            "market_average_profitability": market_average_profitabilities,
            "reference_market": reference_market,
            "end_portfolio": end_portfolios,
            "starting_portfolio": starting_portfolios,
            "trading_mode": trading_mode
        }
        return report

    def log_report(self):
        self.logger.info(" **** Backtesting report ****")
        for exchange_id in self.octobot_backtesting.exchange_manager_ids:
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            exchange_name = trading_api.get_exchange_name(exchange_manager)
            self.logger.info(f" ========= Trades on {exchange_name} =========")
            self._log_trades_history(exchange_manager, exchange_name)

            self.logger.info(f" ========= Prices evolution on {exchange_name} =========")
            min_timeframe = time_frame_manager.find_min_time_frame(trading_api.get_watched_timeframes(exchange_manager))
            for symbol in self.symbols_to_create_exchange_classes[exchange_name]:
                self._log_symbol_report(symbol, exchange_manager, min_timeframe)

            self.logger.info(" ========= Octobot end state =========")
            self._log_global_report(exchange_manager)

    def _log_trades_history(self, exchange_manager, exchange_name):
        trades_history_string = "\n".join([pretty_printer.trade_pretty_printer(exchange_name, trade)
                                           for trade in trading_api.get_trade_history(exchange_manager)])
        self.logger.info(f"\n{trades_history_string}")

    def _log_symbol_report(self, symbol, exchange_manager, min_time_frame):
        market_delta = self._get_market_delta(symbol, exchange_manager, min_time_frame)
        self.logger.info(f"{symbol} Profitability : {market_delta * 100}%")

    def _log_global_report(self, exchange_manager):
        _, profitability, _, market_average_profitability, _ = trading_api.get_profitability_stats(exchange_manager)
        reference_market = trading_api.get_reference_market(self.backtesting_config)
        end_portfolio = trading_api.get_portfolio(exchange_manager)
        end_portfolio_value = trading_api.get_current_portfolio_value(exchange_manager)
        starting_portfolio = trading_api.get_origin_portfolio(exchange_manager)
        starting_portfolio_value = trading_api.get_origin_portfolio_value(exchange_manager)

        self.logger.info(f"[End portfolio]      value {round(end_portfolio_value, 5)} {reference_market} "
                         f"Holdings: {pretty_printer.global_portfolio_pretty_print(end_portfolio, ' | ')}")

        self.logger.info(f"[Starting portfolio] value {round(starting_portfolio_value, 5)} {reference_market} "
                         f"Holdings: {pretty_printer.global_portfolio_pretty_print(starting_portfolio, ' | ')}")

        self.logger.info(f"Global market profitability (vs {reference_market}) : "
                         f"{market_average_profitability}% | Octobot : {profitability}%")

        self.logger.info(
            f"Simulation lasted "
            f"{round(backtesting_api.get_backtesting_duration(self.octobot_backtesting.backtesting), 3)} sec")

    def _adapt_config(self):
        self.backtesting_config[common_constants.CONFIG_TRADING][common_constants.CONFIG_TRADER_RISK] = self.risk
        self.backtesting_config[common_constants.CONFIG_TRADING][
            common_constants.CONFIG_TRADER_REFERENCE_MARKET] = self._find_reference_market()
        self.backtesting_config[common_constants.CONFIG_SIMULATOR][
            common_constants.CONFIG_STARTING_PORTFOLIO] = self.starting_portfolio
        self.backtesting_config[common_constants.CONFIG_SIMULATOR][
            common_constants.CONFIG_SIMULATOR_FEES] = self.fees_config
        if self.forced_time_frames:
            self.backtesting_config[evaluator_constants.CONFIG_FORCED_TIME_FRAME] = self.forced_time_frames
        self._add_config_default_backtesting_values()

    def _find_reference_market(self):
        ref_market_candidate = None
        ref_market_candidates = {}
        for pairs in self.symbols_to_create_exchange_classes.values():
            for pair in pairs:
                base = symbol_util.split_symbol(pair)[1]
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
        if backtesting_constants.CONFIG_BACKTESTING not in self.backtesting_config:
            self.backtesting_config[backtesting_constants.CONFIG_BACKTESTING] = {}
        self.backtesting_config[backtesting_constants.CONFIG_BACKTESTING][common_constants.CONFIG_ENABLED_OPTION] = True
        self.backtesting_config[common_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        self.backtesting_config[common_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True

    def _add_crypto_currencies_config(self):
        for pairs in self.symbols_to_create_exchange_classes.values():
            for pair in pairs:
                if pair not in self.backtesting_config[common_constants.CONFIG_CRYPTO_CURRENCIES]:
                    self.backtesting_config[common_constants.CONFIG_CRYPTO_CURRENCIES][pair] = {
                        common_constants.CONFIG_CRYPTO_PAIRS: []
                    }
                    self.backtesting_config[common_constants.CONFIG_CRYPTO_CURRENCIES][pair][
                        common_constants.CONFIG_CRYPTO_PAIRS] = [pair]
