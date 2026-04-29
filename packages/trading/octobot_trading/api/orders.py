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
import decimal
import typing

import octobot_commons.logging as logging
import octobot_commons.signals as signals

import octobot_trading.personal_data as personal_data
import octobot_trading.enums
import octobot_trading.constants as constants
import octobot_trading.storage as storage

LOGGER = logging.get_logger(constants.API_LOGGER_TAG)


async def create_order(exchange_manager,
                       order_type: octobot_trading.enums.TraderOrderType,
                       symbol: str,
                       current_price: float,
                       quantity: float,
                       price: float,
                       wait_for_creation=True,
                       creation_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
                       force_if_disabled=True
    ) -> personal_data.Order:
    return await exchange_manager.trader.create_order(
        exchange_manager.trader.create_order_instance(order_type=order_type,
                                                      symbol=symbol,
                                                      current_price=current_price,
                                                      quantity=quantity,
                                                      price=price),
        wait_for_creation=wait_for_creation,
        creation_timeout=creation_timeout,
        force_if_disabled=force_if_disabled
    )


def get_open_orders(exchange_manager, symbol=None, active=None) -> list:
    return exchange_manager.exchange_personal_data.orders_manager.get_open_orders(symbol=symbol, active=active)


def get_all_orders(exchange_manager, symbol=None, active=None) -> list:
    return exchange_manager.exchange_personal_data.orders_manager.get_all_orders(symbol=symbol, active=active)


def get_pending_creation_orders(exchange_manager) -> list:
    return exchange_manager.exchange_personal_data.orders_manager.pending_creation_orders


async def cancel_all_open_orders(
    exchange_manager, emit_trading_signals=True, force_if_disabled=True
) -> tuple[bool, list]:
    return await exchange_manager.trader.cancel_all_open_orders(
        emit_trading_signals=emit_trading_signals, force_if_disabled=force_if_disabled
    )


async def cancel_all_open_orders_with_currency(
    exchange_manager, currency, emit_trading_signals=True, dependencies=None, force_if_disabled=True
) -> tuple[bool, signals.SignalDependencies]:
    return await exchange_manager.trader.cancel_all_open_orders_with_currency(
        currency, emit_trading_signals=emit_trading_signals, dependencies=dependencies, force_if_disabled=force_if_disabled
    )


async def cancel_order_with_id(
    exchange_manager, order_id, emit_trading_signals=True, wait_for_cancelling=True, dependencies=None, force_if_disabled=True
) -> tuple[bool, typing.Optional[signals.SignalDependencies]]:
    return await exchange_manager.trader.cancel_order_with_id(
        order_id, emit_trading_signals=emit_trading_signals, wait_for_cancelling=wait_for_cancelling, dependencies=dependencies, force_if_disabled=force_if_disabled
    )


def get_order_exchange_name(order) -> str:
    return order.exchange_manager.get_exchange_name()


def order_to_dict(order) -> dict:
    return order.to_dict()


def parse_order_type(dict_order) -> octobot_trading.enums.TraderOrderType:
    return personal_data.parse_order_type(dict_order)[1]


def parse_order_status(dict_order) -> octobot_trading.enums.OrderStatus:
    return personal_data.parse_order_status(dict_order)


def is_order_pending(order: personal_data.Order) -> bool:
    return order.status == octobot_trading.enums.OrderStatus.PENDING_CREATION


def get_order_profitability(exchange_manager, order_id) -> float:
    try:
        return exchange_manager.exchange_personal_data.orders_manager.get_order(order_id).get_profitability()
    except KeyError:
        # try in trades (order might be filled and stored in trades)
        return exchange_manager.exchange_personal_data.trades_manager.get_trade(order_id).trade_profitability


def get_minimal_order_cost(exchange_manager, symbol, default_price=None) -> float:
    return personal_data.get_minimal_order_cost(
        exchange_manager.exchange.get_market_status(symbol, with_fixer=False),
        default_price=default_price
    )


def get_order_trailing_profile_dict(order: personal_data.Order) -> dict:
    return storage.get_order_trailing_profile_dict(order)


def get_orders_locked_amounts_by_asset(open_orders: list[personal_data.Order]) -> dict[str, decimal.Decimal]:
    return personal_data.get_orders_locked_amounts_by_asset(open_orders)
