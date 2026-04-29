#  Drakkar-Software OctoBot-Tentacles
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
import octobot_backtesting.api as backtesting_api


def set_backtesting_iteration_timeout(ctx, iteration_timeout_in_seconds: int):
    if ctx.exchange_manager.is_backtesting:
        backtesting_api.set_iteration_timeout(
            ctx.exchange_manager.exchange.backtesting,
            iteration_timeout_in_seconds
        )


def register_backtesting_timestamp_whitelist(ctx, timestamps, check_callback=None, append_to_whitelist=True):
    if check_callback is None:
        def _open_order_and_position_check():
            # by default, avoid skipping timestamps when there are open orders or active positions
            if ctx.exchange_manager.exchange_personal_data.orders_manager.get_open_orders():
                return True
            for position in ctx.exchange_manager.exchange_personal_data.positions_manager.positions.values():
                if not position.is_idle():
                    return True
            return False

        check_callback = _open_order_and_position_check
    if ctx.exchange_manager.is_backtesting and \
            backtesting_api.get_backtesting_timestamp_whitelist(ctx.exchange_manager.exchange.backtesting) \
            != sorted(set(timestamps)):
        return backtesting_api.register_backtesting_timestamp_whitelist(
            ctx.exchange_manager.exchange.backtesting,
            timestamps,
            check_callback,
            append_to_whitelist=append_to_whitelist
        )


def is_registered_backtesting_timestamp_whitelist(ctx):
    return ctx.exchange_manager.is_backtesting and \
            backtesting_api.get_backtesting_timestamp_whitelist(ctx.exchange_manager.exchange.backtesting) is not None
