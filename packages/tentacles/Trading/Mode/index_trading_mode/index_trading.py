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
import decimal
import enum
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.authentication as authentication
import octobot_commons.signals as commons_signals
import octobot_trading.constants as trading_constants
import octobot_trading.dsl as trading_dsl
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes as trading_modes
import octobot_trading.util as trading_util
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.signals as signals

import octobot_copy.constants as octobot_copy_constants
import octobot_copy.rebalancing as rebalancer
import octobot_copy.errors as copy_errors
import octobot_copy.enums as rebalancer_enums
import octobot_copy.exchange.exchange_interface as exchange_interface
import octobot_copy.rebalancing.planner
import octobot_copy.rebalancing.rebalancing_client_interface as rebalancing_client_interface


class IndexActivity(enum.Enum):
    REBALANCING_DONE = "rebalancing_done"
    REBALANCING_SKIPPED = "rebalancing_skipped"


class RebalanceSkipDetails(enum.Enum):
    ALREADY_BALANCED = "already_balanced"
    NOT_ENOUGH_AVAILABLE_FOUNDS = "not_enough_available_founds"


DEFAULT_QUOTE_ASSET_REBALANCE_TRIGGER_MIN_RATIO = 0.1  # 10%
DEFAULT_REBALANCE_TRIGGER_MIN_RATIO = 0.05  # 5%


class IndexTradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.trading_mode: IndexTradingMode = typing.cast(IndexTradingMode, self.trading_mode)
        self._already_logged_aborted_rebalance_error = False

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        details = kwargs[self.CREATE_ORDER_DATA_PARAM]
        dependencies = kwargs.get(self.CREATE_ORDER_DEPENDENCIES_PARAM, None)
        if state == trading_enums.EvaluatorStates.NEUTRAL.value:
            try:
                self.trading_mode.is_processing_rebalance = True
                return await self._rebalance_portfolio(details, dependencies)
            finally:
                self.trading_mode.is_processing_rebalance = False
        self.logger.error(f"Unknown index state: {state}")
        return []
    
    async def _rebalance_portfolio(self, details: dict, initial_dependencies: typing.Optional[commons_signals.SignalDependencies]):
        self.logger.info(f"Executing rebalance on [{self.exchange_manager.exchange_name}]")
        orders = []
        if self.trading_mode.rebalance_actions_planner is None:
            self.logger.error("Rebalance aborted: rebalance_actions_planner is not initialized")
            return orders
        self.trading_mode._sync_rebalance_planner()
        portfolio_rebalancer = self.trading_mode.create_rebalancer(self.exchange_manager)
        try:
            # 1. make sure we can actually rebalance the portfolio
            self.logger.info("Step 1/3: ensuring enough funds are available for rebalance")
            await portfolio_rebalancer.ensure_enough_funds_to_buy_after_selling()
            # 2. sell indexed coins for reference market
            is_simple_buy_without_selling = portfolio_rebalancer.can_simply_buy_coins_without_selling(details)
            sell_orders_dependencies = initial_dependencies
            if is_simple_buy_without_selling:
                self.logger.info(
                    f"Step 2/3: skipped: no coin to sell for "
                    f"{self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market}"
                )
            else:
                self.logger.info(
                    f"Step 2/3: selling coins to free "
                    f"{self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market}"
                )
                orders += await portfolio_rebalancer.sell_targeted_coins_for_reference_market(details, initial_dependencies)
                sell_orders_dependencies = signals.get_orders_dependencies(orders)
            # 3. split reference market into indexed coins
            self.logger.info(
                f"Step 3/3: buying coins using "
                f"{self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market}"
            )
            orders += await portfolio_rebalancer.split_reference_market_into_targeted_coins(
                details,
                is_simple_buy_without_selling,
                sell_orders_dependencies,
            )
            # reset flag to relog if a next rebalance is aborted
            self._already_logged_aborted_rebalance_error = False
        except (trading_errors.MissingMinimalExchangeTradeVolume, copy_errors.RebalanceAborted) as err:
            log_level = self.logger.warning
            if isinstance(err, copy_errors.RebalanceAborted) and not self._already_logged_aborted_rebalance_error:
                log_level = self.logger.error
                self._already_logged_aborted_rebalance_error = True
            log_level(
                f"Aborting rebalance on {self.exchange_manager.exchange_name}: {err} ({err.__class__.__name__})"
            )
            self._update_producer_last_activity(
                IndexActivity.REBALANCING_SKIPPED,
                RebalanceSkipDetails.NOT_ENOUGH_AVAILABLE_FOUNDS.value
            )
        finally:
            self.logger.info("Portoflio rebalance process complete")
        return orders


class IndexTradingModeProducer(trading_modes.AbstractTradingModeProducer):
    REFRESH_INTERVAL = "refresh_interval"
    CANCEL_OPEN_ORDERS = "cancel_open_orders"
    ALLOW_SKIP_ASSET = "allow_skip_asset"
    REBALANCE_TRIGGER_MIN_PERCENT = octobot_copy_constants.CONFIG_REBALANCE_TRIGGER_MIN_PERCENT
    SELECTED_REBALANCE_TRIGGER_PROFILE = octobot_copy_constants.CONFIG_SELECTED_REBALANCE_TRIGGER_PROFILE
    REBALANCE_TRIGGER_PROFILES = octobot_copy_constants.CONFIG_REBALANCE_TRIGGER_PROFILES
    REBALANCE_TRIGGER_PROFILE_NAME = octobot_copy_constants.CONFIG_REBALANCE_TRIGGER_PROFILE_NAME
    REBALANCE_TRIGGER_PROFILE_MIN_PERCENT = octobot_copy_constants.CONFIG_REBALANCE_TRIGGER_PROFILE_MIN_PERCENT
    QUOTE_ASSET_REBALANCE_TRIGGER_MIN_PERCENT = "quote_asset_rebalance_trigger_min_percent"
    MIN_ORDER_SIZE_MARGIN = "min_order_size_margin"
    REFERENCE_MARKET_RATIO = "reference_market_ratio"
    SYNCHRONIZATION_POLICY = "synchronization_policy"
    SELL_UNINDEXED_TRADED_COINS = "sell_unindexed_traded_coins"
    INDEX_CONTENT = octobot_copy_constants.CONFIG_INDEX_CONTENT
    MIN_INDEXED_COINS = 1

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.trading_mode: IndexTradingMode = typing.cast(IndexTradingMode, self.trading_mode)
        self._last_trigger_time = 0
        self.state = trading_enums.EvaluatorStates.NEUTRAL

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        await super().stop()

    async def manual_trigger(
        self, matrix_id: str, cryptocurrency: str,
        symbol: str, time_frame, trigger_source: str
    ) -> None:
        return await self._check_index_if_necessary()

    async def ohlcv_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                             time_frame: str, candle: dict, init_call: bool = False):
        await self._check_index_if_necessary()

    async def kline_callback(self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str,
                             time_frame, kline: dict):
        await self._check_index_if_necessary()

    async def _check_index_if_necessary(self):
        current_time = self.exchange_manager.exchange.get_exchange_current_time()
        if (
            current_time - self._last_trigger_time
        ) >= self.trading_mode.refresh_interval_days * commons_constants.DAYS_TO_SECONDS:
            if self.trading_mode.automatically_update_historical_config_on_set_intervals():
                self.trading_mode.update_config_and_user_inputs_if_necessary()
            if self.trading_mode.is_processing_rebalance:
                self.logger.info(
                    f"[{self.exchange_manager.exchange_name}] Index is already being rebalanced, skipping index check"
                )
                return
            if len(self.trading_mode.indexed_coins) < self.MIN_INDEXED_COINS:
                self.logger.error(
                    f"At least {self.MIN_INDEXED_COINS} coin is required to maintain an index. Please "
                    f"select more trading pairs using "
                    f"{self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market} as "
                    f"quote currency."
                )
            else:
                self._notify_if_missing_too_many_coins()
                await self.ensure_index()
            if not self.trading_mode.is_updating_at_each_price_change():
                self.logger.debug(f"Next index check in {self.trading_mode.refresh_interval_days} days")
            self._last_trigger_time = current_time

    async def _prepare_indexed_coins(self):
        portfolio_rebalancer = self.trading_mode.create_rebalancer(self.exchange_manager)
        for coin in self.trading_mode.indexed_coins:
            await portfolio_rebalancer.prepare_coin_rebalancing(coin)

    def _get_full_traded_pairs(self):
        return self.exchange_manager.exchange_config.traded_symbol_pairs + self.exchange_manager.exchange_config.additional_traded_pairs

    async def _wait_for_topic_init(self, topic, topic_name, timeout) -> bool:
        """
        Wait for topic to be initialized. This ensures that existing topic data
        are loaded from the exchange before calculating holdings ratios.
        """
        try:
            full_symbols = self._get_full_traded_pairs()
            if full_symbols:
                await trading_util.wait_for_topic_init(
                    self.exchange_manager, timeout,
                    topic,
                    symbols=full_symbols
                )
            return True
        except (asyncio.TimeoutError,):
            self.logger.warning(
                f"{topic_name} initialization took more than {timeout} seconds. "
                f"Existing {topic_name} might not be reflected in holdings calculations."
            )
            return False

    async def _wait_for_positions_init(self, timeout) -> bool:
        if not (self.exchange_manager.is_future or self.exchange_manager.is_option):
            return True
        return await self._wait_for_topic_init(
            commons_enums.InitializationEventExchangeTopics.POSITIONS.value,
            "positions",
            timeout
        )

    async def _wait_for_orders_init(self, timeout) -> bool:
        return await self._wait_for_topic_init(
            commons_enums.InitializationEventExchangeTopics.ORDERS.value,
            "orders",
            timeout
        )

    @trading_modes.enabled_trader_only()
    async def ensure_index(self):
        await self._wait_for_symbol_prices_and_profitability_init(self._get_config_init_timeout())
        await self._prepare_indexed_coins()
        await self._register_traded_symbol_pairs_update()
        await self._wait_for_positions_init(self._get_config_init_timeout())
        await self._wait_for_orders_init(self._get_config_init_timeout())
        self.logger.info(
            f"Ensuring Index on [{self.exchange_manager.exchange_name}] "
            f"{len(self.trading_mode.indexed_coins)} coins: {self.trading_mode.indexed_coins} with reference market: "
            f"{self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market}"
        )
        dependencies = None
        if self.trading_mode.cancel_open_orders:
            dependencies = await self.cancel_traded_pairs_open_orders_if_any()
        if self.trading_mode.requires_initializing_appropriate_coins_distribution:
            self.trading_mode.ensure_updated_coins_distribution(adapt_to_holdings=True)
            self.trading_mode.requires_initializing_appropriate_coins_distribution = False
        is_rebalance_required, rebalance_details = self._get_rebalance_details()
        if is_rebalance_required:
            await self._trigger_rebalance(rebalance_details, dependencies)
            self.last_activity = trading_modes.TradingModeActivity(
                IndexActivity.REBALANCING_DONE,
                rebalance_details,
            )
        else:
            allowance = round(self.trading_mode.rebalance_trigger_min_ratio * trading_constants.ONE_HUNDRED, 2)
            self.logger.info(
                f"[{self.exchange_manager.exchange_name}] is following the index [+/-{allowance}%], no rebalance is required."
            )
            self.last_activity = trading_modes.TradingModeActivity(IndexActivity.REBALANCING_SKIPPED)

    async def _trigger_rebalance(self, rebalance_details: dict, dependencies: typing.Optional[commons_signals.SignalDependencies]):
        self.logger.info(
            f"Triggering rebalance on [{self.exchange_manager.exchange_name}] "
            f"with rebalance details: {rebalance_details}."
        )
        await self.submit_trading_evaluation(
            cryptocurrency=None,
            symbol=None,    # never set symbol in order to skip consumer.can_create_order check
            time_frame=None,
            final_note=None,
            state=trading_enums.EvaluatorStates.NEUTRAL,
            data=rebalance_details,
            dependencies=dependencies
        )
        # send_notification
        await self._send_alert_notification()

    async def _send_alert_notification(self):
        if self.exchange_manager.is_backtesting:
            return
        try:
            import octobot_services.api as services_api
            import octobot_services.enums as services_enum
            title = "Index trigger"
            alert = f"Rebalance triggered for {len(self.trading_mode.indexed_coins)} coins"
            await services_api.send_notification(services_api.create_notification(
                alert, title=title, markdown_text=alert,
                category=services_enum.NotificationCategory.PRICE_ALERTS
            ))
        except ImportError as e:
            self.logger.exception(e, True, f"Impossible to send notification: {e}")

    def _notify_if_missing_too_many_coins(self):
        if ideal_distribution := self.trading_mode.get_ideal_distribution(self.trading_mode.trading_config):
            if len(self.trading_mode.indexed_coins) < len(ideal_distribution) / 2:
                self.logger.error(
                    f"Less than half of configured coins can be traded on {self.exchange_manager.exchange_name}. "
                    f"Traded: {self.trading_mode.indexed_coins}, configured: {ideal_distribution}"
                )

    def _get_rebalance_details(self) -> typing.Tuple[bool, dict]:
        self.trading_mode._sync_rebalance_planner()
        return self.trading_mode.rebalance_actions_planner.get_rebalance_details()

    async def _register_traded_symbol_pairs_update(self):
        if self.trading_mode.indexed_coins:
            reference_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
            if self.exchange_manager.is_future or self.exchange_manager.is_option:
                added_pairs = [
                    coin
                    for coin in self.trading_mode.indexed_coins
                ]
            else:
                # on spot, add coins with the reference market as quote currency to trade
                added_pairs = [
                    symbol_util.merge_currencies(coin, reference_market)
                    for coin in self.trading_mode.indexed_coins
                ]
            self.logger.debug(f"Update traded symbol pair: {added_pairs}...")
            # TODO: remove the pairs when the coins are entirely removed from the index
            await self.exchange_manager.exchange_config.add_traded_symbols(added_pairs, [])

    def get_channels_registration(self):
        # use candles to trigger at each candle interval and when initializing
        topics = [
            self.TOPIC_TO_CHANNEL_NAME[commons_enums.ActivationTopics.FULL_CANDLES.value],
        ]
        if self.trading_mode.is_updating_at_each_price_change():
            # use kline to trigger at each price change
            self.logger.info(f"Using price change bound update instead of time-based update.")
            topics.append(
                self.TOPIC_TO_CHANNEL_NAME[commons_enums.ActivationTopics.IN_CONSTRUCTION_CANDLES.value]
            )
        return topics

    async def cancel_traded_pairs_open_orders_if_any(self) -> typing.Optional[commons_signals.SignalDependencies]:
        dependencies = commons_signals.SignalDependencies()
        if symbol_open_orders := [
            order
            for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders()
            if order.symbol in self.exchange_manager.exchange_config.traded_symbol_pairs
            and not isinstance(order, trading_personal_data.MarketOrder) # market orders can't be cancelled
        ]:
            self.logger.info(
                f"Cancelling {len(symbol_open_orders)} open orders"
            )
            for order in symbol_open_orders:
                try:
                    is_cancelled, dependency = await self.trading_mode.cancel_order(order)
                    if is_cancelled:
                        dependencies.extend(dependency)
                except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                    self.logger.warning(f"Skipped order cancel: {err}, order: {order}")
        return dependencies or None


class IndexTradingMode(trading_modes.AbstractTradingMode):
    MODE_PRODUCER_CLASSES = [IndexTradingModeProducer]
    MODE_CONSUMER_CLASSES = [IndexTradingModeConsumer]
    SUPPORTS_INITIAL_PORTFOLIO_OPTIMIZATION = True
    SUPPORTS_HEALTH_CHECK = False

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.refresh_interval_days = 1
        self.rebalance_trigger_min_ratio = decimal.Decimal(float(DEFAULT_REBALANCE_TRIGGER_MIN_RATIO))
        self.rebalance_trigger_profiles: typing.Optional[list] = None
        self.selected_rebalance_trigger_profile: typing.Optional[dict] = None
        self.sell_unindexed_traded_coins = True
        self.cancel_open_orders = True
        self.allow_skip_asset = False
        self.quote_asset_rebalance_ratio_threshold = decimal.Decimal(str(DEFAULT_QUOTE_ASSET_REBALANCE_TRIGGER_MIN_RATIO))
        self.reference_market_ratio = trading_constants.ONE
        self.min_order_size_margin = decimal.Decimal("2")
        self.synchronization_policy: rebalancer_enums.SynchronizationPolicy = rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
        self.requires_initializing_appropriate_coins_distribution = False
        self.indexed_coins_prices = {}
        self.is_processing_rebalance = False
        self.rebalance_actions_planner: octobot_copy.rebalancing.planner.HistoricalConfigurationRebalanceActionsPlanner = None # type: ignore
        if exchange_manager:
            self.rebalance_actions_planner = octobot_copy.rebalancing.planner.HistoricalConfigurationRebalanceActionsPlanner(
                exchange=exchange_interface.ExchangeInterface(exchange_manager, trading_mode=self),
                client=self._create_rebalancing_client(),
            )

    def _create_rebalancing_client(self) -> rebalancing_client_interface.RebalancingClientInterface:
        return rebalancing_client_interface.RebalancingClientInterface(
            client_name=self.get_name(),
            min_order_size_margin=self.min_order_size_margin,
            rebalance_trigger_min_ratio=self.rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=self.quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=self.reference_market_ratio,
            sell_untargeted_traded_coins=self.sell_unindexed_traded_coins,
            synchronization_policy=self.synchronization_policy,
            allow_skip_asset=self.allow_skip_asset,
            can_include_assets_in_open_orders_in_holdings_ratio=True,
            raise_all_order_errors=False,
            get_config=lambda: self.trading_config,
            get_previous_config=lambda: self.previous_trading_config,
            get_historical_configs=lambda ft, tt: self.get_historical_configs(ft, tt),
            get_ideal_distribution=self.get_ideal_distribution,
        )

    @property
    def ratio_per_asset(self) -> dict:
        if self.rebalance_actions_planner is None:
            return {}
        return self.rebalance_actions_planner.ratio_per_asset

    @ratio_per_asset.setter
    def ratio_per_asset(self, value: dict) -> None:
        if self.rebalance_actions_planner is not None:
            self.rebalance_actions_planner.ratio_per_asset = value

    @property
    def total_ratio_per_asset(self) -> decimal.Decimal:
        if self.rebalance_actions_planner is None:
            return trading_constants.ZERO
        return self.rebalance_actions_planner.total_ratio_per_asset

    @total_ratio_per_asset.setter
    def total_ratio_per_asset(self, value: decimal.Decimal) -> None:
        if self.rebalance_actions_planner is not None:
            self.rebalance_actions_planner.total_ratio_per_asset = value

    @property
    def indexed_coins(self) -> list:
        if self.rebalance_actions_planner is None:
            return []
        return self.rebalance_actions_planner.targeted_coins

    @indexed_coins.setter
    def indexed_coins(self, value: list) -> None:
        if self.rebalance_actions_planner is not None:
            self.rebalance_actions_planner.targeted_coins = value

    def _sync_rebalance_planner(self) -> None:
        if self.rebalance_actions_planner is None:
            return
        self.rebalance_actions_planner.update(
            min_order_size_margin=self.min_order_size_margin,
            synchronization_policy=self.synchronization_policy,
            rebalance_trigger_min_ratio=self.rebalance_trigger_min_ratio,
            quote_asset_rebalance_ratio_threshold=self.quote_asset_rebalance_ratio_threshold,
            reference_market_ratio=self.reference_market_ratio,
            sell_untargeted_traded_coins=self.sell_unindexed_traded_coins,
            allow_skip_asset=self.allow_skip_asset,
            can_include_assets_in_open_orders_in_holdings_ratio=True,
        )

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        trading_config = self.trading_config
        self.refresh_interval_days = float(self.UI.user_input(
            IndexTradingModeProducer.REFRESH_INTERVAL, commons_enums.UserInputTypes.FLOAT,
            self.refresh_interval_days, inputs,
            min_val=0,
            title="Trigger period: Days to wait between each rebalance. Can be a fraction of a day. "
                  "When set to 0, every new price will trigger a rebalance check.",
        ))
        self.quote_asset_rebalance_ratio_threshold = decimal.Decimal(str(self.UI.user_input(
            IndexTradingModeProducer.QUOTE_ASSET_REBALANCE_TRIGGER_MIN_PERCENT, commons_enums.UserInputTypes.FLOAT,
            float(self.quote_asset_rebalance_ratio_threshold * trading_constants.ONE_HUNDRED), inputs,
            min_val=0, max_val=100,
            title="Quote asset rebalance cap: maximum allowed percent holding of traded pairs' quote asset before "
                "triggering a rebalance. Useful to force a rebalance when adding quote asset to the portfolio",
        ))) / trading_constants.ONE_HUNDRED
        self.rebalance_trigger_min_ratio = decimal.Decimal(str(self.UI.user_input(
            IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT, commons_enums.UserInputTypes.FLOAT,
            float(self.rebalance_trigger_min_ratio * trading_constants.ONE_HUNDRED), inputs,
            min_val=0, max_val=100,
            title="Rebalance cap: maximum allowed percent holding of a coin beyond initial ratios before "
                  "triggering a rebalance.",
        ))) / trading_constants.ONE_HUNDRED
        self.reference_market_ratio = decimal.Decimal(str(self.UI.user_input(
            IndexTradingModeProducer.REFERENCE_MARKET_RATIO, commons_enums.UserInputTypes.FLOAT,
            float(self.reference_market_ratio * trading_constants.ONE_HUNDRED), inputs,
            min_val=0, max_val=100,
            title="Percentage of the portfolio to trade (distributed among indexed coins). "
                  "The remaining percentage will be kept in the reference market.",
        ))) / trading_constants.ONE_HUNDRED
        self.min_order_size_margin = decimal.Decimal(str(self.UI.user_input(
            IndexTradingModeProducer.MIN_ORDER_SIZE_MARGIN, commons_enums.UserInputTypes.FLOAT,
            float(self.min_order_size_margin), inputs,
            min_val=1,
            title="Min order size safety factor: ideal amount must be at least this multiple of the exchange min cost. "
                  "Higher values are more conservative.",
        )))

        self.rebalance_trigger_profiles = self.trading_config.get(IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES, None)
        if self.rebalance_trigger_profiles:
            # only display selector if there are profiles to display
            rebalance_trigger_profiles_inputs = [{
                IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME: self.UI.user_input(
                    IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME, commons_enums.UserInputTypes.TEXT,
                    "profile name", inputs,
                    parent_input_name=IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES,
                    array_indexes=[0],
                    title=f"Name: name of the reference trigger profile"
                ),
                IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT: self.UI.user_input(
                    IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT, commons_enums.UserInputTypes.FLOAT,
                    float(self.rebalance_trigger_min_ratio * trading_constants.ONE_HUNDRED), inputs,
                    parent_input_name=IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES,
                    array_indexes=[0],
                    min_val=0, max_val=100,
                    title=(
                    "Rebalance cap: maximum allowed percent holding of a coin beyond initial ratios before "
                    "triggering a rebalance when this profile is selected."
                    )
                ),
            }]
            self.UI.user_input(
                IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES, commons_enums.UserInputTypes.OBJECT_ARRAY, rebalance_trigger_profiles_inputs, inputs,
                other_schema_values={"minItems": 1, "uniqueItems": True},
                item_title="Rebalance trigger profile",
                title="Rebalance trigger profiles",
            )
            selected_rebalance_trigger_profile_name = self.UI.user_input(
                IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE, commons_enums.UserInputTypes.OPTIONS,
                None, inputs,
                options=[p[IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME] for p in self.rebalance_trigger_profiles],
                title="Selected rebalance trigger profile, override the default Rebalance cap value.",
            )
            selected_profile = [
                p for p in self.rebalance_trigger_profiles 
                if p[IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME] == selected_rebalance_trigger_profile_name
            ]
            if selected_profile:
                self.selected_rebalance_trigger_profile = selected_profile[0]
                # apply selected rebalance trigger profile ratio
                self.rebalance_trigger_min_ratio = decimal.Decimal(str(
                    self.selected_rebalance_trigger_profile[IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT])
                ) / trading_constants.ONE_HUNDRED
            else:
                self.logger.warning(
                    f"Selected rebalance trigger profile {selected_rebalance_trigger_profile_name} not found in rebalance trigger profiles: {self.rebalance_trigger_profiles}"
                )
                self.selected_rebalance_trigger_profile = None
        sync_policy: str = self.UI.user_input(
            IndexTradingModeProducer.SYNCHRONIZATION_POLICY, commons_enums.UserInputTypes.OPTIONS,
            self.synchronization_policy.value, inputs, 
            options=[p.value for p in rebalancer_enums.SynchronizationPolicy],
            editor_options={"enum_titles": [p.value.replace("_", " ") for p in rebalancer_enums.SynchronizationPolicy]},
            title="Synchronization policy: should coins that are removed from index be sold as soon as possible or only when rebalancing is triggered when coins don't follow the configured ratios.",
        )
        try:
            self.synchronization_policy = rebalancer_enums.SynchronizationPolicy(sync_policy)
        except ValueError as err:
            self.logger.exception(
                err, 
                True, 
                f"Impossible to parse synchronization policy: {err}. Using default policy: {self.synchronization_policy.value}."
            )
        self.cancel_open_orders = float(self.UI.user_input(
            IndexTradingModeProducer.CANCEL_OPEN_ORDERS, commons_enums.UserInputTypes.BOOLEAN,
            self.cancel_open_orders, inputs,
            title="Cancel open orders: When enabled, open orders of the index trading pairs will be canceled to free "
                  "funds and invest in the index content.",
        ))
        self.allow_skip_asset = bool(self.UI.user_input(
            IndexTradingModeProducer.ALLOW_SKIP_ASSET, commons_enums.UserInputTypes.BOOLEAN,
            self.allow_skip_asset, inputs,
            title="Allow skipping assets that don't meet minimum order size requirements instead of aborting portfolio rebalancing.",
        ))
        self.sell_unindexed_traded_coins = trading_config.get(
            IndexTradingModeProducer.SELL_UNINDEXED_TRADED_COINS,
            self.sell_unindexed_traded_coins
        )
        if (not self.exchange_manager or not self.exchange_manager.is_backtesting) and (
            authentication.Authenticator.instance().has_open_source_package() or self.synchronous_execution
        ):
            self.UI.user_input(IndexTradingModeProducer.INDEX_CONTENT, commons_enums.UserInputTypes.OBJECT_ARRAY,
                               trading_config.get(IndexTradingModeProducer.INDEX_CONTENT, None), inputs,
                               item_title="Coin",
                               other_schema_values={"minItems": 0, "uniqueItems": True},
                               title="Custom distribution: when used, only coins listed in this distribution and "
                                     "in your profile traded pairs will be traded. "
                                     "Leave empty to evenly allocate funds in each traded coin.")
            self.UI.user_input(rebalancer_enums.DistributionKeys.NAME, commons_enums.UserInputTypes.TEXT,
                               "BTC", inputs,
                               other_schema_values={"minLength": 1},
                               parent_input_name=IndexTradingModeProducer.INDEX_CONTENT,
                               title="Name of the coin.")
            self.UI.user_input(rebalancer_enums.DistributionKeys.VALUE, commons_enums.UserInputTypes.FLOAT,
                               50, inputs,
                               min_val=0,
                               parent_input_name=IndexTradingModeProducer.INDEX_CONTENT,
                               title="Weight of the coin within this distribution.")
        self.requires_initializing_appropriate_coins_distribution = self.synchronization_policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
        if self.rebalance_actions_planner is not None:
            self._sync_rebalance_planner()
            self.rebalance_actions_planner.update_distribution()

    @classmethod
    def get_tentacle_config_traded_symbols(cls, config: dict, reference_market: str) -> list:
        return [
            symbol_util.merge_currencies(asset[rebalancer_enums.DistributionKeys.NAME], reference_market)
            for asset in (cls.get_ideal_distribution(config) or [])
        ]

    @classmethod
    def get_dsl_dependencies(cls, trading_config: dict, config: dict) -> list:
        index_content = cls.get_ideal_distribution(trading_config)
        if not index_content:
            return []
        try:
            reference_market = trading_util.get_reference_market(config)
        except (KeyError, TypeError):
            reference_market = commons_constants.DEFAULT_REFERENCE_MARKET
        symbols = cls.get_tentacle_config_traded_symbols(trading_config, reference_market)
        return [trading_dsl.SymbolDependency(symbol=symbol) for symbol in symbols]

    def is_updating_at_each_price_change(self):
        return self.refresh_interval_days == 0

    def automatically_update_historical_config_on_set_intervals(self) -> bool:
        return (
            self.supports_historical_config() 
            and self.synchronization_policy == rebalancer_enums.SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
        )

    def ensure_updated_coins_distribution(self, adapt_to_holdings: bool = False, force_latest: bool = False):
        if self.rebalance_actions_planner is not None:
            self._sync_rebalance_planner()
            self.rebalance_actions_planner.update_distribution(adapt_to_holdings, force_latest)

    @classmethod
    def get_ideal_distribution(cls, config: dict):
        return config.get(IndexTradingModeProducer.INDEX_CONTENT, None)

    @staticmethod
    def get_default_historical_time_frame() -> typing.Optional[commons_enums.TimeFrames]:
        return commons_enums.TimeFrames.ONE_DAY

    @staticmethod
    def use_backtesting_accurate_price_update() -> bool:
        """
        Return True if the trading mode is more accurate in backtesting when using a short price update time frame
        """
        # a short price update time frame is not increasing accuracy for index trading mode
        return False

    @staticmethod
    def get_config_history_propagated_tentacles_config_keys() -> list[str]:
        """
        Returns the list of config keys that should be propagated to historical configurations
        """
        return [
            # The selected rebalance trigger profile should be applied to all historical configs 
            # to ensure the user selected profile is always used
            IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE,
            IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES,
            IndexTradingModeProducer.SYNCHRONIZATION_POLICY,
        ]

    def get_removed_coins_from_config(self, available_traded_bases):
        if self.rebalance_actions_planner is None:
            return []
        self._sync_rebalance_planner()
        return self.rebalance_actions_planner.get_removed_coins_from_config(available_traded_bases)

    def get_target_ratio(self, currency) -> decimal.Decimal:
        if self.rebalance_actions_planner is None:
            return trading_constants.ZERO
        return self.rebalance_actions_planner.get_target_ratio(currency)

    def create_rebalancer(self, exchange_manager) -> rebalancer.AbstractRebalancer:
        self._sync_rebalance_planner()
        exchange = exchange_interface.ExchangeInterface(exchange_manager, trading_mode=self)
        if self.rebalance_actions_planner is None:
            raise RuntimeError("rebalance_actions_planner must be initialized before create_rebalancer")
        if exchange_manager.is_option:
            return rebalancer.OptionRebalancer(
                exchange,
                self.rebalance_actions_planner,
                self.indexed_coins_prices,
            )
        if exchange_manager.is_future:
            return rebalancer.FuturesRebalancer(
                exchange,
                self.rebalance_actions_planner,
                self.indexed_coins_prices,
            )
        return rebalancer.SpotRebalancer(
            exchange,
            self.rebalance_actions_planner,
            self.indexed_coins_prices,
        )

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return True

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
            trading_enums.ExchangeTypes.OPTION,
        ]

    def get_current_state(self) -> tuple:
        return trading_enums.EvaluatorStates.NEUTRAL.name, f"Indexing {len(self.indexed_coins)} coins"

    async def single_exchange_process_optimize_initial_portfolio(
        self, sellable_assets: list, target_asset: str, tickers: dict
    ) -> list:
        raise_all_order_errors = (
            self.rebalance_actions_planner.client.raise_all_order_errors
            if self.rebalance_actions_planner is not None
            else False
        )
        return await trading_modes.convert_assets_to_target_asset(
            sellable_assets,
            target_asset,
            tickers,
            raise_all_order_errors=raise_all_order_errors,
            trading_mode=self,
            exchange_manager=self.exchange_manager,
        )
