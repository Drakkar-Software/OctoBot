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
import contextlib
import typing

import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.personal_data.orders as orders
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.signals.trading_signal_bundle_builder as trading_signal_bundle_builder
import octobot_trading.signals.util as signals_util

import octobot_commons.logging as logging
import octobot_commons.signals as signals
import octobot_commons.errors as commons_errors
import octobot_commons.authentication as authentication


@contextlib.asynccontextmanager
async def remote_signal_publisher(exchange_manager, symbol: str, emit_trading_signals: bool):
    try:
        if emit_trading_signals:
            try:
                trading_mode = exchange_manager.trading_modes[0]
            except IndexError:
                yield None
                return
            try:
                async with signals.SignalPublisher.instance().remote_signal_bundle_builder(
                    symbol,
                    trading_mode.get_trading_signal_identifier(),
                    trading_mode.TRADING_SIGNAL_TIMEOUT,
                    trading_signal_bundle_builder.TradingSignalBundleBuilder,
                    (trading_mode.get_name(),)
                ) as signal_builder:
                    yield signal_builder
            except (authentication.AuthenticationRequired, authentication.UnavailableError) as e:
                logging.get_logger(__name__).exception(e, True, f"Failed to send trading signals: {e}")
        else:
            yield None
    except commons_errors.MissingSignalBuilder as e:
        logging.get_logger(__name__).exception(e, True, f"Error when sending trading signal: no signal builder {e}")


def should_emit_trading_signal(exchange_manager):
    try:
        return exchange_manager.trading_modes[0].should_emit_trading_signal()
    except IndexError:
        return False


async def _get_order_portfolio_percent(order, exchange_manager):
    percent = await orders.get_order_size_portfolio_percent(
        exchange_manager,
        order.origin_quantity,
        order.side,
        order.symbol
    )
    return f"{float(percent)}{script_keywords.QuantityType.PERCENT.value}"


async def create_order(
    exchange_manager, should_emit_signal, order,
    loaded: bool = False, params: dict = None,
    wait_for_creation=True,
    creation_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
    dependencies: typing.Optional[signals.SignalDependencies] = None,
    force_if_disabled=False
):
    order_pf_percent = f"0{script_keywords.QuantityType.PERCENT.value}"
    chained_orders_pf_percent = []
    if should_emit_signal:
        order_pf_percent = await _get_order_portfolio_percent(order, exchange_manager)
        chained_orders_pf_percent = [
            (chained_order, await _get_order_portfolio_percent(chained_order, exchange_manager))
            for chained_order in order.chained_orders
        ]
    created_order = await exchange_manager.trader.create_order(
        order, loaded=loaded, params=params,
        wait_for_creation=wait_for_creation, creation_timeout=creation_timeout,
        force_if_disabled=force_if_disabled
    )
    if created_order is not None and should_emit_signal:
        builder = signals.SignalPublisher.instance().get_signal_bundle_builder(created_order.symbol)
        builder.add_created_order(
            created_order, exchange_manager, target_amount=order_pf_percent, dependencies=dependencies
        )
        for chained_order, chained_order_pf_percent in chained_orders_pf_percent:
            builder.add_created_order(
                chained_order, exchange_manager, target_amount=chained_order_pf_percent, dependencies=dependencies
            )

    return created_order


async def update_order_as_inactive(
    exchange_manager, should_emit_signal, order, ignored_order: object = None, wait_for_cancelling=True,
    cancelling_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT, dependencies: typing.Optional[signals.SignalDependencies] = None
) -> bool:
    cancelled = await exchange_manager.trader.update_order_as_inactive(
        order, ignored_order=ignored_order,
        wait_for_cancelling=wait_for_cancelling,
        cancelling_timeout=cancelling_timeout,
    )
    if should_emit_signal:
        # implement relevant signals if necessary (different from regular cancel signal)
        logging.get_logger(__name__).error("update_order_as_inactive signals emission is not implemented.")
    return cancelled


async def update_order_as_active(
    exchange_manager, should_emit_signal, order, params: dict = None, wait_for_creation=True,
    creation_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT, dependencies: typing.Optional[signals.SignalDependencies] = None
) -> bool:
    created_order = await exchange_manager.trader.update_order_as_active(
        order, params=params, wait_for_creation=wait_for_creation, creation_timeout=creation_timeout
    )
    if should_emit_signal:
        # implement relevant signals if necessary (different from regular create signal)
        logging.get_logger(__name__).error("update_order_as_active signals emission is not implemented.")
    return created_order


async def cancel_order(
    exchange_manager, should_emit_signal, order, ignored_order: object = None,
    wait_for_cancelling=True, cancelling_timeout=constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT, dependencies: typing.Optional[signals.SignalDependencies] = None, force_if_disabled=False
) -> tuple[bool, signals.SignalDependencies]:
    cancelled = await exchange_manager.trader.cancel_order(
        order, ignored_order=ignored_order,
        wait_for_cancelling=wait_for_cancelling,
        cancelling_timeout=cancelling_timeout,
        force_if_disabled=force_if_disabled
    )
    if should_emit_signal and cancelled:
        signals.SignalPublisher.instance().get_signal_bundle_builder(order.symbol).add_cancelled_order(
            order, exchange_manager, dependencies=dependencies
        )
    return cancelled, signals_util.get_order_dependency(order)


async def edit_order(
    exchange_manager,
    should_emit_signal,
    order,
    edited_quantity: decimal.Decimal = None,
    edited_price: decimal.Decimal = None,
    edited_stop_price: decimal.Decimal = None,
    edited_current_price: decimal.Decimal = None,
    params: dict = None,
    dependencies: typing.Optional[signals.SignalDependencies] = None
) -> bool:
    changed = await exchange_manager.trader.edit_order(
        order,
        edited_quantity=edited_quantity,
        edited_price=edited_price,
        edited_stop_price=edited_stop_price,
        edited_current_price=edited_current_price,
        params=params
    )
    if should_emit_signal and changed:
        signals.SignalPublisher.instance().get_signal_bundle_builder(order.symbol).add_edited_order(
            order,
            exchange_manager,
            updated_target_amount=edited_quantity,
            updated_limit_price=edited_price,
            updated_stop_price=edited_stop_price,
            updated_current_price=edited_current_price,
            dependencies=dependencies
        )
    return changed


async def set_leverage(
    exchange_manager, should_emit_signal, symbol: str, side: typing.Optional[enums.PositionSide],
    leverage: decimal.Decimal, dependencies: typing.Optional[signals.SignalDependencies] = None
) -> bool:
    changed = await exchange_manager.trader.set_leverage(symbol, side, leverage)
    if should_emit_signal and changed:
        signals.SignalPublisher.instance().get_signal_bundle_builder(symbol).add_leverage_update(
            symbol, side, leverage, exchange_manager, dependencies=dependencies
        )
    return changed
