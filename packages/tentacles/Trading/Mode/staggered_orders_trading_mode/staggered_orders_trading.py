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
import collections
import enum
import dataclasses
import math
import asyncio
import decimal
import typing

import async_channel.constants as channel_constants
import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.data_util as data_util
import octobot_commons.signals as commons_signals
import octobot_trading.api as trading_api
import octobot_trading.modes as trading_modes
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.errors as trading_errors
import octobot_trading.exchanges.util as exchange_util
import octobot_trading.signals as signals


class StrategyModes(enum.Enum):
    NEUTRAL = "neutral"
    MOUNTAIN = "mountain"
    VALLEY = "valley"
    SELL_SLOPE = "sell slope"
    BUY_SLOPE = "buy slope"
    FLAT = "flat"


class ForceResetOrdersException(Exception):
    pass


class TrailingAborted(Exception):
    pass


class NoOrdersToTrail(Exception):
    pass


INCREASING = "increasing_towards_current_price"
DECREASING = "decreasing_towards_current_price"
STABLE = "stable_towards_current_price"
MULTIPLIER = "multiplier"
MAX_TRAILING_PROCESS_DURATION = 5 * commons_constants.MINUTE_TO_SECONDS # enough to cancel & re-create orders

ONE_PERCENT_DECIMAL = decimal.Decimal("1.01")
TEN_PERCENT_DECIMAL = decimal.Decimal("1.1")

CREATED_ORDER_AVAILABLE_FUNDS_ALLOWED_RATIO = decimal.Decimal("0.97")


StrategyModeMultipliersDetails = {
    StrategyModes.FLAT: {
        MULTIPLIER: trading_constants.ZERO,
        trading_enums.TradeOrderSide.BUY: STABLE,
        trading_enums.TradeOrderSide.SELL: STABLE
    },
    StrategyModes.NEUTRAL: {
        MULTIPLIER: decimal.Decimal("0.3"),
        trading_enums.TradeOrderSide.BUY: INCREASING,
        trading_enums.TradeOrderSide.SELL: INCREASING
    },
    StrategyModes.MOUNTAIN: {
        MULTIPLIER: trading_constants.ONE,
        trading_enums.TradeOrderSide.BUY: INCREASING,
        trading_enums.TradeOrderSide.SELL: INCREASING
    },
    StrategyModes.VALLEY: {
        MULTIPLIER: trading_constants.ONE,
        trading_enums.TradeOrderSide.BUY: DECREASING,
        trading_enums.TradeOrderSide.SELL: DECREASING
    },
    StrategyModes.BUY_SLOPE: {
        MULTIPLIER: trading_constants.ONE,
        trading_enums.TradeOrderSide.BUY: DECREASING,
        trading_enums.TradeOrderSide.SELL: INCREASING
    },
    StrategyModes.SELL_SLOPE: {
        MULTIPLIER: trading_constants.ONE,
        trading_enums.TradeOrderSide.BUY: INCREASING,
        trading_enums.TradeOrderSide.SELL: DECREASING
    }
}


@dataclasses.dataclass
class OrderData:
    side: trading_enums.TradeOrderSide = None
    quantity: decimal.Decimal = trading_constants.ZERO
    price: decimal.Decimal = trading_constants.ZERO
    symbol: str = 0
    is_virtual: bool = True
    associated_entry_id: str = None


class StaggeredOrdersTradingMode(trading_modes.AbstractTradingMode):
    CONFIG_PAIR_SETTINGS = "pair_settings"
    CONFIG_PAIR = "pair"
    CONFIG_MODE = "mode"
    CONFIG_SPREAD = "spread_percent"
    CONFIG_INCREMENT_PERCENT = "increment_percent"
    CONFIG_LOWER_BOUND = "lower_bound"
    CONFIG_UPPER_BOUND = "upper_bound"
    CONFIG_USE_EXISTING_ORDERS_ONLY = "use_existing_orders_only"
    CONFIG_ALLOW_INSTANT_FILL = "allow_instant_fill"
    CONFIG_OPERATIONAL_DEPTH = "operational_depth"
    CONFIG_MIRROR_ORDER_DELAY = "mirror_order_delay"
    CONFIG_ALLOW_FUNDS_REDISPATCH = "allow_funds_redispatch"
    CONFIG_ENABLE_TRAILING_UP = "enable_trailing_up"
    CONFIG_ENABLE_TRAILING_DOWN = "enable_trailing_down"
    CONFIG_ORDER_BY_ORDER_TRAILING = "order_by_order_trailing"
    CONFIG_FUNDS_REDISPATCH_INTERVAL = "funds_redispatch_interval"
    COMPENSATE_FOR_MISSED_MIRROR_ORDER = "compensate_for_missed_mirror_order"
    CONFIG_STARTING_PRICE = "starting_price"
    CONFIG_BUY_FUNDS = "buy_funds"
    CONFIG_SELL_FUNDS = "sell_funds"
    CONFIG_SELL_VOLUME_PER_ORDER = "sell_volume_per_order"
    CONFIG_BUY_VOLUME_PER_ORDER = "buy_volume_per_order"
    CONFIG_IGNORE_EXCHANGE_FEES = "ignore_exchange_fees"
    ENABLE_UPWARDS_PRICE_FOLLOW = "enable_upwards_price_follow"
    CONFIG_DEFAULT_SPREAD_PERCENT = 1.5
    CONFIG_DEFAULT_INCREMENT_PERCENT = 0.5
    REQUIRE_TRADES_HISTORY = True   # set True when this trading mode needs the trade history to operate
    SUPPORTS_INITIAL_PORTFOLIO_OPTIMIZATION = True  # set True when self._optimize_initial_portfolio is implemented
    SUPPORTS_HEALTH_CHECK = False   # set True when self.health_check is implemented

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle, should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(self.CONFIG_PAIR_SETTINGS, commons_enums.UserInputTypes.OBJECT_ARRAY,
                           self.trading_config.get(self.CONFIG_PAIR_SETTINGS, None), inputs,
                           item_title="Pair configuration",
                           other_schema_values={"minItems": 1, "uniqueItems": True},
                           title="Configuration for each traded pairs.")
        self.UI.user_input(self.CONFIG_PAIR, commons_enums.UserInputTypes.TEXT, "BTC/USDT", inputs,
                           other_schema_values={"minLength": 3, "pattern": commons_constants.TRADING_SYMBOL_REGEX},
                           parent_input_name=self.CONFIG_PAIR_SETTINGS,
                           title="Name of the traded pair."),
        self.UI.user_input(
            self.CONFIG_MODE, commons_enums.UserInputTypes.OPTIONS, StrategyModes.NEUTRAL.value, inputs,
            options=list(mode.value for mode in StrategyModes),
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Mode: way to allocate funds in created orders.",
        )
        self.UI.user_input(
            self.CONFIG_SPREAD, commons_enums.UserInputTypes.FLOAT,
            self.CONFIG_DEFAULT_SPREAD_PERCENT, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Spread: price difference between buy and sell orders: percent of the current price to use as "
                  "spread (difference between highest buy and lowest sell). "
                  "Example: enter 10 to use 10% of the current price as spread.",
        )
        self.UI.user_input(
            self.CONFIG_INCREMENT_PERCENT, commons_enums.UserInputTypes.FLOAT,
            self.CONFIG_DEFAULT_INCREMENT_PERCENT, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Increment: price difference between grid orders: percent of the current price to use as increment "
                  "between orders. Example: enter 3 to use 3% of the current price as increment. "
                  "WARNING: this should be lower than the Spread value: profitability is close to "
                  "Spread-Increment.",
        )
        self.UI.user_input(
            self.CONFIG_LOWER_BOUND, commons_enums.UserInputTypes.FLOAT, 0.005, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Lower bound: lower limit of the grid: minimum price to start placing buy orders from: lower "
                  "limit of the grid. "
                  "Example: a lower bound of 0.2 will create a grid covering a price down to 0.2."
        )
        self.UI.user_input(
            self.CONFIG_UPPER_BOUND, commons_enums.UserInputTypes.FLOAT, 0.005, inputs,
            min_val=0, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Upper bound: upper limit of the grid: maximum price to stop placing sell orders. "
                  "Example: an upper bound of 1000 will create a grid covering up to a price for 1000.",
        )
        self.UI.user_input(
            self.CONFIG_OPERATIONAL_DEPTH, commons_enums.UserInputTypes.INT, 50, inputs,
            min_val=1, other_schema_values={"exclusiveMinimum": True},
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Operational depth: maximum number of orders to be maintained on exchange.",
        )
        self.UI.user_input(
            self.CONFIG_MIRROR_ORDER_DELAY, commons_enums.UserInputTypes.FLOAT, 0, inputs,
            min_val=0,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="[Optional] Mirror order delay: Seconds to wait for before creating a mirror order when an order "
                  "is filled. This can generate extra profits on quick market moves.",
        )
        self.UI.user_input(
            self.CONFIG_IGNORE_EXCHANGE_FEES, commons_enums.UserInputTypes.BOOLEAN, True, inputs,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Ignore exchange fees: when checked, exchange fees won't be considered when creating mirror orders. "
                  "When unchecked, a part of the total volume will be reduced to take exchange "
                  "fees into account.",
        )
        self.UI.user_input(
            self.CONFIG_USE_EXISTING_ORDERS_ONLY, commons_enums.UserInputTypes.BOOLEAN, False, inputs,
            parent_input_name=self.CONFIG_PAIR_SETTINGS,
            title="Use existing orders only: when checked, new orders will only be created upon pre-existing orders "
                  "fill. OctoBot won't create orders at startup: it will use the ones already on exchange instead. "
                  "This mode allows staggered orders to operate on user created orders. "
                  "Can't work on trading simulator.",
        )

    def get_current_state(self) -> (str, float):
        order = self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(self.symbol)
        sell_count = len([o for o in order if o.side == trading_enums.TradeOrderSide.SELL])
        buy_count = len(order) - sell_count
        if buy_count > sell_count:
            state = trading_enums.EvaluatorStates.LONG
        elif buy_count < sell_count:
            state = trading_enums.EvaluatorStates.SHORT
        else:
            state = trading_enums.EvaluatorStates.NEUTRAL
        return state.name, f"{buy_count} buy {sell_count} sell"

    def get_mode_producer_classes(self) -> list:
        return [StaggeredOrdersTradingModeProducer]

    def get_mode_consumer_classes(self) -> list:
        return [StaggeredOrdersTradingModeConsumer]

    async def create_consumers(self) -> list:
        consumers = await super().create_consumers()
        # order consumer: filter by symbol not be triggered only on this symbol's orders
        order_consumer = await exchanges_channel.get_chan(trading_personal_data.OrdersChannel.get_name(),
                                                          self.exchange_manager.id).new_consumer(
            self._order_notification_callback,
            symbol=self.symbol if self.symbol else channel_constants.CHANNEL_WILDCARD
        )
        return consumers + [order_consumer]

    async def _order_notification_callback(self, exchange, exchange_id, cryptocurrency, symbol, order,
                                           update_type, is_from_bot):
        if (
            order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.FILLED.value
            and order[trading_enums.ExchangeConstantsOrderColumns.TYPE.value] in (
                trading_enums.TradeOrderType.LIMIT.value
            )
            and is_from_bot
        ):
            await self.producers[0].order_filled_callback(order)

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        return False

    def set_default_config(self):
        raise RuntimeError(f"Impossible to start {self.get_name()} without a valid configuration file.")

    async def single_exchange_process_health_check(self, chained_orders: list, tickers: dict) -> list:
        created_orders = []
        if await self._should_rebalance_orders():
            target_asset = exchange_util.get_common_traded_quote(self.exchange_manager)
            created_orders += await self.single_exchange_process_optimize_initial_portfolio([], target_asset, tickers)
            for producer in self.producers:
                await producer.trigger_staggered_orders_creation()
        return created_orders

    async def _should_rebalance_orders(self):
        for producer in self.producers:
            if producer.enable_upwards_price_follow:
                # trigger rebalance when current price is beyond the highest sell order
                if await producer.is_price_beyond_boundaries():
                    return True
        return False

    async def single_exchange_process_optimize_initial_portfolio(
        self, sellable_assets: list, target_asset: str, tickers: dict
    ) -> list:
        portfolio = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
        producer = self.producers[0]
        pair_bases = set()
        # 1. cancel open orders
        try:
            cancelled_orders, part_1_dependencies = await self._cancel_associated_orders(producer, pair_bases)
        except Exception as err:
            self.logger.exception(err, True, f"Error during portfolio optimization cancel orders step: {err}")
            cancelled_orders = []

        # 2. convert assets to sell funds into target assets
        try:
            part_1_orders = await self._convert_assets_into_target(
                producer, pair_bases, target_asset, set(sellable_assets), tickers, part_1_dependencies
            )
        except Exception as err:
            self.logger.exception(
                err, True, f"Error during portfolio optimization convert into target step: {err}"
            )
            part_1_orders = []

        # 3. compute necessary funds for each configured_pairs
        converted_quote_amount_per_symbol = self._get_converted_quote_amount_per_symbol(
            portfolio, pair_bases, target_asset
        )

        # 4. buy assets
        if converted_quote_amount_per_symbol == trading_constants.ZERO:
            self.logger.warning(f"No {target_asset} in portfolio after optimization.")
            part_2_orders = []
        else:
            part_2_dependencies = signals.get_orders_dependencies(part_1_orders)
            part_2_orders = await self._buy_assets(
                producer, pair_bases, target_asset, converted_quote_amount_per_symbol, tickers, part_2_dependencies
            )

        return [cancelled_orders, part_1_orders, part_2_orders]

    async def _cancel_associated_orders(
        self, producer, pair_bases
    ) -> tuple[list, typing.Optional[commons_signals.SignalDependencies]]:
        cancelled_orders = []
        dependencies = commons_signals.SignalDependencies()
        self.logger.info(f"Optimizing portfolio: cancelling existing open orders on "
                         f"{self.exchange_manager.exchange_config.traded_symbol_pairs}")
        for symbol in self.exchange_manager.exchange_config.traded_symbol_pairs:
            if producer.get_symbol_trading_config(symbol) is not None:
                pair_bases.add(symbol_util.parse_symbol(symbol).base)
                for order in self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
                    symbol=symbol
                ):
                    if not (order.is_cancelled() or order.is_closed()):
                        cancelled, dependency = await self.cancel_order(order)
                        if cancelled:
                            dependencies.extend(dependency)
                        cancelled_orders.append(order)
        return cancelled_orders, (dependencies or None)

    async def _convert_assets_into_target(
        self, producer, pair_bases, common_quote, to_sell_assets, tickers, 
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        to_sell_assets = to_sell_assets.union(pair_bases)
        self.logger.info(f"Optimizing portfolio: selling {to_sell_assets} to buy {common_quote}")
        # need portfolio available to be up-to-date with cancelled orders
        orders = await trading_modes.convert_assets_to_target_asset(
            self, list(to_sell_assets), common_quote, tickers, dependencies=dependencies
        )
        if orders:
            await asyncio.gather(
                *[
                    trading_personal_data.wait_for_order_fill(
                        order, producer.MISSING_MIRROR_ORDERS_MARKET_REBALANCE_TIMEOUT, True
                    ) for order in orders
                ]
            )
        return orders

    async def _buy_assets(
        self, producer, pair_bases, common_quote, converted_quote_amount_per_symbol, tickers, 
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> list:
        created_orders = []
        for base in pair_bases:
            self.logger.info(
                f"Optimizing portfolio: buying {base} with "
                f"{float(converted_quote_amount_per_symbol)} {common_quote}"
            )
            try:
                created_orders += await trading_modes.convert_asset_to_target_asset(
                    self, common_quote, base, tickers,
                    asset_amount=converted_quote_amount_per_symbol,
                    dependencies=dependencies
                )
            except Exception as err:
                self.logger.exception(err, True, f"Error when creating order to buy {base}: {err}")
        if created_orders:
            await asyncio.gather(
                *[
                    trading_personal_data.wait_for_order_fill(
                        order, producer.MISSING_MIRROR_ORDERS_MARKET_REBALANCE_TIMEOUT, True
                    ) for order in created_orders
                ]
            )
        return created_orders

    def _get_converted_quote_amount_per_symbol(self, portfolio, pair_bases, common_quote) -> decimal.Decimal:
        trading_pairs_count = len(pair_bases)
        # need portfolio available to be up-to-date with balancing orders
        try:
            kept_quote_amount = portfolio.portfolio[common_quote].available / decimal.Decimal(2)
            return (
                (portfolio.portfolio[common_quote].available - kept_quote_amount) /
                decimal.Decimal(trading_pairs_count)
            )
        except KeyError:
            # no common_quote in portfolio
            return trading_constants.ZERO
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            # no pair_bases
            return trading_constants.ZERO


class StaggeredOrdersTradingModeConsumer(trading_modes.AbstractTradingModeConsumer):
    ORDER_DATA_KEY = "order_data"
    CURRENT_PRICE_KEY = "current_price"
    SYMBOL_MARKET_KEY = "symbol_market"
    COMPLETING_TRAILING_KEY = "completing_trailing"

    def __init__(self, trading_mode):
        super().__init__(trading_mode)
        self.skip_orders_creation = False

    async def cancel_orders_creation(self):
        self.logger.info(f"Cancelling all orders creation for {self.trading_mode.symbol}")
        self.skip_orders_creation = True
        try:
            while not self.queue.empty():
                await asyncio.sleep(0.1)
        finally:
            self.logger.info(f"Orders creation fully cancelled for {self.trading_mode.symbol}")
            self.skip_orders_creation = False

    async def create_new_orders(self, symbol, final_note, state, **kwargs):
        # use dict default getter: can't afford missing data
        data = kwargs[self.CREATE_ORDER_DATA_PARAM]
        dependencies = kwargs[self.CREATE_ORDER_DEPENDENCIES_PARAM]
        try:
            if not self.skip_orders_creation:
                order_data = data[self.ORDER_DATA_KEY]
                current_price = data[self.CURRENT_PRICE_KEY]
                symbol_market = data[self.SYMBOL_MARKET_KEY]
                return await self.create_order(
                    order_data, current_price, symbol_market, dependencies
                )
            else:
                self.logger.info(f"Skipped {data.get(self.ORDER_DATA_KEY, '')}")
        finally:
            if data[self.COMPLETING_TRAILING_KEY]:
                for producer in self.trading_mode.producers:
                    # trailing process complete
                    self.logger.info(f"Completed {symbol} trailing process.")
                    producer.is_currently_trailing = False

    async def create_order(
        self, order_data, current_price, symbol_market, 
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ):
        created_order = None
        currency, market = symbol_util.parse_symbol(order_data.symbol).base_and_quote()
        try:
            base_available = trading_api.get_portfolio_currency(self.exchange_manager, currency).available
            quote_available = trading_api.get_portfolio_currency(self.exchange_manager, market).available
            selling = order_data.side == trading_enums.TradeOrderSide.SELL
            quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
                self.exchange_manager, order_data.symbol,
                trading_enums.TraderOrderType.SELL_LIMIT if selling else trading_enums.TraderOrderType.BUY_LIMIT,
                order_data.quantity, order_data.price, order_data.side
            )
            if selling and base_available < quantity and base_available > quantity * CREATED_ORDER_AVAILABLE_FUNDS_ALLOWED_RATIO:
                quantity = quantity * CREATED_ORDER_AVAILABLE_FUNDS_ALLOWED_RATIO
                self.logger.info(f"Slightly adapted {order_data.symbol} {order_data.side.value} quantity to {quantity} to fit available funds")
            elif not selling:
                cost = quantity * order_data.price
                if quote_available < cost and quote_available > cost * CREATED_ORDER_AVAILABLE_FUNDS_ALLOWED_RATIO:
                    quantity = quantity * CREATED_ORDER_AVAILABLE_FUNDS_ALLOWED_RATIO
                    self.logger.info(f"Slightly adapted {order_data.symbol} {order_data.side.value} quantity to {quantity} to fit available funds")
            for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                    quantity,
                    order_data.price,
                    symbol_market):
                if selling:
                    if base_available < order_quantity:
                        self.logger.warning(
                            f"Skipping {order_data.symbol} {order_data.side.value} "
                            f"[{self.exchange_manager.exchange_name}] order creation of "
                            f"{order_quantity} at {float(order_price)}: "
                            f"not enough {currency}: available: {base_available}, required: {order_quantity}"
                        )
                        return []
                elif quote_available < order_quantity * order_price:
                    self.logger.warning(
                        f"Skipping {order_data.symbol} {order_data.side.value} "
                        f"[{self.exchange_manager.exchange_name}] order creation of "
                        f"{order_quantity} at {float(order_price)}: "
                        f"not enough {market}: available: {quote_available}, required: {order_quantity * order_price}"
                    )
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
                    associated_entry_id=order_data.associated_entry_id
                )
                # disable instant fill to avoid looping order fill in simulator
                current_order.allow_instant_fill = False
                created_order = await self.trading_mode.create_order(
                    current_order, dependencies=dependencies
                )
            if not created_order:
                self.logger.warning(
                    f"No order created for {order_data} (cost: {quantity * order_data.price}): "
                    f"incompatible with exchange minimum rules. "
                    f"Limits: {symbol_market[trading_enums.ExchangeConstantsMarketStatusColumns.LIMITS.value]}"
                )
        except trading_errors.MissingFunds as e:
            raise e
        except Exception as e:
            self.logger.exception(e, True, f"Failed to create order : {e}. Order: {order_data}")
            return None
        return [] if created_order is None else [created_order]


class StaggeredOrdersTradingModeProducer(trading_modes.AbstractTradingModeProducer):
    FILL = 1
    ERROR = 2
    NEW = 3
    min_quantity = "min_quantity"
    max_quantity = "max_quantity"
    min_cost = "min_cost"
    max_cost = "max_cost"
    min_price = "min_price"
    max_price = "max_price"
    PRICE_FETCHING_TIMEOUT = 60
    MISSING_MIRROR_ORDERS_MARKET_REBALANCE_TIMEOUT = 60
    # health check once every 3 days
    HEALTH_CHECK_INTERVAL_SECS = commons_constants.DAYS_TO_SECONDS * 3
    # recent filled allowed time delay to consider as pending order_filled callback
    RECENT_TRADES_ALLOWED_TIME = 10
    # when True, orders creation/health check will be performed on start()
    SCHEDULE_ORDERS_CREATION_ON_START = True
    ORDERS_DESC = "staggered"
    # keep track of available funds in order placement process to avoid spending multiple times
    # the same funds due to async between producers and consumers and the possibility to trade multiple pairs with
    # shared quote or base
    AVAILABLE_FUNDS = {}
    FUNDS_INCREASE_RATIO_THRESHOLD = decimal.Decimal("0.5")  # ratio bellow with funds will be reallocated:
    # used to track new funds and update orders accordingly
    ALLOWED_MISSED_MIRRORED_ORDERS_ADAPT_DELTA_RATIO = decimal.Decimal("0.5")

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        # no state for this evaluator: always neutral
        self.state = trading_enums.EvaluatorStates.NEUTRAL
        self.symbol = trading_mode.symbol
        self.symbol_market = None
        self.min_max_order_details = {}
        fees = trading_api.get_fees(exchange_manager, self.symbol)
        try:
            self.max_fees = decimal.Decimal(str(max(fees[trading_enums.ExchangeConstantsMarketPropertyColumns.TAKER.value],
                                                    fees[trading_enums.ExchangeConstantsMarketPropertyColumns.MAKER.value]
                                                    )))
        except TypeError as err:
            # don't crash if fees are not available
            market_status = self.exchange_manager.exchange.get_market_status(self.symbol, with_fixer=False)
            self.logger.error(f"Error reading fees for {self.symbol}: {err}. Market status: {market_status}")
            self.max_fees = decimal.Decimal(str(trading_constants.CONFIG_DEFAULT_FEES))
        self.flat_increment = None
        self.flat_spread = None
        self.current_price = None
        self.scheduled_health_check = None
        self.sell_volume_per_order = self.buy_volume_per_order = self.starting_price = trading_constants.ZERO
        self.mirror_orders_tasks = []
        self.mirroring_pause_task = None
        self.allow_order_funds_redispatch = False
        self.enable_trailing_up = False
        self.enable_trailing_down = False
        self.use_order_by_order_trailing = True # enabled by default
        self.funds_redispatch_interval = 24
        self._expect_missing_orders = False
        self._skip_order_restore_on_recently_closed_orders = True
        self._use_recent_trades_for_order_restore = False
        self._already_created_init_orders = False
        self.compensate_for_missed_mirror_order = False

        self.healthy = False

        # used not to refresh orders when order_fill_callback is processing
        self.lock = asyncio.Lock()

        # staggered orders strategy parameters
        self.symbol_trading_config = None

        self.use_existing_orders_only = self.limit_orders_count_if_necessary = False
        self.ignore_exchange_fees = True
        self.enable_upwards_price_follow = True
        self.mode = self.spread \
            = self.increment = self.operational_depth \
            = self.lowest_buy = self.highest_sell \
            = None
        self.single_pair_setup = len(self.trading_mode.trading_config[self.trading_mode.CONFIG_PAIR_SETTINGS]) <= 1
        self.mirror_order_delay = self.buy_funds = self.sell_funds = 0
        self.allowed_mirror_orders = asyncio.Event()
        self.allow_virtual_orders = True
        self.health_check_interval_secs = self.__class__.HEALTH_CHECK_INTERVAL_SECS
        self.healthy = False
        self.is_currently_trailing = False
        self.last_trailing_process_started_at = 0

        try:
            self._load_symbol_trading_config()
        except KeyError as e:
            error_message = f"Impossible to start {self.ORDERS_DESC} orders for {self.symbol}: missing " \
                            f"configuration in trading mode config file. "
            self.logger.exception(e, True, error_message)
            return
        if self.symbol_trading_config is None:
            configured_pairs = \
                [c[self.trading_mode.CONFIG_PAIR]
                 for c in self.trading_mode.trading_config[self.trading_mode.CONFIG_PAIR_SETTINGS]]
            self.logger.error(f"No {self.ORDERS_DESC} orders configuration for trading pair: {self.symbol}. Add "
                              f"this pair's details into your {self.ORDERS_DESC} orders configuration or disable this "
                              f"trading pairs. Configured {self.ORDERS_DESC} orders pairs are"
                              f" {', '.join(configured_pairs)}")
            return
        self.already_errored_on_out_of_window_price = False

        self.allowed_mirror_orders.set()
        self.read_config()
        self._check_params()
        self._already_created_init_orders = True if self.use_existing_orders_only else False

        self.logger.debug(f"Loaded healthy config for {self.symbol}")
        self.healthy = True

    def _load_symbol_trading_config(self) -> bool:
        config = self.get_symbol_trading_config(self.symbol)
        if config is None:
            return False
        self.symbol_trading_config = config
        return True

    def get_symbol_trading_config(self, symbol):
        for config in self.trading_mode.trading_config[self.trading_mode.CONFIG_PAIR_SETTINGS]:
            if config[self.trading_mode.CONFIG_PAIR] == symbol:
                return config
        return None

    def read_config(self):
        mode = ""
        try:
            mode = self.symbol_trading_config[self.trading_mode.CONFIG_MODE]
            self.mode = StrategyModes(mode)
        except ValueError as e:
            self.logger.error(f"Invalid {self.ORDERS_DESC} orders strategy mode: {mode} for {self.symbol}"
                              f"supported modes are {[m.value for m in StrategyModes]}")
            raise e
        self.spread = decimal.Decimal(str(self.symbol_trading_config[self.trading_mode.CONFIG_SPREAD] / 100))
        self.increment = decimal.Decimal(str(self.symbol_trading_config[self.trading_mode.CONFIG_INCREMENT_PERCENT] / 100))
        self.operational_depth = self.symbol_trading_config[self.trading_mode.CONFIG_OPERATIONAL_DEPTH]
        self.lowest_buy = decimal.Decimal(str(self.symbol_trading_config[self.trading_mode.CONFIG_LOWER_BOUND]))
        self.highest_sell = decimal.Decimal(str(self.symbol_trading_config[self.trading_mode.CONFIG_UPPER_BOUND]))
        self.use_existing_orders_only = self.symbol_trading_config.get(
            self.trading_mode.CONFIG_USE_EXISTING_ORDERS_ONLY,
            self.use_existing_orders_only)
        self.mirror_order_delay = self.symbol_trading_config.get(self.trading_mode.CONFIG_MIRROR_ORDER_DELAY,
                                                                 self.mirror_order_delay)
        self.buy_funds = decimal.Decimal(str(self.symbol_trading_config.get(self.trading_mode.CONFIG_BUY_FUNDS,
                                                                            self.buy_funds)))
        self.sell_funds = decimal.Decimal(str(self.symbol_trading_config.get(self.trading_mode.CONFIG_SELL_FUNDS,
                                                                             self.sell_funds)))
        self.ignore_exchange_fees = self.symbol_trading_config.get(self.trading_mode.CONFIG_IGNORE_EXCHANGE_FEES,
                                                                   self.ignore_exchange_fees)
        self.enable_upwards_price_follow = self.symbol_trading_config.get(
            self.trading_mode.ENABLE_UPWARDS_PRICE_FOLLOW, self.enable_upwards_price_follow
        )

    async def start(self) -> None:
        await super().start()
        if StaggeredOrdersTradingModeProducer.SCHEDULE_ORDERS_CREATION_ON_START and self.healthy:
            self.logger.debug(f"Initializing orders creation")
            await self._ensure_staggered_orders_and_reschedule()

    def get_extra_init_symbol_topics(self) -> typing.Optional[list]:
        if self.exchange_manager.is_backtesting:
            # disabled in backtesting as price might not be initialized at this point
            return None
        # required as trigger happens independently of price events for initial orders
        return [commons_enums.InitializationEventExchangeTopics.PRICE.value]

    async def stop(self):
        if self.trading_mode is not None:
            self.trading_mode.flush_trading_mode_consumers()
        if self.scheduled_health_check is not None:
            self.scheduled_health_check.cancel()
        if self.mirroring_pause_task is not None and not self.mirroring_pause_task.done():
            self.mirroring_pause_task.cancel()
        for task in self.mirror_orders_tasks:
            task.cancel()
        if self.exchange_manager:
            if self.exchange_manager.id in StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS:
                # remove self.exchange_manager.id from available funds
                StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS.pop(self.exchange_manager.id, None)
        await super().stop()

    async def set_final_eval(self, matrix_id: str, cryptocurrency: str, symbol: str, time_frame, trigger_source: str):
        # nothing to do: this is not a strategy related trading mode
        pass

    async def is_price_beyond_boundaries(self):
        open_orders = self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(self.symbol)
        price = await trading_personal_data.get_up_to_date_price(
            self.exchange_manager, self.symbol, timeout=self.PRICE_FETCHING_TIMEOUT
        )
        max_order_price = max(
            order.origin_price for order in open_orders
        )
        # price is above max order price
        if max_order_price < price and self.enable_upwards_price_follow:
            return True

    def _schedule_order_refresh(self):
        # schedule order creation / health check
        asyncio.create_task(self._ensure_staggered_orders_and_reschedule())

    async def _ensure_staggered_orders_and_reschedule(self):
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
                await self._ensure_staggered_orders()
            except asyncio.TimeoutError:
                can_create_orders = False
        if not self.should_stop:
            if can_create_orders:
                # a None self.health_check_interval_secs disables health check
                if self.health_check_interval_secs is not None:
                    self.scheduled_health_check = asyncio.get_event_loop().call_later(
                        self.health_check_interval_secs,
                        self._schedule_order_refresh
                    )
            else:
                self.logger.debug(f"Can't yet create initialize orders for {self.symbol}")
                self.scheduled_health_check = asyncio.get_event_loop().call_soon(
                    self._schedule_order_refresh
                )

    async def trigger_staggered_orders_creation(self):
        if self.symbol_trading_config:
            await self._ensure_staggered_orders(ignore_mirror_orders_only=True)
        else:
            self.logger.error(f"No configuration for {self.symbol}")

    def start_mirroring_pause(self, delay):
        if self.allowed_mirror_orders.is_set():
            self.mirroring_pause_task = asyncio.create_task(self.stop_mirror_orders(delay))
        else:
            self.logger.info(f"Cancelling previous {self.symbol} mirror order delay")
            self.mirroring_pause_task.cancel()
            self.mirroring_pause_task = asyncio.create_task(self.stop_mirror_orders(delay))

    async def stop_mirror_orders(self, delay):
        self.logger.info(f"Pausing {self.symbol} mirror orders creation for the next {delay} seconds")
        self.allowed_mirror_orders.clear()
        await asyncio.sleep(delay)
        self.allowed_mirror_orders.set()
        self.logger.info(f"Resuming {self.symbol} mirror orders creation after a {delay} seconds pause")

    async def _ensure_staggered_orders(
        self, ignore_mirror_orders_only=False, ignore_available_funds=False, trigger_trailing=False
    ):
        _, _, _, self.current_price, self.symbol_market = await trading_personal_data.get_pre_order_data(
            self.exchange_manager,
            symbol=self.symbol,
            timeout=self.PRICE_FETCHING_TIMEOUT
        )
        self.logger.debug(f"{self.symbol} symbol_market initialized")
        await self.create_state(
            self._get_new_state_price(), ignore_mirror_orders_only, ignore_available_funds, trigger_trailing
        )

    def _get_new_state_price(self):
        return decimal.Decimal(str(self.current_price if self.starting_price == 0 else self.starting_price))

    @trading_modes.enabled_trader_only()
    async def create_state(self, current_price, ignore_mirror_orders_only, ignore_available_funds, trigger_trailing):
        if current_price is not None:
            self._refresh_symbol_data(self.symbol_market)
            async with self.get_lock(), self.trading_mode_trigger(skip_health_check=True):
                await self._handle_staggered_orders(
                    current_price, ignore_mirror_orders_only, ignore_available_funds, trigger_trailing
                )
                self.logger.debug(f"{self.symbol} orders updated on {self.exchange_name}")

    async def order_filled_callback(self, filled_order: dict):
        # create order on the order side
        new_order = self._create_mirror_order(filled_order)
        self.logger.debug(f"Creating mirror order: {new_order} after filled order: {filled_order}")
        filled_price = decimal.Decimal(str(
            filled_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
        ))
        if self.mirror_order_delay == 0 or trading_api.get_is_backtesting(self.exchange_manager):
            await self._ensure_trailing_and_create_order_when_possible(new_order, filled_price)
        else:
            # create order after waiting time
            self.mirror_orders_tasks.append(asyncio.get_event_loop().call_later(
                self.mirror_order_delay,
                asyncio.create_task,
                self._ensure_trailing_and_create_order_when_possible(new_order, filled_price)
            ))

    def _create_mirror_order(self, filled_order: dict):
        now_selling = filled_order[
          trading_enums.ExchangeConstantsOrderColumns.SIDE.value
        ] == trading_enums.TradeOrderSide.BUY.value
        new_side = trading_enums.TradeOrderSide.SELL if now_selling else trading_enums.TradeOrderSide.BUY
        associated_entry_id = filled_order[
            trading_enums.ExchangeConstantsOrderColumns.ID.value
        ] if now_selling else None  # don't double count PNL: only record entries on sell orders
        if self.flat_increment is None:
            details = "self.flat_increment is unset"
            if self.symbol_market is None:
                details = "self.symbol_market is unset. Symbol mark price has not yet been initialized"
            self.logger.error(f"Impossible to create symmetrical order for {self.symbol}: "
                              f"{details}.")
            return
        if self.flat_spread is None:
            if not self.increment:
                self.logger.error(f"Impossible to create symmetrical order for {self.symbol}: "
                                  f"self.flat_spread is None and self.increment is {self.increment}.")
            self.flat_spread = trading_personal_data.decimal_adapt_price(
                self.symbol_market, self.spread * self.flat_increment / self.increment
            )
        mirror_price_difference = self.flat_spread - self.flat_increment
        # try to get the order origin price to compute mirror order price
        filled_price = decimal.Decimal(str(
            filled_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]
        ))
        maybe_trade, maybe_order = self.exchange_manager.exchange_personal_data.get_trade_or_open_order(
            filled_order[trading_enums.ExchangeConstantsOrderColumns.ID.value]
        )
        if maybe_trade:
            # normal case
            order_origin_price = maybe_trade.origin_price
        elif maybe_order:
            # should not happen but still handle it just in case
            order_origin_price = maybe_order.origin_price
        else:
            # can't find order: default to filled price, even though it might be different from origin price
            self.logger.warning(
                f"Computing mirror order price using filled order price: no associated trade or order has been "
                f"found, this can lead to inconsistent order intervals (order: {filled_order})"
            )
            order_origin_price = filled_price
        price = order_origin_price + mirror_price_difference if now_selling else order_origin_price - mirror_price_difference

        filled_volume = decimal.Decimal(str(filled_order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value]))
        fee = filled_order[trading_enums.ExchangeConstantsOrderColumns.FEE.value]
        volume = self._compute_mirror_order_volume(now_selling, filled_price, price, filled_volume, fee)
        checked_volume = self._get_available_funds_confirmed_order_volume(now_selling, price, volume)
        return OrderData(new_side, checked_volume, price, self.symbol, False, associated_entry_id)

    def _get_available_funds_confirmed_order_volume(self, selling, price, volume):
        parsed_symbol = symbol_util.parse_symbol(self.symbol)
        try:
            if selling:
                available_funds = trading_api.get_portfolio_currency(self.exchange_manager, parsed_symbol.base).available
                return min(available_funds, volume)
            else:
                available_funds = trading_api.get_portfolio_currency(self.exchange_manager, parsed_symbol.quote).available
                required_cost = price * volume
                return min(available_funds, required_cost) / price
        except decimal.DecimalException as err:
            self.logger.exception(err, True, f"Error when checking mirror order volume: {err}")
        return volume

    def _compute_mirror_order_volume(self, now_selling, filled_price, target_price, filled_volume, paid_fees: dict):
        # use target volumes if set
        if self.sell_volume_per_order != trading_constants.ZERO and now_selling:
            return self.sell_volume_per_order
        if self.buy_volume_per_order != trading_constants.ZERO and not now_selling:
            return self.buy_volume_per_order
        # otherwise: compute mirror volume
        new_order_quantity = filled_volume
        if not now_selling:
            # buying => adapt order quantity
            new_order_quantity = filled_price / target_price * filled_volume
        # use max possible volume
        if self.ignore_exchange_fees:
            return new_order_quantity
        # remove exchange fees
        if paid_fees:
            base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
            fees_in_base = trading_personal_data.get_fees_for_currency(paid_fees, base)
            fees_in_base += trading_personal_data.get_fees_for_currency(paid_fees, quote) / filled_price
            if fees_in_base == trading_constants.ZERO:
                self.logger.debug(
                    f"Zero fees for trade on {self.symbol}"
                )
        else:
            self.logger.debug(
                f"No fees given to compute {self.symbol} mirror order size, using default ratio of {self.max_fees}"
            )
            fees_in_base = new_order_quantity * self.max_fees
        return new_order_quantity - fees_in_base

    async def _ensure_trailing_and_create_order_when_possible(self, new_order, current_price):
        if self._should_trigger_trailing(None, None, True):
            # do not give current price as in this context, having only one-sided orders requires trailing
            await self._ensure_staggered_orders(
                trigger_trailing=True, ignore_available_funds=not self._should_lock_available_funds(True)
            )
        else:
            async with self.get_lock():
                await self._lock_portfolio_and_create_order_when_possible(new_order, current_price)

    async def _lock_portfolio_and_create_order_when_possible(self, new_order, current_price):
        await asyncio.wait_for(self.allowed_mirror_orders.wait(), timeout=None)
        async with self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.lock:
            await self._create_order(new_order, current_price, False, [])

    def _should_trigger_trailing(
        self,
        orders: typing.Optional[list],
        current_price: typing.Optional[decimal.Decimal],
        trail_on_missing_orders: bool
    ) -> bool:
        if not (self.enable_trailing_up or self.enable_trailing_down):
            return False
        existing_orders = (
            orders or self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(self.symbol)
        )
        buy_orders = sorted(
            [order for order in existing_orders if order.side == trading_enums.TradeOrderSide.BUY],
            key=lambda o: -o.origin_price
        )
        sell_orders = sorted(
            [order for order in existing_orders if order.side == trading_enums.TradeOrderSide.SELL],
            key=lambda o: o.origin_price
        )
        # 3 to allow trailing even if a few order from the other side have also been filled
        one_sided_orders_trailing_threshold = self.operational_depth / 3
        if self.enable_trailing_up and not sell_orders:
            if len(buy_orders) < one_sided_orders_trailing_threshold and not trail_on_missing_orders:
                (self.logger.info if trail_on_missing_orders else self.logger.warning)(
                    f"{self.symbol} trailing up process aborted: too many missing buy orders. "
                    f"Only {len(buy_orders)} are online while configured total orders is {self.operational_depth}"
                )
                return False
            # only buy orders remaining: everything has been sold, trigger tailing up when enabled if price is
            # beyond range
            if current_price and buy_orders:
                missing_orders_count = self.operational_depth - len(buy_orders)
                price_delta = missing_orders_count * self.flat_increment
                first_order = buy_orders[0]
                approximated_highest_buy_price = first_order.origin_price + price_delta
                if current_price >= approximated_highest_buy_price:
                    # current price is beyond grid maximum buy price: trigger trailing
                    return True
                last_order = buy_orders[-1]
                if last_order.origin_price - self.flat_increment < trading_constants.ZERO:
                    # not all buy orders could have been created: trigger trailing as there is no way to check
                    # the theoretical max price of the grid
                    return len(buy_orders) >= self.operational_depth / 2 and current_price > first_order.origin_price
            elif trail_on_missing_orders:
                # needed for backtesting on-order-fill trailing trigger
                return True
        if self.enable_trailing_down and not buy_orders:
            if len(sell_orders) < one_sided_orders_trailing_threshold and not trail_on_missing_orders:
                (self.logger.info if trail_on_missing_orders else self.logger.warning)(
                    f"{self.symbol} trailing down process aborted: too many missing sell orders. "
                    f"Only {len(sell_orders)} are online while configured total orders is {self.operational_depth}"
                )
                return False
            # only sell orders remaining: everything has been bought, trigger tailing up when enabled if price is
            # beyond range
            if current_price:
                missing_orders_count = self.operational_depth - len(sell_orders)
                price_delta = missing_orders_count * self.flat_increment
                first_order = sell_orders[0]
                approximated_lowest_sell_price = first_order.origin_price - price_delta
                if current_price <= approximated_lowest_sell_price:
                    # current price is beyond grid minimum sell price: trigger trailing
                    return True
            elif trail_on_missing_orders:
                # needed for backtesting on-order-fill trailing trigger
                return True
        return False

    def is_in_trailing_process(self) -> bool:
        if self.is_currently_trailing:
            last_trailing_duration = (
                self.exchange_manager.exchange.get_exchange_current_time() - self.last_trailing_process_started_at
            )
            if last_trailing_duration > MAX_TRAILING_PROCESS_DURATION:
                self.logger.info(f"Removing trailing process flag: {MAX_TRAILING_PROCESS_DURATION} seconds reached")
                self.is_currently_trailing = False
        return self.is_currently_trailing

    async def _handle_staggered_orders(
        self, current_price, ignore_mirror_orders_only, ignore_available_funds, trigger_trailing
    ):
        self._ensure_current_price_in_limit_parameters(current_price)
        if not ignore_mirror_orders_only and self.use_existing_orders_only:
            # when using existing orders only, no need to check existing orders (they can't be wrong since they are
            # already on exchange): only initialize increment and order fill events will do the rest
            self._set_increment_and_spread(current_price)
        else:
            async with self.producer_exchange_wide_lock(self.exchange_manager):
                if trigger_trailing and self.is_in_trailing_process():
                    self.logger.debug(
                        f"{self.symbol} on {self.exchange_name}: trailing signal ignored: "
                        f"a trailing process is already running"
                    )
                    return
                # use exchange level lock to prevent funds double spend
                buy_orders, sell_orders, triggering_trailing, create_order_dependencies = await self._generate_staggered_orders(
                    current_price, ignore_available_funds, trigger_trailing
                )
                staggered_orders = self._merged_and_sort_not_virtual_orders(buy_orders, sell_orders)
                await self._create_not_virtual_orders(
                    staggered_orders, current_price, triggering_trailing, create_order_dependencies
                )
                if staggered_orders:
                    self._already_created_init_orders = True
    
    def _should_lock_available_funds(self, trigger_trailing: bool) -> bool:
        if trigger_trailing:
            # don't lock available funds during order by order trailing
            return not self.use_order_by_order_trailing
        # don't lock available funds again after initial orders creation
        return not self._already_created_init_orders

    def _ensure_current_price_in_limit_parameters(self, current_price):
        message = None
        if self.highest_sell < current_price:
            message = f"The current price is hover the {self.ORDERS_DESC} orders boundaries for {self.symbol}: upper " \
                      f"bound is {self.highest_sell} and price is {current_price}. OctoBot can't trade using " \
                      f"these settings at this current price. Adjust your {self.ORDERS_DESC} orders upper bound " \
                      f"settings to use this trading mode."
        if self.lowest_buy > current_price:
            message = f"The current price is bellow the {self.ORDERS_DESC} orders boundaries for {self.symbol}: " \
                      f"lower bound is {self.lowest_buy} and price is {current_price}. OctoBot can't trade using " \
                      f"these settings at this current price. Adjust your {self.ORDERS_DESC} orders " \
                      f"lower bound settings to use this trading mode."
        if message is not None:
            # Only log once in error, use warning of later messages.
            self._log_window_error_or_warning(message, not self.already_errored_on_out_of_window_price)
            self.already_errored_on_out_of_window_price = True
        else:
            self.already_errored_on_out_of_window_price = False

    def _log_window_error_or_warning(self, message, using_error):
        log_func = self.logger.error if using_error else self.logger.warning
        log_func(message)

    async def _generate_staggered_orders(
        self, current_price, ignore_available_funds, trigger_trailing
    ):
        order_manager = self.exchange_manager.exchange_personal_data.orders_manager
        interfering_orders_pairs = self._get_interfering_orders_pairs(order_manager.get_open_orders())
        if interfering_orders_pairs:
            self.logger.error(
                f"Impossible to create {self.ORDERS_DESC} orders for {self.symbol} with interfering orders using "
                f"pair(s): {', '.join(interfering_orders_pairs)}. {self.ORDERS_DESC.capitalize()} orders require no "
                f"other orders in both base and quote. Please use the Grid Trading Mode with configured Total funds"
                f" trade with interfering orders."
            )
            return [], [], False, None
        existing_orders = order_manager.get_open_orders(self.symbol)

        sorted_orders = sorted(existing_orders, key=lambda order: order.origin_price)

        recent_trades_time = trading_api.get_exchange_current_time(
            self.exchange_manager) - self.RECENT_TRADES_ALLOWED_TIME
        recently_closed_trades = trading_api.get_trade_history(self.exchange_manager, symbol=self.symbol,
                                                               since=recent_trades_time)
        recently_closed_trades = sorted(recently_closed_trades, key=lambda trade: trade.origin_price or trade.executed_price)
        candidate_flat_increment = None
        trigger_trailing = trigger_trailing or bool(
            sorted_orders and self._should_trigger_trailing(sorted_orders, current_price, False)
        )
        next_step_dependencies = None
        trailing_buy_orders = trailing_sell_orders = []
        highest_buy = min(current_price, self.highest_sell)
        lowest_sell = max(current_price, self.lowest_buy)
        confirmed_trailing = False
        if trigger_trailing:
            # trailing has no initial dependencies here
            _, __, trailing_buy_orders, trailing_sell_orders, next_step_dependencies = await self._prepare_trailing(
                sorted_orders, recently_closed_trades, self.lowest_buy, highest_buy, lowest_sell, self.highest_sell, 
                current_price, None
            )
            confirmed_trailing = True
            # trailing will cancel all orders: set state to NEW with no existing order
            missing_orders, state, sorted_orders = None, self.NEW, []
        else:
            missing_orders, state, candidate_flat_increment = self._analyse_current_orders_situation(
                sorted_orders, recently_closed_trades, self.lowest_buy, self.highest_sell, current_price
            )
        self._set_increment_and_spread(current_price, candidate_flat_increment)
        try:
            if trailing_buy_orders or trailing_sell_orders:
                buy_orders = trailing_buy_orders
                sell_orders = trailing_sell_orders
            else:
                buy_orders = self._create_orders(self.lowest_buy, highest_buy, trading_enums.TradeOrderSide.BUY, sorted_orders,
                                                current_price, missing_orders, state, self.buy_funds, ignore_available_funds,
                                                recently_closed_trades)
                sell_orders = self._create_orders(lowest_sell, self.highest_sell, trading_enums.TradeOrderSide.SELL, sorted_orders,
                                                current_price, missing_orders, state, self.sell_funds, ignore_available_funds,
                                                recently_closed_trades)
                if state is self.FILL:
                    self._ensure_used_funds(buy_orders, sell_orders, sorted_orders, recently_closed_trades)
                elif state is self.NEW:
                    if trigger_trailing and not (buy_orders or sell_orders):
                        self.logger.error(f"Unhandled situation: no orders created for {self.symbol} with trigger_trailing={trigger_trailing}")
            create_order_dependencies = next_step_dependencies
        except ForceResetOrdersException:
            buy_orders, sell_orders, state, create_order_dependencies = await self._reset_orders(
                sorted_orders, self.lowest_buy, highest_buy, lowest_sell, self.highest_sell,
                current_price, ignore_available_funds, next_step_dependencies
            )

        if state == self.NEW:
            self._set_virtual_orders(buy_orders, sell_orders, self.operational_depth)

        return buy_orders, sell_orders, confirmed_trailing, create_order_dependencies

    async def _reset_orders(
        self, sorted_orders, lowest_buy, highest_buy, lowest_sell, highest_sell, 
        current_price, ignore_available_funds, 
        dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> tuple[list, list, int, typing.Optional[commons_signals.SignalDependencies]]:
        self.logger.info("Resetting orders")
        cancelled_and_dependency_results = await asyncio.gather(*(self._cancel_open_order(order, dependencies) for order in sorted_orders))
        orders_dependencies = commons_signals.SignalDependencies()
        for result in cancelled_and_dependency_results:
            if result[0] and result[1] is not None:
                orders_dependencies.extend(result[1])
        self._reset_available_funds()
        state = self.NEW
        buy_orders = self._create_orders(
            lowest_buy, highest_buy, trading_enums.TradeOrderSide.BUY, sorted_orders,
            current_price, [], state, self.buy_funds, ignore_available_funds, []
        )
        sell_orders = self._create_orders(
            lowest_sell, highest_sell, trading_enums.TradeOrderSide.SELL, sorted_orders,
            current_price, [], state, self.sell_funds, ignore_available_funds, []
        )
        return buy_orders, sell_orders, state, (orders_dependencies or None)

    def _reset_available_funds(self):
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        self._set_initially_available_funds(
            base,
            trading_api.get_portfolio_currency(self.exchange_manager, base).available,
        )
        self._set_initially_available_funds(
            quote,
            trading_api.get_portfolio_currency(self.exchange_manager, quote).available,
        )

    def _ensure_used_funds(self, new_buy_orders, new_sell_orders, existing_orders, recently_closed_trades):
        if not self.allow_order_funds_redispatch:
            return
        existing_buy_orders_count = len([
            order for order in existing_orders if order.side is trading_enums.TradeOrderSide.BUY
        ])
        existing_sell_orders_count = len(existing_orders) - existing_buy_orders_count
        updated_orders = sorted(
            new_buy_orders + new_sell_orders + existing_orders, key=lambda t: self.get_trade_or_order_price(t)
        )
        if (not updated_orders) or (recently_closed_trades and self._skip_order_restore_on_recently_closed_orders):
            # nothing to check
            return
        if (len(updated_orders) >= self.operational_depth
                and self._get_max_theoretical_orders_count() > self.operational_depth):
            # has virtual order: not supported
            return
        else:
            # can more or bigger orders be created ?
            self._ensure_full_funds_usage(updated_orders, existing_buy_orders_count, existing_sell_orders_count)

    def _get_max_theoretical_orders_count(self):
        return math.floor(
            (self.highest_sell - self.lowest_buy - self.flat_spread + self.flat_increment) / self.flat_increment
        ) if self.flat_increment else 0

    def _ensure_full_funds_usage(self, orders, existing_buy_orders_count, existing_sell_orders_count):
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        total_locked_base, total_locked_quote = self._get_locked_funds(orders)
        max_buy_funds = trading_api.get_portfolio_currency(self.exchange_manager, quote).available + total_locked_quote
        if self.buy_funds:
            max_buy_funds = min(max_buy_funds, self.buy_funds)
        max_sell_funds = trading_api.get_portfolio_currency(self.exchange_manager, base).available + total_locked_base
        if self.sell_funds:
            max_sell_funds = min(max_sell_funds, self.sell_funds)
        used_buy_funds = trading_constants.ZERO
        used_sell_funds = trading_constants.ZERO
        total_sell_orders_value = trading_constants.ZERO
        for order in orders:
            order_locked_base, order_locked_quote = self._get_order_locked_funds(order)
            buying = order.side is trading_enums.TradeOrderSide.BUY
            if (
                (used_buy_funds + order_locked_quote <= max_buy_funds)
                and (buying or used_sell_funds + order_locked_base > max_sell_funds)
            ):
                used_buy_funds += order_locked_quote
            else:
                used_sell_funds += order_locked_base
                total_sell_orders_value += order_locked_quote

        # consider sell orders funds only if they are NOT drastically lower than buy orders funds
        can_consider_sell_order_funds = total_sell_orders_value > used_buy_funds / decimal.Decimal(2)
        # consider buy orders funds only if they are NOT drastically lower than sell orders funds
        can_consider_buy_order_funds = used_buy_funds > total_sell_orders_value / decimal.Decimal(2)
        if (
            # reset if buy or sell funds are underused and sell funds are not overused
            (
                # has buy orders
                existing_buy_orders_count > 0 and can_consider_buy_order_funds
                # and buy orders are not using all funds they should
                and used_buy_funds < max_buy_funds * self.FUNDS_INCREASE_RATIO_THRESHOLD
                # funds locked in sell orders are lower than the theoretical max funds to sell
                # (buy orders have not been converted into sell orders)
                and used_sell_funds < max_sell_funds
            )
            or (
                # has sell orders
                existing_sell_orders_count > 0 and can_consider_sell_order_funds
                # and sell orders are not using all funds they should
                and used_sell_funds < max_sell_funds * self.FUNDS_INCREASE_RATIO_THRESHOLD
            )
        ):
            self.logger.info(
                f"Triggering order reset: used_buy_funds={used_buy_funds}, max_buy_funds={max_buy_funds} "
                f"used_sell_funds={used_sell_funds} max_sell_funds={max_sell_funds}"
            )
            # bigger orders can be created
            raise ForceResetOrdersException
        else:
            self.logger.debug(f"No extra funds to dispatch")

    def get_trade_or_order_price(self, trade_or_order) -> decimal.Decimal:
        if isinstance(trade_or_order, trading_personal_data.Order):
            return trade_or_order.origin_price
        if isinstance(trade_or_order, OrderData):
            return trade_or_order.price
        else:
            return trade_or_order.origin_price or trade_or_order.executed_price

    def _get_locked_funds(self, orders):
        locked_base = locked_quote = trading_constants.ZERO
        for order in orders:
            order_locked_base, order_locked_quote = self._get_order_locked_funds(order)
            if order.side is trading_enums.TradeOrderSide.BUY:
                locked_quote += order_locked_quote
            else:
                locked_base += order_locked_base
        return locked_base, locked_quote

    def _get_order_locked_funds(self, order):
        quantity = order.quantity if isinstance(order, OrderData) else order.origin_quantity  # don't use remaining quantity
        price = order.price if isinstance(order, OrderData) else order.origin_price
        return quantity, quantity * price

    def _set_increment_and_spread(self, current_price, candidate_flat_increment=None):
        origin_flat_increment = self.flat_increment
        if self.flat_increment is None and candidate_flat_increment is not None:
            self.flat_increment = decimal.Decimal(str(candidate_flat_increment))
        elif self.flat_increment is None:
            self.flat_increment = trading_personal_data.decimal_adapt_price(self.symbol_market,
                                                                            current_price * self.increment)
        if origin_flat_increment is not self.flat_increment:
            self.flat_increment = trading_personal_data.decimal_adapt_price(self.symbol_market, self.flat_increment)
        if self.flat_spread is None and self.flat_increment is not None:
            self.flat_spread = trading_personal_data.decimal_adapt_price(
                self.symbol_market, self.spread * self.flat_increment / self.increment
            )
        self.logger.debug(f"{self.symbol} flat spread and increment initialized")

    def _get_interfering_orders_pairs(self, orders):
        # Not a problem if allowed funds are set
        if (self.buy_funds > 0 and self.sell_funds > 0) \
                or (self.buy_volume_per_order > 0 and self.sell_volume_per_order > 0):
            return []
        else:
            current_base, current_quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
            interfering_pairs = set()
            for order in orders:
                order_symbol = order.symbol
                if order_symbol != self.symbol:
                    base, quote = symbol_util.parse_symbol(order_symbol).base_and_quote()
                    if current_base == base or current_base == quote or current_quote == base or current_quote == quote:
                        interfering_pairs.add(order_symbol)
            return interfering_pairs

    def _check_params(self):
        if self.increment >= self.spread:
            self.logger.error(f"Your spread_percent parameter should always be higher than your increment_percent"
                              f" parameter: average profit is spread-increment. ({self.symbol})")
        if self.lowest_buy >= self.highest_sell:
            self.logger.error(f"Your lower_bound should always be lower than your upper_bound ({self.symbol})")

    async def _handle_missed_mirror_orders_fills(self, sorted_trades, missing_orders, current_price):
        if not self.compensate_for_missed_mirror_order or not sorted_trades or not missing_orders:
            return
        trades_with_missing_mirror_order_fills = self._find_missing_mirror_order_fills(sorted_trades, missing_orders)
        if not trades_with_missing_mirror_order_fills:
            return
        await self._pack_and_balance_missing_orders(trades_with_missing_mirror_order_fills, current_price)

    async def _pack_and_balance_missing_orders(self, trades_with_missing_mirror_order_fills, current_price):
        base, quote = symbol_util.parse_symbol(self.symbol).base_and_quote()
        self.logger.info(
            f"Packing {len(trades_with_missing_mirror_order_fills)} missed [{self.exchange_manager.exchange_name}] "
            f"mirror orders, trades {[trade.to_dict() for trade in trades_with_missing_mirror_order_fills]}"
        )
        to_create_order_quantity = sum(
            (trade.executed_quantity - trading_personal_data.get_fees_for_currency(trade.fee, base))
            * (-1 if trade.side is trading_enums.TradeOrderSide.BUY else 1)
            for trade in trades_with_missing_mirror_order_fills
        )
        self.logger.info(
            f"Packed {len(trades_with_missing_mirror_order_fills)} missed [{self.exchange_manager.exchange_name}] "
            f"balancing quantity into: {to_create_order_quantity} {base}"
        )
        if to_create_order_quantity == trading_constants.ZERO:
            return
        # create a market order to balance funds
        order_type = trading_enums.TraderOrderType.SELL_MARKET if to_create_order_quantity < trading_constants.ZERO \
            else trading_enums.TraderOrderType.BUY_MARKET
        target_amount = abs(to_create_order_quantity)
        currency_available, _, market_quantity = \
            trading_personal_data.get_portfolio_amounts(self.exchange_manager, self.symbol, current_price)
        limiting_amount = currency_available if order_type is trading_enums.TraderOrderType.SELL_MARKET \
            else market_quantity
        if target_amount > limiting_amount:
            # use limiting_amount if delta from order_amount is bellow allowed threshold
            delta = target_amount - limiting_amount
            try:
                if delta / target_amount < self.ALLOWED_MISSED_MIRRORED_ORDERS_ADAPT_DELTA_RATIO:
                    target_amount = limiting_amount
                    self.logger.info(f"Adapted balancing quantity according to available amount. Using {target_amount}")
            except (decimal.DivisionByZero, decimal.InvalidOperation):
                # leave as is
                pass
        buying = order_type is trading_enums.TraderOrderType.BUY_MARKET
        fees_adapted_target_amount = trading_personal_data.decimal_adapt_order_quantity_because_fees(
            self.exchange_manager, self.symbol, order_type, target_amount,
            current_price, trading_enums.TradeOrderSide.BUY if buying else trading_enums.TradeOrderSide.SELL,
        )
        if fees_adapted_target_amount != target_amount:
            self.logger.info(
                f"Adapted balancing quantity to comply with exchange fees. Using {fees_adapted_target_amount} "
                f"instead of {target_amount}"
            )
            target_amount = fees_adapted_target_amount
        to_create_details = trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            target_amount,
            current_price,
            self.symbol_market
        )
        if not to_create_details:
            self.logger.warning(
                f"No enough computed funds to recreate packed missed [{self.exchange_manager.exchange_name}] "
                f"mirror order balancing order on {self.symbol}: target_amount: {target_amount} is not enough "
                f"for exchange minimal trading amounts rules"
            )
            return
        for order_amount, order_price in to_create_details:
            if order_amount > limiting_amount:
                limiting_currency = base if order_type is trading_enums.TraderOrderType.SELL_MARKET \
                    else quote
                other_amount = currency_available if order_type is trading_enums.TraderOrderType.BUY_MARKET \
                    else market_quantity
                other_currency = base if order_type is trading_enums.TraderOrderType.BUY_MARKET \
                    else quote
                self.logger.warning(
                    f"No enough available funds to create missed [{self.exchange_manager.exchange_name}] mirror "
                    f"order {order_type.value} balancing order on {self.symbol}. "
                    f"Required {float(order_amount)} {limiting_currency}, available {float(limiting_amount)} "
                    f"{limiting_currency} ({other_currency} available: {other_amount})"
                )
                return
            self.logger.info(
                f"{len(trades_with_missing_mirror_order_fills)} missed [{self.exchange_manager.exchange_name}] order "
                f"fills on {self.symbol}, creating a {order_type.value} order of {float(order_amount)} {base} "
                f"to compensate."
            )

            balancing_order = trading_personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=order_type,
                symbol=self.symbol,
                current_price=order_price,
                quantity=order_amount,
                price=order_price,
                reduce_only=False,
            )
            created_order = await self.trading_mode.create_order(balancing_order)
            # wait for order to be filled
            await trading_personal_data.wait_for_order_fill(
                created_order, self.MISSING_MIRROR_ORDERS_MARKET_REBALANCE_TIMEOUT, True
            )

    def _get_just_filled_unmirrored_missing_order_trade(self, sorted_trades, missing_order_price, missing_order_side):
        price_increment = self.flat_spread - self.flat_increment
        price_window = self.flat_increment / decimal.Decimal(4)
        # each missing order should have is mirror side equivalent in recently_closed_trades
        # when it is not the case, a fill is missing
        now_selling = missing_order_side is trading_enums.TradeOrderSide.BUY
        mirror_order_price = missing_order_price + price_increment if now_selling \
            else missing_order_price - price_increment
        for trade in sorted_trades:
            # use origin price if available, otherwise use executed price which is less accurate as it 
            # might be different from initial order's origin price
            lower_window = (trade.origin_price or trade.executed_price) - price_window
            higher_window = (trade.origin_price or trade.executed_price) + price_window
            if lower_window < mirror_order_price < higher_window and trade.side is not missing_order_side:
                # found mirror order fill
                break
            if lower_window < missing_order_price < higher_window and trade.side is missing_order_side:
                # found missing order in trades before mirror order: this missing order has been filled but not yet 
                # replaced by a mirror order
                return trade
        return None

    def _find_missing_mirror_order_fills(self, sorted_trades, missing_orders):
        trades_with_missing_mirror_order_fills = []
        
        for missing_order_price, missing_order_side in missing_orders:
            if trade := self._get_just_filled_unmirrored_missing_order_trade(
                sorted_trades, missing_order_price, missing_order_side
            ):
                trades_with_missing_mirror_order_fills.append(trade)

        if trades_with_missing_mirror_order_fills:

            def _printable_trade(trade):
                return f"{trade.side.name} {trade.executed_quantity}@{trade.origin_price or trade.executed_price}"

            self.logger.info(
                f"Found {len(trades_with_missing_mirror_order_fills)} {self.symbol} missing order fills based "
                f"on {len(sorted_trades)} "
                f"trades. Missing fills: {[_printable_trade(t) for t in trades_with_missing_mirror_order_fills]}, "
                f"trades: {[_printable_trade(t) for t in trades_with_missing_mirror_order_fills]} "
                f"[{self.exchange_manager.exchange_name}]"
            )
        return trades_with_missing_mirror_order_fills

    async def _cancel_open_order(
        self, order, dependencies: typing.Optional[commons_signals.SignalDependencies]
    ) -> tuple[bool, typing.Optional[commons_signals.SignalDependencies]]:
        if not (order.is_cancelled() or order.is_closed()):
            try:
                cancelled, cancel_order_dependency = await self.trading_mode.cancel_order(order, dependencies=dependencies)
                return cancelled, (cancel_order_dependency if cancelled else None)
            except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                self.logger.warning(f"Skipped order cancel: {err}, order: {order}")
        return False, None

    async def _prepare_trailing(
        self, sorted_orders: list, recently_closed_trades: list, 
        lowest_buy: decimal.Decimal, highest_buy: decimal.Decimal, lowest_sell: decimal.Decimal, highest_sell: decimal.Decimal, 
        current_price: decimal.Decimal, 
        dependencies: typing.Optional[commons_signals.SignalDependencies],
    ) -> tuple[list, list, list, list, typing.Optional[commons_signals.SignalDependencies]]:
        is_trailing_up = len([o for o in sorted_orders if o.side == trading_enums.TradeOrderSide.BUY]) > len(sorted_orders) / 2 
        log_header = (
            f"[{self.exchange_manager.exchange_name}] {self.symbol} @ {current_price} "
            f"{'order by order' if self.use_order_by_order_trailing else 'full grid'} "
            f"trailing {'up' if is_trailing_up else 'down'} process: "
        )
        if current_price <= trading_constants.ZERO:
            self.logger.error(
                f"Aborting {log_header}current price is {current_price}")
            return [], [], [], [], None
        if self.use_order_by_order_trailing:
            cancelled_orders, orders, trailing_buy_orders, trailing_sell_orders, dependencies = await self._prepare_order_by_order_trailing(
                sorted_orders, recently_closed_trades, 
                lowest_buy, highest_buy, lowest_sell, highest_sell, current_price, is_trailing_up,
                dependencies, log_header
            )
            self.is_currently_trailing = True
            self.last_trailing_process_started_at = self.exchange_manager.exchange.get_exchange_current_time()
            return cancelled_orders, orders, trailing_buy_orders, trailing_sell_orders, dependencies
        return await self._prepare_full_grid_trailing(
            sorted_orders, current_price, dependencies, log_header
        )

    async def _prepare_order_by_order_trailing(
        self, sorted_orders: list, recently_closed_trades: list, 
        lowest_buy: decimal.Decimal, highest_buy: decimal.Decimal, 
        lowest_sell: decimal.Decimal, highest_sell: decimal.Decimal,
        current_price: decimal.Decimal, is_trailing_up: bool,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        log_header: str
    ) -> tuple[list, list, list, list, typing.Optional[commons_signals.SignalDependencies]]:
        # 1. identify orders to cancel
        # 1.a find and replace missing orders if any
        replaced_buy_orders = replaced_sell_orders = []
        try:
            ignore_available_funds = True # trailing happens after initial funds locking, ignore & don't change initial funds
            replaced_buy_orders, replaced_sell_orders = await self._compute_trailing_replaced_orders(
                sorted_orders, recently_closed_trades, lowest_buy, highest_buy, lowest_sell, highest_sell,
                current_price, ignore_available_funds, log_header
            )
            # 1.b identify orders to cancel:
            #     cancelled = enough orders to create up to the 1st order on the other side using grid settings
            to_cancel_orders_with_trailed_prices, to_execute_order_with_trailing_price = self._get_orders_to_replace_with_updated_price_for_trailing(
                sorted_orders, replaced_buy_orders+replaced_sell_orders, current_price
            )
            self.logger.info(
                f"{log_header} Replacing orders at prices: {[float(self.get_trade_or_order_price(o[0])) for o in (to_cancel_orders_with_trailed_prices + [to_execute_order_with_trailing_price])]} with "
                f"{[float(o[1]) for o in (to_cancel_orders_with_trailed_prices + [to_execute_order_with_trailing_price])]}"
            )
        except TrailingAborted as err:
            # A normal missing order replacement should happen 
            # Can happen when all orders from a side are missing and price when back to a valid in-grid value
            self.logger.info(f"{log_header}trailing aborted: {err}. Replacing orders with: {replaced_buy_orders=} {replaced_sell_orders=}")
            return [], [], replaced_buy_orders, replaced_sell_orders, None
        except NoOrdersToTrail as err:
            # happens when all orders are filled at once: use the "new" state to recreate the grid, should be rare
            self.logger.warning(
                f"{log_header}no order to trail from, using full grid trailing to balance funds before recreating the grid: {err}"
            )
            return await self._prepare_full_grid_trailing(sorted_orders, current_price, dependencies, log_header)
        except ValueError as err:
            self.logger.error(f"{log_header}error when identifying orders to cancel: {err}")
            return [], [], [], [], None
        # 2. cancel orders to be replaced with updated prices
        cancelled_replaced_orders, cancelled_orders, convert_dependencies = await self._cancel_replaced_orders(
            [order for order, _ in to_cancel_orders_with_trailed_prices + [to_execute_order_with_trailing_price]],
            dependencies
        )
        # 3. execute extrema order amount as market order to convert funds
        to_convert_order = to_execute_order_with_trailing_price[0]
        orders = await self._convert_order_funds(
            to_convert_order, current_price, convert_dependencies, log_header
        )
        orders_dependencies = signals.get_orders_dependencies(orders)
        # 4. compute trailing orders
        trailing_buy_orders, trailing_sell_orders = self._get_updated_trailing_orders(
            replaced_buy_orders, replaced_sell_orders, cancelled_replaced_orders, 
            to_cancel_orders_with_trailed_prices, to_execute_order_with_trailing_price, current_price,
            is_trailing_up
        )
        self.logger.info(f"{log_header}creating {len(trailing_buy_orders)} buy orders and {len(trailing_sell_orders)} sell orders: {trailing_buy_orders=} {trailing_sell_orders=}")
        return cancelled_orders, orders, trailing_buy_orders, trailing_sell_orders, (orders_dependencies or convert_dependencies or None)

    async def _cancel_replaced_orders(
        self, replaced_orders: list[typing.Union[OrderData, trading_personal_data.Order]], dependencies
    ) -> tuple[list[OrderData], list[trading_personal_data.Order], commons_signals.SignalDependencies]:
        cancelled_orders = []
        cancelled_replaced_orders = []
        new_dependencies = commons_signals.SignalDependencies()
        for order in replaced_orders:
            if isinstance(order, OrderData):
                cancelled_replaced_orders.append(order)
            else:
                cancelled, cancel_order_dependency = await self._cancel_open_order(order, dependencies)
                if cancelled:
                    cancelled_orders.append(order)
                    if cancel_order_dependency:
                        new_dependencies.extend(cancel_order_dependency)

        return cancelled_replaced_orders, cancelled_orders, new_dependencies

    async def _compute_trailing_replaced_orders(
        self, sorted_orders, recently_closed_trades, 
        lowest_buy, highest_buy, lowest_sell, highest_sell, 
        current_price, ignore_available_funds, log_header
    ) -> tuple[list[OrderData], list[OrderData]]:
        missing_orders, state, _ = self._analyse_current_orders_situation(
            sorted_orders, recently_closed_trades, lowest_buy, highest_sell, current_price
        )
        if state == self.NEW and not sorted_orders:
            raise NoOrdersToTrail(f"no open order to trail, nothing to replace")
        if state != self.FILL:
            raise ValueError(f"unhandled state: {state} (expected: self.FILL: {self.FILL})")
        replaced_buy_orders = replaced_sell_orders = []
        if missing_orders:
            self.logger.info(
                f"{log_header}found {len(missing_orders)} missing orders: preparing orders before "
                f"order by order trailing process {missing_orders}"
            )
            await self._handle_missed_mirror_orders_fills(recently_closed_trades, missing_orders, current_price)
            replaced_buy_orders = self._create_orders(
                lowest_buy, highest_buy, trading_enums.TradeOrderSide.BUY, sorted_orders,
                current_price, missing_orders, state, self.buy_funds, ignore_available_funds, recently_closed_trades
            )
            replaced_sell_orders = self._create_orders(
                lowest_sell, highest_sell, trading_enums.TradeOrderSide.SELL, sorted_orders,
                current_price, missing_orders, state, self.sell_funds, ignore_available_funds, recently_closed_trades
            )
        return replaced_buy_orders, replaced_sell_orders

    async def _convert_order_funds(
        self, to_convert_order, current_price, convert_dependencies, log_header
    ) -> list[trading_personal_data.Order]:
        base, quote = symbol_util.parse_symbol(to_convert_order.symbol).base_and_quote()
        base_amount_to_convert = to_convert_order.quantity if isinstance(to_convert_order, OrderData) \
            else to_convert_order.get_remaining_quantity()
        if to_convert_order.side is trading_enums.TradeOrderSide.BUY:
            # replace buy order by a sell order => convert quote to base
            to_sell = quote
            to_buy = base
            amount_to_convert = base_amount_to_convert * self.get_trade_or_order_price(to_convert_order)
        else:
            # replace sell order by a buy order => convert base to quote
            to_sell = base
            to_buy = quote
            amount_to_convert = base_amount_to_convert
        self.logger.info(f"{log_header}selling {amount_to_convert} {base} worth of {to_sell} to buy {to_buy}")
        # need portfolio available to be up-to-date with cancelled orders
        orders = await trading_modes.convert_asset_to_target_asset(
            self.trading_mode, to_sell, to_buy, {
                self.symbol: {
                    trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: current_price,
                }
            }, asset_amount=amount_to_convert,
            dependencies=convert_dependencies
        )
        orders = [order for order in orders if order is not None]
        if orders:
            await asyncio.gather(*[
                trading_personal_data.wait_for_order_fill(
                    order, self.MISSING_MIRROR_ORDERS_MARKET_REBALANCE_TIMEOUT, True
                ) for order in orders
            ])
        return orders

    def _get_updated_trailing_orders(
        self, replaced_buy_orders, replaced_sell_orders, cancelled_replaced_orders, 
        to_cancel_orders_with_trailed_prices, to_execute_order_with_trailing_price, current_price,
        is_trailing_up
    ) -> tuple[list[OrderData], list[OrderData]]:
        to_convert_order = to_execute_order_with_trailing_price[0]
        trailing_buy_orders = [
            buy_order for buy_order in replaced_buy_orders if buy_order not in cancelled_replaced_orders
        ]
        trailing_sell_orders = [
            sell_order for sell_order in replaced_sell_orders if sell_order not in cancelled_replaced_orders
        ]
        # add orders with price covering up to the current price
        for cancelled_order, trailed_price in (to_cancel_orders_with_trailed_prices + [to_execute_order_with_trailing_price]):
            trailed_order_side = (
                trading_enums.TradeOrderSide.BUY if trailed_price <= current_price else trading_enums.TradeOrderSide.SELL
            )
            if cancelled_order is to_convert_order:
                # force the order side to be the opposite of the trailing direction and make sure this order 
                # gets created at the side, even if it's at the current price
                trailed_order_side = trading_enums.TradeOrderSide.SELL if is_trailing_up else trading_enums.TradeOrderSide.BUY
                ideal_base_quantity = to_convert_order.total_cost / trailed_price 
                parsed_symbol = symbol_util.parse_symbol(to_convert_order.symbol)
                other_side_currency = parsed_symbol.quote if trailed_order_side is trading_enums.TradeOrderSide.BUY else parsed_symbol.base
                available_amount = trading_api.get_portfolio_currency(self.exchange_manager, other_side_currency).available
                available_amount_in_base = available_amount if other_side_currency == parsed_symbol.base else available_amount / trailed_price
                if available_amount_in_base < ideal_base_quantity:
                    trailing_order_quantity = available_amount_in_base
                    self.logger.warning(
                        f"Not enough available funds to create a full {ideal_base_quantity} {parsed_symbol.base} {to_convert_order.symbol} {trailed_order_side.name} trailing "
                        f"order: available: {available_amount} {other_side_currency} < {ideal_base_quantity} "
                        f"(={available_amount_in_base} {parsed_symbol.base}). Using {trailing_order_quantity} instead."
                    )
                else:
                    trailing_order_quantity = ideal_base_quantity
            else:
                initial_quantity = cancelled_order.quantity if isinstance(cancelled_order, OrderData) \
                    else cancelled_order.get_remaining_quantity()
                if cancelled_order.side is trading_enums.TradeOrderSide.BUY:
                    # trailed buy orders inherit the total cost of the orders they are replacing
                    initial_price = self.get_trade_or_order_price(cancelled_order)
                    trailing_order_quantity = initial_quantity * initial_price / trailed_price
                else:
                    # trailed sell orders can inherit the quantity of the orders they are replacing
                    trailing_order_quantity = initial_quantity
            order = OrderData(
                trailed_order_side, trailing_order_quantity, trailed_price, self.symbol, False
            )
            if trailed_order_side is trading_enums.TradeOrderSide.BUY:
                trailing_buy_orders.append(order)
            else:
                trailing_sell_orders.append(order)
        return trailing_buy_orders, trailing_sell_orders

    def _get_orders_to_replace_with_updated_price_for_trailing(
        self, sorted_orders: list[trading_personal_data.Order], replaced_orders: list[OrderData], current_price: decimal.Decimal
    ) -> tuple[
        list[tuple[typing.Union[trading_personal_data.Order, OrderData], decimal.Decimal]], 
        tuple[trading_personal_data.Order, decimal.Decimal]
    ]:
        if not sorted_orders:
            raise ValueError(f"No input sorted orders, trailing can't happen on {self.symbol}")
        confirmed_sorted_grid_prices = sorted([
            replaced_order.price for replaced_order in replaced_orders
        ] + [
            order.origin_price for order in (sorted_orders)
        ])
        is_trailing_up = current_price > confirmed_sorted_grid_prices[-1]
        if not is_trailing_up and current_price >= confirmed_sorted_grid_prices[0]:
            raise TrailingAborted(
                f"Current price is not beyond grid boundaries: {current_price}, "
                f"grid min: {confirmed_sorted_grid_prices[0]}, grid max: {confirmed_sorted_grid_prices[-1]}"
            )
        orders_to_replace_with_trailed_price: list[
            tuple[typing.Union[trading_personal_data.Order, OrderData], decimal.Decimal]
        ] = []
        if not (self.flat_increment and self.flat_spread):
            raise ValueError(
                f"Flat increment and flat spread mush be set {self.flat_increment=} {self.flat_spread=}"
            )
        if is_trailing_up:
            # trailing up: free enough funds to create orders up to the current price, including 1 sell order above the current price
            extrema_order_price = confirmed_sorted_grid_prices[-1]
            if extrema_order_price + self.flat_spread > current_price:
                # no order to create, only the other side order to handle
                order_count_to_create = 0
            else:
                order_count_to_create = math.ceil((current_price - self.flat_spread - extrema_order_price) / self.flat_increment)
            other_side_order_price = extrema_order_price + (self.flat_increment * order_count_to_create) + self.flat_spread
        else:
            # trailing down: free enough funds to create orders down to the current price, including 1 buy order below the current price
            extrema_order_price = confirmed_sorted_grid_prices[0]
            if extrema_order_price - self.flat_spread < current_price:
                # no order to create, only the other side order to handle
                order_count_to_create = 0
            else:
                order_count_to_create = math.ceil((extrema_order_price - self.flat_spread - current_price) / self.flat_increment)
            other_side_order_price = extrema_order_price - (self.flat_increment * order_count_to_create) - self.flat_spread

        order_by_price: dict[decimal.Decimal, typing.Union[trading_personal_data.Order, OrderData]] = {
            self.get_trade_or_order_price(order): order
            for order in replaced_orders + sorted_orders
        }
        # order_to_replace_by_other_side_order should be an open order, not a replaced order
        order_to_replace_by_other_side_order_price = sorted_orders[0].origin_price if is_trailing_up else sorted_orders[-1].origin_price
        order_to_replace_by_other_side_order = order_by_price[order_to_replace_by_other_side_order_price]
        if not isinstance(order_to_replace_by_other_side_order, trading_personal_data.Order):
            # should never happen
            raise ValueError(f"Order to replace by other side order is not an open order: {order_to_replace_by_other_side_order}")
        confirmed_prices = [
            price for price in confirmed_sorted_grid_prices if price != order_to_replace_by_other_side_order_price
        ]
        # 1 trailing price per confirmed price (don't create more than the number of confirmed prices in case price is way off)
        trailing_order_prices = [
            extrema_order_price + (self.flat_increment * (i + 1) * (1 if is_trailing_up else -1))
            for i in range(int(order_count_to_create))
        ][-len(confirmed_prices):]
        remaining_order_prices = collections.deque(sorted(
            confirmed_prices, key=lambda price: price if is_trailing_up else -price
        ))
        self.logger.info(f"trailing_order_prices: {trailing_order_prices} {confirmed_prices=}")
        for trailing_order_price in trailing_order_prices:
            # associate each new order price to an existing order
            order_to_replace_price = remaining_order_prices.popleft()
            order_to_replace  = order_by_price[order_to_replace_price]
            orders_to_replace_with_trailed_price.append((order_to_replace, trailing_order_price))

        return orders_to_replace_with_trailed_price, (order_to_replace_by_other_side_order, other_side_order_price)


    async def _prepare_full_grid_trailing(
        self, open_orders: list, current_price: decimal.Decimal, 
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        log_header: str
    ) -> tuple[list, list, list, list, typing.Optional[commons_signals.SignalDependencies], bool]:
        # 1. cancel all open orders
        convert_dependencies = commons_signals.SignalDependencies()
        try:
            cancelled_orders = []
            self.logger.info(f"{log_header}cancelling {len(open_orders)} open orders on {self.symbol}")
            for order in open_orders:
                cancelled, cancel_order_dependency = await self._cancel_open_order(order, dependencies)
                if cancelled:
                    cancelled_orders.append(order)
                    if cancel_order_dependency:
                        convert_dependencies.extend(cancel_order_dependency)
        except Exception as err:
            self.logger.exception(err, True, f"Error in {log_header} cancel orders step: {err}")
            cancelled_orders = []

        # 2. if necessary, convert a part of the funds to be able to create buy and sell orders
        orders = []
        try:
            parsed_symbol = symbol_util.parse_symbol(self.symbol)
            available_base_amount = trading_api.get_portfolio_currency(self.exchange_manager, parsed_symbol.base).available
            available_quote_amount = trading_api.get_portfolio_currency(self.exchange_manager, parsed_symbol.quote).available
            usable_amount_in_quote = available_quote_amount + (available_base_amount * current_price)
            config_max_amount = self.buy_funds + (self.sell_funds * current_price)
            if config_max_amount > trading_constants.ZERO:
                usable_amount_in_quote = min(usable_amount_in_quote, config_max_amount)
            # amount = the total amount (in base) to put into the grid at the current price
            usable_amount_in_base = usable_amount_in_quote / current_price

            target_base = usable_amount_in_base / decimal.Decimal(2)
            target_quote = usable_amount_in_quote / decimal.Decimal(2)

            amount = trading_constants.ZERO
            to_sell = to_buy = None
            if available_base_amount < target_base:
                # buy order
                to_buy = parsed_symbol.base
                to_sell = parsed_symbol.quote
                amount = (target_base - available_base_amount) * current_price
            if available_quote_amount < target_quote:
                if amount != trading_constants.ZERO:
                    # can't buy with currencies, this should never happen: log error
                    self.logger.error(f"{log_header}can't buy and sell {parsed_symbol} at the same time.")
                else:
                    # sell order
                    to_buy = parsed_symbol.quote
                    to_sell = parsed_symbol.base
                    amount = (target_quote - available_quote_amount) / current_price

            if amount > trading_constants.ZERO:
                self.logger.info(f"{log_header}selling {amount} {to_sell} to buy {to_buy}")
                # need portfolio available to be up-to-date with cancelled orders
                orders = await trading_modes.convert_asset_to_target_asset(
                    self.trading_mode, to_sell, to_buy, {
                        self.symbol: {
                            trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: current_price,
                        }
                    }, asset_amount=amount,
                    dependencies=convert_dependencies
                )
                if orders:
                    await asyncio.gather(*[
                        trading_personal_data.wait_for_order_fill(
                            order, self.MISSING_MIRROR_ORDERS_MARKET_REBALANCE_TIMEOUT, True
                        ) for order in orders
                    ])
            else:
                self.logger.info(f"{log_header}nothing to buy or sell. Current funds are enough")
        except Exception as err:
            self.logger.exception(
                err, True, f"Error in {log_header}convert into target step: {err}"
            )

        # 3. reset available funds (free funds from cancelled orders)
        self._reset_available_funds()

        self.logger.info(
            f"Completed {log_header} {len(cancelled_orders)} cancelled orders, {len(orders)} "
            f"created conversion orders"
        )
        orders_dependencies = signals.get_orders_dependencies(orders)
        self.is_currently_trailing = True
        self.last_trailing_process_started_at = self.exchange_manager.exchange.get_exchange_current_time()
        return cancelled_orders, orders, [], [], (orders_dependencies or convert_dependencies or None)

    def _analyse_current_orders_situation(self, sorted_orders, recently_closed_trades, lower_bound, higher_bound, current_price):
        if not sorted_orders:
            return None, self.NEW, None
        # check if orders are staggered orders
        return self._bootstrap_parameters(sorted_orders, recently_closed_trades, lower_bound, higher_bound, current_price)

    def _create_orders(self, lower_bound, upper_bound, side, sorted_orders,
                       current_price, missing_orders, state, allowed_funds, ignore_available_funds, recent_trades) -> list[OrderData]:

        if lower_bound == upper_bound:
            self.logger.info(
                f"No {side.name} orders to create for {self.symbol} lower bound = upper bound = {upper_bound}"
            )
            return []
        if lower_bound > upper_bound:
            self.logger.warning(
                f"No {side.name} orders to create for {self.symbol}: "
                f"Your configured increment or spread value is likely too large for the current price. "
                f"Current price: {current_price}, increment: {self.flat_increment}, spread: {self.flat_spread}. "
                f"Current price beyond boundaries: "
                f"computed lower bound: {lower_bound}, computed upper bound: {upper_bound}. "
                f"Lower bound should be inferior to upper bound."
            )
            return []

        selling = side == trading_enums.TradeOrderSide.SELL

        currency, market = symbol_util.parse_symbol(self.symbol).base_and_quote()
        order_limiting_currency = currency if selling else market

        order_limiting_currency_amount = trading_api.get_portfolio_currency(self.exchange_manager, order_limiting_currency).available
        if state == self.NEW:
            # create staggered orders
            return self._create_new_orders_bundle(
                lower_bound, upper_bound, side, current_price, allowed_funds, ignore_available_funds, selling,
                order_limiting_currency, order_limiting_currency_amount
            )
        if state == self.FILL:
            # complete missing orders
            orders = self._fill_missing_orders(
                lower_bound, upper_bound, side, sorted_orders, current_price, missing_orders, selling,
                order_limiting_currency, order_limiting_currency_amount, currency, recent_trades
            )
            return orders
        if state == self.ERROR:
            self.logger.error(f"Impossible to create {self.ORDERS_DESC} orders for {self.symbol} when incompatible "
                              f"order are already in place. Cancel these orders of you want to use this trading mode.")
        return []

    def _create_new_orders_bundle(
        self, lower_bound, upper_bound, side, current_price, allowed_funds, ignore_available_funds, selling,
        order_limiting_currency, order_limiting_currency_amount
    ) -> list[OrderData]:
        orders = []
        funds_to_use = self._get_maximum_traded_funds(allowed_funds,
                                                      order_limiting_currency_amount,
                                                      order_limiting_currency,
                                                      selling,
                                                      ignore_available_funds)
        if funds_to_use == 0:
            return []
        starting_bound = lower_bound * (1 + self.spread / 2) if selling else upper_bound * (1 - self.spread / 2)
        self.flat_spread = trading_personal_data.decimal_adapt_price(self.symbol_market,
                                                                     current_price * self.spread)
        self._create_new_orders(orders, current_price, selling, lower_bound, upper_bound,
                                funds_to_use, order_limiting_currency, starting_bound, side,
                                True, self.mode, order_limiting_currency_amount)
        return orders

    def _fill_missing_orders(
        self, lower_bound, upper_bound, side, sorted_orders, current_price, missing_orders, selling,
        order_limiting_currency, order_limiting_currency_amount, currency, recent_trades
    ):
        orders = []
        if missing_orders and [o for o in missing_orders if o[1] is side]:
            max_quant_per_order = order_limiting_currency_amount / len([o for o in missing_orders if o[1] is side])
            missing_orders_around_spread = []
            for missing_order_price, missing_order_side in missing_orders:
                if missing_order_side == side:
                    previous_o = None
                    following_o = None
                    for o in sorted_orders:
                        if previous_o is None:
                            previous_o = o
                        elif o.origin_price > missing_order_price:
                            following_o = o
                            break
                        else:
                            previous_o = o
                    if following_o is None or previous_o.side == following_o.side:
                        decimal_missing_order_price = decimal.Decimal(str(missing_order_price))
                        # missing order between similar orders
                        quantity = self._get_surrounded_missing_order_quantity(
                            previous_o, following_o, max_quant_per_order, decimal_missing_order_price, recent_trades,
                            current_price, sorted_orders, side
                        )
                        orders.append(OrderData(missing_order_side, quantity,
                                                decimal_missing_order_price, self.symbol, False))
                        self.logger.debug(f"Creating missing orders not around spread: {orders[-1]} "
                                          f"for {self.symbol}")
                    else:
                        missing_orders_around_spread.append((missing_order_price, missing_order_side))

            if missing_orders_around_spread:
                # missing order next to spread
                starting_bound = upper_bound if selling else lower_bound
                increment_window = self.flat_increment / 2
                order_limiting_currency_available_amount = trading_api.get_portfolio_currency(
                    self.exchange_manager, order_limiting_currency
                ).available
                decimal_order_limiting_currency_available_amount = decimal.Decimal(
                    str(order_limiting_currency_available_amount))
                portfolio_total = trading_api.get_portfolio_currency(self.exchange_manager,
                                                                     order_limiting_currency).total
                order_limiting_currency_amount = portfolio_total
                if order_limiting_currency_available_amount:
                    orders_count, average_order_quantity = \
                        self._get_order_count_and_average_quantity(
                            current_price, selling, lower_bound, upper_bound, portfolio_total, currency, self.mode
                        )

                    for missing_order_price, missing_order_side in missing_orders_around_spread:
                        added_missing_order = False
                        limiting_amount_from_this_order = order_limiting_currency_amount
                        price = starting_bound - self.flat_increment if selling else starting_bound + self.flat_increment
                        found_order = False
                        exceeded_price = False
                        i = 0
                        max_orders_count = max(orders_count, self.operational_depth)
                        while not (
                            found_order or exceeded_price or
                            limiting_amount_from_this_order < trading_constants.ZERO or
                            i >= max_orders_count
                        ):
                            if price != 0:
                                order_quantity = self._get_spread_missing_order_quantity(
                                    average_order_quantity, side, i, orders_count, price, selling,
                                    limiting_amount_from_this_order,
                                    decimal_order_limiting_currency_available_amount, recent_trades, sorted_orders,
                                    current_price
                                )
                                if price is not None and limiting_amount_from_this_order > 0 and \
                                        price - increment_window <= missing_order_price <= price + increment_window:
                                    found_order = True
                                    if order_quantity is not None:
                                        orders.append(OrderData(side, decimal.Decimal(str(order_quantity)),
                                                                decimal.Decimal(str(missing_order_price)), self.symbol,
                                                                False))
                                        added_missing_order = True
                                        self.logger.debug(f"Creating missing order around spread {orders[-1]} "
                                                          f"for {self.symbol}")
                                if order_quantity is not None:
                                    used_amount = order_quantity if selling else order_quantity * price
                                    limiting_amount_from_this_order -= used_amount
                            price = price - self.flat_increment if selling else price + self.flat_increment
                            if (
                                selling and price < (missing_order_price - self.flat_increment)
                            ) or (
                                (not selling) and price > missing_order_price + self.flat_increment
                            ):
                                exceeded_price = True
                            i += 1
                        if not added_missing_order:
                            self.logger.warning(
                                f"Missing order not restored: price {missing_order_price} side: {missing_order_side}"
                            )
        return orders

    def _get_surrounded_missing_order_quantity(
        self, previous_order, following_order, max_quant_per_order, order_price, recent_trades,
            current_price, sorted_orders, side
    ):
        selling = side == trading_enums.TradeOrderSide.SELL
        if sorted_orders:
            if quantity := self._get_quantity_from_existing_orders(
                order_price, sorted_orders, selling
            ):
                return quantity
        quantity_from_trades = self._get_quantity_from_recent_trades(
            order_price, max_quant_per_order, recent_trades, current_price, selling
        )
        return quantity_from_trades or \
            decimal.Decimal(str(
                min(
                    data_util.mean([previous_order.origin_quantity, following_order.origin_quantity])
                    if following_order else previous_order.origin_quantity,
                    (max_quant_per_order if selling else max_quant_per_order / order_price)
                )
            ))

    def _get_spread_missing_order_quantity(
        self, average_order_quantity, side, i, orders_count, price, selling, limiting_amount_from_this_order,
        order_limiting_currency_available_amount, recent_trades, sorted_orders,
        current_price
    ):
        quantity = None
        if sorted_orders:
            quantity = self._get_quantity_from_existing_orders(
                price, sorted_orders, selling
            )
            if quantity:
                # quantity is from currently open orders: use it as is
                return quantity
        # quantity is not in open orders: infer it
        if not quantity:
            quantity = self._get_quantity_from_recent_trades(
                price, limiting_amount_from_this_order, recent_trades, current_price, selling
            )
        if not quantity:
            try:
                quantity = self._get_quantity_from_iteration(
                    average_order_quantity, self.mode, side, i, orders_count, price, price
                )
            except trading_errors.NotSupported:
                quantity = self._get_quantity_from_existing_boundary_orders(
                    price, sorted_orders, selling
                )
                if quantity:
                    self.logger.info(
                        f"Using boundary orders to compute restored order quantity for {'sell' if selling else 'buy'} "
                        f"order at {price}: no equivalent order for in recent trades (recent trades: "
                        f"{[str(t) for t in recent_trades]})."
                    )
                else:
                    self.logger.error(
                        f"Error when computing restored order quantity for {'sell' if selling else 'buy'} order at "
                        f"price: {price}: recent trades or active orders are required."
                    )
                    return None
        if quantity is None:
            return None
        # always ensure ideal quantity is available
        limiting_currency_quantity = quantity
        limiting_cost = limiting_currency_quantity if selling else limiting_currency_quantity * price
        if limiting_cost > limiting_amount_from_this_order or \
                limiting_cost > order_limiting_currency_available_amount:
            limiting_cost = min(
                limiting_amount_from_this_order,
                order_limiting_currency_available_amount
            )
        try:
            return limiting_cost if selling else limiting_cost / price
        except decimal.DecimalException as err:
            self.logger.exception(err, True, f"Error when computing missing order quantity: {err}")
            return limiting_currency_quantity

    def _get_quantity_from_existing_orders(self, price, sorted_orders, selling):
        increment_window = self.flat_increment / 4
        price_window_lower_bound = price - increment_window
        price_window_higher_bound = price + increment_window
        for order in sorted_orders:
            if price_window_lower_bound <= order.origin_price <= price_window_higher_bound and (
                order.side is (trading_enums.TradeOrderSide.SELL if selling else trading_enums.TradeOrderSide.BUY)
            ):
                return order.origin_quantity
        return None

    def _get_quantity_from_existing_boundary_orders(self, price, sorted_orders, selling):
        # Should be the last attempt: compute price from existing orders using cost
        # of the 1st order on target side and compute linear quantity. Use boundary order as it has the most chances
        # to remain according to the initial orders costs (compared to an average that could contain results of trades
        # from the order side, which cost might not be balanced with the current order side)
        example_order = sorted_orders[-1] if selling else sorted_orders[0]
        target_side = trading_enums.TradeOrderSide.SELL if selling else trading_enums.TradeOrderSide.BUY
        if example_order.side is not target_side:
            # an order from the same side is required
            return None
        target_cost = example_order.total_cost
        # use linear equivalent of the target cost
        return target_cost / price

    def _get_quantity_from_recent_trades(self, price, max_quantity, recent_trades, current_price, selling):
        if not self._use_recent_trades_for_order_restore or not recent_trades:
            return None
        # try to find accurate quantity from the available recent trades
        trade = self._get_associated_trade(price, recent_trades, selling)
        if trade is None:
            return None
        now_selling = trade.side == trading_enums.TradeOrderSide.BUY
        return self._compute_mirror_order_volume(
            now_selling, (trade.origin_price or trade.executed_price), price, trade.executed_quantity, trade.fee
        )

    def _get_associated_trade(self, price, trades, selling):
        increment_window = self.flat_increment / 4
        price_window_lower_bound = price - increment_window
        price_window_higher_bound = price + increment_window
        for trade in trades:
            is_sell_trade = trade.side == trading_enums.TradeOrderSide.SELL
            trade_price = trade.origin_price or trade.executed_price
            if is_sell_trade == selling:
                # same side
                if price_window_lower_bound <= trade_price <= price_window_higher_bound:
                    # found the exact same trade
                    return trade
            else:
                # different side: use spread to compute mirror order price
                price_increment = self.flat_spread - self.flat_increment
                mirror_order_price = (trade_price - price_increment) \
                    if is_sell_trade else (trade_price + price_increment)
                if price_window_lower_bound <= mirror_order_price <= price_window_higher_bound:
                    # found mirror trade
                    return trade
        return None

    def _get_maximum_traded_funds(self, allowed_funds, total_available_funds, currency, selling, ignore_available_funds):
        to_trade_funds = total_available_funds
        if allowed_funds > 0:
            if total_available_funds < allowed_funds:
                self.logger.warning(
                    f"Impossible to create every {self.ORDERS_DESC} orders for {self.symbol} using the total "
                    f"{'sell' if selling else 'buy'} funds configuration ({allowed_funds}): not enough "
                    f"available {currency} funds ({total_available_funds}). Trying to use available funds only.")
                to_trade_funds = total_available_funds
            else:
                to_trade_funds = allowed_funds
        if not ignore_available_funds and self._is_initially_available_funds_set(currency):
            # check if enough funds are available
            unlocked_funds = self._get_available_funds(currency)
            if to_trade_funds > unlocked_funds:
                if unlocked_funds <= 0:
                    self.logger.error(f"Impossible to create {self.ORDERS_DESC} orders for {self.symbol}: {currency} "
                                      f"funds are already locked for other trading pairs.")
                    return 0
                self.logger.warning(f"Impossible to create {self.ORDERS_DESC} orders for {self.symbol} using the "
                                    f"total funds ({allowed_funds}): {currency} funds are already locked for other "
                                    f"trading pairs. Trying to use remaining funds only.")
                to_trade_funds = unlocked_funds
        return to_trade_funds

    def _create_new_orders(self, orders, current_price, selling, lower_bound, upper_bound,
                           order_limiting_currency_amount, order_limiting_currency, starting_bound, side,
                           virtual_orders, mode, total_available_funds):
        orders_count, average_order_quantity = \
            self._get_order_count_and_average_quantity(current_price, selling, lower_bound,
                                                       upper_bound, order_limiting_currency_amount,
                                                       order_limiting_currency, mode)
        # orders closest to the current price are added first
        for i in range(orders_count):
            price = self._get_price_from_iteration(starting_bound, selling, i)
            if price is not None:
                quantity = self._get_quantity_from_iteration(average_order_quantity, mode,
                                                             side, i, orders_count, price, starting_bound)
                if quantity is not None:
                    orders.append(OrderData(side, quantity, price, self.symbol, virtual_orders))
        if not orders:
            message = "change change the strategy settings to make less but bigger orders." \
                if self._use_variable_orders_volume(side) else \
                f"reduce {'buy' if side is trading_enums.TradeOrderSide.BUY else 'sell'} the orders volume."
            # Todo: send it as visible notification to the user instead of warning/error
            self.logger.warning(
                f"Not enough {order_limiting_currency} to create {side.name} orders. "
                f"For the strategy to work better, add {order_limiting_currency} funds or "
                f"{message}"
            )
        else:
            # register the locked orders funds
            if not self._is_initially_available_funds_set(order_limiting_currency):
                self._set_initially_available_funds(order_limiting_currency, total_available_funds)

    def _bootstrap_parameters(self, sorted_orders, recently_closed_trades, lower_bound, higher_bound, current_price):
        # no decimal.Decimal computation here
        mode = self.mode or None
        spread = None
        increment = self.flat_increment or None
        bigger_buys_closer_to_center = None
        first_sell = None
        ratio = None
        state = self.FILL

        missing_orders = []

        previous_order = None

        only_sell = False
        only_buy = False
        if sorted_orders:
            if sorted_orders[0].side == trading_enums.TradeOrderSide.SELL:
                # only sell orders
                (self.logger.info if self.enable_trailing_down else self.logger.warning)(
                    f"Only sell orders are online for {self.symbol}, "
                    f"{'checking trailing' if self.enable_trailing_down else 'now waiting for the price to go up to create new buy orders'}."
                )
                first_sell = sorted_orders[0]
                only_sell = True
            if sorted_orders[-1].side == trading_enums.TradeOrderSide.BUY:
                # only buy orders
                (self.logger.info if self.enable_trailing_up else self.logger.warning)(
                    f"Only buy orders are online ({len(sorted_orders)} orders) for {self.symbol}, "
                    f"{'checking trailing' if self.enable_trailing_up else 'now waiting for the price to go down to create new sell orders'}."
                )
                only_buy = True
            for order in sorted_orders:
                if order.symbol != self.symbol:
                    self.logger.warning(f"Error when analyzing orders for {self.symbol}: order.symbol != self.symbol.")
                    return None, self.ERROR, None
                spread_point = False
                if previous_order is None:
                    previous_order = order
                else:
                    if previous_order.side != order.side:
                        # changing order side: reached spread point
                        if spread is None:
                            if lower_bound < self.current_price < higher_bound:
                                spread_point = True
                                delta_spread = order.origin_price - previous_order.origin_price

                                if increment is None:
                                    self.logger.warning(f"Error when analyzing orders for {self.symbol}: increment "
                                                        f"is None.")
                                    return None, self.ERROR, None
                                else:
                                    inferred_spread = self.flat_spread or self.spread * increment / self.increment
                                    missing_orders_count = (delta_spread - inferred_spread) / increment
                                    # should be 0 when no order is missing
                                    if float(missing_orders_count) > 0.5:
                                        # missing orders around spread point: symmetrical orders were not created when
                                        # orders were filled => re-create them
                                        next_missing_order_price = previous_order.origin_price + increment
                                        spread_lower_boundary = order.origin_price - inferred_spread

                                        # re-create buy orders starting from the closest buy up to spread
                                        while next_missing_order_price < self.current_price and \
                                                next_missing_order_price <= spread_lower_boundary:
                                            # missing buy order
                                            if next_missing_order_price + increment > spread_lower_boundary:
                                                # This potential missing buy is the last before spread. Before considering it missing,
                                                # make sure that the missing order is not on the selling side of the spread (and 
                                                # therefore the missing order should be a sell)
                                                if recently_closed_trades and self._get_just_filled_unmirrored_missing_order_trade(
                                                    recently_closed_trades, next_missing_order_price, trading_enums.TradeOrderSide.BUY
                                                ):
                                                    # this order has just been filled on the buying side: the missing order is a sell, 
                                                    # it will be identified as missing right after: exit buy orders loop now
                                                    break
                                            if not self._is_just_closed_order(
                                                next_missing_order_price, recently_closed_trades
                                            ):
                                                missing_orders.append(
                                                    (next_missing_order_price, trading_enums.TradeOrderSide.BUY))
                                            next_missing_order_price += increment

                                        # create sell orders down to the highest buy order + spread
                                        # next_missing_order_price - increment is the price of the highest buy order
                                        spread_higher_boundary = next_missing_order_price - increment + inferred_spread

                                        next_missing_order_price = order.origin_price - increment
                                        # re-create sell orders starting from the closest sell down to spread
                                        while next_missing_order_price >= spread_higher_boundary:
                                            # missing sell order
                                            if not self._is_just_closed_order(
                                                next_missing_order_price, recently_closed_trades
                                            ):
                                                missing_orders.append(
                                                    (next_missing_order_price, trading_enums.TradeOrderSide.SELL))
                                            next_missing_order_price -= increment

                                        spread = inferred_spread
                                    else:
                                        spread = delta_spread

                                # calculations to infer ratio
                                last_buy_cost = previous_order.origin_price * previous_order.origin_quantity
                                first_buy_cost = sorted_orders[0].origin_price * sorted_orders[0].origin_quantity
                                bigger_buys_closer_to_center = last_buy_cost - first_buy_cost > 0
                                first_sell = order
                                ratio = last_buy_cost / first_buy_cost if bigger_buys_closer_to_center \
                                    else first_buy_cost / last_buy_cost
                            else:
                                self.logger.info(f"Current price ({self.current_price}) for {self.symbol} "
                                                 f"is out of range.")
                                return None, self.ERROR, None
                    if increment is None:
                        increment = self.flat_increment or order.origin_price - previous_order.origin_price
                        if increment <= 0:
                            self.logger.warning(f"Error when analyzing orders for {self.symbol}: increment <= 0.")
                            return None, self.ERROR, None
                    elif not spread_point:
                        delta_increment = order.origin_price - previous_order.origin_price
                        # skip not-yet-updated orders
                        if previous_order.side == order.side:
                            missing_orders_count = float(delta_increment / increment)
                            if missing_orders_count > 2.5 and not self._expect_missing_orders:
                                self.logger.warning(f"Error when analyzing orders for {self.symbol}: "
                                                    f"missing_orders_count > 2.5.")
                                if not self._is_just_closed_order(previous_order.origin_price + increment,
                                                                  recently_closed_trades):
                                    return None, self.ERROR, None
                            elif missing_orders_count > 1.5:
                                if len(sorted_orders) < self.operational_depth and \
                                   (not self._skip_order_restore_on_recently_closed_orders or (
                                       self._skip_order_restore_on_recently_closed_orders and not recently_closed_trades
                                   )):
                                    order_price = previous_order.origin_price + increment
                                    while order_price < order.origin_price:
                                        if not self._is_just_closed_order(order_price, recently_closed_trades):
                                            missing_orders.append((order_price, order.side))
                                        order_price += increment

                    previous_order = order
            if (only_buy or only_sell) and (increment and self.flat_spread):
                # missing orders between others have been taken into account, now add potential missing orders
                # on boundaries
                # make sure that no buy order is missing from previous sell orders (or the opposite)
                if only_buy:
                    start_price = sorted_orders[-1].origin_price
                    end_price = higher_bound
                else:
                    start_price = lower_bound
                    end_price = sorted_orders[0].origin_price
                missing_orders_count = float((end_price - start_price) / increment)
                if missing_orders_count > 1.5:
                    last_order_price = sorted_orders[-1 if only_buy else 0].origin_price
                    same_side_order_price = last_order_price + increment if only_buy else last_order_price - increment
                    if (
                        # creating a new buy order <= the current price, its price is previous buy order price + increment
                        same_side_order_price <= current_price and only_buy
                    ) or (
                        # creating a new sell order >= the current price, its price is previous sell order price - increment
                        same_side_order_price >= current_price and not only_buy
                    ):
                        order_price = same_side_order_price
                    else:
                        # creating a new order on the other side, its price is taking spread into account
                        order_price = last_order_price + self.flat_spread if only_buy else last_order_price - self.flat_spread
                    lowest_sell = lower_bound + self.flat_spread - self.flat_increment
                    highest_buy = higher_bound - self.flat_spread + self.flat_increment
                    to_create_missing_orders_count = self.operational_depth - len(sorted_orders)

                    while lower_bound <= order_price <= higher_bound and (
                        self.allow_virtual_orders or len(missing_orders) < to_create_missing_orders_count
                    ):
                        if not self._is_just_closed_order(order_price, recently_closed_trades):
                            side = trading_enums.TradeOrderSide.BUY if order_price < current_price \
                                else trading_enums.TradeOrderSide.SELL
                            min_price = lower_bound if side == trading_enums.TradeOrderSide.BUY else lowest_sell
                            max_price = highest_buy if side == trading_enums.TradeOrderSide.BUY else higher_bound
                            if min_price <= order_price <= max_price:
                                missing_orders.append((order_price, side))
                        next_price = order_price + increment if only_buy else order_price - increment
                        price_delta = increment
                        if order_price <= current_price <= next_price or order_price >= current_price >= next_price:
                            # about to switch side: apply spread
                            price_delta = self.flat_spread
                        order_price = order_price + price_delta if only_buy else order_price - price_delta

            if ratio is not None:
                first_sell_cost = first_sell.origin_price * first_sell.origin_quantity
                last_sell_cost = sorted_orders[-1].origin_price * sorted_orders[-1].origin_quantity
                bigger_sells_closer_to_center = first_sell_cost - last_sell_cost > 0

                if bigger_buys_closer_to_center is not None and bigger_sells_closer_to_center is not None:
                    if bigger_buys_closer_to_center:
                        if bigger_sells_closer_to_center:
                            mode = StrategyModes.NEUTRAL if 0.1 < ratio - 1 < 0.5 else StrategyModes.MOUNTAIN
                        else:
                            mode = StrategyModes.SELL_SLOPE
                    else:
                        if bigger_sells_closer_to_center:
                            mode = StrategyModes.BUY_SLOPE
                        else:
                            mode = StrategyModes.VALLEY

                if mode is None or increment is None or spread is None:
                    self.logger.warning(f"Error when analyzing orders for {self.symbol}: mode is None or increment "
                                        f"is None or spread is None.")
                    return None, self.ERROR, None
            if increment is None or (not (only_sell or only_buy) and spread is None):
                self.logger.warning(f"Error when analyzing orders for {self.symbol}: increment is None or "
                                    f"(not(only_sell or only_buy) and spread is None).")
                return None, self.ERROR, None
            return missing_orders, state, increment
        else:
            # no orders
            return None, self.ERROR, None

    def _is_just_closed_order(self, price, recently_closed_trades):
        if not self._skip_order_restore_on_recently_closed_orders:
            return False
        if self.flat_increment is None:
            return len(recently_closed_trades)
        else:
            inc = self.flat_spread * decimal.Decimal("1.5")
            for trade in recently_closed_trades:
                trade_price = trade.origin_price or trade.executed_price
                if trade_price - inc <= price <= trade_price + inc:
                    return True
        return False

    @staticmethod
    def _spread_in_recently_closed_order(min_amount, max_amount, sorted_closed_orders):
        for order in sorted_closed_orders:
            if min_amount <= order.get_origin_price() <= max_amount:
                return True
        return False

    @staticmethod
    def _merged_and_sort_not_virtual_orders(buy_orders, sell_orders):
        # create sell orders first follows by buy orders
        return StaggeredOrdersTradingModeProducer._filter_virtual_order(sell_orders) + \
               StaggeredOrdersTradingModeProducer._filter_virtual_order(buy_orders)

    @staticmethod
    def _filter_virtual_order(orders):
        return [order for order in orders if not order.is_virtual]

    @staticmethod
    def _set_virtual_orders(buy_orders, sell_orders, operational_depth):
        # all orders that are further than self.operational_depth are virtual
        orders_count = 0
        buy_index = 0
        sell_index = 0
        at_least_one_added = True
        while orders_count < operational_depth and at_least_one_added:
            # priority to orders closer to current price
            at_least_one_added = False
            if len(buy_orders) > buy_index:
                buy_orders[buy_index].is_virtual = False
                buy_index += 1
                orders_count += 1
                at_least_one_added = True
            if len(sell_orders) > sell_index and orders_count < operational_depth:
                sell_orders[sell_index].is_virtual = False
                sell_index += 1
                orders_count += 1
                at_least_one_added = True

    def _get_order_count_and_average_quantity(self, current_price, selling, lower_bound, upper_bound, holdings,
                                              currency, mode):
        if lower_bound >= upper_bound:
            self.logger.error(f"Invalid bounds for {self.symbol}: too close to the current price")
            return 0, 0
        if selling:
            order_distance = upper_bound - (lower_bound + self.flat_spread / 2)
        else:
            order_distance = (upper_bound - self.flat_spread / 2) - lower_bound
        order_count_divisor = self.flat_increment
        orders_count = math.floor(order_distance / order_count_divisor + 1) if order_count_divisor else 0
        if orders_count < 1:
            self.logger.warning(f"Impossible to create {'sell' if selling else 'buy'} orders for {currency}: "
                                f"not enough funds.")
            return 0, 0
        if self._use_variable_orders_volume(trading_enums.TradeOrderSide.SELL if selling
           else trading_enums.TradeOrderSide.BUY):
            return self._ensure_average_order_quantity(orders_count, current_price, selling, holdings,
                                                       currency, mode)
        else:
            return self._get_orders_count_from_fixed_volume(selling, current_price, holdings, orders_count)

    def _use_variable_orders_volume(self, side):
        return (self.sell_volume_per_order == decimal.Decimal(0) and side is trading_enums.TradeOrderSide.SELL) \
               or self.buy_volume_per_order == decimal.Decimal(0)

    def _get_orders_count_from_fixed_volume(self, selling, current_price, holdings, orders_count):
        volume_in_currency = self.sell_volume_per_order if selling else current_price * self.buy_volume_per_order
        orders_count = min(math.floor(holdings / volume_in_currency), orders_count) if volume_in_currency else 0
        return orders_count, self.sell_volume_per_order if selling else self.buy_volume_per_order

    def _ensure_average_order_quantity(self, orders_count, current_price, selling,
                                       holdings, currency, mode):
        if not (orders_count and current_price):
            # avoid div by 0
            self.logger.warning(
                f"Can't compute average order quantity: orders_count={orders_count} and current_price={current_price}"
            )
            return 0, 0
        holdings_in_quote = holdings if selling else holdings / current_price
        average_order_quantity = holdings_in_quote / orders_count
        min_order_quantity, max_order_quantity = self._get_min_max_quantity(average_order_quantity, self.mode)
        if self.min_max_order_details[self.min_quantity] is not None \
                and self.min_max_order_details[self.min_cost] is not None:
            min_quantity = max(self.min_max_order_details[self.min_quantity],
                               self.min_max_order_details[self.min_cost] / current_price)
            min_quantity = min_quantity * decimal.Decimal(TEN_PERCENT_DECIMAL)    # increase min quantity by 10% to be sure to be
            # able to create orders in minimal funds conditions
            adapted_min_order_quantity = trading_personal_data.decimal_adapt_quantity(
                self.symbol_market, min_order_quantity
            )
            adapted_min_quantity = trading_personal_data.decimal_adapt_quantity(self.symbol_market, min_quantity)
            if adapted_min_order_quantity < adapted_min_quantity:
                # 1.01 to account for order creation rounding
                if holdings_in_quote < average_order_quantity * ONE_PERCENT_DECIMAL:
                    return 0, 0
                elif self.limit_orders_count_if_necessary:
                    self.logger.warning(f"Not enough funds to create every {self.symbol} {self.ORDERS_DESC} "
                                        f"{trading_enums.TradeOrderSide.SELL.name if selling else trading_enums.TradeOrderSide.BUY.name} "
                                        f"orders according to exchange's rules. Creating the maximum possible number "
                                        f"of valid orders instead.")
                    return self._adapt_orders_count_and_quantity(holdings_in_quote, adapted_min_quantity, mode)
                else:
                    min_funds = self._get_min_funds(orders_count, min_quantity, self.mode, current_price)
                    self.logger.error(f"Impossible to create {self.symbol} {self.ORDERS_DESC} "
                                      f"{trading_enums.TradeOrderSide.SELL.name if selling else trading_enums.TradeOrderSide.BUY.name} "
                                      f"orders: minimum quantity for {self.mode.value} mode is lower than the minimum "
                                      f"allowed for this trading pair on this exchange: requested minimum: "
                                      f"{min_order_quantity} and exchange minimum is {min_quantity}. "
                                      f"Minimum required funds are {min_funds}{f' {currency}' if currency else ''}.")
                return 0, 0
        return orders_count, average_order_quantity

    def _adapt_orders_count_and_quantity(self, holdings, min_quantity, mode):
        # called when there are enough funds for at least one order but too many orders are requested
        min_average_quantity = self._get_average_quantity_from_exchange_minimal_requirements(min_quantity, mode)
        if 2 * holdings > min_average_quantity >= holdings:
            return 1, min_average_quantity
        max_orders_count = math.floor(holdings / min_average_quantity) if min_average_quantity else 0
        if max_orders_count > 0:
            # count remaining holdings if any
            average_quantity = min_average_quantity + \
                               (holdings - min_average_quantity * max_orders_count) / max_orders_count
            return max_orders_count, average_quantity
        return 0, 0

    def _get_price_from_iteration(self, starting_bound, is_selling, iteration):
        price_step = self.flat_increment * iteration
        price = starting_bound + price_step if is_selling else starting_bound - price_step
        if self.min_max_order_details[self.min_price] and price < self.min_max_order_details[self.min_price]:
            return None
        return price

    def _get_quantity_from_iteration(self, average_order_quantity, mode, side,
                                     iteration, max_iteration, price, starting_bound):
        multiplier_price_ratio = 1
        min_quantity, max_quantity = self._get_min_max_quantity(average_order_quantity, mode)
        delta = max_quantity - min_quantity
        if max_iteration == 1:
            quantity = average_order_quantity
            scaled_quantity = quantity
        else:
            if iteration >= max_iteration:
                raise trading_errors.NotSupported
            iterations_progress = iteration / (max_iteration - 1)
            if StrategyModeMultipliersDetails[mode][side] == INCREASING:
                multiplier_price_ratio = 1 - iterations_progress
            elif StrategyModeMultipliersDetails[mode][side] == DECREASING:
                multiplier_price_ratio = iterations_progress
            elif StrategyModeMultipliersDetails[mode][side] == STABLE:
                multiplier_price_ratio = 0
            if price <= 0:
                return None
            quantity = (min_quantity +
                                   (decimal.Decimal(str(delta)) * decimal.Decimal(str(multiplier_price_ratio))))
            # when self.quote_volume_per_order is set, keep the same volume everywhere
            scaled_quantity = quantity * (starting_bound / price if self._use_variable_orders_volume(side)
                                          else trading_constants.ONE)

        # reduce last order quantity to avoid python float representation issues
        if iteration == max_iteration - 1 and self._use_variable_orders_volume(side):
            scaled_quantity = scaled_quantity * decimal.Decimal("0.999")
            quantity = quantity * decimal.Decimal("0.999")
        if self._is_valid_order_quantity_for_exchange(scaled_quantity, price):
            return scaled_quantity
        if self._is_valid_order_quantity_for_exchange(quantity, price):
            return quantity
        return None

    def _is_valid_order_quantity_for_exchange(self, quantity, price):
        if self.min_max_order_details[self.min_quantity] and (quantity < self.min_max_order_details[self.min_quantity]):
            return False
        cost = quantity * price
        if self.min_max_order_details[self.min_cost] and (cost < self.min_max_order_details[self.min_cost]):
            return False
        return True

    def _get_min_funds(self, orders_count, min_order_quantity, mode, current_price):
        mode_multiplier = StrategyModeMultipliersDetails[mode][MULTIPLIER]
        required_average_quantity = min_order_quantity / (1 - mode_multiplier / 2)

        if self.min_cost in self.min_max_order_details:
            average_cost = current_price * required_average_quantity
            if self.min_max_order_details[self.min_cost]:
                min_cost = self.min_max_order_details[self.min_cost]
                if average_cost < min_cost:
                    required_average_quantity = min_cost / current_price

        return orders_count * required_average_quantity * TEN_PERCENT_DECIMAL

    @staticmethod
    def _get_average_quantity_from_exchange_minimal_requirements(exchange_min, mode):
        mode_multiplier = StrategyModeMultipliersDetails[mode][MULTIPLIER]
        # add 1% to prevent rounding issues
        return exchange_min / (1 - mode_multiplier / 2) * ONE_PERCENT_DECIMAL

    @staticmethod
    def _get_min_max_quantity(average_order_quantity, mode):
        mode_multiplier = StrategyModeMultipliersDetails[mode][MULTIPLIER]
        min_quantity = average_order_quantity * (1 - mode_multiplier / 2)
        max_quantity = average_order_quantity * (1 + mode_multiplier / 2)
        return min_quantity, max_quantity

    async def _create_order(self, order, current_price, completing_trailing, dependencies: list[str]):
        data = {
            StaggeredOrdersTradingModeConsumer.ORDER_DATA_KEY: order,
            StaggeredOrdersTradingModeConsumer.CURRENT_PRICE_KEY: current_price,
            StaggeredOrdersTradingModeConsumer.SYMBOL_MARKET_KEY: self.symbol_market,
            StaggeredOrdersTradingModeConsumer.COMPLETING_TRAILING_KEY: completing_trailing,
        }
        state = trading_enums.EvaluatorStates.LONG if order.side is trading_enums.TradeOrderSide.BUY else trading_enums.EvaluatorStates.SHORT
        await self.submit_trading_evaluation(cryptocurrency=self.trading_mode.cryptocurrency,
                                             symbol=self.trading_mode.symbol,
                                             time_frame=None,
                                             state=state,
                                             data=data,
                                             dependencies=dependencies)

    async def _create_not_virtual_orders(
        self, orders_to_create: list, current_price: decimal.Decimal, 
        triggering_trailing: bool, dependencies: typing.Optional[commons_signals.SignalDependencies]
    ):
        locks_available_funds = self._should_lock_available_funds(triggering_trailing)
        for index, order in enumerate(orders_to_create):
            is_completing_trailing = triggering_trailing and (index == len(orders_to_create) - 1)
            await self._create_order(order, current_price, is_completing_trailing, dependencies)
            if locks_available_funds:
                base, quote = symbol_util.parse_symbol(order.symbol).base_and_quote()
                # keep track of the required funds
                volume = order.quantity if order.side is trading_enums.TradeOrderSide.SELL \
                    else order.price * order.quantity
                self._remove_from_available_funds(
                    base if order.side is trading_enums.TradeOrderSide.SELL else quote, volume
                )

    def _refresh_symbol_data(self, symbol_market):
        min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = \
            trading_personal_data.get_min_max_amounts(symbol_market)
        self.min_max_order_details[self.min_quantity] = None if min_quantity is None \
            else decimal.Decimal(str(min_quantity))
        self.min_max_order_details[self.max_quantity] = None if max_quantity is None \
            else decimal.Decimal(str(max_quantity))
        self.min_max_order_details[self.min_cost] = None if min_cost is None \
            else decimal.Decimal(str(min_cost))
        self.min_max_order_details[self.max_cost] = None if max_cost is None \
            else decimal.Decimal(str(max_cost))
        self.min_max_order_details[self.min_price] = None if min_price is None \
            else decimal.Decimal(str(min_price))
        self.min_max_order_details[self.max_price] = None if max_price is None \
            else decimal.Decimal(str(max_price))

    @classmethod
    def get_should_cancel_loaded_orders(cls):
        return False

    def _remove_from_available_funds(self, currency, amount) -> None:
        if self.exchange_manager.id in StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS:
            StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS[self.exchange_manager.id][currency] = \
                StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS[self.exchange_manager.id][currency] - amount

    def _set_initially_available_funds(self, currency, amount) -> None:
        if self.exchange_manager.id not in StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS:
            StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS[self.exchange_manager.id] = {}
        StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS[self.exchange_manager.id][currency] = amount

    def _is_initially_available_funds_set(self, currency) -> bool:
        try:
            return currency in StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS[self.exchange_manager.id]
        except KeyError:
            return False

    def _get_available_funds(self, currency) -> float:
        try:
            # only used when creating orders in NEW state, when NOT ignoring available funds
            return StaggeredOrdersTradingModeProducer.AVAILABLE_FUNDS[self.exchange_manager.id][currency]
        except KeyError:
            return 0

    # syntax: "async with xxx.get_lock():"
    def get_lock(self):
        return self.lock
