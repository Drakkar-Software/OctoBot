# pylint: disable=W0706
#  Drakkar-Software OctoBot-Trading
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
import contextlib
import copy

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.symbols as symbol_util
import octobot_commons.errors as common_errors
import octobot_commons.databases as databases
import octobot_commons.display as commons_display
import octobot_commons.optimization_campaign as optimization_campaign
import octobot_commons.tree.base_tree as event_tree
import octobot_commons.signals as signals
import octobot_backtesting.api as backtesting_api
import octobot_trading.modes as modes
import octobot_trading.signals as trading_signals
import octobot_trading.storage.util as storage_util
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_tentacles_manager.models as tentacles_manager_models


def get_base_context(trading_mode, symbol=None, init_call=False):
    return get_full_context(trading_mode, None, None, symbol, None, None, None, None, None, init_call=init_call)


def get_full_context(trading_mode, matrix_id, cryptocurrency, symbol, time_frame, trigger_source, trigger_cache_timestamp,
                     candle, kline, init_call=False):
    context = Context(
        trading_mode,
        trading_mode.exchange_manager,
        trading_mode.exchange_manager.trader,
        trading_mode.exchange_manager.exchange_name,
        symbol or trading_mode.symbol,
        matrix_id,
        cryptocurrency,
        time_frame,
        trading_mode.logger,
        trading_mode.__class__,
        trigger_cache_timestamp,
        trigger_source,
        candle or kline,
        None,
        None,
    )
    context.enable_trading = not init_call
    return context


class Context(databases.CacheClient):
    def __init__(
        self,
        tentacle,
        exchange_manager,
        trader,
        exchange_name,
        traded_pair,
        matrix_id,
        cryptocurrency,
        time_frame,
        logger,
        trading_mode_class,
        trigger_cache_timestamp,
        trigger_source,
        trigger_value,
        backtesting_id,
        optimizer_id,
        optimization_campaign_name=None,
        backtesting_analysis_settings=None,
    ):
        # no cache if live trading to ensure cache is always writen
        super().__init__(
            tentacle,
            exchange_name,
            traded_pair,
            time_frame,
            exchange_manager.tentacles_setup_config if exchange_manager else None,
            not exchange_manager.is_backtesting if exchange_manager else False
        )
        self.backtesting_analysis_settings = backtesting_analysis_settings
        self.exchange_manager = exchange_manager
        self.trader = trader
        self.matrix_id = matrix_id
        self.cryptocurrency = cryptocurrency
        self.logger = logger
        bot_id = exchange_manager.bot_id if \
            (exchange_manager is not None) \
            and (exchange_manager.bot_id is not None) \
            and databases.RunDatabasesProvider.instance().is_storage_enabled(
                exchange_manager.bot_id
            ) else None
        self.run_data_writer = self.orders_writer = self.trades_writer = self.transaction_writer = self.symbol_writer \
            = None
        if bot_id:
            self.run_data_writer = databases.RunDatabasesProvider.instance().get_run_db(bot_id)
            account_type = None
            if self.exchange_manager is not None:
                account_type = storage_util.get_account_type_suffix_from_exchange_manager(self.exchange_manager)
            elif self.run_data_writer is not None:
                account_type = storage_util.get_account_type_suffix_from_run_metadata(self.run_data_writer)
            self.symbol_writer = databases.RunDatabasesProvider.instance().get_symbol_db(
                bot_id, self.exchange_name, self.symbol
            ) if self.symbol else None
            if account_type is not None:
                self.orders_writer = databases.RunDatabasesProvider.instance().get_orders_db(
                    bot_id, account_type, self.exchange_name
                )
                self.trades_writer = databases.RunDatabasesProvider.instance().get_trades_db(
                    bot_id, account_type, self.exchange_name
                )
                self.transaction_writer = databases.RunDatabasesProvider.instance().get_transactions_db(
                    bot_id, account_type, self.exchange_name
                )
        self.trading_mode_class = trading_mode_class
        self.trigger_cache_timestamp = trigger_cache_timestamp
        self.trigger_source = trigger_source
        self.trigger_value = trigger_value
        self._sanitized_traded_pair = symbol_util.merge_symbol(self.symbol) \
            if self.symbol else self.symbol
        self.backtesting_id = backtesting_id
        self.optimizer_id = optimizer_id
        self.allow_artificial_orders = False
        self.plot_orders = False
        self.just_created_orders = []

        self.enable_trading = True

        # nested calls management
        self.top_level_tentacle = tentacle
        self.is_nested_tentacle = False
        self.nested_depth = 0
        self.nested_config_names = []
        self.tentacles_requirements = tentacles_manager_models.TentacleRequirementsTree(self.tentacle, self.config_name)
        self.parent_tentacles_requirements = None
        self.optimization_campaign_name = optimization_campaign_name
        self.signal_builder = None

    def get_signal_builder(self) -> "trading_signals.TradingSignalBundleBuilder":
        if self.signal_builder is None:
            self.signal_builder = trading_signals.TradingSignalBundleBuilder(
                self.tentacle.get_trading_signal_identifier(),
                self.tentacle.get_name()
            )
        return self.signal_builder

    def is_trading_signal_emitter(self):
        try:
            return modes.is_trading_signal_emitter(self.tentacle)
        except AttributeError:
            return False

    def set_is_trading_signal_emitter(self, is_trading_signal_emitter):
        self.tentacle.trading_config[common_constants.CONFIG_EMIT_TRADING_SIGNALS] = is_trading_signal_emitter

    async def emit_signal(self):
        if self.signal_builder is None or not self.is_trading_signal_emitter() or self.exchange_manager.is_backtesting:
            return
        signal_bundle = self.signal_builder.build()
        self.logger.debug(f"Emitting trading signal for {self.signal_builder.strategy}: {signal_bundle}")
        await signals.emit_signal_bundle(
            signal_bundle
        )
        self.signal_builder.reset()

    @contextlib.contextmanager
    def adapted_trigger_timestamp(self, tentacle_class, config_name):
        previous_trigger_cache_timestamp = self.trigger_cache_timestamp
        try:
            if isinstance(self.tentacle, modes.AbstractTradingMode) and \
                    self.trigger_source == common_enums.TriggerSource.EVALUATION_MATRIX.value:
                # only trading modes can have a delayed trigger timestamp when they are waken up from evaluators
                self.trigger_cache_timestamp = self._get_adapted_trigger_timestamp(tentacle_class,
                                                                                   previous_trigger_cache_timestamp,
                                                                                   config_name)
            yield self
        finally:
            self.trigger_cache_timestamp = previous_trigger_cache_timestamp

    @contextlib.asynccontextmanager
    async def local_nested_tentacle_config(self, tentacle_class, config_name, is_nested_tentacle):
        previous_is_nested_tentacle = self.is_nested_tentacle
        previous_config_name = self.config_name
        previous_parent_tentacles_requirements = self.parent_tentacles_requirements
        previous_tentacle_requirements = self.tentacles_requirements
        try:
            self.is_nested_tentacle = is_nested_tentacle
            self.config_name = config_name
            self.nested_depth += 1
            self.nested_config_names.append(config_name)
            self.parent_tentacles_requirements = self.tentacles_requirements
            # self.tentacles_requirements.get_requirement might return None on the 1st call,
            # it will be populated during this first call
            self.tentacles_requirements = self.tentacles_requirements.get_requirement(tentacle_class, config_name)
            yield self
        finally:
            self.is_nested_tentacle = previous_is_nested_tentacle
            self.config_name = previous_config_name
            self.parent_tentacles_requirements = previous_parent_tentacles_requirements
            self.tentacles_requirements = previous_tentacle_requirements
            self.nested_depth -= 1
            del self.nested_config_names[-1]
            if self._requires_cache_sync_synchronization():
                # if tentacles requirements changed: reset cache of this tentacle to include the new requirements
                await self._reset_cache()

    @staticmethod
    def minimal(trading_mode_class, logger, exchange_name, traded_pair, backtesting_id,
                optimizer_id, optimization_campaign_name, backtesting_analysis_settings):
        return Context(
            None,
            None,
            None,
            exchange_name,
            traded_pair,
            None,
            None,
            None,
            logger,
            trading_mode_class,
            None,
            None,
            None,
            backtesting_id,
            optimizer_id,
            optimization_campaign_name,
            backtesting_analysis_settings,
        )

    @contextlib.asynccontextmanager
    async def nested_call_context(self, tentacle):
        context = Context(
            tentacle,
            self.exchange_manager,
            self.trader,
            self.exchange_name,
            self.symbol,
            self.matrix_id,
            self.cryptocurrency,
            self.time_frame,
            self.logger,
            self.trading_mode_class,
            self.trigger_cache_timestamp,
            self.trigger_source,
            self.trigger_value,
            self.backtesting_id,
            self.optimizer_id
        )
        context.is_nested_tentacle = self.is_nested_tentacle
        context.config_name = self.config_name
        context.nested_depth = self.nested_depth
        context.nested_config_names = copy.copy(self.nested_config_names)
        # always keep top level tentacle
        context.top_level_tentacle = self.top_level_tentacle
        context.tentacles_requirements = self.tentacles_requirements  # keep the same tentacles_requirements
        context.parent_tentacles_requirements = self.parent_tentacles_requirements
        context.add_tentacle_requirement_from_nested_context(tentacle, context.config_name)
        try:
            yield context
        finally:
            if not self.exchange_manager.is_backtesting:
                # when not in backtesting, make sure to flush the cache after nested call
                await context.get_cache().flush()

    def add_tentacle_requirement_from_nested_context(self, tentacle, config_name) \
            -> (bool, tentacles_manager_models.TentacleRequirementsTree):
        """
        Used to add a requirement to a tentacle that has been triggered. Allows initialise its cache.
        Updates self.tentacles_requirements and self.parent_tentacles_requirements
        :param tentacle: the required tentacle tentacle
        :param config_name: its configuration name
        :return True if the requirement was not already registered and the created requirement
        """
        # self.tentacles_requirements might be None during the 1st nested call as it is retrieved from
        # the parent context. At 1st call, it has not yet been initialized
        if self.tentacles_requirements is None:
            self.tentacles_requirements = tentacles_manager_models.TentacleRequirementsTree(tentacle, config_name)
        return self.parent_tentacles_requirements.add_requirement(self.tentacles_requirements), \
            self.tentacles_requirements

    def add_referenced_tentacle_requirement(self, tentacle_class, config_name) \
            -> (bool, tentacles_manager_models.TentacleRequirementsTree):
        """
        Used to add a requirement to a tentacle that was already triggered. Does not allow to initialise its cache.
        Only updates self.tentacles_requirements.
        Does not update self.parent_tentacles_requirements is it should already contain a reference to
        self.tentacles_requirements from the previous trigger. Even if it was called, resetting its cache would fail
        because there is no available tentacle instance to get its configuration from (only a class is available).
        Set the return requirement tentacle attribute to allow cache initialization
        :param tentacle_class: the required tentacle class
        :param config_name: its configuration name
        :return True if the requirement was not already registered and the created requirement
        """
        requirement = tentacles_manager_models.TentacleRequirementsTree(None, config_name, tentacle_class=tentacle_class)
        return self.tentacles_requirements.add_requirement(requirement), requirement

    def _get_adapted_trigger_timestamp(self, tentacle_class, base_trigger_timestamp, config_name):
        try:
            if self.has_cache(self.symbol, self.time_frame, tentacle_name=tentacle_class.get_name(),
                              config_name=config_name):
                cache = self.get_cache(tentacle_name=tentacle_class.get_name(), config_name=config_name)
                if cache.metadata.get(common_enums.CacheDatabaseColumns.TRIGGERED_AFTER_CANDLES_CLOSE.value, False):
                    return base_trigger_timestamp - \
                           common_enums.TimeFramesMinutes[common_enums.TimeFrames(self.time_frame)] * \
                           common_constants.MINUTE_TO_SECONDS
            return base_trigger_timestamp
        except common_errors.NoCacheValue:
            # should not happen
            raise

    def get_cache_registered_requirements(self, tentacle_name=None, config_name=None):
        try:
            return self.cache_manager.get_cache_registered_requirements(
                tentacle_name or self.tentacle.get_name(),
                self.exchange_name,
                self.symbol,
                self.time_frame,
                config_name or self.config_name
            )
        except event_tree.NodeExistsError:
            return None

    async def ensure_tentacle_cache_requirements(self, tentacle_class, config_name):
        """
        Takes into account a tentacle and its config_name to identify cache.
        Requires the given tentacle to have been called previously as this method is not
        initializing this tentacle cache but only binding to it
        """
        added, requirement = self.add_referenced_tentacle_requirement(tentacle_class, config_name)
        if added and self._requires_cache_sync_synchronization():
            # build a new tentacle instance with appropriate config (from previous trigger) to use it as requirement
            config_name, _, _, tentacles_setup_config, _ = \
                self.get_tentacle_config_elements(tentacle_class, config_name, None)
            # use already registered requirement to access its configuration (config might be updated during script run)
            registered_requirement = self.get_cache_registered_requirements(tentacle_class.get_name(), config_name)
            try:
                import octobot_evaluators.evaluators as evaluators
                requirement.tentacle = evaluators.create_temporary_evaluator_with_local_config(
                    tentacle_class,
                    tentacles_setup_config,
                    registered_requirement.tentacle_config
                )
            except ImportError:
                self.logger.error("Octobot-Evaluators is required for ensure_tentacle_cache_requirements")
            await self._reset_cache()

    @staticmethod
    def get_config_name_or_default(tentacle_class, config_name):
        return f"nested_{tentacle_class.get_name()}_config" if config_name is None else config_name

    def get_tentacle_config_elements(self, tentacle_class, config_name, config):
        config_name = self.get_config_name_or_default(tentacle_class, config_name)
        cleaned_config_name = config_name.replace(" ", "_")
        config = {key.replace(" ", "_"): val for key, val in config.items()} if config else {}
        tentacles_setup_config = self.tentacle.tentacles_setup_config \
            if hasattr(self.tentacle, "tentacles_setup_config") else self.exchange_manager.tentacles_setup_config
        return config_name, cleaned_config_name, config, tentacles_setup_config, self.tentacle.get_local_config()

    def _requires_cache_sync_synchronization(self):
        registered_requirements = self.get_cache_registered_requirements()
        return registered_requirements is not None and not registered_requirements.includes_nested_requirements(
                self.tentacles_requirements
        )

    async def _reset_cache(self):
        previous_cache_requirements = self.get_cache_registered_requirements()
        await self.cache_manager.reset_cache(
            self.tentacle.get_name(), self.exchange_name, self.symbol, self.time_frame, self.config_name
        )
        self.init_cache()
        self.logger.debug(f"Replaced cache for {self.tentacle.get_name()} ({self.config_name}) to include "
                          f"{self.get_cache_registered_requirements()} requirements (previously was "
                          f"{previous_cache_requirements}")

    def ensure_no_missing_cached_value(self, is_missing):
        if is_missing:
            raise common_errors.NoCacheValue(
                f"No cache value for {self.trigger_cache_timestamp} with cache "
                f"key: {common_enums.CacheDatabaseColumns.VALUE.value} on {self.tentacle}. Impossible process "
                f"{common_constants.DO_NOT_OVERRIDE_CACHE} return value.")

    def init_cache(self):
        self.get_cache()

    async def get_cached_value(self,
                               value_key: str = common_enums.CacheDatabaseColumns.VALUE.value,
                               cache_key=None,
                               tentacle_name=None,
                               config_name=None,
                               ignore_requirement=False) -> tuple:
        """
        Get a value for the current cache
        :param value_key: identifier of the value
        :param cache_key: timestamp to use in order to look for a value
        :param tentacle_name: name of the tentacle to get cache from
        :param config_name: name of the tentacle configuration as used in nested tentacle calls
        :return: the cached value and a boolean (True if cached value is missing from cache)
        :param ignore_requirement: if True, tentacle_name will not be added as a requirement from this call
        """
        try:
            return await super().get_cached_value(
                value_key=value_key,
                cache_key=cache_key or self.trigger_cache_timestamp,
                tentacle_name=tentacle_name,
                config_name=config_name
            )
        finally:
            if not ignore_requirement:
                await self._try_add_tentacle_as_cache_requirement(tentacle_name, config_name)

    async def get_cached_values(self,
                                value_key: str = common_enums.CacheDatabaseColumns.VALUE.value,
                                cache_key=None,
                                limit=-1,
                                tentacle_name=None,
                                config_name=None,
                                bound_to_backtesting_time=True,
                                ignore_requirement=False) -> list:
        """
        Get a value for the current cache within the current backtesting boundaries
        :param value_key: identifier of the value
        :param cache_key: timestamp to use in order to look for a value
        :param limit: the maximum number elements to select (no limit by default)
        :param tentacle_name: name of the tentacle to get cache from
        :param config_name: name of the tentacle configuration as used in nested tentacle calls
        :param bound_to_backtesting_time: only select cache from values within the current total backtesting time window
        :param ignore_requirement: if True, tentacle_name will not be added as a requirement from this call
        :return: the cached values
        """
        try:
            min_timestamp = 0
            max_timestamp = cache_key or self.trigger_cache_timestamp
            if bound_to_backtesting_time and self.exchange_manager.is_backtesting:
                min_timestamp = backtesting_api.get_backtesting_starting_time(
                    self.exchange_manager.exchange.backtesting)
                max_timestamp = min(cache_key or self.trigger_cache_timestamp,
                                    backtesting_api.get_backtesting_ending_time(
                                        self.exchange_manager.exchange.backtesting))

            return await self.get_cache(tentacle_name=tentacle_name, config_name=config_name) \
                .get_values(max_timestamp, name=value_key, limit=limit,
                            min_timestamp=min_timestamp)

        except common_errors.NoCacheValue:
            return []
        finally:
            if not ignore_requirement:
                await self._try_add_tentacle_as_cache_requirement(tentacle_name, config_name)

    async def _try_add_tentacle_as_cache_requirement(self, tentacle_name, config_name):
        try:
            if tentacle_name is not None:
                tentacle_class = tentacles_manager_api.get_tentacle_class_from_string(tentacle_name) \
                    if isinstance(tentacle_name, str) else tentacle_name
                await self.ensure_tentacle_cache_requirements(tentacle_class, config_name)
        except Exception as e:
            self.logger.exception(e, True, f"Error when adding tentacle as a requirement {e}")

    async def set_cached_value(self, value, value_key: str = common_enums.CacheDatabaseColumns.VALUE.value,
                               cache_key=None, flush_if_necessary=False, tentacle_name=None, config_name=None,
                               **kwargs):
        """
        Set a value into the current cache
        :param value: value to set
        :param value_key: identifier of the value
        :param cache_key: timestamp to associate the value to
        :param flush_if_necessary: flush the cache after set (write into database)
        :param tentacle_name: name of the tentacle to get cache from
        :param config_name: name of the tentacle configuration as used in nested tentacle calls
        :param kwargs: other related value_key / value couples to set at this timestamp. Use for plotted data
        :return: None
        """
        return await super().set_cached_value(
            value,
            value_key=value_key,
            cache_key=cache_key or self.trigger_cache_timestamp,
            flush_if_necessary=flush_if_necessary,
            tentacle_name=tentacle_name,
            config_name=config_name,
            **kwargs
        )

    @contextlib.asynccontextmanager
    async def backtesting_results(self, with_lock=False, cache_size=None, database_adaptor=databases.TinyDBAdaptor):
        display = commons_display.display_translator_factory()
        run_dbs_identifier = databases.RunDatabasesIdentifier(
            self.trading_mode_class,
            self.optimization_campaign_name or optimization_campaign.OptimizationCampaign.get_campaign_name(),
            database_adaptor=database_adaptor,
            backtesting_id=self.backtesting_id,
            optimizer_id=self.optimizer_id,
            context=self
        )
        if not await run_dbs_identifier.exchange_base_identifier_exists(self.exchange_name):
            single_exchange = await run_dbs_identifier.get_single_existing_exchange()
            if single_exchange is None:
                # no single exchange with data
                raise common_errors.MissingExchangeDataError(
                    f"No data for {self.exchange_name}. This run might have happened on other exchange(s)"
                )
            else:
                # retarget run_dbs_identifier to use single_exchange instead
                self.exchange_name = single_exchange
        async with databases.MetaDatabase.database(run_dbs_identifier, with_lock=with_lock,
                                                   cache_size=cache_size) as meta_db:
            yield meta_db, display
