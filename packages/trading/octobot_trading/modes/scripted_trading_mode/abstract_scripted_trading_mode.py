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
import time
import importlib

import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_trading.modes.abstract_trading_mode as abstract_trading_mode
import octobot_trading.modes.channel as modes_channel
import octobot_trading.modes.script_keywords.context_management as context_management
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.modes_util as modes_util
import octobot_trading.errors as errors
import octobot_tentacles_manager.api as tentacles_manager_api


class AbstractScriptedTradingMode(abstract_trading_mode.AbstractTradingMode):
    TRADING_SCRIPT_MODULE = None
    BACKTESTING_SCRIPT_MODULE = None
    ALLOW_CUSTOM_TRIGGER_SOURCE = True

    INITIALIZED_TRADING_PAIR_BY_BOT_ID = {}

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self._live_script = None
        self._backtesting_script = None
        self.timestamp = time.time()
        self.script_name = None

        if exchange_manager:
            # add config folder to importable files to import the user script
            tentacles_manager_api.import_user_tentacles_config_folder(self.exchange_manager.tentacles_setup_config)

    def get_current_state(self) -> (str, float):
        return super().get_current_state()[0] if self.producers[0].state is None else self.producers[0].state.name, \
               "N/A"

    def get_mode_producer_classes(self) -> list:
        return [AbstractScriptedTradingModeProducer]

    async def user_commands_callback(self, bot_id, subject, action, data) -> None:
        # do not call super as reload_config is called by reload_scripts already
        # on RELOAD_CONFIG command
        if action == commons_enums.UserCommands.RELOAD_CONFIG.value:
            # also reload script on RELOAD_CONFIG
            await self.reload_scripts()
        elif action == commons_enums.UserCommands.RELOAD_SCRIPT.value:
            await self.reload_scripts()
        elif action == commons_enums.UserCommands.CLEAR_PLOTTING_CACHE.value:
            await modes_util.clear_plotting_cache(self)
        elif action == commons_enums.UserCommands.CLEAR_SIMULATED_ORDERS_CACHE.value:
            await modes_util.clear_simulated_orders_cache(self)

    @classmethod
    async def get_backtesting_plot(cls, exchange, symbol, backtesting_id, optimizer_id,
                                   optimization_campaign, backtesting_analysis_settings):
        ctx = context_management.Context.minimal(cls, logging.get_logger(cls.get_name()), exchange, symbol,
                                                 backtesting_id, optimizer_id,
                                                 optimization_campaign, backtesting_analysis_settings)
        return await cls.get_script_from_module(cls.BACKTESTING_SCRIPT_MODULE)(ctx)

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False

    def get_script(self, live=True):
        return self._live_script if live else self._backtesting_script

    def register_script_module(self, script_module, live=True):
        if live:
            self.__class__.TRADING_SCRIPT_MODULE = script_module
            self._live_script = self.get_script_from_module(script_module)
        else:
            self.__class__.BACKTESTING_SCRIPT_MODULE = script_module
            self._backtesting_script = self.get_script_from_module(script_module)

    @staticmethod
    def get_script_from_module(module):
        return module.script

    async def reload_scripts(self):
        for is_live in (False, True):
            module = self.__class__.TRADING_SCRIPT_MODULE if is_live else self.__class__.BACKTESTING_SCRIPT_MODULE
            importlib.reload(module)
            self.register_script_module(module, live=is_live)
            # reload config
            await self.reload_config(self.exchange_manager.bot_id)
            if is_live:
                # todo cancel and restart live tasks
                await self.start_over_database()

    async def start_over_database(self):
        await modes_util.clear_plotting_cache(self)
        symbol_db = databases.RunDatabasesProvider.instance().get_symbol_db(self.bot_id,
                                                                            self.exchange_manager.exchange_name,
                                                                            self.symbol)
        symbol_db.set_initialized_flags(False)
        for producer in self.producers:
            for time_frame, call_args in producer.last_call_by_timeframe.items():
                run_db = databases.RunDatabasesProvider.instance().get_run_db(self.bot_id)
                await producer.init_user_inputs(False)
                run_db.set_initialized_flags(False, (time_frame, ))
                await databases.CacheManager().close_cache(commons_constants.UNPROVIDED_CACHE_IDENTIFIER,
                                                           reset_cache_db_ids=True)
                await producer.call_script(*call_args)
                await run_db.flush()

    def set_initialized_trading_pair_by_bot_id(self, symbol, time_frame, initialized):
        # todo migrate to event tree
        try:
            self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][self.exchange_manager.exchange_name][
                symbol][time_frame] = initialized
        except KeyError:
            if self.bot_id not in self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID:
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id] = {}
            if self.exchange_manager.exchange_name not in \
                    self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id]:
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][self.exchange_manager.exchange_name] = {}
            if symbol not in \
                    self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][self.exchange_manager.exchange_name]:
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name][symbol] = {}
            if time_frame not in \
                    self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][self.exchange_manager.exchange_name][
                        symbol]:
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][self.exchange_manager.exchange_name][
                    symbol][time_frame] = initialized

    def get_initialized_trading_pair_by_bot_id(self, symbol, time_frame):
        try:
            return self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][self.exchange_manager.exchange_name][
                    symbol][time_frame]
        except KeyError:
            return False

    async def get_additional_metadata(self, _):
        return {
            commons_enums.BacktestingMetadata.NAME.value: self.script_name
        }


class AbstractScriptedTradingModeProducer(modes_channel.AbstractTradingModeProducer):

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.last_call_by_timeframe = {}

    async def start(self) -> None:
        await super().start()
        # refresh user inputs
        if not self.exchange_manager.is_backtesting:
            await self._schedule_initialization_call()

    async def _schedule_initialization_call(self):
        # initialization call is a special call that does not trigger trades and allows the script
        # to be run at least once in order to initialize its configuration
        if self.exchange_manager.is_backtesting:
            # not necessary in backtesting
            return

        # fake a full candle call
        cryptocurrency, symbol, time_frame = self._get_initialization_call_args()
        # wait for symbol data to be initialized
        candle = await self._wait_for_symbol_init(symbol, time_frame, self._get_config_init_timeout())
        if candle is None:
            self.logger.error(f"Can't initialize trading script: {symbol} {time_frame} candles are not fetched")
        await self.ohlcv_callback(self.exchange_name, self.exchange_manager.id, cryptocurrency, symbol, time_frame,
                                  candle, init_call=True)

    async def _wait_for_symbol_init(self, symbol, time_frame, timeout):
        if not await super()._wait_for_symbol_init(symbol, time_frame, timeout):
            return None
        return self._get_latest_full_candle(symbol, time_frame)

    def _get_latest_full_candle(self, symbol, time_frame):
        tf = commons_enums.TimeFrames(time_frame)
        candles_manager = self.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
            symbol,
            allow_creation=False) \
            .symbol_candles[tf]
        candle_data = candles_manager.get_candles(5)
        current_time = self.exchange_manager.exchange.get_exchange_current_time()
        time_frame_sec = commons_enums.TimeFramesMinutes[tf] * commons_constants.MINUTE_TO_SECONDS
        last_full_candle_time = current_time - current_time % time_frame_sec - time_frame_sec
        for candle in reversed(candle_data):
            if candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] == last_full_candle_time:
                return candle
        # return the candle right before the last (last being in construction)
        return candle_data[-2]

    def _get_initialization_call_args(self):
        currency = next(iter(self.exchange_manager.exchange_config.traded_cryptocurrencies))
        symbol = self.exchange_manager.exchange_config.traded_cryptocurrencies[currency][0]
        time_frame = self.exchange_manager.exchange_config.traded_time_frames[0]
        return currency, symbol, time_frame.value

    async def ohlcv_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                             time_frame: str, candle: dict, init_call: bool = False):
        async with self.trading_mode_trigger(), self.trading_mode.remote_signal_publisher(symbol):
            # add a full candle to time to get the real time
            trigger_time = candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value] + \
                           commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame)] * \
                           commons_constants.MINUTE_TO_SECONDS
            await self.call_script(self.matrix_id, cryptocurrency, symbol, time_frame,
                                   commons_enums.TriggerSource.OHLCV.value,
                                   trigger_time,
                                   candle=candle,
                                   init_call=init_call)

    async def kline_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                             time_frame, kline: dict):
        async with self.trading_mode_trigger(), self.trading_mode.remote_signal_publisher(symbol):
            await self.call_script(self.matrix_id, cryptocurrency, symbol, time_frame,
                                   commons_enums.TriggerSource.KLINE.value,
                                   kline[commons_enums.PriceIndexes.IND_PRICE_TIME.value],
                                   kline=kline)

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        await self.call_script(matrix_id, cryptocurrency, symbol, time_frame, trigger_source,
                               self._get_latest_eval_time(matrix_id, cryptocurrency, symbol, time_frame))

    def _get_latest_eval_time(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame):
        try:
            import octobot_evaluators.matrix as matrix
            import octobot_evaluators.enums as evaluators_enums
            return matrix.get_latest_eval_time(matrix_id,
                                               exchange_name=self.exchange_name,
                                               tentacle_type=evaluators_enums.EvaluatorMatrixTypes.SCRIPTED.value,
                                               cryptocurrency=cryptocurrency,
                                               symbol=symbol,
                                               time_frame=time_frame)
        except ImportError:
            self.logger.error("OctoBot-Evaluators is required for a matrix callback")
            return None

    async def call_script(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame: str,
                          trigger_source: str, trigger_cache_timestamp: float,
                          candle: dict = None, kline: dict = None, init_call: bool = False):
        context = context_management.get_full_context(
            self.trading_mode, matrix_id, cryptocurrency, symbol, time_frame,
            trigger_source, trigger_cache_timestamp, candle, kline, init_call=init_call
        )
        self.last_call_by_timeframe[time_frame] = \
            (matrix_id, cryptocurrency, symbol, time_frame, trigger_source, trigger_cache_timestamp, candle, kline, init_call)
        context.matrix_id = matrix_id
        context.cryptocurrency = cryptocurrency
        context.symbol = symbol
        context.time_frame = time_frame
        initialized = True
        run_data_writer = databases.RunDatabasesProvider.instance().get_run_db(self.exchange_manager.bot_id)
        try:
            await self._pre_script_call(context)
            await self.trading_mode.get_script(live=True)(context)
        except errors.UnreachableExchange:
            raise
        except (commons_errors.MissingDataError, commons_errors.ExecutionAborted) as e:
            self.logger.debug(f"Script execution aborted: {e}")
            initialized = run_data_writer.are_data_initialized
        except Exception as e:
            self.logger.exception(e, True, f"Error when running script: {e}")
        finally:
            if not self.exchange_manager.is_backtesting:
                if context.has_cache(context.symbol, context.time_frame):
                    await context.get_cache().flush()
                for symbol in self.exchange_manager.exchange_config.traded_symbol_pairs:
                    await databases.RunDatabasesProvider.instance().get_symbol_db(
                        self.exchange_manager.bot_id,
                        self.exchange_manager.exchange_name,
                        symbol
                    ).flush()
            run_data_writer.set_initialized_flags(initialized)
            databases.RunDatabasesProvider.instance().get_symbol_db(self.exchange_manager.bot_id,
                                                                  self.exchange_name, symbol)\
                .set_initialized_flags(initialized, (time_frame,))

    async def _pre_script_call(self, context):
        await basic_keywords.set_leverage(context, await basic_keywords.user_select_leverage(context))

    async def post_trigger(self):
        if not self.exchange_manager.is_backtesting:
            # update db after each run only in live mode
            for database in self.all_databases().values():
                if database:
                    try:
                        await database.flush()
                    except Exception as err:
                        self.logger.exception(err, True, f"Error when flushing database: {err}")
