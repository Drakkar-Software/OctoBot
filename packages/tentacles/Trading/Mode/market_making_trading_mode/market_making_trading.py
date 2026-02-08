# pylint: disable=E701
# Drakkar-Software OctoBot-Tentacles
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
import collections
import dataclasses
import decimal
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.constants as common_constants
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.pretty_printer
import octobot_tentacles_manager.api
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes as trading_modes
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchanges as trading_exchanges
import tentacles.Trading.Mode.market_making_trading_mode.order_book_distribution as order_book_distribution
import tentacles.Trading.Mode.market_making_trading_mode.reference_price as reference_price_import


@dataclasses.dataclass
class OrderData:
    side: trading_enums.TradeOrderSide = None
    quantity: decimal.Decimal = trading_constants.ZERO
    price: decimal.Decimal = trading_constants.ZERO
    symbol: str = 0


class OrderAction:
    pass


@dataclasses.dataclass
class CreateOrderAction(OrderAction):
    order_data: OrderData

    @classmethod
    def from_book_order_data(cls, symbol, order: order_book_distribution.BookOrderData):
        return cls(
            OrderData(
                side=order.side,
                quantity=order.amount,
                price=order.price,
                symbol=symbol,
            )
        )


@dataclasses.dataclass
class CancelOrderAction(OrderAction):
    order: trading_personal_data.Order


@dataclasses.dataclass
class OrdersUpdatePlan:
    order_actions: list[OrderAction] = dataclasses.field(default_factory=list)
    cancelled: bool = False
    cancellable: bool = True
    force_cancelled: bool = False
    processed: asyncio.Event = dataclasses.field(default_factory=asyncio.Event)
    trigger_source: str = ""

    def __str__(self):
        cancel_actions = [a for a in self.order_actions if isinstance(a, CancelOrderAction)]
        create_actions = [a for a in self.order_actions if isinstance(a, CreateOrderAction)]
        return (
            f"{self.__class__.__name__} of {len(self.order_actions)} {OrderAction.__name__} [{len(cancel_actions)} "
            f"{CancelOrderAction.__name__} & {len(create_actions)} {CreateOrderAction.__name__}], "
            f"cancelled: {self.cancelled} cancellable: {self.cancellable} "
            f"[trigger_source: {self.trigger_source}]"
        )


class SkippedAction(Exception):
    pass


class MarketMakingTradingMode(trading_modes.AbstractTradingMode):
    REQUIRE_TRADES_HISTORY = False   # set True when this trading mode needs the trade history to operate
    SUPPORTS_INITIAL_PORTFOLIO_OPTIMIZATION = False  # set True when self._optimize_initial_portfolio is implemented
    SUPPORTS_HEALTH_CHECK = False   # set True when self.health_check is implemented

    MIN_SPREAD = "min_spread"
    MAX_SPREAD = "max_spread"
    BIDS_COUNT = "bids_count"
    ASKS_COUNT = "asks_count"
    REFERENCE_EXCHANGE = "reference_exchange"
    LOCAL_EXCHANGE_PRICE = "local"

    MIN_SPREAD_DESC = "Min spread %: Percentage of the current price to use as bid-ask spread."
    MAX_SPREAD_DESC = "Max spread %: Percentage of the current price to use to define the target order book depth."
    BIDS_COUNT_DECS = "Bids count: How many buy orders to create in the order book."
    ASKS_COUNT_DECS = "Asks count: How many sell orders to create in the order book."
    REFERENCE_EXCHANGE_DESC = (
        f"Reference exchange. Used as the price source to create the order book's orders from. "
        f"This exchange need to have a trading market for the selected traded pair. Example: \"binance\". "
        f"Use \"{LOCAL_EXCHANGE_PRICE}\" to use the current exchange price."
    )

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(
            self.MIN_SPREAD, commons_enums.UserInputTypes.FLOAT, 2, inputs,
            min_val=0, max_val=int(order_book_distribution.TARGET_CUMULATED_VOLUME_PERCENT * 2) ,
            other_schema_values={"exclusiveMinimum": True, "exclusiveMaximum": True}, title=self.MIN_SPREAD_DESC
        )
        self.UI.user_input(
            self.MAX_SPREAD, commons_enums.UserInputTypes.FLOAT, 6, inputs,
            min_val=0, max_val=200, other_schema_values={"exclusiveMinimum": True, "exclusiveMaximum": True},
            title=self.MAX_SPREAD_DESC,
        )
        self.UI.user_input(
            self.BIDS_COUNT, commons_enums.UserInputTypes.INT, 5, inputs,
            min_val=0, max_val=order_book_distribution.MAX_HANDLED_BIDS_ORDERS,
            other_schema_values={"exclusiveMinimum": True, "exclusiveMaximum": False}, title=self.BIDS_COUNT_DECS,
        )
        self.UI.user_input(
            self.ASKS_COUNT, commons_enums.UserInputTypes.INT, 5, inputs,
            min_val=0, max_val=order_book_distribution.MAX_HANDLED_ASKS_ORDERS,
            other_schema_values={"exclusiveMinimum": True, "exclusiveMaximum": False}, title=self.ASKS_COUNT_DECS,
        )
        self.UI.user_input(
            self.REFERENCE_EXCHANGE, commons_enums.UserInputTypes.TEXT,
            "binance", inputs,
            other_schema_values={"inputAttributes": {"placeholder": "binance"}},
            title=self.REFERENCE_EXCHANGE_DESC
        )

    def get_current_state(self) -> (str, float):
        order = self.producers[0].get_market_making_orders() if self.producers else []
        bids = [o for o in order if o.side == trading_enums.TradeOrderSide.SELL]
        asks = [o for o in order if o.side == trading_enums.TradeOrderSide.BUY]
        if len(bids) > len(asks):
            state = trading_enums.EvaluatorStates.LONG
        elif len(bids) < len(asks):
            state = trading_enums.EvaluatorStates.SHORT
        else:
            state = trading_enums.EvaluatorStates.NEUTRAL
        bid_volume = sum(o.total_cost for o in bids)
        ask_volume = sum(o.origin_quantity for o in asks)
        symbol = symbol_util.parse_symbol(self.symbol)
        return (
            state.name,
            f"{bid_volume} {symbol.quote} in {len(bids)} bids, {ask_volume} {symbol.base} in {len(asks)} asks"
        )

    def get_mode_producer_classes(self) -> list:
        return [MarketMakingTradingModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [MarketMakingTradingModeConsumer]

    @classmethod
    def get_is_trading_on_exchange(cls, exchange_name, tentacles_setup_config) -> bool:
        """
        returns True if exchange_name is trading exchange or the hedging exchange
        """
        return cls.has_trading_exchange_configuration(
            exchange_name, octobot_tentacles_manager.api.get_tentacle_config(tentacles_setup_config, cls)
        )

    @classmethod
    def get_is_using_trading_mode_on_exchange(cls, exchange_name, tentacles_setup_config) -> bool:
        """
        returns True if exchange_name is a trading exchange that is not the hedging exchange
        """
        return cls.has_trading_exchange_configuration(
            exchange_name, octobot_tentacles_manager.api.get_tentacle_config(tentacles_setup_config, cls)
        )

    @classmethod
    def has_trading_exchange_configuration(cls, exchange_name, tentacle_config: dict):
        pairs_settings_for_exchange = cls.get_pair_settings_for_exchange(exchange_name, tentacle_config)
        # trade on this exchange if there is at least a pair config for this exchange
        return bool(pairs_settings_for_exchange)

    @classmethod
    def get_pair_settings_for_exchange(cls, target_exchange_name, tentacle_config) -> list:
        if cls.is_exchange_compatible_pair_setting(tentacle_config, target_exchange_name):
            return [tentacle_config]
        return []

    def get_pair_settings(self) -> list:
        if self.is_exchange_compatible_pair_setting(self.trading_config, self.exchange_manager.exchange_name):
            return [self.trading_config]
        return []

    @classmethod
    def is_exchange_compatible_pair_setting(cls, trading_config: dict, target_exchange_name: str) -> bool:
        return (
            trading_config[cls.REFERENCE_EXCHANGE] != target_exchange_name
        )

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False

    @staticmethod
    def is_backtestable():
        return False

    @classmethod
    def is_ignoring_cancelled_orders_trades(cls) -> bool:
        return True

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()
        # order consumer: filter by symbol not be triggered only on this symbol's orders
        order_consumer = await exchanges_channel.get_chan(trading_personal_data.OrdersChannel.get_name(),
                                                          self.exchange_manager.id).new_consumer(
            self._order_notification_callback,
            symbol=self.symbol
        )
        return consumers + [order_consumer]

    async def _order_notification_callback(
        self, exchange, exchange_id, cryptocurrency, symbol, order, update_type, is_from_bot
    ):
        if (
            order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.FILLED.value
            and order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] in (
                trading_enums.TradeOrderType.LIMIT.value
            )
        ):
            await self.producers[0].order_filled_callback(order)

    def set_default_config(self):
        raise RuntimeError(f"Impossible to start {self.get_name()} without a valid configuration file.")

    @classmethod
    def get_order_book_distribution(cls, pair_config: dict) -> order_book_distribution.OrderBookDistribution:
        try:
            min_spread = decimal.Decimal(str(pair_config[cls.MIN_SPREAD] / 100))
            max_spread = decimal.Decimal(str(pair_config[cls.MAX_SPREAD] / 100))
            bids_count = int(pair_config[cls.BIDS_COUNT])
            asks_count = int(pair_config[cls.ASKS_COUNT])
            return order_book_distribution.OrderBookDistribution(
                bids_count, asks_count, min_spread, max_spread,
            )
        except TypeError as err:
            raise ValueError(f"Invalid config value: {err}") from err


class MarketMakingTradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    ORDER_ACTIONS_PLAN_KEY = "order_actions_plan"
    CURRENT_PRICE_KEY = "current_price"
    SYMBOL_MARKET_KEY = "symbol_market"

    def skip_portfolio_available_check_before_creating_orders(self) -> bool:
        """
        When returning true, will skip portfolio available funds check
        before calling self.create_new_orders().
        Override if necessary
        """
        # will cancel orders and free funds if necessary
        return True

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        # use dict default getter: can't afford missing data
        data = kwargs[self.CREATE_ORDER_DATA_PARAM]
        order_actions_plan: OrdersUpdatePlan = data[self.ORDER_ACTIONS_PLAN_KEY]
        current_price = data[self.CURRENT_PRICE_KEY]
        symbol_market = data[self.SYMBOL_MARKET_KEY]
        try:
            if self.trading_mode.producers[0].should_stop:
                self.logger.info(
                    f"Skipping creating new orders for {symbol} {self.exchange_manager.exchange_name}: "
                    f"bot should stop"
                )
                return []
            if order_actions_plan.cancelled:
                # any plan can be cancelled if it did not start processing
                self.logger.info(f"Cancelling {str(order_actions_plan)} action plan processing: plan did not start")
                return []
            else:
                self.logger.info(f"Starting {str(order_actions_plan)} action plan processing")
                return await self._process_plan(order_actions_plan, current_price, symbol_market)
        finally:
            order_actions_plan.processed.set()

    async def _process_plan(
        self,
        order_actions_plan: OrdersUpdatePlan,
        current_price: decimal.Decimal,
        symbol_market: dict
    ):
        created_orders = []
        cancelled_orders = []
        processed_actions = {}
        skipped_actions = {}
        scheduled_actions = collections.deque(order_actions_plan.order_actions)

        while scheduled_actions:
            action = scheduled_actions.popleft()
            try:
                if (
                    (order_actions_plan.cancelled and order_actions_plan.cancellable) or order_actions_plan.force_cancelled
                ):
                    actions_class = action.__class__.__name__
                    self.logger.debug(
                        f"{self.trading_mode.symbol} {self.exchange_manager.exchange_name} "
                        f"order actions cancelled, skipping {actions_class} action."
                    )
                    if actions_class not in skipped_actions:
                        skipped_actions[actions_class] = 1
                    else:
                        skipped_actions[actions_class] += 1
                else:
                    await self._process_action(
                        action, current_price, symbol_market,
                        processed_actions, created_orders, cancelled_orders
                    )
            except Exception as err:
                self.logger.exception(err, True, f"Error when processing {action}: {err}")

        self._log_actions_report(
            order_actions_plan, processed_actions, skipped_actions, created_orders, cancelled_orders
        )
        return created_orders

    def _log_actions_report(
        self, order_actions_plan, processed_actions, skipped_actions, created_orders, cancelled_orders
    ):
        skipped_actions_str = f", skipped actions: {skipped_actions}" if skipped_actions else ''
        create_actions = processed_actions.get(CreateOrderAction.__name__, 0)
        cancel_actions = processed_actions.get(CancelOrderAction.__name__, 0)
        self.logger.info(
            f"Completed {self.trading_mode.symbol} [{self.exchange_manager.exchange_name}] "
            f"{cancel_actions + create_actions}/{len(order_actions_plan.order_actions)} "
            f"order actions: {len(created_orders)}/{create_actions} created orders, "
            f"{len(cancelled_orders)}/{cancel_actions} cancelled orders{skipped_actions_str}."
        )

    async def _process_action(
        self, action: OrderAction, current_price, symbol_market,
        processed_actions: dict, created_orders: list, cancelled_orders: list,
        **kwargs,
    ):
        actions_class = action.__class__.__name__
        if isinstance(action, CreateOrderAction):
            created_orders += (
                await self.create_order(action.order_data, current_price, symbol_market, **kwargs)
            )
        elif isinstance(action, CancelOrderAction):
            if action.order.is_open():
                try:
                    await self.trading_mode.cancel_order(action.order)
                    cancelled_orders.append(action.order.order_id)
                except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                    self.logger.warning(f"Skipped order cancel: {err}, order: {str(action.order)}")
                except trading_errors.OrderCancelError as err:
                    self.logger.warning(
                        f"Error when cancelling order, considering order as closed. Error: {err}, "
                        f"order: {str(action.order)}"
                    )
            else:
                self.logger.info(
                    f"{self.trading_mode.symbol} {self.exchange_manager.exchange_name} ignored cancel order "
                    f"action: Order is not open anymore. Order: {str(action.order)}"
                )
        else:
            raise NotImplementedError(
                f"{self.trading_mode.symbol} {self.exchange_manager.exchange_name} {action} is not supported"
            )
        if actions_class not in processed_actions:
            processed_actions[actions_class] = 1
        else:
            processed_actions[actions_class] += 1

    async def create_order(self, order_data, current_price, symbol_market, **kwargs):
        created_order = None
        currency, market = symbol_util.parse_symbol(order_data.symbol).base_and_quote()
        try:
            base_available = trading_api.get_portfolio_currency(self.exchange_manager, currency).available
            quote_available = trading_api.get_portfolio_currency(self.exchange_manager, market).available
            selling = order_data.side == trading_enums.TradeOrderSide.SELL
            quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
                self.exchange_manager, order_data.symbol,
                trading_enums.TraderOrderType.SELL_LIMIT if selling else trading_enums.TraderOrderType.BUY_LIMIT,
                order_data.quantity, order_data.price, order_data.side,
            )
            orders_quantity_and_price = trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                quantity,
                order_data.price,
                symbol_market
            )
            if orders_quantity_and_price:
                if len(orders_quantity_and_price) > 1:
                    self.logger.error(
                        f"Orders to create are too large and have to be split. This is not supported. "
                        f"Only creating the 1s order."
                    )
                    orders_quantity_and_price = orders_quantity_and_price[:1]
                for order_quantity, order_price in orders_quantity_and_price:
                    order_desc = (
                        f"{order_data.symbol} {order_data.side.value} [{self.exchange_manager.exchange_name}] order "
                        f"creation of {order_quantity} at {float(order_price)}"
                    )
                    should_skip, skip_message = self._should_skip(
                        selling, base_available, quote_available, order_quantity, order_price, order_desc, currency,
                        market, **kwargs
                    )
                    if should_skip:
                        self.logger.warning(f"Skipping {skip_message}")
                        return []
                    order_type = trading_enums.TraderOrderType.SELL_LIMIT if selling \
                        else trading_enums.TraderOrderType.BUY_LIMIT
                    current_order = trading_personal_data.create_order_instance(
                        trader=self.exchange_manager.trader,
                        order_type=order_type,
                        symbol=order_data.symbol,
                        current_price=current_price,
                        quantity=order_quantity,
                        price=order_price,
                    )
                    # disable instant fill to avoid looping order fill in simulator
                    current_order.allow_instant_fill = False
                    created_order = await self.trading_mode.create_order(current_order)
            if not created_order:
                self.logger.warning(
                    f"No order created for {order_data} (quantity: {quantity}): "
                    f"incompatible with exchange minimum rules. "
                    f"Limits: {symbol_market[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]}"
                )
        except (SkippedAction, trading_errors.MissingFunds):
            raise
        except Exception as err:
            self.logger.error(f"Failed to create order : {err}. Order: {order_data}")
            return []
        return [] if created_order is None else [created_order]

    def _should_skip(
        self, selling, base_available, quote_available, order_quantity, order_price,
        order_desc, currency, market, **kwargs
    ):
        skip_message = ""
        if selling:
            if base_available < order_quantity:
                skip_message = (
                    f"{order_desc}: "
                    f"not enough {currency}: available: {base_available}, required: {order_quantity}"
                )
        elif quote_available < order_quantity * order_price:
            skip_message = (
                f"Skipping {order_desc}: not enough {market}: available: {quote_available}, "
                f"required: {order_quantity * order_price}"
            )
        return bool(skip_message), skip_message


class MarketMakingTradingModeProducer(trading_modes.AbstractTradingModeProducer):
    PRICE_FETCHING_TIMEOUT = 60
    ORDER_ACTION_TIMEOUT = 20
    INIT_RETRY_TIMER = 5
    REFERENCE_PRICE_INIT_DELAY = 60 # allow 60s before logging missing reference prices as error
    ORDERS_DESC = "market making"


    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        # no state for this evaluator: always neutral
        self.state = trading_enums.EvaluatorStates.NEUTRAL

        # config
        self.symbol: str = trading_mode.symbol
        self.order_book_distribution: order_book_distribution.OrderBookDistribution = None
        self.reference_price = reference_price_import.PriceSource
        self.replace_whole_book_distance_threshold: float = 0.5

        self.symbol_trading_config: dict = None
        self.healthy = False
        self.is_first_execution: bool = True
        self._started_at: float = 0
        self._last_error_at: float = 0
        self.latest_actions_plan: OrdersUpdatePlan = None
        self.last_target_buy_orders_count: int = 0
        self.last_target_sell_orders_count: int = 0
        self.subscribed_requirements_exchange_ids: set[str] = set()

        try:
            self._load_symbol_trading_config()
        except KeyError as e:
            error_message = f"Impossible to start {self.ORDERS_DESC} orders for {self.symbol}: missing " \
                            f"configuration in trading mode config file. "
            self.logger.exception(e, True, error_message)
            return
        if self.symbol_trading_config is None:
            return
        self.read_config()

        self.logger.debug(f"Loaded healthy config for {self.symbol}")
        self.healthy: bool = True
        self._last_disabled_trader_log_at: float = 0

    def _load_symbol_trading_config(self) -> bool:
        self.symbol_trading_config = self.trading_mode.get_pair_settings()[0]
        return True

    def read_config(self):
        self.order_book_distribution = self.trading_mode.get_order_book_distribution(self.symbol_trading_config)
        self.reference_price = reference_price_import.PriceSource(
            self.symbol_trading_config[self.trading_mode.REFERENCE_EXCHANGE],
            self.symbol
        )
        if len(self.exchange_manager.exchange_config.traded_symbols) > 1:
            error = (
                f"Multiple trading pair is not supported on {self.trading_mode.get_name()}. "
                f"Please select only one trading pair in configuration."
            )
            asyncio.create_task(
                self.sent_once_critical_notification(
                    "Configuration issue",
                    error
                )
            )
            raise ValueError(error)
        enabled_exchanges = trading_exchanges.get_enabled_exchanges(self.exchange_manager.config)
        if (
            self.reference_price.exchange != self.trading_mode.LOCAL_EXCHANGE_PRICE and
            self.reference_price.exchange not in enabled_exchanges
        ):
            error = (
                f"Reference exchange is missing from configuration. Please add {self.reference_price.exchange} to "
                f"configured exchanges or use another reference exchange."
            )
            asyncio.create_task(
                self.sent_once_critical_notification(
                    "Configuration issue",
                    error
                )
            )
            raise ValueError(error)

    async def start(self) -> None:
        await super().start()
        if self.healthy:
            await self._register_pair_requirement_on_reference_exchange()
            self.logger.debug(f"Initializing orders creation")
            await self._ensure_market_making_orders_and_reschedule()

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        # nothing to do: this is not a strategy related trading mode
        pass

    async def _register_pair_requirement_on_reference_exchange(self):
        await trading_api.register_new_pairs_on_exchange(
            self.exchange_manager.exchange_name,
            trading_api.get_matrix_id_from_exchange_id(
                self.exchange_manager.exchange_name, self.exchange_manager.id
            ),
            [self.symbol],
            watch_only=True
        )

    def _schedule_order_refresh(self):
        # schedule order creation / health check
        asyncio.create_task(self._ensure_market_making_orders_and_reschedule())

    async def _ensure_market_making_orders_and_reschedule(self):
        if self.should_stop:
            return
        can_create_orders = (
            not trading_api.get_is_backtesting(self.exchange_manager)
            or trading_api.is_mark_price_initialized(self.exchange_manager, symbol=self.symbol)
        ) and (
            trading_api.get_portfolio(self.exchange_manager) != {}
            or trading_api.is_trader_simulated(self.exchange_manager)
        )
        if can_create_orders:
            try:
                if not await self._ensure_market_making_orders(
                    "initial trigger" if self.is_first_execution else "periodic trigger"
                ):
                    can_create_orders = False
            except asyncio.TimeoutError:
                can_create_orders = False
        if not self.should_stop:
            await self._reschedule_if_necessary(can_create_orders)

    async def _reschedule_if_necessary(self, can_create_orders: bool):
        if not can_create_orders:
            self.logger.info(
                f"Can't yet create initialize orders for {self.symbol}, retrying in {self.INIT_RETRY_TIMER} seconds"
            )
            # avoid spamming retries when price is not available
            self.scheduled_health_check = asyncio.get_event_loop().call_later(
                self.INIT_RETRY_TIMER,
                self._schedule_order_refresh
            )

    async def _ensure_market_making_orders(self, trigger_source: str) -> bool:
        # can be called:
        #   - on initialization
        #   - when price moves beyond spread
        #   - when orders are filled
        _, _, _, current_price, symbol_market = await trading_personal_data.get_pre_order_data(
            self.exchange_manager,
            symbol=self.symbol,
            timeout=self.PRICE_FETCHING_TIMEOUT
        )
        return await self.create_state(current_price, symbol_market, trigger_source, False)

    async def create_state(
        self, current_price, symbol_market, trigger_source: str, force_full_refresh: bool
    ) -> bool:
        if current_price is not None:
            async with self.trading_mode_trigger(skip_health_check=True):
                try:
                    if await self._handle_market_making_orders(
                        current_price, symbol_market, trigger_source, force_full_refresh
                    ):
                        self.is_first_execution = False
                        self._started_at = self.exchange_manager.exchange.get_exchange_current_time()
                        return True
                except trading_errors.TraderDisabledError as err:
                    current_time = self.exchange_manager.exchange.get_exchange_current_time()
                    current_minute_ts = current_time - current_time % (5 * common_constants.MINUTE_TO_SECONDS)
                    if self._last_disabled_trader_log_at < current_minute_ts:
                        # log warning at most once per 5 minutes to avoid spamming at each new price
                        self.logger.warning(str(err))
                        self._last_disabled_trader_log_at = current_minute_ts
                    return False
                except ValueError as err:
                    if self._last_error_at <= self._started_at:
                        # only log full exception every 1st time it occurs then use warnings to avoid flooding
                        # when on websockets
                        self.logger.exception(
                            err, True, f"Unexpected error when starting {self.symbol} trading mode: {err}"
                        )
                    else:
                        self.logger.warning(f"Skipped {self.symbol} orders update: {err}")
                    self._last_error_at = self.exchange_manager.exchange.get_exchange_current_time()
                    if "Missing volume" not in str(err):
                        # config error: should not happen, in this case, return true to skip auto reschedule
                        await self.sent_once_critical_notification(
                            "Configuration issue",
                            f"Impossible to start {self.symbol} market making "
                            f"on {self.exchange_manager.exchange_name}: {err}"
                        )
                    return True
        return False

    def _is_previous_plan_still_processing(self) -> bool:
        return self.latest_actions_plan is not None and not self.latest_actions_plan.processed.is_set()

    @trading_modes.enabled_trader_only(raise_when_disabled=True)
    async def _handle_market_making_orders(
        self, current_price, symbol_market, trigger_source: str, force_full_refresh: bool
    ):
        # 1. get price from external source
        reference_price = await self._get_reference_price()
        if not reference_price:
            method = self.logger.info if self.is_first_execution else self.logger.error
            method(
                f"Skipped trigger: can't compute {self.symbol} reference price for"
                f" {self.exchange_manager.exchange_name}: {reference_price=}"
            )
            return False
        daily_base_volume, daily_quote_volume = self._get_daily_volume(reference_price)
        if not all(v and not v.is_nan() for v in (daily_base_volume, daily_quote_volume)):
            method = self.logger.info if self.is_first_execution else self.logger.error
            method(
                f"Skipped trigger: can't compute {self.symbol} daily volume for"
                f" {self.exchange_manager.exchange_name}: {daily_base_volume=} {daily_quote_volume=}"
            )
            return False
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        self.logger.info(
            f"Trigger for {self.symbol} on {self.exchange_manager.exchange_name}. Ref price: {float(reference_price)} "
            f"daily {base} vol: {octobot_commons.pretty_printer.get_min_string_from_number(daily_base_volume)} "
            f"daily {quote} vol: {octobot_commons.pretty_printer.get_min_string_from_number(daily_quote_volume)} "
            f"[trigger source: {trigger_source}]"
        )
        open_orders = self.get_market_making_orders()
        require_data_refresh = False
        if self._is_previous_plan_still_processing():
            # if previous plan is still processing but being cancelled: skip call (another one is waiting for cancel)
            skip_exec = self.latest_actions_plan.cancelled
            # if previous plan is still processing and not being cancelled: check if cancel is required
            if not self.latest_actions_plan.cancelled:
                # only cancel latest plan if outdated and still processing, otherwise ignore signal
                previous_plan_orders = [
                    action.order_data
                    for action in self.latest_actions_plan.order_actions
                    if isinstance(action, CreateOrderAction)
                ]
                previous_plan_cancelled_orders = [
                    action.order
                    for action in self.latest_actions_plan.order_actions
                    if isinstance(action, CancelOrderAction)
                ]
                remaining_open_orders = [
                    order
                    for order in open_orders
                    if order not in previous_plan_cancelled_orders
                ]
                if self._get_orders_to_cancel(previous_plan_orders + remaining_open_orders, reference_price):
                    # cancel previous plan
                    self.latest_actions_plan.cancelled = True
                    if self.latest_actions_plan.cancellable:
                        self.logger.debug(
                            f"Cancelling previous plan after {reference_price} {self.symbol} price update for "
                            f"{self.exchange_manager.exchange_name}: orders are outdated "
                            f"[trigger source: {trigger_source}]."
                        )
                    else:
                        self.logger.debug(
                            f"Waiting for non-cancellable action plan to complete: {reference_price} {self.symbol} "
                            f"price update for {self.exchange_manager.exchange_name}: orders are outdated "
                            f"[trigger source: {trigger_source}]."
                        )
                    try:
                        waiting_plan = self.latest_actions_plan
                        await asyncio.wait_for(waiting_plan.processed.wait(), self.ORDER_ACTION_TIMEOUT)
                        if (
                            self.latest_actions_plan is not waiting_plan
                            and not self.latest_actions_plan.processed.is_set()
                        ):
                            # plan just changed, skip this update
                            self.logger.debug(
                                f"Skip {self.symbol} {self.exchange_manager.exchange_name} plan execution: a new"
                                f"plan is already being executed [trigger source: {trigger_source}]"
                            )
                            skip_exec = True
                        else:
                            self.logger.debug(
                                f"Continuing {reference_price} {self.symbol} after latest action plan cancel "
                                f"[trigger source: {trigger_source}]"
                            )
                    except asyncio.TimeoutError:
                        # don't continue, next refresh will take care of it
                        self.logger.debug(
                            f"Timeout when waiting for {reference_price} {self.symbol} latest action plan: "
                            f"{str(self.latest_actions_plan)} [trigger source: {trigger_source}]"
                        )
                        skip_exec = True
                    finally:
                        require_data_refresh = True
                else:
                    skip_exec = True
            if skip_exec:
                # let previous plan execute, ignore signal
                self.logger.debug(
                    f"Ignored {reference_price} {self.symbol} price update for {self.exchange_manager.exchange_name} "
                    f"while previous orders plan is still processing [trigger source: {trigger_source}]"
                )
                return False

        if require_data_refresh:
            # update reference price in case it changed
            reference_price = await self._get_reference_price()
            if not reference_price:
                self.logger.error(
                    f"Can't compute reference price for {self.exchange_manager.exchange_name}: after waiting "
                    f"for previous plan processing: {reference_price=}"
                )
                return False
            # update open orders in case it changed after waiting
            open_orders = self.get_market_making_orders()

        sorted_orders = self._sort_orders(open_orders)
        available_base, available_quote = self._get_available_funds()
        theoretically_available_base, theoretically_available_quote = (
            self._get_all_theoretically_available_funds(open_orders)
        )
        self.logger.debug(
            f"MM available {self.symbol} funds: {base}: {float(available_base)} {quote}: {float(available_quote)}"
        )

        # 2. cancel outdated orders
        outdated_orders = self._get_orders_to_cancel(sorted_orders, reference_price)
        if outdated_orders:
            self.logger.info(
                f"{len(outdated_orders)} outdated orders for {self.symbol} on {self.exchange_manager.exchange_name} (trigger_source: {trigger_source}): "
                f"{[str(o) for o in outdated_orders]}"
            )

        # get ideal distribution
        ideal_distribution = self.order_book_distribution.compute_distribution(
            reference_price,
            daily_base_volume, daily_quote_volume,
            symbol_market,
            available_base=theoretically_available_base, available_quote=theoretically_available_quote,
        )
        # update last target orders count
        self.last_target_sell_orders_count = len(ideal_distribution.asks)
        self.last_target_buy_orders_count = len(ideal_distribution.bids)
        cancelled_orders = created_orders = []
        missing_all_orders_sides = []
        try:
            if force_full_refresh:
                raise order_book_distribution.FullBookRebalanceRequired("Forced full refresh")
            book_orders_after_swaps, cancelled_orders, created_orders = (
                self._get_swapped_book_orders(
                    sorted_orders, outdated_orders, available_base, available_quote, reference_price,
                    ideal_distribution, daily_base_volume, daily_quote_volume
                )
            )
            is_spread_according_to_config = ideal_distribution.is_spread_according_to_config(
                book_orders_after_swaps, open_orders
            )
            # Compute distance from distribution.
            # Warning: filled orders result in more funds being available, which can create full order book rebalance as
            # distance from ideal would become too large. This can happen when the order book depth is far from the required
            # value.
            distance_from_ideal_after_swaps = ideal_distribution.get_shape_distance_from(
                book_orders_after_swaps, theoretically_available_base, theoretically_available_quote,
                reference_price, daily_base_volume, daily_quote_volume, trigger_source
            )
            can_just_replace_a_few_orders = is_spread_according_to_config and (
                distance_from_ideal_after_swaps < self.replace_whole_book_distance_threshold
            )
        except order_book_distribution.MissingOrderException as err:
            orders = []
            if isinstance(err, order_book_distribution.MissingAllOrders):
                orders = ideal_distribution.asks + ideal_distribution.bids
                missing_all_orders_sides.extend((trading_enums.TradeOrderSide.BUY, trading_enums.TradeOrderSide.SELL))
            elif isinstance(err, order_book_distribution.MissingAllAsks):
                orders = ideal_distribution.asks
                missing_all_orders_sides.append(trading_enums.TradeOrderSide.SELL)
            elif isinstance(err, order_book_distribution.MissingAllBids):
                orders = ideal_distribution.bids
                missing_all_orders_sides.append(trading_enums.TradeOrderSide.BUY)
            # no open order but can create some if the total amount of orders is > 0
            # => means we have the funds to create those orders, we should create them
            self.logger.info(
                f"Missing orders on {2 if isinstance(err, order_book_distribution.MissingAllOrders) else 1} "
                f"side: {err.__class__.__name__}"
            )
            is_spread_according_to_config = False
            distance_from_ideal_after_swaps = trading_constants.ONE
            can_just_replace_a_few_orders = not sum(o.amount for o in orders) > trading_constants.ZERO
        except order_book_distribution.FullBookRebalanceRequired as err:
            cancelled_orders = created_orders = []
            is_spread_according_to_config = True
            distance_from_ideal_after_swaps = trading_constants.ONE
            can_just_replace_a_few_orders = False
            self.logger.info(f"Scheduling full order book refresh: {err}")

        if can_just_replace_a_few_orders:
            if sum(o.amount for o in created_orders) <= trading_constants.ZERO:
                # no order can be created (not enough funds)
                created_orders = []
                await self._send_missing_funds_critical_notification(missing_all_orders_sides)
                self.logger.info(
                    f"No order to create (order amounts is 0), leaving book as is [trigger source: {trigger_source}]"
                )
            elif not self._can_create_all_order(created_orders, symbol_market):
                # if orders can't be created (because too small for example), then recreate the whole book to
                # create all orders
                self.logger.warning(
                    f"Missing funds: few orders can't be created, resizing book instead [trigger source: {trigger_source}]"
                )
                can_just_replace_a_few_orders = False

        if can_just_replace_a_few_orders:
            # A. Threshold is not met
            if not (outdated_orders or cancelled_orders or created_orders):
                # A.1: no order to replace, nothing to do
                self.logger.debug(
                    f"{self.symbol} {self.exchange_manager.exchange_name} orders are up to date "
                    f"[trigger source: {trigger_source}]"
                )
                return True
            else:
                # A.2: orders are just created to fill the order book
                self.logger.info(
                    f"Replacing {self.symbol} {self.exchange_manager.exchange_name} missing orders: "
                    f"{len(outdated_orders)} outdated orders, {len(cancelled_orders)} cancelled_orders, "
                    f"{len(created_orders)} created_orders spread conform to config: {is_spread_according_to_config} "
                    f"[trigger source: {trigger_source}]"
                )
                order_actions_plan = self._get_create_missing_orders_plan(
                    outdated_orders, cancelled_orders, created_orders
                )
        else:
            # B. A full order book replacement is required if new orders can fix the issue
            if len(missing_all_orders_sides) != 1 or (
                len(missing_all_orders_sides) == 1 and ideal_distribution.can_create_at_least_one_order(
                    missing_all_orders_sides, symbol_market
                )
            ):
                # B.1: Orders should and can be replaced: replaced them one by one
                self.logger.info(
                    f"Re-creating the whole {self.symbol} {self.exchange_manager.exchange_name} order book: book is too "
                    f"different from configuration (distance: {distance_from_ideal_after_swaps}) "
                    f"[trigger source: {trigger_source}]"
                )
            else:
                # B.2: Orders can't be replaced: they are not following exchange requirements: skip them
                for side in missing_all_orders_sides:
                    # filter out orders
                    created_orders = [
                        order for order in created_orders
                        if order.side != side
                    ]
                    # remove filtered orders from ideal_distribution in case an action plan gets created
                    if side == trading_enums.TradeOrderSide.BUY:
                        ideal_distribution.bids.clear()
                    else:
                        ideal_distribution.asks.clear()
                skip_iteration = not created_orders and not cancelled_orders
                error_details = await self._send_missing_funds_critical_notification(missing_all_orders_sides)
                self.logger.warning(f"{'Skipped iteration: ' if skip_iteration else ''}{error_details}")
                if skip_iteration:
                    # all the orders to create can't actually be created and there is nothing to replace: nothing to do
                    return True
            # create action plan from ideal distribution
            order_actions_plan = self._get_replace_full_book_plan(
                outdated_orders, sorted_orders, ideal_distribution
            )

        order_actions_plan.trigger_source = trigger_source
        # 4. push orders creation and cancel plan
        await self._schedule_order_actions(order_actions_plan, current_price, symbol_market)
        return True

    async def _send_missing_funds_critical_notification(self, missing_all_orders_sides) -> str:
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        required_funds = []
        for side in missing_all_orders_sides:
            if side == trading_enums.TradeOrderSide.BUY:
                required_funds.append(quote)
            else:
                required_funds.append(base)
        if required_funds:
            missing_funds = ' and '.join(required_funds)
            error_details = (
                f"Impossible to create {self.symbol} {' and '.join([s.value for s in missing_all_orders_sides])} "
                f"orders: missing available funds to comply with {self.exchange_manager.exchange_name} "
                f"minimal order size rules. Additional {missing_funds} required."
            )
            await self.sent_once_critical_notification(f"More {missing_funds} required", error_details)
            return error_details
        return ""

    def _can_create_all_order(self, created_orders: list[order_book_distribution.BookOrderData], symbol_market):
        for order in created_orders:
            if not trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                order.amount,
                order.price,
                symbol_market
            ):
                self.logger.info(f"{order} can't be created: {order.amount=} or {order.price=} are too small")
                return False
        return True

    def _get_swapped_book_orders(
        self, sorted_orders, outdated_orders, available_base,
        available_quote, reference_price, ideal_distribution,
        daily_base_volume, daily_quote_volume
    ):
        remaining_orders = [o for o in sorted_orders if o not in outdated_orders]
        remaining_orders_data = [
            order_book_distribution.BookOrderData(
                o.origin_price,
                o.origin_quantity,
                o.side,
            )
            for o in remaining_orders
        ]
        remaining_order_prices = [o.price for o in remaining_orders_data]
        updated_book_orders: list[order_book_distribution.BookOrderData] = (
            ideal_distribution.infer_full_order_data_after_swaps(
                remaining_orders_data, outdated_orders, available_base,
                available_quote, reference_price, daily_base_volume, daily_quote_volume
            )
        )
        created_orders = [
            order
            for order in updated_book_orders
            if order.price not in remaining_order_prices
        ]
        updated_book_order_prices = [o.price for o in updated_book_orders]
        cancelled_orders = [
            order
            for order in remaining_orders
            if order.origin_price not in updated_book_order_prices
        ]
        return updated_book_orders, cancelled_orders, created_orders

    def _get_create_missing_orders_plan(
        self,
        outdated_orders: list[trading_personal_data.Order],
        cancelled_orders: list[trading_personal_data.Order],
        created_orders: list[order_book_distribution.BookOrderData]
    ) -> OrdersUpdatePlan:
        # 1. cancel outdated orders
        orders_actions: list[OrderAction] = [CancelOrderAction(order) for order in outdated_orders]
        # 2. replace orders
        orders_actions += self._get_alternated_cancel_and_create_order_actions(
            cancelled_orders, created_orders, False
        )
        return OrdersUpdatePlan(orders_actions)

    def _get_replace_full_book_plan(
        self,
        outdated_orders: list[trading_personal_data.Order],
        existing_orders: list[trading_personal_data.Order],
        ideal_distribution: order_book_distribution.OrderBookDistribution
    ) -> OrdersUpdatePlan:
        # 1. cancel outdated orders
        orders_actions: list[OrderAction] = [CancelOrderAction(order) for order in outdated_orders]
        cancelled_orders = [o for o in existing_orders if o not in outdated_orders]
        # 2. recreate orders
        orders_actions += self._get_alternated_cancel_and_create_order_actions(
            cancelled_orders, ideal_distribution.asks + ideal_distribution.bids, True
        )
        return OrdersUpdatePlan(orders_actions, cancellable=False)

    def _get_alternated_cancel_and_create_order_actions(
        self,
        cancelled_orders: list[trading_personal_data.Order],
        created_orders: list[order_book_distribution.BookOrderData],
        cancel_closer_orders_first_from_second_cancel: bool,
    ):
        orders_actions: list[OrderAction] = []
        cancelled_buy_orders, created_buy_orders, cancelled_sell_orders, created_sell_orders = \
            self._get_prioritized_orders(
                cancelled_orders, created_orders, cancel_closer_orders_first_from_second_cancel
            )
        # alternate between cancel and create to "move" orders to their new price
        for i in range(max(
            len(cancelled_buy_orders), len(created_buy_orders), len(cancelled_sell_orders), len(created_sell_orders)
        )):
            if i < len(cancelled_buy_orders):
                orders_actions.append(CancelOrderAction(cancelled_buy_orders[i]))
            if i < len(cancelled_sell_orders):
                orders_actions.append(CancelOrderAction(cancelled_sell_orders[i]))
            if i < len(created_buy_orders):
                orders_actions.append(CreateOrderAction.from_book_order_data(self.symbol, created_buy_orders[i]))
            if i < len(created_sell_orders):
                orders_actions.append(CreateOrderAction.from_book_order_data(self.symbol, created_sell_orders[i]))
        return orders_actions

    def _get_prioritized_orders(
        self,
        cancelled_orders: list[trading_personal_data.Order],
        created_orders: list[order_book_distribution.BookOrderData],
        cancel_closer_orders_first_from_second_cancel: bool,
    ):
        # 1st cancelled order is always the furthest from spread.
        cancelled_buy_orders = sorted(
            [o for o in cancelled_orders if o.side is trading_enums.TradeOrderSide.BUY],
            key=lambda o: o.origin_price,  # lowest first
        )
        cancelled_sell_orders = sorted(
            [o for o in cancelled_orders if o.side is trading_enums.TradeOrderSide.SELL],
            key=lambda o: o.origin_price, reverse=True,  # highest first
        )
        if cancel_closer_orders_first_from_second_cancel:
            # 2nd cancelled order onwards are either start from the spread or from the outer orders
            if len(cancelled_buy_orders) > 1:
                cancelled_buy_orders = [cancelled_buy_orders[0]] + list(reversed(cancelled_buy_orders[1:]))
            if len(cancelled_sell_orders) > 1:
                cancelled_sell_orders = [cancelled_sell_orders[0]] + list(reversed(cancelled_sell_orders[1:]))
        created_buy_orders = order_book_distribution.get_sorted_sided_orders(
            [o for o in created_orders if o.side is trading_enums.TradeOrderSide.BUY],
            True  # highest first
        )

        created_sell_orders = order_book_distribution.get_sorted_sided_orders(
            [o for o in created_orders if o.side is trading_enums.TradeOrderSide.SELL],
            True  # lowest first
        )
        return (
            cancelled_buy_orders, created_buy_orders, cancelled_sell_orders, created_sell_orders
        )

    def _get_orders_to_cancel(
        self,
        open_orders: list[typing.Union[trading_personal_data.Order, OrderData]],
        reference_price: decimal.Decimal
    ) -> list[trading_personal_data.Order]:
        return [
            order
            for order in open_orders
            if self._is_outdated(
                order.origin_price if isinstance(order, trading_personal_data.Order) else order.price,
                order.side,
                reference_price
            )
        ]

    def _is_outdated(
        self, order_price: decimal.Decimal, side: trading_enums.TradeOrderSide, reference_price: decimal.Decimal
    ) -> bool:
        if side == trading_enums.TradeOrderSide.BUY:
            return order_price > reference_price
        return order_price < reference_price

    def _sort_orders(self, open_orders: list) -> list:
        """
        Sort orders from the closest to the farthest from spread starting with buy orders
        """
        buy_orders = [o for o in open_orders if o.side == trading_enums.TradeOrderSide.BUY]
        sell_orders = [o for o in open_orders if o.side == trading_enums.TradeOrderSide.SELL]
        return (
            sorted(buy_orders, key=lambda o: o.origin_price, reverse=True)
            + sorted(sell_orders, key=lambda o: o.origin_price)
        )

    @classmethod
    def get_should_cancel_loaded_orders(cls):
        return False

    async def _schedule_order_actions(self, order_actions_plan: OrdersUpdatePlan, current_price, symbol_market):
        if self.should_stop:
            self.logger.info(
                f"Skipping scheduling order actions for {self.symbol} {self.exchange_manager.exchange_name}: "
                f"bot should stop"
            )
            return
        self.logger.info(
            f"Scheduling {self.symbol} {self.exchange_manager.exchange_name} {str(order_actions_plan)} using "
            f"current price: {current_price}"
        )
        data = {
            MarketMakingTradingModeConsumer.ORDER_ACTIONS_PLAN_KEY: order_actions_plan,
            MarketMakingTradingModeConsumer.CURRENT_PRICE_KEY: current_price,
            MarketMakingTradingModeConsumer.SYMBOL_MARKET_KEY: symbol_market,
        }
        self.latest_actions_plan = order_actions_plan
        await self.submit_trading_evaluation(
            cryptocurrency=self.trading_mode.cryptocurrency,
            symbol=self.trading_mode.symbol,
            time_frame=None,
            state=trading_enums.EvaluatorStates.NEUTRAL,
            data=data
        )

    def _get_orders_to_create(
        self,
        reference_price: decimal.Decimal,
        daily_base_volume: decimal.Decimal, daily_quote_volume: decimal.Decimal,
        available_base: decimal.Decimal, available_quote: decimal.Decimal,
        symbol_market: dict
    ) -> list[OrderData]:
        orders = []
        distribution = self.order_book_distribution.compute_distribution(
            reference_price,
            daily_base_volume, daily_quote_volume,
            symbol_market,
            available_base=available_base, available_quote=available_quote,
        )
        asks = collections.deque(
            OrderData(
                trading_enums.TradeOrderSide.SELL,
                book_order.amount,
                book_order.price,
                self.symbol,

            )
            for book_order in distribution.asks
        )
        bids = collections.deque(
            OrderData(
                trading_enums.TradeOrderSide.BUY,
                book_order.amount,
                book_order.price,
                self.symbol,

            )
            for book_order in distribution.bids
        )
        self.logger.info(
            f"{self.symbol} {self.exchange_manager.exchange_name} target market marking orders: "
            f"{len(bids)} bids & {len(asks)} asks: {bids=} {asks=}"
        )
        # alternate by and sell orders to create book from the inside out
        while asks and bids:
            orders.append(asks.pop())
            orders.append(bids.pop())
        # add remaining orders if any
        if asks:
            orders += list(asks)
        if bids:
            orders += list(bids)
        return orders

    def _get_daily_volume(self, reference_price: decimal.Decimal) -> (decimal.Decimal, decimal.Decimal):
        symbol_data = self.exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
            self.symbol, allow_creation=False
        )
        try:
            return trading_api.get_daily_base_and_quote_volume(symbol_data, reference_price)
        except ValueError as err:
            raise ValueError(
                f"Missing volume for {self.symbol} on {self.exchange_manager.exchange_name}: "
                f"{err}. {reference_price=}"
            ) from err

    def _get_available_funds(self) -> (decimal.Decimal, decimal.Decimal):
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        return (
            trading_api.get_portfolio_currency(self.exchange_manager, base).available,
            trading_api.get_portfolio_currency(self.exchange_manager, quote).available
        )

    def _get_all_theoretically_available_funds(self, open_orders: list) -> (decimal.Decimal, decimal.Decimal):
        technically_available_base, technically_available_quote = self._get_available_funds()
        for order in open_orders:
            # order.filled_quantity is not handled in simulator
            filled_quantity = trading_constants.ZERO if self.exchange_manager.trader.simulate else order.filled_quantity
            if order.side == trading_enums.TradeOrderSide.BUY:
                initial_cost = order.origin_quantity * order.origin_price
                filled_cost = filled_quantity * order.filled_price
                technically_available_quote += initial_cost - filled_cost
            elif order.side == trading_enums.TradeOrderSide.SELL:
                technically_available_base += order.origin_quantity - filled_quantity
        return technically_available_base, technically_available_quote

    def get_market_making_orders(self) -> list[trading_personal_data.Order]:
        return [
            order
            for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
                symbol=self.symbol
            )
            # exclude market and stop orders
            if isinstance(order, (trading_personal_data.BuyLimitOrder, trading_personal_data.SellLimitOrder))
        ]

    def _is_missing_open_orders(
        self, sided_orders: list[trading_personal_data.Order], side: trading_enums.TradeOrderSide
    ) -> bool:
        if not sided_orders:
            # no orders on this side: orders are missing
            return True
        if (last_target_orders_count := (
            self.last_target_buy_orders_count
            if side == trading_enums.TradeOrderSide.BUY
            else self.last_target_sell_orders_count
        )) and (len(sided_orders) < last_target_orders_count) and not self._is_previous_plan_still_processing():
            self.logger.info(
                f"Missing {last_target_orders_count - len(sided_orders)} {self.symbol} {side.value} "
                f"orders [{self.exchange_manager.exchange_name}], last target count: {last_target_orders_count}"
            )
            # at least one order is missing compared to the last check
            return True
        return False

    async def on_new_reference_price(self, reference_price: decimal.Decimal) -> bool:
        trigger = False
        open_orders = self.get_market_making_orders()
        buy_orders = [
            order
            for order in open_orders
            if order.side == trading_enums.TradeOrderSide.BUY
        ]
        if self._is_missing_open_orders(buy_orders, trading_enums.TradeOrderSide.BUY):
            trigger = True
        else:
            max_buy_price = max(order.origin_price for order in buy_orders)
            if max_buy_price > reference_price:
                trigger = True
        sell_orders = [
            order
            for order in open_orders
            if order.side == trading_enums.TradeOrderSide.SELL
        ]
        if self._is_missing_open_orders(sell_orders, trading_enums.TradeOrderSide.SELL):
            trigger = True
        else:
            min_sell_price = min(order.origin_price for order in sell_orders)
            if min_sell_price < reference_price:
                trigger = True
        return trigger

    async def _on_reference_price_update(self):
        trigger = False
        if reference_price := await self._get_reference_price():
            trigger = await self.on_new_reference_price(reference_price)
        if trigger:
            await self._ensure_market_making_orders(f"reference price update: {float(reference_price)}")

    async def order_filled_callback(self, order: dict):
        self.logger.info(
            f"Triggering {self.symbol} [{self.exchange_manager.exchange_name}] order update an order got filled: "
            f"{order}"
        )
        await self._ensure_market_making_orders(
            f"filled {order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]} order"
        )

    async def _mark_price_callback(
        self, exchange: str, exchange_id: str, cryptocurrency: str, symbol: str, mark_price
    ):
        """
        Called on a price update from an exchange that is different from the current one
        :param exchange: name of the exchange
        :param exchange_id: id of the exchange
        :param cryptocurrency: related cryptocurrency
        :param symbol: related symbol
        :param mark_price: updated mark price
        :return: None
        """
        await self._on_reference_price_update()

    async def _register_pair_requirement_on_reference_exchanges(self):
        local_exchange_name = self.exchange_manager.exchange_name
        for exchange_id in trading_api.get_all_exchange_ids_with_same_matrix_id(
            local_exchange_name, self.exchange_manager.id
        ):
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            if exchange_manager.trading_modes and exchange_manager is not self.exchange_manager:
                await self.sent_once_critical_notification(
                    "Configuration issue",
                    f"Multiple simultaneous trading exchanges is not supported on {self.trading_mode.get_name()}"
                )
            other_exchange_key = self.trading_mode.LOCAL_EXCHANGE_PRICE if (
                self.trading_mode.LOCAL_EXCHANGE_PRICE == self.reference_price.exchange
                and local_exchange_name == exchange_manager.exchange_name
            ) else exchange_manager.exchange_name
            if other_exchange_key != self.reference_price.exchange:
                continue
            if exchange_id not in self.subscribed_requirements_exchange_ids:
                await self._subscribe_to_exchange_mark_price(exchange_id, exchange_manager)
                self.subscribed_requirements_exchange_ids.add(exchange_id)
    
    def _is_registered_on_all_reference_exchanges(self) -> bool:
        return len(self.subscribed_requirements_exchange_ids) == 1

    async def _subscribe_to_exchange_mark_price(self, exchange_id: str, exchange_manager):
        if not self.already_subscribed_to_channel(
            exchange_id, trading_constants.MARK_PRICE_CHANNEL, self._mark_price_callback, symbol=self.trading_mode.symbol
        ):
            await exchanges_channel.get_chan(trading_constants.MARK_PRICE_CHANNEL, exchange_id).new_consumer(
                callback=self._mark_price_callback,
                symbol=self.trading_mode.symbol
            )
            self.logger.info(
                f"{self.trading_mode.get_name()} for {self.trading_mode.symbol} on {self.exchange_name}  "
                f"subscribed to {exchange_manager.exchange_name} price data feed."
            )

    def already_subscribed_to_channel(
        self, exchange_id: str, channel: str, callback: typing.Callable, **filter_kwargs
    ) -> bool:
        chan = exchanges_channel.get_chan(channel, exchange_id)
        consumers = chan.get_consumer_from_filters(filter_kwargs)
        return any(consumer.callback == callback for consumer in consumers)

    async def _register_on_reference_exchanges_if_required(self) -> bool:
        """
        Returns True if all reference exchanges have already been registered
        """
        if self._is_registered_on_all_reference_exchanges():
            return True
        self.logger.debug(
            f"Not all reference exchanges are registered for {self.symbol}. Skipping trigger for {self.symbol}"
        )
        await self._register_pair_requirement_on_reference_exchanges()
        return self._is_registered_on_all_reference_exchanges()

    async def _get_reference_price(self) -> decimal.Decimal:
        if not await self._register_on_reference_exchanges_if_required():
            return trading_constants.ZERO
        local_exchange_name = self.exchange_manager.exchange_name
        price = trading_constants.ZERO
        for exchange_id in trading_api.get_all_exchange_ids_with_same_matrix_id(
            local_exchange_name, self.exchange_manager.id
        ):
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            try:
                price, updated = trading_personal_data.get_potentially_outdated_price(
                    exchange_manager, self.reference_price.pair
                )
                if not updated:
                    self.logger.warning(
                        f"{exchange_manager.exchange_name} mark price: {price} is outdated for {self.symbol}. "
                        f"Using it anyway"
                    )
            except KeyError:
                method = self.logger.info if self.is_first_execution else (
                    self.logger.error if (
                        self.exchange_manager.exchange.get_exchange_current_time() - self._started_at
                        > self.REFERENCE_PRICE_INIT_DELAY
                    )
                    else self.logger.warning
                )
                method(
                    f"No {exchange_manager.exchange_name} exchange symbol data for {self.symbol}, "
                    f"it's probably initializing"
                )
        return price
