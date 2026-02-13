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
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes as trading_modes
import octobot_trading.util as trading_util
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.signals as signals

import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution
import tentacles.Trading.Mode.index_trading_mode.rebalancer as rebalancer


class IndexActivity(enum.Enum):
    REBALANCING_DONE = "rebalancing_done"
    REBALANCING_SKIPPED = "rebalancing_skipped"


class RebalanceSkipDetails(enum.Enum):
    ALREADY_BALANCED = "already_balanced"
    NOT_ENOUGH_AVAILABLE_FOUNDS = "not_enough_available_founds"


class RebalanceDetails(enum.Enum):
    SELL_SOME = "SELL_SOME"
    BUY_MORE = "BUY_MORE"
    REMOVE = "REMOVE"
    ADD = "ADD"
    SWAP = "SWAP"
    FORCED_REBALANCE = "FORCED_REBALANCE"


class SynchronizationPolicy(enum.Enum):
    SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE = "sell_removed_index_coins_on_ratio_rebalance"
    SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE = "sell_removed_index_coins_as_soon_as_possible"


DEFAULT_QUOTE_ASSET_REBALANCE_TRIGGER_MIN_RATIO = 0.1  # 10%
DEFAULT_REBALANCE_TRIGGER_MIN_RATIO = 0.05  # 5%


class IndexTradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    SIMPLE_ADD_MIN_TOLERANCE_RATIO = decimal.Decimal("0.8")  # 20% tolerance

    IDEAL_AMOUNT = "ideal_amount"
    IDEAL_PRICE = "ideal_price"

    def __init__(self, trading_mode):
        super().__init__(trading_mode)
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
        try:
            # 1. make sure we can actually rebalance the portfolio
            self.logger.info("Step 1/3: ensuring enough funds are available for rebalance")
            await self._ensure_enough_funds_to_buy_after_selling()
            # 2. sell indexed coins for reference market
            is_simple_buy_without_selling = self._can_simply_buy_coins_without_selling(details)
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
                orders += await self.trading_mode.rebalancer.sell_indexed_coins_for_reference_market(details, initial_dependencies)
                sell_orders_dependencies = signals.get_orders_dependencies(orders)
            # 3. split reference market into indexed coins
            self.logger.info(
                f"Step 3/3: buying coins using "
                f"{self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market}"
            )
            orders += await self._split_reference_market_into_indexed_coins(
                details, is_simple_buy_without_selling, sell_orders_dependencies
            )
            # reset flag to relog if a next rebalance is aborted
            self._already_logged_aborted_rebalance_error = False
        except (trading_errors.MissingMinimalExchangeTradeVolume, rebalancer.RebalanceAborted) as err:
            log_level = self.logger.warning
            if isinstance(err, rebalancer.RebalanceAborted) and not self._already_logged_aborted_rebalance_error:
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

    
    def _can_simply_buy_coins_without_selling(self, details: dict) -> bool:
        simple_buy_coins = self._get_simple_buy_coins(details)
        if not simple_buy_coins:
            return False
        # check if there is enough free funds to buy those coins
        ref_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        reference_market_to_split = self._get_traded_assets_holdings_value(ref_market)
        free_reference_market_holding = self._get_free_reference_market_holding(ref_market)
        cumulated_ratio = sum(
            self.trading_mode.get_target_ratio(coin)
            for coin in simple_buy_coins
        )
        tolerated_min_amount = reference_market_to_split * cumulated_ratio * self.SIMPLE_ADD_MIN_TOLERANCE_RATIO
        # can reach target ratios without selling if this condition is met
        return tolerated_min_amount <= free_reference_market_holding

    def _get_simple_buy_coins(self, details: dict) -> list:
        # Returns the list of coins to simply buy.
        # Used to avoid a full rebalance when coins are seen as added to a basket
        # AND funds are available to buy it AND no asset should be sold
        added = details[RebalanceDetails.ADD.value] or details[RebalanceDetails.BUY_MORE.value]
        if added and not (
            details[RebalanceDetails.SWAP.value]
            or details[RebalanceDetails.SELL_SOME.value]
            or details[RebalanceDetails.REMOVE.value]
            or details[RebalanceDetails.FORCED_REBALANCE.value]
        ):
            added_coins = list(details[RebalanceDetails.ADD.value]) + list(details[RebalanceDetails.BUY_MORE.value])
            return [
                coin
                for coin in self.trading_mode.indexed_coins # iterate over self.trading_mode.indexed_coins to keep order
                if coin in added_coins
            ] + [
                coin
                for coin in added_coins
                if coin not in self.trading_mode.indexed_coins
            ]
        return []

    def _get_traded_assets_holdings_value(self, reference_market: typing.Optional[str] = None, coins_whitelist: typing.Optional[typing.Iterable] = None) -> decimal.Decimal:
        reference_market = reference_market or self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        return self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager. \
            portfolio_value_holder.get_traded_assets_holdings_value(reference_market, coins_whitelist)

    def _get_free_reference_market_holding(self, reference_market: typing.Optional[str] = None) -> decimal.Decimal:
        reference_market = reference_market or self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        return self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.get_currency_portfolio(reference_market).available

    async def _ensure_enough_funds_to_buy_after_selling(self):
        reference_market_to_split = self._get_traded_assets_holdings_value()
        # will raise if funds are missing
        await self._get_symbols_and_amounts(self.trading_mode.indexed_coins, self.trading_mode.indexed_coins_prices, reference_market_to_split)

    async def _split_reference_market_into_indexed_coins(
        self, 
        details: dict, 
        is_simple_buy_without_selling: bool, 
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        orders = []
        await self.trading_mode.rebalancer.pre_cancel_conflicting_orders(details, dependencies, trading_enums.TradeOrderSide.SELL)
        ref_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        coins_prices = self.trading_mode.indexed_coins_prices
        if details[RebalanceDetails.SWAP.value] or is_simple_buy_without_selling:
            # has to infer total reference market holdings
            reference_market_to_split = self._get_traded_assets_holdings_value()
            coins_to_buy = (
                self._get_simple_buy_coins(details) if is_simple_buy_without_selling
                else list(details[RebalanceDetails.SWAP.value].values())
            ) 
        else:
            # can use actual reference market holdings: everything has been sold
            reference_market_to_split = self._get_free_reference_market_holding()
            coins_to_buy = self.trading_mode.indexed_coins

        # Distribute a percentage among indexed coins, keep the rest in reference market
        # If reference_market_ratio is 0, distribute everything (no reservation)
        if self.trading_mode.reference_market_ratio > trading_constants.ZERO:
            reference_market_to_distribute = reference_market_to_split * self.trading_mode.reference_market_ratio
            reference_market_reserved = reference_market_to_split - reference_market_to_distribute
        else:
            reference_market_to_distribute = reference_market_to_split
            reference_market_reserved = trading_constants.ZERO
        
        if reference_market_reserved > trading_constants.ZERO:
            self.logger.info(
                f"Distributing {reference_market_to_distribute} {ref_market} ({self.trading_mode.reference_market_ratio * trading_constants.ONE_HUNDRED}%) "
                f"among indexed coins, reserving {reference_market_reserved} {ref_market} for reference market"
            )

        amount_by_symbol = await self._get_symbols_and_amounts(coins_to_buy, coins_prices, reference_market_to_distribute)
        for symbol, values in amount_by_symbol.items():
            orders.extend(await self.trading_mode.rebalancer.buy_coin(symbol, values.get(self.IDEAL_AMOUNT), values.get(self.IDEAL_PRICE), dependencies))
        if not orders and not self.trading_mode.allow_skip_asset:
            raise trading_errors.MissingMinimalExchangeTradeVolume()
        return orders

    async def _get_symbols_and_amounts(
        self, 
        coins_to_buy: list,
        coins_prices: dict,
        reference_market_to_split: decimal.Decimal
    ) -> dict:
        amount_by_symbol = {}
        for coin in coins_to_buy:
            if not symbol_util.is_symbol(coin):
                if coin == self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market:
                    # nothing to do for reference market, keep as is
                    continue
                symbol = symbol_util.merge_currencies(
                    coin,
                    self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
                )
            else:
                symbol = coin

            up_to_date_price = await trading_personal_data.get_up_to_date_price(
                self.exchange_manager, symbol, timeout=trading_constants.ORDER_DATA_FETCHING_TIMEOUT
            )
            price = coins_prices.get(symbol, up_to_date_price)
            symbol_market = self.exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
            ratio = self.trading_mode.get_target_ratio(coin)
            if ratio == trading_constants.ZERO:
                # coin is not to handle
                continue
            try:
                ideal_amount = ratio * reference_market_to_split / price
            except decimal.DecimalException as err:
                raise rebalancer.RebalanceAborted(
                    f"Error computing {symbol} ideal amount ({ratio=}, {reference_market_to_split=}, {price=}): {err=}"
                ) from err
            # worse case (ex with 5 USDT min order size): exactly 5 USDT can be in portfolio, we therefore want to
            # trade at least 5 USDT to be able to buy more.
            # - we want ideal_amount - min_cost > min_cost
            # - in other words ideal_amount > min_cost * min_order_size_margin
            #   => ideal_amount / min_order_size_margin > min_cost
            min_order_size_margin = self.trading_mode.min_order_size_margin
            if min_order_size_margin < trading_constants.ONE:
                min_order_size_margin = trading_constants.ONE
            adapted_quantity = trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                ideal_amount / min_order_size_margin,
                price,
                symbol_market
            )
            if not adapted_quantity:
                if self.trading_mode.allow_skip_asset:
                    self.logger.warning(
                        f"Skipping {symbol} buy: available funds are too low to buy {ratio*trading_constants.ONE_HUNDRED}% "
                        f"of {reference_market_to_split} holdings: {round(ideal_amount / min_order_size_margin, 9)} {coin}"
                    )
                    continue
                # if we can't create an order in this case, we won't be able to balance the portfolio.
                # don't try to avoid triggering new rebalances on each wakeup cycling market sell & buy orders
                raise trading_errors.MissingMinimalExchangeTradeVolume(
                    f"Can't buy {symbol}: available funds are too low to buy {ratio*trading_constants.ONE_HUNDRED}% "
                    f"of {reference_market_to_split} holdings: {round(ideal_amount / min_order_size_margin, 9)} {coin} "
                    f"required order size is not compatible with {symbol} exchange requirements: "
                    f"{symbol_market[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]}."
                )

            amount_by_symbol[symbol] = {
                self.IDEAL_AMOUNT: ideal_amount,
                self.IDEAL_PRICE: price,
            }
        return amount_by_symbol


class IndexTradingModeProducer(trading_modes.AbstractTradingModeProducer):
    REFRESH_INTERVAL = "refresh_interval"
    CANCEL_OPEN_ORDERS = "cancel_open_orders"
    ALLOW_SKIP_ASSET = "allow_skip_asset"
    REBALANCE_TRIGGER_MIN_PERCENT = "rebalance_trigger_min_percent"
    SELECTED_REBALANCE_TRIGGER_PROFILE = "selected_rebalance_trigger_profile"
    REBALANCE_TRIGGER_PROFILES = "rebalance_trigger_profiles"
    REBALANCE_TRIGGER_PROFILE_NAME = "name"
    REBALANCE_TRIGGER_PROFILE_MIN_PERCENT = "min_percent"
    QUOTE_ASSET_REBALANCE_TRIGGER_MIN_PERCENT = "quote_asset_rebalance_trigger_min_percent"
    MIN_ORDER_SIZE_MARGIN = "min_order_size_margin"
    REFERENCE_MARKET_RATIO = "reference_market_ratio"
    SYNCHRONIZATION_POLICY = "synchronization_policy"
    SELL_UNINDEXED_TRADED_COINS = "sell_unindexed_traded_coins"
    INDEX_CONTENT = "index_content"
    MIN_INDEXED_COINS = 1
    ALLOWED_1_TO_1_SWAP_COUNTS = 1
    MIN_RATIO_TO_SELL = decimal.Decimal("0.0001")  # 1/10000
    QUOTE_ASSET_TO_INDEXED_SWAP_RATIO_THRESHOLD = decimal.Decimal("0.1")  # 10%

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self._last_trigger_time = 0
        self.state = trading_enums.EvaluatorStates.NEUTRAL

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        await super().stop()

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
        for coin in self.trading_mode.indexed_coins:
            await self.trading_mode.rebalancer.prepare_coin_rebalancing(coin)

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

    def get_holdings_ratio(self, coin: str, traded_symbols_only: bool = False, include_assets_in_open_orders=False, coins_whitelist: typing.Optional[list] = None) -> decimal.Decimal:
        return self.trading_mode.exchange_manager.exchange_personal_data.portfolio_manager. \
            portfolio_value_holder.get_holdings_ratio(
                coin, traded_symbols_only=traded_symbols_only, include_assets_in_open_orders=include_assets_in_open_orders, coins_whitelist=coins_whitelist
            )

    def _register_coins_update(self, rebalance_details: dict) -> bool:
        should_rebalance = False
        for coin in set(self.trading_mode.indexed_coins):
            # Use adjusted target ratio to account for reference market percentage
            target_ratio = self.trading_mode.get_adjusted_target_ratio(coin)
            coin_ratio = self.get_holdings_ratio(coin, traded_symbols_only=True, include_assets_in_open_orders=True)
            beyond_ratio = True
            if coin_ratio == trading_constants.ZERO and target_ratio > trading_constants.ZERO:
                # missing coin in portfolio
                rebalance_details[RebalanceDetails.ADD.value][coin] = target_ratio
                should_rebalance = True
            elif coin_ratio < target_ratio - self.trading_mode.rebalance_trigger_min_ratio:
                # not enough in portfolio
                rebalance_details[RebalanceDetails.BUY_MORE.value][coin] = target_ratio
                should_rebalance = True
            elif coin_ratio > target_ratio + self.trading_mode.rebalance_trigger_min_ratio:
                # too much in portfolio
                rebalance_details[RebalanceDetails.SELL_SOME.value][coin] = target_ratio
                should_rebalance = True
            else:
                beyond_ratio = False
            if beyond_ratio:
                allowance = round(self.trading_mode.rebalance_trigger_min_ratio * trading_constants.ONE_HUNDRED, 2)
                self.logger.info(
                    f"{coin} is beyond the target ratio of {round(target_ratio * trading_constants.ONE_HUNDRED, 2)}[+/-{allowance}]%, "
                    f"ratio: {round(coin_ratio * trading_constants.ONE_HUNDRED, 2)}%. A rebalance is required."
                )
        return should_rebalance

    def _register_removed_coin(self, rebalance_details: dict, available_traded_bases: set[str]) -> bool:
        should_rebalance = False
        for coin in self.trading_mode.get_removed_coins_from_config(available_traded_bases):
            if coin in available_traded_bases:
                coin_ratio = self.get_holdings_ratio(coin, traded_symbols_only=True, include_assets_in_open_orders=True)
                if coin_ratio >= self.MIN_RATIO_TO_SELL:
                    # coin to sell in portfolio
                    rebalance_details[RebalanceDetails.REMOVE.value][coin] = coin_ratio
                    self.logger.info(
                        f"{coin} (holdings: {round(coin_ratio * trading_constants.ONE_HUNDRED, 3)}%) is not in index "
                        f"anymore. A rebalance is required."
                    )
                    should_rebalance = True
            else:
                if trading_util.is_symbol_disabled(self.exchange_manager.config, coin):
                    self.logger.info(
                        f"Ignoring {coin} holding: {coin} is not in index anymore but is disabled."
                    )
                else:
                    self.logger.error(
                        f"Ignoring {coin} holding: Can't sell {coin} as it is not in any trading pair"
                        f" but is not in index anymore. This is unexpected"
                    )
        return should_rebalance

    def _register_quote_asset_rebalance(self, rebalance_details: dict) -> bool:
        non_indexed_quote_assets_ratio = self._get_non_indexed_quote_assets_ratio()
        if self._should_rebalance_due_to_non_indexed_quote_assets_ratio(
            non_indexed_quote_assets_ratio, rebalance_details
        ):
            rebalance_details[RebalanceDetails.FORCED_REBALANCE.value] = True
            self.logger.info(
                f"Rebalancing due to a high non-indexed quote asset holdings ratio: "
                f"{round(non_indexed_quote_assets_ratio * trading_constants.ONE_HUNDRED, 2)}%, quote rebalance "
                f"threshold = {self.trading_mode.quote_asset_rebalance_ratio_threshold * trading_constants.ONE_HUNDRED}%"
            )
            return True
        return False

    async def _register_traded_symbol_pairs_update(self):
        if self.trading_mode.indexed_coins:
            self.logger.debug(f"Update traded symbol pair: {self.trading_mode.indexed_coins}...")
            # TODO: remove the pairs when the coins are entirely removed from the index
            await self.exchange_manager.exchange_config.add_traded_symbols(
                self.trading_mode.indexed_coins, []
            )

    def _empty_rebalance_details(self) -> dict:
        return {
            RebalanceDetails.SELL_SOME.value: {},
            RebalanceDetails.BUY_MORE.value: {},
            RebalanceDetails.REMOVE.value: {},
            RebalanceDetails.ADD.value: {},
            RebalanceDetails.SWAP.value: {},
            RebalanceDetails.FORCED_REBALANCE.value: False,
        }

    def _get_rebalance_details(self) -> typing.Tuple[bool, dict]:
        rebalance_details = self._empty_rebalance_details()
        should_rebalance = False
        # look for coins update in indexed_coins
        available_traded_bases = set(
            symbol.base
            for symbol in self.exchange_manager.exchange_config.traded_symbols
        )

        # compute rebalance details for current coins distribution
        if self.trading_mode.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            should_rebalance = self._register_removed_coin(rebalance_details, available_traded_bases)
        should_rebalance = self._register_coins_update(rebalance_details) or should_rebalance
        should_rebalance = self._register_quote_asset_rebalance(rebalance_details) or should_rebalance
        if (
            should_rebalance 
            and self.trading_mode.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
        ):
            # use latest coins distribution to compute rebalance details
            self.trading_mode.ensure_updated_coins_distribution(force_latest=True)
            # re-compute the whole rebalance details for latest coins distribution 
            # to avoid side effects from previous distribution
            rebalance_details = self._empty_rebalance_details()
            self._register_removed_coin(rebalance_details, available_traded_bases)
            self._register_coins_update(rebalance_details)
            self._register_quote_asset_rebalance(rebalance_details)

        if not rebalance_details[RebalanceDetails.FORCED_REBALANCE.value]:
            # finally, compute swaps when no forced rebalance is required
            self._resolve_swaps(rebalance_details)
            for origin, target in rebalance_details[RebalanceDetails.SWAP.value].items():
                origin_ratio = round(
                    rebalance_details[RebalanceDetails.REMOVE.value][origin] * trading_constants.ONE_HUNDRED,
                    3
                )
                target_ratio = round(
                    rebalance_details[RebalanceDetails.ADD.value].get(
                        target,
                        rebalance_details[RebalanceDetails.BUY_MORE.value].get(target, trading_constants.ZERO)
                    ) * trading_constants.ONE_HUNDRED,
                    3
                ) or "???"
                self.logger.info(
                    f"Swapping {origin} (holding ratio: {origin_ratio}%) for {target} (to buy ratio: {target_ratio}%) "
                    f"on [{self.exchange_manager.exchange_name}]: ratios are similar enough to allow swapping."
                )   
        return (should_rebalance or rebalance_details[RebalanceDetails.FORCED_REBALANCE.value]), rebalance_details

    def _should_rebalance_due_to_non_indexed_quote_assets_ratio(self, non_indexed_quote_assets_ratio: decimal.Decimal, rebalance_details: dict) -> bool:
        total_added_ratio = (
            self._sum_ratios(rebalance_details, RebalanceDetails.ADD.value) 
            + self._sum_ratios(rebalance_details, RebalanceDetails.BUY_MORE.value)
        )
        
        if (
            total_added_ratio * (trading_constants.ONE - self.QUOTE_ASSET_TO_INDEXED_SWAP_RATIO_THRESHOLD)
            <= non_indexed_quote_assets_ratio
            <= total_added_ratio * (trading_constants.ONE + self.QUOTE_ASSET_TO_INDEXED_SWAP_RATIO_THRESHOLD)
        ):
            total_removed_ratio = (
                self._sum_ratios(rebalance_details, RebalanceDetails.REMOVE.value) 
                + self._sum_ratios(rebalance_details, RebalanceDetails.SELL_SOME.value)
            )
            # added coins are equivalent to free quote assets: just buy with quote assets
            if total_removed_ratio == trading_constants.ZERO:
                return False
        # there are removed coins or added ratio is not equivalent to free quote assets: rebalance if necessary
        min_ratio = min(
            min(
                self.trading_mode.get_target_ratio(coin)
                for coin in self.trading_mode.indexed_coins
            ) if self.trading_mode.indexed_coins else self.trading_mode.quote_asset_rebalance_ratio_threshold,
            self.trading_mode.quote_asset_rebalance_ratio_threshold
        )
        return non_indexed_quote_assets_ratio >= min_ratio

    @staticmethod
    def _sum_ratios(rebalance_details: dict, key: str) -> decimal.Decimal:
        return decimal.Decimal(str(sum(
            ratio
            for ratio in rebalance_details[key].values()
        ))) if rebalance_details[key] else trading_constants.ZERO 

    def _get_non_indexed_quote_assets_ratio(self) -> decimal.Decimal:
        reference_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
        reference_market_ratio = self.trading_mode.reference_market_ratio
        total = trading_constants.ZERO
        for quote in set(
            symbol.quote
            for symbol in self.exchange_manager.exchange_config.traded_symbols
            if symbol.quote not in self.trading_mode.indexed_coins
        ):
            ratio = decimal.Decimal(str(
                self.get_holdings_ratio(quote, traded_symbols_only=True, include_assets_in_open_orders=True)
            ))
            if quote == reference_market and reference_market_ratio > trading_constants.ZERO:
                # Only the excess above the desired reference market reserve counts toward triggering
                # reference_market_ratio is the percentage to trade, so (1 - reference_market_ratio) is the percentage to keep
                reference_market_keep_ratio = trading_constants.ONE - reference_market_ratio
                ratio = max(trading_constants.ZERO, ratio - reference_market_keep_ratio)
            total += ratio
        return decimal.Decimal(str(total))

    def _resolve_swaps(self, details: dict):
        removed = details[RebalanceDetails.REMOVE.value]
        details[RebalanceDetails.SWAP.value] = {}
        if details[RebalanceDetails.SELL_SOME.value]:
            # rebalance within held coins: global rebalance required
            return
        added = {**details[RebalanceDetails.ADD.value], **details[RebalanceDetails.BUY_MORE.value]}
        if len(removed) == len(added) == self.ALLOWED_1_TO_1_SWAP_COUNTS:
            for removed_coin, removed_ratio, added_coin, added_ratio in zip(
                removed, removed.values(), added, added.values()
            ):
                added_holding_ratio = self.get_holdings_ratio(added_coin, traded_symbols_only=True, coins_whitelist=self.trading_mode.get_coins_to_consider_for_ratio())
                required_added_ratio = added_ratio - added_holding_ratio
                if (
                    removed_ratio - self.trading_mode.rebalance_trigger_min_ratio
                    < required_added_ratio
                    < removed_ratio + self.trading_mode.rebalance_trigger_min_ratio
                ):
                    # removed can be swapped for added: only sell removed
                    details[RebalanceDetails.SWAP.value][removed_coin] = added_coin
                else:
                    # reset to_sell to sell everything
                    details[RebalanceDetails.SWAP.value] = {}
                    return

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
        self.ratio_per_asset = {}
        self.sell_unindexed_traded_coins = True
        self.cancel_open_orders = True
        self.allow_skip_asset = False
        self.total_ratio_per_asset = trading_constants.ZERO
        self.quote_asset_rebalance_ratio_threshold = decimal.Decimal(str(DEFAULT_QUOTE_ASSET_REBALANCE_TRIGGER_MIN_RATIO))
        self.reference_market_ratio = trading_constants.ONE
        self.min_order_size_margin = decimal.Decimal("2")
        self.synchronization_policy: SynchronizationPolicy = SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
        self.requires_initializing_appropriate_coins_distribution = False
        self.indexed_coins = []
        self.indexed_coins_prices = {}
        self.is_processing_rebalance = False
        self.rebalancer: typing.Optional[rebalancer.AbstractRebalancer] = self._create_rebalancer(exchange_manager) if exchange_manager else None
    
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
            options=[p.value for p in SynchronizationPolicy],
            editor_options={"enum_titles": [p.value.replace("_", " ") for p in SynchronizationPolicy]},
            title="Synchronization policy: should coins that are removed from index be sold as soon as possible or only when rebalancing is triggered when coins don't follow the configured ratios.",
        )
        try:
            self.synchronization_policy = SynchronizationPolicy(sync_policy)
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
        if (not self.exchange_manager or not self.exchange_manager.is_backtesting) and \
                authentication.Authenticator.instance().has_open_source_package():
            self.UI.user_input(IndexTradingModeProducer.INDEX_CONTENT, commons_enums.UserInputTypes.OBJECT_ARRAY,
                               trading_config.get(IndexTradingModeProducer.INDEX_CONTENT, None), inputs,
                               item_title="Coin",
                               other_schema_values={"minItems": 0, "uniqueItems": True},
                               title="Custom distribution: when used, only coins listed in this distribution and "
                                     "in your profile traded pairs will be traded. "
                                     "Leave empty to evenly allocate funds in each traded coin.")
            self.UI.user_input(index_distribution.DISTRIBUTION_NAME, commons_enums.UserInputTypes.TEXT,
                               "BTC", inputs,
                               other_schema_values={"minLength": 1},
                               parent_input_name=IndexTradingModeProducer.INDEX_CONTENT,
                               title="Name of the coin.")
            self.UI.user_input(index_distribution.DISTRIBUTION_VALUE, commons_enums.UserInputTypes.FLOAT,
                               50, inputs,
                               min_val=0,
                               parent_input_name=IndexTradingModeProducer.INDEX_CONTENT,
                               title="Weight of the coin within this distribution.")
        self.requires_initializing_appropriate_coins_distribution = self.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
        self.ensure_updated_coins_distribution()

    @classmethod
    def get_tentacle_config_traded_symbols(cls, config: dict, reference_market: str) -> list:
        return [
            symbol_util.merge_currencies(asset[index_distribution.DISTRIBUTION_NAME], reference_market)
            for asset in (cls.get_ideal_distribution(config) or [])
        ]

    def is_updating_at_each_price_change(self):
        return self.refresh_interval_days == 0

    def automatically_update_historical_config_on_set_intervals(self) -> bool:
        return (
            self.supports_historical_config() 
            and self.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE
        )

    def ensure_updated_coins_distribution(self, adapt_to_holdings: bool = False, force_latest: bool = False):
        distribution = self._get_supported_distribution(adapt_to_holdings, force_latest)
        self.ratio_per_asset = {
            asset[index_distribution.DISTRIBUTION_NAME]: asset
            for asset in distribution
        }
        self.total_ratio_per_asset = decimal.Decimal(sum(
            asset[index_distribution.DISTRIBUTION_VALUE]
            for asset in self.ratio_per_asset.values()
        ))
        self.indexed_coins = self._get_filtered_traded_coins(self.ratio_per_asset)

    def _get_filtered_traded_coins(self, ratio_per_asset: dict):
        if self.exchange_manager:
            ref_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
            coins = set(
                symbol.base
                for symbol in self.exchange_manager.exchange_config.traded_symbols
                if symbol.base in ratio_per_asset and symbol.quote == ref_market
            )
            if ref_market in ratio_per_asset and coins:
                # there is at least 1 coin traded against ref market, can add ref market if necessary
                coins.add(ref_market)
            return sorted(list(coins))
        return []

    def get_coins_to_consider_for_ratio(self) -> list:
        return self.indexed_coins + [self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market]

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

    def _get_currently_applied_historical_config_according_to_holdings(
        self, config: dict, traded_bases: set[str]
    ) -> dict:
        # 1. check if latest config is the running one
        if self._is_index_config_applied(config, traded_bases):
            self.logger.info(f"Using {self.get_name()} latest config.")
            return config
        # 2. check if historical configs are available (iterating from most recent to oldest)
        historical_configs = self.get_historical_configs(
            0, self.exchange_manager.exchange.get_exchange_current_time()
        )
        if not historical_configs or (
            # only 1 historical config which is the same as the latest config
            len(historical_configs) == 1 and (
                self.get_ideal_distribution(historical_configs[0]) == self.get_ideal_distribution(config)
                and historical_configs[0][IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT] == config[IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT]
            )
        ):
            # current config is the first historical config
            self.logger.info(f"Using {self.get_name()} latest config as no historical configs are available.")
            return config
        for index, historical_config in enumerate(historical_configs):
            if self._is_index_config_applied(historical_config, traded_bases):
                self.logger.info(f"Using [N-{index}] {self.get_name()} historical config distribution: {self.get_ideal_distribution(historical_config)}.")
                return historical_config
        # 3. no suitable config found: return latest config
        self.logger.info(f"No suitable {self.get_name()} config found: using latest distribution: {self.get_ideal_distribution(config)}.")
        return config

    def _is_index_config_applied(self, config: dict, traded_bases: set[str]) -> bool:
        full_assets_distribution = self.get_ideal_distribution(config)
        if not full_assets_distribution:
            return False
        assets_distribution = [
            asset
            for asset in full_assets_distribution
            if asset[index_distribution.DISTRIBUTION_NAME] in traded_bases
        ]
        if len(assets_distribution) != len(full_assets_distribution):
            # if assets are missing from traded pairs, the config is not applied
            # might be due to delisted or renamed coins
            missing_assets = [
                asset[index_distribution.DISTRIBUTION_NAME]
                for asset in full_assets_distribution
                if asset not in assets_distribution
            ]
            self.logger.warning(
                f"Ignored {self.get_name()} config candidate as {len(missing_assets)} configured assets {missing_assets} are missing from {self.exchange_manager.exchange_name} traded pairs."
            )
            return False

        total_ratio = decimal.Decimal(sum(
            asset[index_distribution.DISTRIBUTION_VALUE]
            for asset in assets_distribution
        ))
        if total_ratio == trading_constants.ZERO:
            return False
        min_trigger_ratio = self._get_config_min_ratio(config)
        for asset_distrib in assets_distribution:
            base_target_ratio = decimal.Decimal(str(asset_distrib[index_distribution.DISTRIBUTION_VALUE])) / total_ratio
            if self.reference_market_ratio < trading_constants.ONE:
                target_ratio = base_target_ratio * self.reference_market_ratio
            else:
                target_ratio = base_target_ratio
            coin_ratio = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.get_holdings_ratio(
                    asset_distrib[index_distribution.DISTRIBUTION_NAME], traded_symbols_only=True
                )
            if not (target_ratio - min_trigger_ratio <= coin_ratio <= target_ratio + min_trigger_ratio):
                # not enough or too much in portfolio
                return False
        return True

    def _get_config_min_ratio(self, config: dict) -> decimal.Decimal:
        ratio = None
        rebalance_trigger_profiles = config.get(IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILES, None)
        if rebalance_trigger_profiles:
            # 1. try to get ratio from selected rebalance trigger profile
            selected_rebalance_trigger_profile_name =config.get(IndexTradingModeProducer.SELECTED_REBALANCE_TRIGGER_PROFILE, None)
            selected_profile = [
                p for p in rebalance_trigger_profiles 
                if p[IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_NAME] == selected_rebalance_trigger_profile_name
            ]
            if selected_profile:
                selected_rebalance_trigger_profile = selected_profile[0]
                ratio = selected_rebalance_trigger_profile[IndexTradingModeProducer.REBALANCE_TRIGGER_PROFILE_MIN_PERCENT]
        if ratio is None:
            # 2. try to get ratio from direct config
            ratio = config.get(IndexTradingModeProducer.REBALANCE_TRIGGER_MIN_PERCENT)
        if ratio is None:
            # 3. default to current config ratio
            return self.rebalance_trigger_min_ratio
        return decimal.Decimal(str(ratio)) / trading_constants.ONE_HUNDRED

    def _get_supported_distribution(self, adapt_to_holdings: bool, force_latest: bool) -> list:
        if detailed_distribution := self.get_ideal_distribution(self.trading_config):
            traded_bases = set(
                symbol.base
                for symbol in self.exchange_manager.exchange_config.traded_symbols
            )
            traded_bases.add(self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market)
            if (
                (adapt_to_holdings or force_latest) 
                and self.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE
            ):
                if adapt_to_holdings:
                    # when policy is SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE, the latest config might not be the 
                    # running one: confirm this using historical configs
                    index_config = self._get_currently_applied_historical_config_according_to_holdings(
                        self.trading_config, traded_bases
                    )
                else:
                    # force latest available config
                    try:
                        index_config = self.get_historical_configs(
                            0, self.exchange_manager.exchange.get_exchange_current_time()
                        )[0]
                        self.logger.info(f"Updated {self.get_name()} to use latest distribution: {self.get_ideal_distribution(index_config)}.")
                    except IndexError:
                        index_config = self.trading_config
                detailed_distribution = self.get_ideal_distribution(index_config)
                if not detailed_distribution:
                    raise ValueError(f"No distribution found in historical index config: {index_config}")
            distribution = [
                asset
                for asset in detailed_distribution
                if asset[index_distribution.DISTRIBUTION_NAME] in traded_bases
            ]
            if removed_assets := [
                asset[index_distribution.DISTRIBUTION_NAME]
                for asset in detailed_distribution
                if asset not in distribution
            ]:
                self.logger.info(
                    f"Ignored {len(removed_assets)} assets {removed_assets} from configured "
                    f"distribution as absent from traded pairs."
                )
            return distribution
        else:
            # compute uniform distribution over traded assets
            return index_distribution.get_uniform_distribution([
                symbol.base
                for symbol in self.exchange_manager.exchange_config.traded_symbols
            ]) if self.exchange_manager else []

    def get_removed_coins_from_config(self, available_traded_bases) -> list:
        removed_coins = []
        if self.get_ideal_distribution(self.trading_config) and self.sell_unindexed_traded_coins:
            # only remove non indexed coins if an ideal distribution is set
            removed_coins = [
                coin
                for coin in available_traded_bases
                if coin not in self.indexed_coins
                and coin != self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
            ]
        if self.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_AS_SOON_AS_POSSIBLE:
            # identify coins to sell from previous config
            if not (self.previous_trading_config and self.trading_config):
                return removed_coins
            current_coins = [
                asset[index_distribution.DISTRIBUTION_NAME]
                for asset in (self.get_ideal_distribution(self.trading_config) or [])
            ]
            ref_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
            return list(set(removed_coins + [
                asset[index_distribution.DISTRIBUTION_NAME]
                for asset in self.previous_trading_config[IndexTradingModeProducer.INDEX_CONTENT]
                if asset[index_distribution.DISTRIBUTION_NAME] not in current_coins
                    and (
                        asset[index_distribution.DISTRIBUTION_NAME]
                        != self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
                    )
            ]))
        elif self.synchronization_policy == SynchronizationPolicy.SELL_REMOVED_INDEX_COINS_ON_RATIO_REBALANCE:
            # identify coins to sell from historical configs
            historical_configs = self.get_historical_configs(
                # use 0 a the initial config time as only relevant historical configs should be available
                0, self.exchange_manager.exchange.get_exchange_current_time()
            )
            if not (historical_configs and self.trading_config):
                return removed_coins
            current_coins = [
                asset[index_distribution.DISTRIBUTION_NAME]
                for asset in (self.get_ideal_distribution(self.trading_config) or [])
            ]
            ref_market = self.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
            removed_coins_from_historical_configs = set()
            for historical_config in historical_configs:
                for asset in historical_config[IndexTradingModeProducer.INDEX_CONTENT]:
                    asset_name = asset[index_distribution.DISTRIBUTION_NAME]
                    if asset_name not in current_coins and asset_name != ref_market:
                        removed_coins_from_historical_configs.add(asset_name)
            return list(removed_coins_from_historical_configs.union(removed_coins))
        else:
            self.logger.error(f"Unknown synchronization policy: {self.synchronization_policy}")
            return []

    def get_target_ratio(self, currency) -> decimal.Decimal:
        if currency in self.ratio_per_asset:
            try:
                return (
                    decimal.Decimal(str(
                        self.ratio_per_asset[currency][index_distribution.DISTRIBUTION_VALUE]
                    )) / self.total_ratio_per_asset
                )
            except (decimal.DivisionByZero, decimal.InvalidOperation):
                pass
        return trading_constants.ZERO

    def get_adjusted_target_ratio(self, currency) -> decimal.Decimal:
        """
        Returns the target ratio adjusted for the reference market percentage.
        If reference_market_ratio is set, the coin's ratio is scaled by reference_market_ratio
        to reflect the percentage of the portfolio to trade (the remaining is kept in reference market).
        """
        base_ratio = self.get_target_ratio(currency)
        if self.reference_market_ratio < trading_constants.ONE:
            return base_ratio * self.reference_market_ratio
        return base_ratio

    def _create_rebalancer(self, exchange_manager) -> rebalancer.AbstractRebalancer:
        if exchange_manager.is_option:
            return rebalancer.OptionRebalancer(self)
        if exchange_manager.is_future:
            return rebalancer.FuturesRebalancer(self)
        return rebalancer.SpotRebalancer(self)

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
        return await trading_modes.convert_assets_to_target_asset(
            self, sellable_assets, target_asset, tickers
        )
