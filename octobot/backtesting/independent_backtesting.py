#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import asyncio
import copy
import logging
import os.path as path

import octobot_commons.constants as common_constants
import octobot_commons.enums as enums
import octobot_commons.errors as errors
import octobot_commons.logging as commons_logging
import octobot_commons.pretty_printer as pretty_printer
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.databases as databases
import octobot_commons.optimization_campaign as optimization_campaign
import octobot_commons.time_frame_manager as time_frame_manager

import octobot.backtesting as backtesting
import octobot_backtesting.api as backtesting_api
import octobot_backtesting.constants as backtesting_constants
import octobot_backtesting.enums as backtesting_enums
import octobot_backtesting.data as backtesting_data

import octobot_evaluators.constants as evaluator_constants

import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums

import octobot.storage as storage


class IndependentBacktesting:
    def __init__(self, config,
                 tentacles_setup_config,
                 backtesting_files,
                 data_file_path=backtesting_constants.BACKTESTING_FILE_PATH,
                 run_on_common_part_only=True,
                 join_backtesting_timeout=backtesting_constants.BACKTESTING_DEFAULT_JOIN_TIMEOUT,
                 start_timestamp=None,
                 end_timestamp=None,
                 enable_logs=True,
                 stop_when_finished=False,
                 enforce_total_databases_max_size_after_run=True,
                 enable_storage=True,
                 run_on_all_available_time_frames=False,
                 backtesting_data=None):
        self.octobot_origin_config = config
        self.tentacles_setup_config = tentacles_setup_config
        self.backtesting_config = {}
        self.backtesting_files = backtesting_files
        self.logger = commons_logging.get_logger(self.__class__.__name__)
        self.data_file_path = data_file_path
        self.symbols_to_create_exchange_classes = {}
        self.risk = 0.1
        self.starting_portfolio = {}
        self.fees_config = {}
        self.forced_time_frames = []
        self.optimizer_id = None
        self.backtesting_id = None
        self._init_default_config_values()
        self.stopped = False
        self.stopped_event = None
        self.post_backtesting_task = None
        self.join_backtesting_timeout = join_backtesting_timeout
        self.enable_logs = enable_logs
        self.stop_when_finished = stop_when_finished
        self.previous_log_level = commons_logging.get_global_logger_level()
        self.enforce_total_databases_max_size_after_run = enforce_total_databases_max_size_after_run
        self.backtesting_data = backtesting_data
        self.octobot_backtesting = backtesting.OctoBotBacktesting(self.backtesting_config,
                                                                  self.tentacles_setup_config,
                                                                  self.symbols_to_create_exchange_classes,
                                                                  self.backtesting_files,
                                                                  run_on_common_part_only,
                                                                  start_timestamp=start_timestamp,
                                                                  end_timestamp=end_timestamp,
                                                                  enable_logs=self.enable_logs,
                                                                  enable_storage=enable_storage,
                                                                  run_on_all_available_time_frames=run_on_all_available_time_frames,
                                                                  backtesting_data=self.backtesting_data)

    async def initialize_and_run(self, log_errors=True):
        try:
            # create stopped_event here only to be sure to create it in the same loop as the one of the
            # backtesting run
            self.logger.debug("Starting backtesting")
            if self.stop_when_finished:
                self.stopped_event = asyncio.Event()
            if not self.enable_logs:
                commons_logging.set_global_logger_level(logging.ERROR)
            await self.initialize_config()
            await self._generate_backtesting_id_if_missing()
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

    async def join_stop_event(self, timeout=None):
        if self.stopped_event is None:
            return
        await asyncio.wait_for(self.stopped_event.wait(), timeout)

    async def join_backtesting_updater(self, timeout=None):
        if self.octobot_backtesting.backtesting is not None:
            await asyncio.wait_for(self.octobot_backtesting.backtesting.time_updater.finished_event.wait(), timeout)

    async def stop(self, memory_check=False, should_raise=False):
        try:
            if not self.stopped:
                await self.octobot_backtesting.stop(memory_check=memory_check, should_raise=should_raise)
        finally:
            self.stopped = True
            if self.stopped_event is not None:
                self.stopped_event.set()
            if not self.enable_logs:
                commons_logging.set_global_logger_level(self.previous_log_level)

    def is_in_progress(self):
        if self.octobot_backtesting.backtesting:
            return self.octobot_backtesting.backtesting.is_in_progress()
        else:
            return False

    def has_finished(self):
        if self.octobot_backtesting.backtesting:
            return self.octobot_backtesting.backtesting.has_finished()
        else:
            return False

    def get_progress(self):
        if self.octobot_backtesting.backtesting:
            return self.octobot_backtesting.backtesting.get_progress()
        else:
            return 0

    def _post_backtesting_start(self):
        commons_logging.reset_backtesting_errors()
        commons_logging.set_error_publication_enabled(False)
        self.post_backtesting_task = asyncio.create_task(self._register_post_backtesting_end_callback())

    async def _register_post_backtesting_end_callback(self):
        await self.join_backtesting_updater(timeout=self.join_backtesting_timeout)
        await self._post_backtesting_end_callback()

    async def _post_backtesting_end_callback(self):
        # re enable logs
        commons_logging.set_error_publication_enabled(True)
        if self.stop_when_finished:
            await self.stop()
        else:
            # stop backtesting importers to release database files
            await self.octobot_backtesting.stop_importers()
        if self.enforce_total_databases_max_size_after_run:
            try:
                await storage.enforce_total_databases_max_size()
            except Exception as e:
                self.logger.exception(e, True, f"Error when enforcing max run databases size: {e}")

    @staticmethod
    def _get_market_delta(symbol, exchange_manager, min_timeframe):
        market_data = trading_api.get_symbol_historical_candles(
            trading_api.get_symbol_data(exchange_manager, str(symbol)), min_timeframe)
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
            data_file_path = data_file
            if not path.isfile(data_file_path):
                data_file_path = path.join(self.data_file_path, data_file)
            description = await backtesting_data.get_file_description(data_file_path)
            if description is None:
                raise RuntimeError(f"Impossible to start backtesting: missing or invalid data file: {data_file}")
            exchange_name = description[backtesting_enums.DataFormatKeys.EXCHANGE.value]
            if exchange_name not in self.symbols_to_create_exchange_classes:
                self.symbols_to_create_exchange_classes[exchange_name] = []
            for symbol in description[backtesting_enums.DataFormatKeys.SYMBOLS.value]:
                self.symbols_to_create_exchange_classes[exchange_name].append(symbol_util.parse_symbol(symbol))

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
        self.optimizer_id = self.octobot_origin_config.get(common_constants.CONFIG_OPTIMIZER_ID)
        self.backtesting_id = self.octobot_origin_config.get(common_constants.CONFIG_BACKTESTING_ID)
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
            ERRORS_COUNT: commons_logging.get_backtesting_errors_count()
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
                report[SYMBOL_REPORT].append({symbol.symbol_str: market_delta * 100})
                report[CHART_IDENTIFIERS].append({
                    "symbol": symbol.symbol_str,
                    "exchange_id": exchange_id,
                    "exchange_name": exchange_name,
                    "time_frame": min_timeframe.value
                })
            profitabilities[exchange_name] = float(profitability)
            market_average_profitabilities[exchange_name] = float(market_average_profitability)
            starting_portfolios[exchange_name] = trading_api.get_origin_portfolio(exchange_manager, as_decimal=False)
            end_portfolios[exchange_name] = trading_api.get_portfolio(exchange_manager, as_decimal=False)

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
        self.logger.info(f"{symbol.symbol_str} Profitability : {market_delta * 100}%")

    def _log_global_report(self, exchange_manager):
        _, profitability, _, market_average_profitability, _ = trading_api.get_profitability_stats(exchange_manager)
        reference_market = trading_api.get_reference_market(self.backtesting_config)
        end_portfolio = trading_api.get_portfolio(exchange_manager, as_decimal=False)
        end_portfolio_value = trading_api.get_current_portfolio_value(exchange_manager)
        starting_portfolio = trading_api.get_origin_portfolio(exchange_manager, as_decimal=False)
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
        self._init_exchange_type()
        self.backtesting_config[common_constants.CONFIG_EXCHANGES] = copy.deepcopy(
            self.octobot_origin_config[common_constants.CONFIG_EXCHANGES])
        for exchange_details in self.backtesting_config[common_constants.CONFIG_EXCHANGES].values():
            exchange_details.pop(common_constants.CONFIG_EXCHANGE_KEY, None)
            exchange_details.pop(common_constants.CONFIG_EXCHANGE_SECRET, None)
            exchange_details.pop(common_constants.CONFIG_EXCHANGE_PASSWORD, None)
            exchange_details.pop(common_constants.CONFIG_EXCHANGE_SANDBOXED, None)
        self.backtesting_config[common_constants.CONFIG_TRADING][common_constants.CONFIG_TRADER_RISK] = self.risk
        self.backtesting_config[common_constants.CONFIG_TRADING][
            common_constants.CONFIG_TRADER_REFERENCE_MARKET] = self._find_reference_market_and_update_contract_type()
        self.backtesting_config[common_constants.CONFIG_SIMULATOR][
            common_constants.CONFIG_STARTING_PORTFOLIO] = self.starting_portfolio
        self.backtesting_config[common_constants.CONFIG_SIMULATOR][
            common_constants.CONFIG_SIMULATOR_FEES] = self.fees_config
        self.backtesting_config[common_constants.CONFIG_OPTIMIZER_ID] = self.optimizer_id
        self.backtesting_config[common_constants.CONFIG_BACKTESTING_ID] = self.backtesting_id
        if self.forced_time_frames:
            self.backtesting_config[evaluator_constants.CONFIG_FORCED_TIME_FRAME] = self.forced_time_frames
        self._add_config_default_backtesting_values()

    def _init_exchange_type(self):
        forced_exchange_type = self.octobot_origin_config.get(common_constants.CONFIG_EXCHANGE_TYPE,
                                                              common_constants.USE_CURRENT_PROFILE)
        try:
            for exchange_name in self.symbols_to_create_exchange_classes:
                if forced_exchange_type == common_constants.USE_CURRENT_PROFILE:
                    # use current profile config to create a spot/future/margin backtesting exchange
                    self.octobot_backtesting.exchange_type_by_exchange[exchange_name] = \
                        self.octobot_origin_config[common_constants.CONFIG_EXCHANGES].get(exchange_name, {}).\
                        get(common_constants.CONFIG_EXCHANGE_TYPE, common_constants.DEFAULT_EXCHANGE_TYPE)
                else:
                    self.octobot_backtesting.exchange_type_by_exchange[exchange_name] = forced_exchange_type
        except StopIteration:
            # use default exchange type
            pass

    async def _generate_backtesting_id_if_missing(self):
        if self.backtesting_config[common_constants.CONFIG_BACKTESTING_ID] is None:
            run_dbs_identifier = databases.RunDatabasesIdentifier(
                trading_api.get_activated_trading_mode(self.tentacles_setup_config),
                optimization_campaign.OptimizationCampaign.get_campaign_name(self.tentacles_setup_config)
            )
            run_dbs_identifier.backtesting_id = await run_dbs_identifier.generate_new_backtesting_id()
            if self.octobot_backtesting.enable_storage:
                # initialize to lock the backtesting id
                await run_dbs_identifier.initialize()
            self.backtesting_config[common_constants.CONFIG_BACKTESTING_ID] = run_dbs_identifier.backtesting_id

    def _find_reference_market_and_update_contract_type(self):
        ref_market_candidate = None
        ref_market_candidates = {}
        forced_contract_type = self.octobot_origin_config.get(common_constants.CONFIG_CONTRACT_TYPE,
                                                              common_constants.USE_CURRENT_PROFILE)
        for symbols in self.symbols_to_create_exchange_classes.values():
            symbol = symbols[0]
            if next(iter(self.octobot_backtesting.exchange_type_by_exchange.values())) \
                    == common_constants.CONFIG_EXCHANGE_FUTURE:
                if forced_contract_type == common_constants.USE_CURRENT_PROFILE:
                    if symbol.is_inverse():
                        if not all([symbol.is_inverse() for symbol in symbols]):
                            self.logger.error(f"Mixed inverse and linear contracts backtesting are not supported yet")
                            self.octobot_backtesting.futures_contract_type = \
                                trading_enums.FutureContractType.INVERSE_PERPETUAL
                    else:
                        if not all([symbol.is_linear() for symbol in symbols]):
                            self.logger.error(f"Mixed inverse and linear contracts backtesting are not supported yet")
                        self.octobot_backtesting.futures_contract_type = \
                            trading_enums.FutureContractType.LINEAR_PERPETUAL
                    # in inverse contracts, use BTC for BTC/USD trading as reference market
                    if symbol.settlement_asset:
                        # only use settlement asset if available
                        return symbol.settlement_asset
                else:
                    self.octobot_backtesting.futures_contract_type = forced_contract_type
                    return symbol.base \
                        if forced_contract_type is trading_enums.FutureContractType.INVERSE_PERPETUAL \
                        else symbol.quote

            for symbol in symbols:
                quote = symbol.quote
                if ref_market_candidate is None:
                    ref_market_candidate = quote
                if quote in ref_market_candidates:
                    ref_market_candidates[quote] += 1
                else:
                    ref_market_candidates[quote] = 1
                if ref_market_candidate != quote and \
                        ref_market_candidates[ref_market_candidate] < ref_market_candidates[quote]:
                    ref_market_candidate = quote
        return ref_market_candidate

    def _add_config_default_backtesting_values(self):
        if backtesting_constants.CONFIG_BACKTESTING not in self.backtesting_config:
            self.backtesting_config[backtesting_constants.CONFIG_BACKTESTING] = {}
        self.backtesting_config[backtesting_constants.CONFIG_BACKTESTING][common_constants.CONFIG_ENABLED_OPTION] = True
        self.backtesting_config[common_constants.CONFIG_TRADER][common_constants.CONFIG_ENABLED_OPTION] = False
        self.backtesting_config[common_constants.CONFIG_SIMULATOR][common_constants.CONFIG_ENABLED_OPTION] = True

    def _add_crypto_currencies_config(self):
        for symbols in self.symbols_to_create_exchange_classes.values():
            for symbol in symbols:
                symbol_id = str(symbol)
                if symbol_id not in self.backtesting_config[common_constants.CONFIG_CRYPTO_CURRENCIES]:
                    self.backtesting_config[common_constants.CONFIG_CRYPTO_CURRENCIES][symbol_id] = {
                        common_constants.CONFIG_CRYPTO_PAIRS: []
                    }
                    self.backtesting_config[common_constants.CONFIG_CRYPTO_CURRENCIES][symbol_id][
                        common_constants.CONFIG_CRYPTO_PAIRS] = [symbol_id]
