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
import asyncio
import decimal
import contextlib
import uuid
import typing

import octobot_commons.symbols as symbol_util
import octobot_commons.constants as commons_constants
import octobot_commons.logging as logging
import octobot_commons.timestamp_util as timestamp_util
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.personal_data.orders.decimal_order_adapter as decimal_order_adapter
import octobot_trading.exchanges.util.exchange_market_status_fixer as exchange_market_status_fixer
import octobot_trading.personal_data.orders.states.fill_order_state as fill_order_state
import octobot_trading.personal_data.orders.order as order_import
import octobot_trading.personal_data.orders.triggers.price_trigger as price_trigger
import octobot_trading.signals as signals
from octobot_trading.enums import ExchangeConstantsMarketStatusColumns as Ecmsc


LOGGER_NAME = "order_util"


def is_valid(element, key, zero_valid=False):
    """
    Checks is the element is valid with the market status fixer
    :param element:
    :param key:
    :param zero_valid: if 0 should be considered a valid value
    :return:
    """
    return key in element and exchange_market_status_fixer.is_ms_valid(element[key], zero_valid=zero_valid)


def get_min_max_amounts(symbol_market, default_value=None):
    """
    Returns the min and max quantity, cost and price according to the specified market
    :param symbol_market:
    :param default_value:
    :return:
    """
    min_quantity = max_quantity = min_cost = max_cost = min_price = max_price = default_value
    if Ecmsc.LIMITS.value in symbol_market:
        symbol_market_limits = symbol_market[Ecmsc.LIMITS.value]

        if Ecmsc.LIMITS_AMOUNT.value in symbol_market_limits:
            limit_amount = symbol_market_limits[Ecmsc.LIMITS_AMOUNT.value]
            if is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MIN.value) \
                    or is_valid(limit_amount, Ecmsc.LIMITS_AMOUNT_MAX.value):
                min_quantity = limit_amount.get(Ecmsc.LIMITS_AMOUNT_MIN.value, default_value)
                max_quantity = limit_amount.get(Ecmsc.LIMITS_AMOUNT_MAX.value, default_value)

        # case 2: use cost and price
        if Ecmsc.LIMITS_COST.value in symbol_market_limits:
            limit_cost = symbol_market_limits[Ecmsc.LIMITS_COST.value]
            if is_valid(limit_cost, Ecmsc.LIMITS_COST_MIN.value) \
                    or is_valid(limit_cost, Ecmsc.LIMITS_COST_MAX.value):
                min_cost = limit_cost.get(Ecmsc.LIMITS_COST_MIN.value, default_value)
                max_cost = limit_cost.get(Ecmsc.LIMITS_COST_MAX.value, default_value)

        # case 2: use quantity and price
        if Ecmsc.LIMITS_PRICE.value in symbol_market_limits:
            limit_price = symbol_market_limits[Ecmsc.LIMITS_PRICE.value]
            if is_valid(limit_price, Ecmsc.LIMITS_PRICE_MIN.value) \
                    or is_valid(limit_price, Ecmsc.LIMITS_PRICE_MAX.value):
                min_price = limit_price.get(Ecmsc.LIMITS_PRICE_MIN.value, default_value)
                max_price = limit_price.get(Ecmsc.LIMITS_PRICE_MAX.value, default_value)

    return min_quantity, max_quantity, min_cost, max_cost, min_price, max_price


def check_cost(total_order_price, min_cost):
    """
    Checks and adapts the quantity and price of the order to ensure it's exchange compliant:
    - are the quantity and price of the order compliant with the exchange's number of digits requirement
        => otherwise quantity will be truncated accordingly
    - is the quantity valid
    - are the order total price and quantity superior or equal to the exchange's minimum order requirement
        => otherwise order is impossible => returns empty list
    - if total cost data are unavailable:
    - is the price of the currency compliant with the exchange's price interval for this currency
        => otherwise order is impossible => returns empty list
    - are the order total price and quantity inferior or equal to the exchange's maximum order requirement
        => otherwise order is impossible as is => split order into smaller ones and returns the list
    => returns the quantity and price list of possible order(s)
    - if exchange symbol data are not enough
        => try fixing exchange data using ExchangeMarketStatusFixer are start again (once only)
    """
    if total_order_price < min_cost:
        if min_cost is None:
            logging.get_logger(LOGGER_NAME).error("Invalid min_cost from exchange")
        return False
    return True


def get_valid_split_orders(
    quantity: decimal.Decimal, prices: list[decimal.Decimal], symbol_market,
    amount_ratio_per_order: typing.Optional[list[decimal.Decimal]] = None
) -> (list[decimal.Decimal], list[decimal.Decimal]):
    if amount_ratio_per_order:
        if len(amount_ratio_per_order) != len(prices):
            raise ValueError(f"amount_ratio_per_order must have {len(prices)} elements")
        if any(amount_ratio <= constants.ZERO for amount_ratio in amount_ratio_per_order):
            raise ValueError(f"all amount_ratio_per_order must by > {constants.ZERO}")
    if len(prices) < 1:
        return [], []
    if len(prices) < 2:
        return [quantity], [prices[0]]
    min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = get_min_max_amounts(symbol_market)
    min_quantity = None if min_quantity is None else decimal.Decimal(f"{min_quantity}")
    max_quantity = None if max_quantity is None else decimal.Decimal(f"{max_quantity}")
    min_cost = None if min_cost is None else decimal.Decimal(f"{min_cost}")
    max_cost = None if max_cost is None else decimal.Decimal(f"{max_cost}")
    min_price = None if min_price is None else decimal.Decimal(f"{min_price}")
    max_price = None if max_price is None else decimal.Decimal(f"{max_price}")
    # try to split quantity evenly amount prices
    current_supported_orders_count = decimal.Decimal(str(len(prices)))
    while current_supported_orders_count > constants.ONE:
        if amount_ratio_per_order:
            used_amount_ratio_per_order = amount_ratio_per_order[:int(current_supported_orders_count)]
            total_ratios = sum(used_amount_ratio_per_order)
            candidate_volumes = [
                quantity * ratio_per_order / total_ratios
                for ratio_per_order in used_amount_ratio_per_order
            ]
        else:
            candidate_volumes = [quantity / current_supported_orders_count] * int(current_supported_orders_count)
        candidate_prices = prices[:int(current_supported_orders_count)]
        if _are_orders_too_small(min_quantity, min_cost, min_price, min(candidate_prices), min(candidate_volumes)):
            # reduce orders count to increase quantity
            current_supported_orders_count -= 1
        elif _are_orders_too_large(max_quantity, max_cost, max_price, max(candidate_prices), max(candidate_volumes)):
            raise errors.InvalidArgumentError(f"Order volume ({max(candidate_volumes)}) is too large")
        else:
            return candidate_volumes, candidate_prices
    # default to full quantity and first price
    return [quantity], [prices[0]]


def get_split_orders_count_and_increment(
    lower_price, higher_price, quantity, orders_count, symbol_market, add_increment_to_min_price
) -> (int, decimal.Decimal):
    """
    :param lower_price: smallest order price
    :param higher_price: largest order price
    :param quantity: total quantity to handle
    :param orders_count: ideal orders count
    :param symbol_market: description of the market to trade on
    :param add_increment_to_min_price: when true, uses lower_price + increment to check min values against symbol market
    :return: the exchange compatible orders count and price increment
    """
    min_quantity, max_quantity, min_cost, max_cost, min_price, max_price = get_min_max_amounts(symbol_market)
    min_quantity = None if min_quantity is None else decimal.Decimal(f"{min_quantity}")
    max_quantity = None if max_quantity is None else decimal.Decimal(f"{max_quantity}")
    min_cost = None if min_cost is None else decimal.Decimal(f"{min_cost}")
    max_cost = None if max_cost is None else decimal.Decimal(f"{max_cost}")
    min_price = None if min_price is None else decimal.Decimal(f"{min_price}")
    max_price = None if max_price is None else decimal.Decimal(f"{max_price}")

    limit_check = _ensure_orders_size(
        lower_price, higher_price, quantity, orders_count,
        min_quantity, min_cost, min_price,
        max_quantity, max_cost, max_price,
        symbol_market, add_increment_to_min_price
    )

    while limit_check > 0:
        if limit_check == 1:
            if orders_count > 1:
                orders_count -= 1
            else:
                # not enough funds to create orders
                logging.get_logger(LOGGER_NAME).warning(f"Not enough funds to create order.")
                return 0, constants.ZERO
        elif limit_check == 2:
            if orders_count < 40:
                orders_count += 1
            else:
                # too many orders to create, must be a problem
                logging.get_logger(LOGGER_NAME).error("Too many orders to create.")
                return 0, constants.ZERO
        limit_check = _ensure_orders_size(
            lower_price, higher_price, quantity, orders_count,
            min_quantity, min_cost, min_price,
            max_quantity, max_cost, max_price,
            symbol_market, add_increment_to_min_price
        )
    return orders_count, (higher_price - lower_price) / orders_count


def _ensure_orders_size(lower_price, higher_price, quantity, orders_count,
                        min_quantity, min_cost, min_price,
                        max_quantity, max_cost, max_price,
                        symbol_market, add_increment_to_min_price):
    increment = (higher_price - lower_price) / orders_count
    first_price = (lower_price + increment) if add_increment_to_min_price else lower_price
    last_price = lower_price + (increment * orders_count)
    order_vol = decimal_order_adapter.decimal_adapt_quantity(symbol_market, quantity / orders_count)

    if _are_orders_too_small(min_quantity, min_cost, min_price, first_price, order_vol):
        return 1
    elif _are_orders_too_large(max_quantity, max_cost, max_price, last_price, order_vol):
        return 2
    return 0


def _are_orders_too_small(min_quantity, min_cost, min_price, price, volume):
    return (min_price and price < min_price) or \
           (min_quantity and volume < min_quantity) or \
           (min_cost and price * volume < min_cost)


def _are_orders_too_large(max_quantity, max_cost, max_price, price, volume):
    return (max_price and price > max_price) or \
           (max_quantity and volume > max_quantity) or \
           (max_cost and price * volume > max_cost)


async def get_up_to_date_price(exchange_manager, symbol: str, timeout: int = None, base_error: str = None):
    exchange_time = exchange_manager.exchange.get_exchange_current_time()
    base_error = base_error or f"Can't get the necessary {exchange_manager.exchange_name} " \
                               f"price data to create a new {symbol} order on the " \
                               f"{timestamp_util.convert_timestamp_to_datetime(exchange_time)} " \
                               f"(timestamp: {exchange_time}):"
    try:
        mark_price = await exchange_manager.exchange_symbols_data.get_exchange_symbol_data(symbol) \
            .prices_manager.get_mark_price(timeout=timeout)
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"{base_error} mark price is not available")
    except errors.UnreachableExchange as e:
        raise errors.UnreachableExchange(f"{base_error} exchange is unreachable") from e
    return decimal.Decimal(str(mark_price))


def get_potentially_outdated_price(exchange_manager, symbol: str) -> (decimal.Decimal, bool):
    symbol_data = exchange_manager.exchange_symbols_data.get_exchange_symbol_data(
        symbol, allow_creation=False
    )
    try:
        return symbol_data.prices_manager.get_mark_price_no_wait(), True
    except ValueError:
        # outdated price, return it anyway
        return symbol_data.prices_manager.mark_price, False


async def get_pre_order_data(exchange_manager, symbol: str, timeout: int = None,
                             portfolio_type=commons_constants.PORTFOLIO_AVAILABLE,
                             target_price=None):
    price = target_price or await get_up_to_date_price(exchange_manager, symbol, timeout=timeout)
    symbol_market = exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
    currency_available, market_available, market_quantity = get_portfolio_amounts(
        exchange_manager, symbol, price, portfolio_type=portfolio_type
    )
    return currency_available, market_available, market_quantity, price, symbol_market


def get_portfolio_amounts(exchange_manager, symbol, price, portfolio_type=commons_constants.PORTFOLIO_AVAILABLE):
    currency, market = symbol_util.parse_symbol(symbol).base_and_quote()
    portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    currency_available = portfolio.get_currency_portfolio(currency).available \
        if portfolio_type == commons_constants.PORTFOLIO_AVAILABLE else portfolio.get_currency_portfolio(currency).total
    market_available = portfolio.get_currency_portfolio(market).available \
        if portfolio_type == commons_constants.PORTFOLIO_AVAILABLE else portfolio.get_currency_portfolio(market).total

    if exchange_manager.is_future:
        pair_future_contract = exchange_manager.exchange.get_pair_future_contract(symbol)
        if pair_future_contract.is_inverse_contract():
            currency_available *= pair_future_contract.current_leverage
            market_quantity = market_available = currency_available
        else:
            market_available *= pair_future_contract.current_leverage / price
            market_quantity = currency_available = market_available
    elif exchange_manager.is_margin:
        market_quantity = constants.ZERO  # TODO
    else:
        market_quantity = market_available / price if price else constants.ZERO
    return currency_available, market_available, market_quantity


def get_futures_max_order_size(exchange_manager, symbol, side, current_price, reduce_only,
                               current_symbol_holding, market_quantity):
    # use position margin when trading futures and reducing the position
    current_position = exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
        symbol,
        enums.PositionSide.BOTH
    )
    if reduce_only and current_position.is_idle():
        # can't reduce an empty position
        return constants.ZERO, False
    # ensure max position order size is taken into account
    new_position_side = current_position.side
    if new_position_side is enums.PositionSide.UNKNOWN:
        new_position_side = enums.PositionSide.LONG if side is enums.TradeOrderSide.BUY \
            else enums.PositionSide.SHORT

    contract_current_symbol_holding = current_symbol_holding
    contract_market_quantity = market_quantity
    added_quantity_from_reverse = constants.ZERO
    might_reverse_position = False
    if current_position.symbol_contract.is_inverse_contract():
        # use USD (in BTC/USD) for order sizes on inverse, convert BTC values into USD ones
        contract_current_symbol_holding = current_symbol_holding * current_price
        contract_market_quantity = market_quantity * current_price
    if side is enums.TradeOrderSide.SELL and current_position.is_long():
        # can also sell the position size in long
        contract_current_symbol_holding = current_position.size
        might_reverse_position = not reduce_only
        added_quantity_from_reverse = current_position.initial_margin
    elif side is enums.TradeOrderSide.BUY and current_position.is_short():
        # can also buy the position size in short
        contract_market_quantity = abs(current_position.size)
        might_reverse_position = not reduce_only
        added_quantity_from_reverse = current_position.initial_margin
    max_reducing_position_order_size = (
        contract_market_quantity if side is enums.TradeOrderSide.BUY else contract_current_symbol_holding
    )
    if (
        (new_position_side is enums.PositionSide.LONG and side is enums.TradeOrderSide.BUY)
        or (new_position_side is enums.PositionSide.SHORT and  side is enums.TradeOrderSide.SELL)
        or might_reverse_position
    ):
        quantity = market_quantity if current_position.symbol_contract.is_inverse_contract() \
            else market_quantity * current_price
        # include added_quantity_from_reverse in case funds get freed from reversing a position
        usable_quantity = quantity + added_quantity_from_reverse
        unleveraged_quantity = usable_quantity / current_position.symbol_contract.current_leverage
        max_position_increased_order_quantity = get_max_order_quantity_for_price(
            current_position, unleveraged_quantity, current_price, new_position_side, symbol
        )
        # apply MAX_INCREASED_POSITION_QUANTITY_MULTIPLIER in case the total order cost computation
        # is not (yet) accurate on this exchange (default is 1, meaning the calculation is accurate)
        if exchange_manager.exchange.MAX_INCREASED_POSITION_QUANTITY_MULTIPLIER != constants.ONE \
           and not exchange_manager.is_backtesting:
            max_position_increased_order_quantity *= \
                exchange_manager.exchange.MAX_INCREASED_POSITION_QUANTITY_MULTIPLIER
        # increasing position: always use the same currency
        return max_position_increased_order_quantity + (
            # include reducing position amount to process reverse
            max_reducing_position_order_size if might_reverse_position else constants.ZERO
        ), True
    return max_reducing_position_order_size, False


def get_max_order_quantity_for_price(position, available_quantity, price, side, symbol):
    """
    Returns the maximum order quantity in market or currency for given total usable funds, price and side.
    This amount is not the total usable funds as it also requires to keep the position's open order fees
    as well as the potential position liquidation fees in portfolio. Those fees are computed by
    get_two_way_taker_fee_for_quantity_and_price
    :param position: the position to compute quantity for
    :param available_quantity: the maximum amount of currency/market to allocate to the position (without leverage)
    :param price: the target entry price of the position
    :param side: the side of the position
    :param side: the symbol of the position
    :return: the computed leveraged maximum entry quantity
    """
    # use position.symbol_contract.current_leverage as quantity to simulate a 1 unit quantity (x leverage)
    two_way_fees = position.get_two_way_taker_fee_for_quantity_and_price(position.symbol_contract.current_leverage,
                                                                         price, side, symbol)
    if position.symbol_contract.is_inverse_contract():
        # Returns the maximum order quantity in market.
        return position.symbol_contract.current_leverage * available_quantity / \
            (two_way_fees + constants.ONE / price)
    # Returns the maximum order quantity in currency.
    return position.symbol_contract.current_leverage * available_quantity / \
        (two_way_fees + price)


def get_locked_funds(order):
    forecasted_fees = order.get_computed_fee(use_origin_quantity_and_price=not order.is_filled())
    if order.side == enums.TradeOrderSide.BUY:
        # locking quote to buy
        quote_fees = get_fees_for_currency(forecasted_fees, order.market)
        return order.origin_quantity * order.origin_price + quote_fees
    else:
        # locking base to sell
        base_fees = get_fees_for_currency(forecasted_fees, order.currency)
        return order.origin_quantity + base_fees


def total_fees_from_order_dict(order_dict, currency):
    return get_fees_for_currency(order_dict[enums.ExchangeConstantsOrderColumns.FEE.value], currency)


def get_fees_for_currency(fee, currency):
    if fee and fee[enums.FeePropertyColumns.CURRENCY.value] == currency:
        return decimal.Decimal(str(fee[enums.FeePropertyColumns.COST.value]))
    return constants.ZERO


def get_order_locked_amount(order: order_import.Order, force_use_origin_quantity_and_price=False) -> decimal.Decimal:
    # take fees into account when in locked asset
    # ( a BTC/USDT order with USDT fees need to lock USDT fees to be able to pay them)
    use_origin_quantity_and_price = force_use_origin_quantity_and_price or not order.is_filled()
    forecasted_fees = order.get_computed_fee(use_origin_quantity_and_price=use_origin_quantity_and_price)
    base, quote = symbol_util.parse_symbol(order.symbol).base_and_quote()
    # use remaining quantity when order is open or partially filled
    locked_amount = order.get_locked_quantity()
    # when buy order
    if order.side == enums.TradeOrderSide.BUY:
        return locked_amount * order.origin_price + get_fees_for_currency(forecasted_fees, quote)
    # when sell order
    return locked_amount + get_fees_for_currency(forecasted_fees, base)


def get_orders_locked_amounts_by_asset(open_orders: list[order_import.Order]) -> dict[str, decimal.Decimal]:
    if not open_orders:
        return {}
    locked_funds_by_asset = {}
    for order in open_orders:
        if not order.is_active:
            # don't count inactive orders in locked funds
            continue
        base, quote = symbol_util.parse_symbol(order.symbol).base_and_quote()
        # use get_order_locked_amount just like trader simulator to ensure locked funds integrity
        if order.side == enums.TradeOrderSide.BUY:
            # buy orders only lock fees in quote
            locked_quote = get_order_locked_amount(order)
            if quote not in locked_funds_by_asset:
                locked_funds_by_asset[quote] = locked_quote
            else:
                locked_funds_by_asset[quote] += locked_quote
        else:
            # sell orders only lock fees in base
            locked_base = get_order_locked_amount(order)
            if base not in locked_funds_by_asset:
                locked_funds_by_asset[base] = locked_base
            else:
                locked_funds_by_asset[base] += locked_base
    return locked_funds_by_asset


def parse_raw_fees(raw_fees):
    fees = raw_fees
    if fees:
        # parsed fees should be from exchange by default
        fees[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] = \
            fees.get(enums.FeePropertyColumns.IS_FROM_EXCHANGE.value, True)
        if enums.FeePropertyColumns.COST.value in fees:
            try:
                raw_fees[enums.FeePropertyColumns.COST.value] = \
                    decimal.Decimal(str(raw_fees[enums.FeePropertyColumns.COST.value]))
            except decimal.InvalidOperation:
                # Ensure fee cost can be used in computations. The original value is kept
                # under the EXCHANGE_ORIGINAL_COST key if relevant
                raw_fees[enums.FeePropertyColumns.COST.value] = constants.ZERO
    return fees


def parse_order_status(raw_order):
    try:
        return enums.OrderStatus(raw_order[enums.ExchangeConstantsOrderColumns.STATUS.value])
    except KeyError:
        return enums.OrderStatus.UNKNOWN
    except ValueError:
        if raw_order[enums.ExchangeConstantsOrderColumns.STATUS.value] == "cancelled":
            # few exchanges use "cancelled" which is not in enums.ExchangeConstantsOrderColumns.STATUS
            raw_order[enums.ExchangeConstantsOrderColumns.STATUS.value] = enums.OrderStatus.CANCELED.value
            return enums.OrderStatus.CANCELED
        raise


def parse_is_cancelled(raw_order):
    return parse_order_status(raw_order) in {enums.OrderStatus.CANCELED, enums.OrderStatus.CLOSED}


def parse_is_pending_cancel(raw_order):
    return parse_order_status(raw_order) is enums.OrderStatus.PENDING_CANCEL


def parse_is_open(raw_order):
    return parse_order_status(raw_order) is enums.OrderStatus.OPEN


def get_pnl_transaction_source_from_order(order):
    if order.order_type in [enums.TraderOrderType.SELL_MARKET, enums.TraderOrderType.BUY_MARKET,
                            enums.TraderOrderType.TAKE_PROFIT]:
        return enums.PNLTransactionSource.MARKET_ORDER
    if order.order_type in [enums.TraderOrderType.SELL_LIMIT, enums.TraderOrderType.BUY_LIMIT,
                            enums.TraderOrderType.TAKE_PROFIT_LIMIT]:
        return enums.PNLTransactionSource.LIMIT_ORDER
    if is_stop_order(order.order_type):
        return enums.PNLTransactionSource.STOP_ORDER
    return enums.PNLTransactionSource.UNKNOWN


def is_stop_order(order_type: enums.TraderOrderType):
    return order_type in [
        enums.TraderOrderType.STOP_LOSS, enums.TraderOrderType.STOP_LOSS_LIMIT,
        enums.TraderOrderType.TRAILING_STOP, enums.TraderOrderType.TRAILING_STOP_LIMIT,
    ]


def is_stop_trade_order_type(order_type: enums.TradeOrderType):
    return order_type in [
        enums.TradeOrderType.STOP_LOSS, enums.TradeOrderType.STOP_LOSS_LIMIT,
        enums.TradeOrderType.TRAILING_STOP, enums.TradeOrderType.TRAILING_STOP_LIMIT,
    ]


def is_take_profit_order(order_type: enums.TraderOrderType):
    return order_type in [
        enums.TraderOrderType.TAKE_PROFIT, enums.TraderOrderType.TAKE_PROFIT_LIMIT,
    ]


def ensure_orders_limit(exchange_manager, symbol, added_orders: list[enums.TraderOrderType]):
    max_limit_orders = exchange_manager.exchange.get_max_orders_count(symbol, enums.TraderOrderType.SELL_LIMIT)
    max_stop_orders = exchange_manager.exchange.get_max_orders_count(symbol, enums.TraderOrderType.STOP_LOSS)
    open_orders = exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
        symbol=symbol, active=None  # consider both active and inactive orders of this symbol
    )
    stop_orders_count = len([o for o in open_orders if is_stop_order(o.order_type)]) + len(
        [o_type for o_type in added_orders if is_stop_order(o_type)]
    )
    limit_orders_count = len(open_orders) + len(added_orders) - stop_orders_count
    if limit_orders_count > max_limit_orders:
        raise errors.MaxOpenOrderReachedForSymbolError(
            f"{symbol} max open limit orders reached: "
            f"limit = {max_limit_orders}, orders count = {limit_orders_count}"
        )
    if stop_orders_count > max_stop_orders:
        raise errors.MaxOpenOrderReachedForSymbolError(
            f"{symbol} max open stop orders reached: "
            f"limit = {max_stop_orders}, orders count = {stop_orders_count}"
        )


def get_trade_order_type(order_type: enums.TraderOrderType) -> enums.TradeOrderType:
    if order_type in (enums.TraderOrderType.BUY_MARKET, enums.TraderOrderType.SELL_MARKET):
        return enums.TradeOrderType.MARKET
    if order_type in (enums.TraderOrderType.BUY_LIMIT, enums.TraderOrderType.SELL_LIMIT):
        return enums.TradeOrderType.LIMIT
    if order_type is enums.TraderOrderType.STOP_LOSS:
        return enums.TradeOrderType.STOP_LOSS
    if order_type is enums.TraderOrderType.TRAILING_STOP:
        return enums.TradeOrderType.TRAILING_STOP
    if order_type is enums.TraderOrderType.STOP_LOSS_LIMIT:
        return enums.TradeOrderType.STOP_LOSS_LIMIT
    if order_type is enums.TraderOrderType.TRAILING_STOP_LIMIT:
        return enums.TradeOrderType.TRAILING_STOP_LIMIT
    if order_type is enums.TraderOrderType.TAKE_PROFIT:
        return enums.TradeOrderType.TAKE_PROFIT
    if order_type is enums.TraderOrderType.TAKE_PROFIT_LIMIT:
        return enums.TradeOrderType.TAKE_PROFIT_LIMIT
    raise ValueError(order_type)


def create_order_price_trigger(
    order: order_import.Order, active_trigger_price: decimal.Decimal, active_trigger_above: bool
) -> price_trigger.PriceTrigger:
    if active_trigger_price is None or active_trigger_above is None:
        raise ValueError("active_trigger_price and active_trigger_above must be specified")
    return price_trigger.PriceTrigger(
        order.on_active_trigger, (None, None), active_trigger_price, active_trigger_above
    )


async def create_as_active_order_using_strategy_if_any(
    order, strategy_timeout: typing.Optional[float], wait_for_fill_callback: typing.Optional[typing.Callable]
):
    if active_swap_strategy := order.order_group.active_order_swap_strategy if order.order_group else None:
        # use strategy to process swap
        await active_swap_strategy.execute(order, wait_for_fill_callback, strategy_timeout)
    else:
        # no strategy: just create this order as active
        await create_as_active_order_on_exchange(order, False)


async def create_as_active_order_on_exchange(order_to_create, emit_trading_signals: bool):
    async with signals.remote_signal_publisher(
        order_to_create.trader.exchange_manager, order_to_create.symbol, emit_trading_signals
    ):
        active_order = await signals.update_order_as_active(
            order_to_create.trader.exchange_manager,
            signals.should_emit_trading_signal(order_to_create.trader.exchange_manager),
            order_to_create,
            params=order_to_create.exchange_creation_params
        )
        if active_order is None:
            logging.get_logger(order_to_create.get_logger_name()).error(
                f"Failed to create active order for {order_to_create}"
            )
        return active_order


async def update_order_as_inactive_on_exchange(order_to_cancel, emit_trading_signals: bool):
    async with signals.remote_signal_publisher(
        order_to_cancel.trader.exchange_manager, order_to_cancel.symbol, emit_trading_signals
    ):
        if not await signals.update_order_as_inactive(
            order_to_cancel.trader.exchange_manager,
            signals.should_emit_trading_signal(order_to_cancel.trader.exchange_manager),
            order_to_cancel,
        ):
            logging.get_logger(order_to_cancel.get_logger_name()).error(f"Failed to cancel active order on exchange: {order_to_cancel}")
            return False
    return True


async def create_as_chained_order(order):
    order.is_waiting_for_chained_trigger = False
    if not order.trader.simulate and order.has_been_bundled:
        # exchange should have created it already, it is either already fetched or
        # will automatically be fetched at the next update
        # warning: not handling instantly filled bundled orders as there is no easy way to do this
        # TODO: figure out instantly filled bundled orders
        if not await _apply_pending_order_on_existing_orders(order):
            # register it as pending creation order for it to be found and update when fetched
            order.exchange_manager.exchange_personal_data.orders_manager.register_pending_creation_order(order)
    else:
        # set created now to consider creation failures as created as well (the caller can always retry later on)
        order.status = enums.OrderStatus.OPEN
        # set uninitialized to allow second initialization from create_order
        order.is_initialized = False
        order.creation_time = order.exchange_manager.exchange.get_exchange_current_time()
        try:
            await order.trader.create_order(
                order,
                loaded=False,
                params=order.exchange_creation_params,
                raise_all_creation_error=True,
                **order.trader_creation_kwargs
            )
        except (errors.ExchangeClosedPositionError, errors.ExchangeOrderInstantTriggerError):
            # Order can be created and might be outdated forward error for the caller to fix it if possible
            raise
        except Exception as err:
            # log warning to be sure to keep track of the failed order details
            logging.get_logger(LOGGER_NAME).warning(
                f"Failed to create chained order {order.to_dict()}: {err} ({err.__class__.__name__})"
            )
            # propagate
            raise


def is_associated_pending_order(pending_order, created_order):
    return created_order.exchange_order_id == pending_order.exchange_order_id or (
        created_order.symbol == pending_order.symbol and
        created_order.origin_quantity == pending_order.origin_quantity and
        created_order.origin_price == pending_order.origin_price and
        created_order.__class__ is pending_order.__class__ and
        created_order.trader is pending_order.trader
    )


async def apply_pending_order_from_created_order(pending_order, created_order, to_be_initialized):
    await pending_order.update_from_order(created_order)
    if to_be_initialized:
        pending_order.is_initialized = False
    logging.get_logger(LOGGER_NAME).debug(f"Updated pending order: {pending_order} using {created_order}")


async def _apply_pending_order_on_existing_orders(pending_order):
    for created_order in pending_order.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
        symbol=pending_order.symbol
    ):
        if is_associated_pending_order(pending_order, created_order) and created_order.order_group is None:
            await apply_pending_order_from_created_order(pending_order, created_order, False)
            pending_order.exchange_manager.exchange_personal_data.orders_manager.replace_order(
                created_order.order_id, pending_order
            )
            created_order.clear()
            return True
    return False


@contextlib.asynccontextmanager
async def ensure_orders_relevancy(order=None, position=None, enable_associated_orders_creation=True):
    exchange_manager = order.exchange_manager if position is None else position.exchange_manager
    # part used in futures trading only
    if exchange_manager.exchange_personal_data.positions_manager.positions:
        position = position or exchange_manager.exchange_personal_data.positions_manager.get_order_position(order)
        pre_update_position_side = position.side
        is_pre_update_position_idle = position.is_idle()
        yield
        if not is_pre_update_position_idle and \
           (position.side != pre_update_position_side or position.is_idle()):
            # when position side is changing (from a non-idle position) or is going back to idle,
            # then associated reduce only orders must be closed
            await _cancel_reduce_only_orders_on_position_reset(
                exchange_manager, position.symbol, enable_associated_orders_creation
            )
    else:
        # as a context manager, yield is mandatory
        yield


async def _cancel_reduce_only_orders_on_position_reset(exchange_manager, symbol, enable_associated_orders_creation):
    for order in list(exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol)):
        # reduce only order are automatically cancelled on exchanges, only cancel simulated orders
        if (exchange_manager.is_trader_simulated or order.is_self_managed()) \
                and order.is_open() and order.reduce_only:
            try:
                await order.trader.cancel_order(order)
                if order.order_group and enable_associated_orders_creation:
                    await order.order_group.on_cancel(order)
            except (    # pylint: disable=try-except-raise
                errors.OrderCancelError, errors.UnexpectedExchangeSideOrderStateError
            ):
                # should never happen as those should be simulated orders
                raise


def get_order_quantity_currency(exchange_manager, symbol):
    try:
        parsed_symbol = symbol_util.parse_symbol(symbol)
        base, quote = parsed_symbol.base_and_quote()
    except ValueError:
        # symbol that can't be split
        return None
    if exchange_manager.is_future:
        return quote if parsed_symbol.is_inverse() else base
    # always base in spot
    return base


async def get_order_size_portfolio_percent(exchange_manager, order_amount, side, symbol):
    current_symbol_holding, current_market_holding, market_quantity, _, _ = \
        await get_pre_order_data(exchange_manager,
                                 symbol=symbol,
                                 timeout=constants.ORDER_DATA_FETCHING_TIMEOUT,
                                 portfolio_type=commons_constants.PORTFOLIO_TOTAL)
    if exchange_manager.is_future:
        # TODO check inverse
        if market_quantity == constants.ZERO:
            return constants.ZERO
        return min(order_amount / market_quantity, constants.ONE) * constants.ONE_HUNDRED
    if side is enums.TradeOrderSide.SELL:
        if current_symbol_holding == constants.ZERO:
            return constants.ZERO
        return min(order_amount / current_symbol_holding, constants.ONE) * constants.ONE_HUNDRED
    if side is enums.TradeOrderSide.BUY:
        if current_market_holding == constants.ZERO:
            return constants.ZERO
        return min(order_amount / market_quantity, constants.ONE) * constants.ONE_HUNDRED
    raise errors.InvalidArgumentError(f"Unhandled side: {side}")


def generate_order_id():
    return str(uuid.uuid4())


def _get_possible_filled_price(
    exchange_manager, symbol: str, side: enums.TradeOrderSide, ideal_price: decimal.Decimal
) -> decimal.Decimal:
    try:
        min_price, max_price = exchange_manager.exchange_symbols_data.get_exchange_symbol_data(symbol).\
            price_events_manager.get_min_and_max_prices()
        if side is enums.TradeOrderSide.SELL:
            if ideal_price < min_price:
                return min_price
        if side is enums.TradeOrderSide.BUY:
            if ideal_price > max_price:
                return max_price
    except IndexError:
        # no available price data
        pass
    return ideal_price


def get_valid_filled_price(order, ideal_price: decimal.Decimal):
    # ensure filled price based on ideal_price makes sense according to the current candle
    # instead of blindly using ideal_price as this could
    # potentially buy higher than the candle high or sell lower than the candle low,
    # which can't happen on real conditions

    if order.exchange_manager.is_backtesting:
        # in backtesting: ensure ideal_price is with in current candle price.
        return _get_possible_filled_price(order.exchange_manager, order.symbol, order.side, ideal_price)
    # not in backtesting: price desync can't happen
    return ideal_price


async def adapt_chained_order_before_creation(base_order, chained_order):
    can_be_created = True
    if chained_order.update_with_triggering_order_fees:
        can_be_created = chained_order.update_quantity_with_order_fees(base_order)
    # ensure price is not outdated
    await chained_order.update_price_if_outdated()
    return can_be_created


async def wait_for_order_fill(order, timeout, wait_for_portfolio_update):
    if order.is_open():
        if order.state is None:
            logging.get_logger(LOGGER_NAME).error(
                f"None state on created order, impossible to wait for fill, order: {order}"
            )
        else:
            try:
                await order.state.wait_for_next_state(timeout)
            except asyncio.TimeoutError:
                logging.get_logger(LOGGER_NAME).error(
                    f"Timeout while waiting for {order.order_type.value} open order fill, order {order}"
                )
            if wait_for_portfolio_update and isinstance(order.state, fill_order_state.FillOrderState):
                # portfolio is updated in FillOrderState: wait for this state to complete
                try:
                    await order.state.wait_for_next_state(timeout)
                except asyncio.TimeoutError:
                    logging.get_logger(LOGGER_NAME).error(
                        f"Timeout while waiting for {order.order_type.value} filled order state to "
                        f"complete, order {order}"
                    )
    if order.is_open():
        logging.get_logger(LOGGER_NAME).error(f"Unexpected: order is still open, order {order}")
    else:
        logging.get_logger(LOGGER_NAME).info(f"Successfully filled order: {order}.")
