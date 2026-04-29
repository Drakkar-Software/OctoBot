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
import decimal
import random
import enum
import typing
import time

import octobot_commons.logging as logging
import octobot_commons.symbols as commons_symbols
import octobot_commons.constants as commons_constants
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as exchanges
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.api as trading_api
import octobot_trading.modes as trading_modes

_PRICE_FETCHING_TIMEOUT = 30

_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID = {}
_INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID = {}
_LOCKED_FUNDS_RATIO = decimal.Decimal("2")    # lock 200% budget
_PRICE_INIT_TIMEOUT = 120
_MIN_COST_ORDER_MULTIPLIER = decimal.Decimal("1.5") # avoid min order size issues by using at least 50% larger orders
_ON_MISSING_FUNDS_MAX_CHECK_INTERVAL = 5 * commons_constants.MINUTE_TO_SECONDS

class LockFundsActions(enum.Enum):
    REALLOCATE_SCHEDULED_VOLUME_FUNDS = "reallocate_scheduled_volume_funds"


class ScheduledVolume:
    def __init__(
        self, exchange_manager, symbol, on_missing_funds_callback,
        min_interval, max_interval, min_quote_amount, max_quote_amount
    ):
        self.exchange_manager: exchanges.ExchangeManager = exchange_manager
        self.symbol: str = symbol
        self.parsed_symbol = commons_symbols.parse_symbol(self.symbol)
        self.min_interval: float = min_interval
        self.max_interval: float = max_interval
        self.min_quote_amount: float = float(min_quote_amount)
        self.max_quote_amount: float = float(max_quote_amount)

        self._healthy = False
        self._should_stop: bool = False
        self._task = None
        self._last_order_side: trading_enums.TradeOrderSide = trading_enums.TradeOrderSide.SELL # buy first

        self._on_missing_funds_callback = on_missing_funds_callback
        self._last_on_missing_funds_callback_call_time = 0

        self.logger = logging.get_logger(
            f"{self.__class__.__name__}[{self.exchange_manager.exchange_name}:{self.symbol}]"
        )

        _init_global_locked_funds(self.exchange_manager.id, self.symbol)
        if self.exchange_manager.id not in _INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID:
            _INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[self.exchange_manager.id] = {}

    async def start(self):
        self._validate_parameters()
        self._should_stop = False
        self._healthy = True
        _register_initializing_locked_funds_by_exchange_manager_id(self.exchange_manager.id, self.symbol)
        self._task = asyncio.create_task(self._schedule_loop())

    def stop(self):
        self._should_stop = True
        if self._task is not None:
            self._task.cancel()
        self._task = None

    def _get_locked_base_and_quote(self) -> (decimal.Decimal, decimal.Decimal):
        return _get_locked_base_and_quote(self.exchange_manager.id, self.symbol)

    def _get_total_locked_funds_quote_value(self, current_price: decimal.Decimal) -> decimal.Decimal:
        locked_base, locked_quote = self._get_locked_base_and_quote()
        return locked_quote + (locked_base * current_price)

    def _should_reset_locked_funds(self, current_price: decimal.Decimal):
        # reset locked funds when total locked value is less than what is required to create max size scheduled volume
        return self._get_total_locked_funds_quote_value(current_price) <= decimal.Decimal(str(self.max_quote_amount))

    def _reset_locked_funds(self, current_price: decimal.Decimal) -> typing.Optional[LockFundsActions]:
        action = None
        if current_price > trading_constants.ZERO:
            quote_locked_funds = _get_locked_funds(self.max_quote_amount)
            # total locked value should be worth quote_locked_funds
            to_add_amount = quote_locked_funds - self._get_total_locked_funds_quote_value(current_price)
            if to_add_amount > trading_constants.ZERO:
                remaining_to_add_quote_value = to_add_amount
                base, quote = commons_symbols.parse_symbol(self.symbol).base_and_quote()
                available_base = trading_api.get_portfolio_currency(self.exchange_manager, base).available - (
                    get_global_locked_funds(self.exchange_manager.id, base, "")
                )
                available_quote = trading_api.get_portfolio_currency(self.exchange_manager, quote).available - (
                    get_global_locked_funds(self.exchange_manager.id, quote, "")
                )
                available_base_value_in_quote = available_base * current_price
                # lock funds from holding the portfolio has the most of
                added_locked_base = trading_constants.ZERO
                added_locked_quote = trading_constants.ZERO
                if available_base_value_in_quote > available_quote:
                    if available_base_value_in_quote > trading_constants.ZERO:
                        added_locked_base = min(available_base_value_in_quote, remaining_to_add_quote_value) / current_price
                        remaining_to_add_quote_value = remaining_to_add_quote_value - (added_locked_base * current_price)
                    if remaining_to_add_quote_value > trading_constants.ZERO:
                        added_locked_quote = min(available_quote, remaining_to_add_quote_value)
                        remaining_to_add_quote_value = remaining_to_add_quote_value - added_locked_quote
                else:
                    if available_quote > trading_constants.ZERO:
                        added_locked_quote = min(available_quote, remaining_to_add_quote_value)
                        remaining_to_add_quote_value = remaining_to_add_quote_value - added_locked_quote
                    if remaining_to_add_quote_value > trading_constants.ZERO:
                        added_locked_base = min(available_base_value_in_quote, remaining_to_add_quote_value) / current_price
                        remaining_to_add_quote_value = remaining_to_add_quote_value - (added_locked_base * current_price)
                if remaining_to_add_quote_value:
                    if open_orders := (
                        self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(self.symbol)
                    ):
                        # not enough available funds to ensure scheduled volume: trigger reallocation
                        # to free funds from open MM orders
                        # => lock funds that will be freed by open orders
                        orders_added_locked_base, orders_added_locked_quote, orders_remaining_to_add_quote_value = (
                            self._get_locked_funds_to_be_freed_from_open_orders(
                                open_orders, remaining_to_add_quote_value, current_price
                            )
                        )
                        if orders_remaining_to_add_quote_value:
                            self.logger.error(
                                f"Not enough available funds to lock [{self.exchange_manager.exchange_name}] {self.symbol} "
                                f"scheduled orders budget of {quote_locked_funds} {quote}, even after canceling orders: "
                                f"missing {orders_remaining_to_add_quote_value} {quote} worth of {base} or {quote}"
                            )
                        else:
                            added_locked_base += orders_added_locked_base
                            added_locked_quote += orders_added_locked_quote
                            self.logger.info(
                                f"Triggering [{self.exchange_manager.exchange_name}] {self.symbol} orders reset to "
                                f"free funds for scheduled volume: "
                                f"{available_base=}, {available_quote=}, {remaining_to_add_quote_value=}. "
                                f"Funds need to be freed to allow scheduled volume trading."
                            )
                            action = LockFundsActions.REALLOCATE_SCHEDULED_VOLUME_FUNDS
                    else:
                        # no order to cancel: funds are really not enough
                        self.logger.error(
                            f"Not enough available funds to lock [{self.exchange_manager.exchange_name}] {self.symbol} "
                            f"scheduled orders budget of {quote_locked_funds} {quote}: "
                            f"missing {remaining_to_add_quote_value} {quote} worth of {base} or {quote}"
                        )
                if added_locked_base or added_locked_quote:
                    # save added locked funds
                    locked_base, locked_quote = self._get_locked_base_and_quote()
                    self._update_locked_funds(locked_base + added_locked_base, locked_quote + added_locked_quote)
                    updated_locked_base, updated_locked_quote = self._get_locked_base_and_quote()
                    self.logger.info(
                        f"Added [{self.exchange_manager.exchange_name}] {self.symbol} scheduled orders locked funds: "
                        f"locked {updated_locked_base} {base} (added {added_locked_base} {base}) "
                        f"locked {updated_locked_quote} {quote} (added {added_locked_quote} {quote}) "
                    )
                else:
                    self.logger.warning(
                        f"No available funds to add to [{self.exchange_manager.exchange_name}] {self.symbol} "
                        f"scheduled orders locked funds"
                    )
        else:
            self.logger.warning(
                f"Can't reset [{self.exchange_manager.exchange_name}] {self.symbol} scheduled orders locked funds "
                f"when current_price is not >0 ({current_price=})"
            )
        return action

    def _get_locked_funds_to_be_freed_from_open_orders(
        self, open_orders: list, remaining_to_add_quote_value: decimal.Decimal, current_price: decimal.Decimal
    ):
        orders_added_locked_base = trading_constants.ZERO
        orders_added_locked_quote = trading_constants.ZERO
        # take funds from orders that have the most funds
        sell_orders_quote_funds = sum(
            o.origin_quantity for o in open_orders if o.side == trading_enums.TradeOrderSide.SELL
        ) * current_price
        buy_orders_quote_funds = sum(
            o.total_cost for o in open_orders if o.side == trading_enums.TradeOrderSide.BUY
        )
        if sell_orders_quote_funds > buy_orders_quote_funds:
            orders_added_locked_base = min(sell_orders_quote_funds, remaining_to_add_quote_value) / current_price
            remaining_to_add_quote_value = remaining_to_add_quote_value - (orders_added_locked_base * current_price)
            if remaining_to_add_quote_value > trading_constants.ZERO:
                orders_added_locked_quote = min(buy_orders_quote_funds, remaining_to_add_quote_value)
                remaining_to_add_quote_value = remaining_to_add_quote_value - orders_added_locked_quote
        else:
            orders_added_locked_quote = min(buy_orders_quote_funds, remaining_to_add_quote_value)
            remaining_to_add_quote_value = remaining_to_add_quote_value - orders_added_locked_quote
            if remaining_to_add_quote_value > trading_constants.ZERO:
                orders_added_locked_base = min(sell_orders_quote_funds, remaining_to_add_quote_value) / current_price
                remaining_to_add_quote_value = remaining_to_add_quote_value - (orders_added_locked_base * current_price)
        return orders_added_locked_base, orders_added_locked_quote, remaining_to_add_quote_value

    def ensure_locked_funds(self, current_price: decimal.Decimal) -> typing.Optional[LockFundsActions]:
        action = None
        if current_price > trading_constants.ZERO and self._should_reset_locked_funds(current_price):
            action = self._reset_locked_funds(current_price)
        return action

    async def wait_required_locked_funds_init(self):
        try:
            if await _wait_required_locked_funds_init(self.exchange_manager.id, self.symbol, _PRICE_INIT_TIMEOUT):
                self.logger.info(
                    f"[{self.exchange_manager.exchange_name}] {self.symbol} locked funds have been initialized"
                )
        except asyncio.TimeoutError as err:
            self.logger.error(
                f"Timeout when waiting for [{self.exchange_manager.exchange_name}] {self.symbol} "
                f"locked funds init: {err}"
            )

    async def _initialize_locked_funds(self, timeout):
        try:
            current_price = await trading_personal_data.get_up_to_date_price(
                self.exchange_manager, self.symbol, timeout=timeout
            )
            # will still be called by MM trigger in case the previous trading_personal_data.get_up_to_date_price timeouts
            self.ensure_locked_funds(current_price)
        except asyncio.TimeoutError as err:
            self.logger.error(
                f"Timeout when initializing [{self.exchange_manager.exchange_name}] {self.symbol} locked funds: {err}"
            )
        except Exception as err:
            self.logger.exception(
                err, True,
                f"Unexpected error when initializing [{self.exchange_manager.exchange_name}] "
                f"{self.symbol} locked funds: {err}"
            )

    def _get_locked_base(self):
        return

    def _update_locked_funds(self, locked_base: decimal.Decimal, locked_quote: decimal.Decimal):
        base, quote = commons_symbols.parse_symbol(self.symbol).base_and_quote()
        self.logger.info(
            f"Updated [{self.exchange_manager.exchange_name}] {self.symbol} "
            f"locked funds: {float(locked_base)} {base} & {float(locked_quote)} {quote}"
        )
        _set_global_locked_funds(self.exchange_manager.id, self.symbol, locked_base, locked_quote)

    def _validate_parameters(self):
        if self.min_interval > self.max_interval:
            raise ValueError("`min_interval` must be greater or equal to `max_interval`")
        if self.min_quote_amount > self.max_quote_amount:
            raise ValueError("`min_quote_amount` must be greater or equal to `max_quote_amount`")

    async def _schedule_loop(self):
        self.logger.info(
            f"Starting [{self.exchange_manager.exchange_name}] {self.symbol} scheduled volume loop. "
            f"Time interval: [{self.min_interval}:{self.max_interval}] "
            f"Quote amount interval: [{self.min_quote_amount}:{self.max_quote_amount}]"
        )
        await self._initialize_locked_funds(_PRICE_FETCHING_TIMEOUT)
        while not self._should_stop:
            try:
                previous_iteration_created_orders = await self._trigger()
            except Exception as err:
                previous_iteration_created_orders = []
                self.logger.exception(
                    err, True,
                    f"Error when triggering [{self.exchange_manager.exchange_name}] "
                    f"{self.symbol} scheduled order: {err}"
                )
            try:
                self._update_locked_funds_from_last_orders_trades(previous_iteration_created_orders)
            except Exception as err:
                self.logger.exception(
                    err, True,
                    f"Error when updating locked funds from previous orders trades "
                    f"[{self.exchange_manager.exchange_name}] {self.symbol}: {err}"
                )
            if self._should_stop:
                break
            await asyncio.sleep(self._get_sleeping_time())

    def _get_sleeping_time(self) -> float:
        return random.uniform(self.min_interval, self.max_interval)

    @trading_modes.enabled_trader_only(disabled_return_value=[])
    async def _trigger(self) -> list:
        _, _, _, current_price, symbol_market = await trading_personal_data.get_pre_order_data(
            self.exchange_manager,
            symbol=self.symbol,
            timeout=_PRICE_FETCHING_TIMEOUT
        )
        if not current_price or current_price.is_nan():
            self.logger.error(
                f"Skipped [{self.exchange_manager.exchange_name}] {self.symbol} "
                f"scheduled orders creation: {current_price=}"
            )
            return []

        next_orders = self._get_next_orders(current_price, symbol_market)
        if not next_orders:
            if not await self._call_on_missing_funds_if_needed():
                identifier = f"[{self.exchange_manager.exchange_name}] {self.symbol}"
                if self._healthy:
                    self.logger.error(f"Not enough funds to create {identifier} scheduled orders")
                    self._healthy = False
                else:
                    self.logger.warning(f"Still not enough funds to create {identifier} scheduled orders")
        created_orders = []
        for order in next_orders:
            if new_order := await self.exchange_manager.trader.create_order(
                order, loaded=False, wait_for_creation=True
            ):
                created_orders.append(new_order)
                self._last_order_side = new_order.side
                fee_str = (
                    f"{new_order.fee[trading_enums.FeePropertyColumns.COST.value]} "
                f"{new_order.fee[trading_enums.FeePropertyColumns.CURRENCY.value]}" if new_order.fee else "?"
                )
                self.logger.info(
                    f"Created [{self.exchange_manager.exchange_name}] {self.symbol} scheduled volume "
                    f"order: {str(self._last_order_side)} {new_order.origin_quantity} at {new_order.origin_price}, "
                    f"fee: {fee_str}"
                )
                # orders creation worked: reset _last_on_missing_funds_callback_call_time
                self._last_on_missing_funds_callback_call_time = 0
                self._healthy = True
            else:
                self.logger.warning(
                    f"Failed to create [{self.exchange_manager.exchange_name}] {self.symbol} scheduled volume "
                    f"order: {order}"
                )
        return created_orders

    async def _call_on_missing_funds_if_needed(self):
        current_time = time.time()
        if current_time - self._last_on_missing_funds_callback_call_time > _ON_MISSING_FUNDS_MAX_CHECK_INTERVAL:
            self._last_on_missing_funds_callback_call_time = current_time
            identifier = f"[{self.exchange_manager.exchange_name}] {self.symbol}"
            self.logger.info(
                f"Forcing on_missing_funds_callback call to free {identifier} scheduled orders funds."
            )
            await self._on_missing_funds_callback(f"Missing {identifier} scheduled orders funds")
            return True
        return False

    def _update_locked_funds_from_last_orders_trades(self, orders: list):
        if not orders:
            return
        trades_or_orders: list[typing.Union[trading_personal_data.Trade, trading_personal_data.Order]] = []
        for order in orders:
            if order_trade := trading_personal_data.aggregate_trades_by_exchange_order_id(
                self.exchange_manager.exchange_personal_data.trades_manager.get_trades(
                    exchange_order_id=order.exchange_order_id
                )
            ).get(order.exchange_order_id):
                trades_or_orders.append(order_trade)
            else:
                # no trade is available, use order instead
                trades_or_orders.append(order)
        base_delta = trading_constants.ZERO
        quote_delta = trading_constants.ZERO
        base, quote = commons_symbols.parse_symbol(self.symbol).base_and_quote()
        for trade_or_order in trades_or_orders:
            quantity = (
                trade_or_order.executed_quantity if (
                    isinstance(trade_or_order, trading_personal_data.Trade) and trade_or_order.executed_quantity
                ) else trade_or_order.origin_quantity
            )
            if trade_or_order.side == trading_enums.TradeOrderSide.BUY:
                base_delta += quantity
                quote_delta -= trade_or_order.total_cost
            else:
                base_delta -= quantity
                quote_delta += trade_or_order.total_cost
            if trade_or_order.fee and trade_or_order.fee.get(trading_enums.FeePropertyColumns.COST.value):
                if trade_or_order.fee[trading_enums.FeePropertyColumns.CURRENCY.value] == base:
                    base_delta -= trade_or_order.fee[trading_enums.FeePropertyColumns.COST.value]
                if trade_or_order.fee[trading_enums.FeePropertyColumns.CURRENCY.value] == quote:
                    quote_delta -= trade_or_order.fee[trading_enums.FeePropertyColumns.COST.value]
        if base_delta or quote_delta:
            # ensure updated locked values align with portfolio available funds
            # => this is especially required in case fees are not counted in scheduled orders locked amounts
            locked_base, locked_quote = self._get_locked_base_and_quote()
            updated_locked_base = min(
                trading_api.get_portfolio_currency(self.exchange_manager, base).available - (
                    get_global_locked_funds(self.exchange_manager.id, base, self.symbol)
                ),
                max(locked_base + base_delta, trading_constants.ZERO)
            )
            updated_locked_quote = min(
                trading_api.get_portfolio_currency(self.exchange_manager, quote).available - (
                    get_global_locked_funds(self.exchange_manager.id, quote, self.symbol)
                ),
                max(locked_quote + quote_delta, trading_constants.ZERO)
            )
            self._update_locked_funds(updated_locked_base, updated_locked_quote)

    def _get_next_orders(self, current_price, symbol_market):
        next_side = (
            trading_enums.TradeOrderSide.BUY
            if self._last_order_side == trading_enums.TradeOrderSide.SELL else trading_enums.TradeOrderSide.SELL
        )
        if next_orders := self._get_next_sided_orders(current_price, symbol_market, next_side):
            return next_orders
        # there might not be enough funds: try the other side
        other_side = (
            trading_enums.TradeOrderSide.BUY if next_side == trading_enums.TradeOrderSide.SELL
            else trading_enums.TradeOrderSide.SELL
        )
        self.logger.info(
            f"Not enough funds to create [{self.exchange_manager.exchange_name}] {self.symbol} scheduled orders "
            f"on {next_side.value} side, using {other_side.value} side"
        )
        if orders := self._get_next_sided_orders(current_price, symbol_market, other_side):
            return orders

        self.logger.info(
            f"Not enough funds to create [{self.exchange_manager.exchange_name}] {self.symbol} scheduled orders "
            f"on {other_side.value} side either"
        )
        return []

    def _get_next_sided_orders(self, current_price, symbol_market, side: trading_enums.TradeOrderSide):
        candidate_next_quote_quantity = decimal.Decimal(str(
            random.uniform(self.min_quote_amount, self.max_quote_amount)
        ))
        min_cost = decimal.Decimal(str(
            trading_personal_data.get_minimal_order_cost(symbol_market, default_price=float(current_price))
        ))
        # ensure order is at least min cost + 20% not to stuck funds when using minimum size orders
        potential_next_quote_quantity = max(candidate_next_quote_quantity, min_cost * _MIN_COST_ORDER_MULTIPLIER)
        available_amount = trading_api.get_portfolio_currency(
            self.exchange_manager,
            self.parsed_symbol.quote if side is trading_enums.TradeOrderSide.BUY else self.parsed_symbol.base
        ).available
        try:
            locked_base, locked_quote = self._get_locked_base_and_quote()
            if side == trading_enums.TradeOrderSide.BUY:
                # available_amount is in quote
                locked_funds_adapted_quote_quantity = min(locked_quote, potential_next_quote_quantity)
                if available_amount < locked_funds_adapted_quote_quantity:
                    self.logger.info(
                        f"Adapting {side.value} order size of {locked_funds_adapted_quote_quantity} to comply with "
                        f"{available_amount} available {self.parsed_symbol.quote} "
                        f"on {self.exchange_manager.exchange_name}"
                    )
                    next_quote_quantity = available_amount
                else:
                    next_quote_quantity = locked_funds_adapted_quote_quantity
                next_base_amount = next_quote_quantity / current_price
            else:
                # available_amount is in base
                potential_next_quote_quantity_in_base = potential_next_quote_quantity / current_price
                locked_funds_adapted_base_quantity = min(locked_base, potential_next_quote_quantity_in_base)
                if available_amount < locked_funds_adapted_base_quantity:
                    self.logger.info(
                        f"Adapting {side.value} order size of {locked_funds_adapted_base_quantity} to comply "
                        f"with {available_amount} available {self.parsed_symbol.base} "
                        f"on {self.exchange_manager.exchange_name} "
                    )
                    next_base_amount = available_amount
                else:
                    next_base_amount = locked_funds_adapted_base_quantity
        except decimal.DecimalException as err:
            raise ValueError(
                f"Impossible to get next [{self.exchange_manager.exchange_name}] {self.symbol} scheduled order "
                f"quantity: {err} ({err.__class__.__name__})"
            )
        orders_quantity_and_price = trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            next_base_amount,
            current_price,
            symbol_market
        )
        orders = [
            trading_personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=trading_enums.TraderOrderType.BUY_MARKET if side is trading_enums.TradeOrderSide.BUY
                else trading_enums.TraderOrderType.SELL_MARKET,
                symbol=self.symbol,
                current_price=current_price,
                quantity=order_quantity,
                price=order_price,
            )
            for order_quantity, order_price in orders_quantity_and_price
        ]
        return orders

    def clear(self):
        self.exchange_manager = None
        self._on_missing_funds_callback = None


def _get_locked_funds(amount: float) -> decimal.Decimal:
    return decimal.Decimal(str(amount)) * _LOCKED_FUNDS_RATIO


def _init_global_locked_funds(exchange_manager_id: str, symbol: str):
    base, quote = commons_symbols.parse_symbol(symbol).base_and_quote()
    if exchange_manager_id not in _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID:
        _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id] = {}
    _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol] = {
        base: trading_constants.ZERO,
        quote: trading_constants.ZERO,
    }


def _set_global_locked_funds(exchange_manager_id: str, symbol: str, base_funds: decimal.Decimal, quote_funds: decimal.Decimal):
    base, quote = commons_symbols.parse_symbol(symbol).base_and_quote()
    _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol][base] = base_funds
    _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol][quote] = quote_funds
    _confirm_initialized_locked_funds_by_exchange_manager_id(exchange_manager_id, symbol)


def _get_locked_base_and_quote(exchange_manager_id: str, symbol: str) -> (decimal.Decimal, decimal.Decimal):
    base, quote = commons_symbols.parse_symbol(symbol).base_and_quote()
    return (
        _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol][base],
        _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol][quote],
    )


def get_global_locked_funds(exchange_manager_id: str, coin: str, ignored_symbol: str) -> decimal.Decimal:
    try:
        return sum(
            funds[coin]
            for symbol, funds in _LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id].items()
            if symbol != ignored_symbol and coin in funds
        )
    except KeyError:
        return trading_constants.ZERO


def _register_initializing_locked_funds_by_exchange_manager_id(exchange_manager_id, symbol):
    _INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol] = asyncio.Event()


def _confirm_initialized_locked_funds_by_exchange_manager_id(exchange_manager_id, symbol):
    try:
        _INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol].set()
    except KeyError:
        _register_initializing_locked_funds_by_exchange_manager_id(exchange_manager_id, symbol)
        _INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id][symbol].set()


async def _wait_required_locked_funds_init(exchange_manager_id, symbol, timeout):
    base, quote = commons_symbols.parse_symbol(symbol).base_and_quote()
    if to_wait := [
        event
        for event_symbol, event in _INITIALIZED_LOCKED_FUNDS_BY_EXCHANGE_MANAGER_ID[exchange_manager_id].items()
        if not event.is_set()
           # wait for init of scheduled volumes related to this symbol's base or quote
           and any(coin in (base, quote) for coin in commons_symbols.parse_symbol(event_symbol).base_and_quote())
    ]:
        await asyncio.wait_for(asyncio.gather(*(event.wait() for event in to_wait)), timeout)
        return True
    return False
