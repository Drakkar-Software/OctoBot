#  Drakkar-Software OctoBot-Services
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
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums

import octobot_services.interfaces as interfaces


def get_all_positions():
    simulated_positions = []
    real_positions = []

    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            if trading_api.is_trader_simulated(exchange_manager):
                simulated_positions += trading_api.get_positions(exchange_manager)
            else:
                real_positions += trading_api.get_positions(exchange_manager)

    return real_positions, simulated_positions


def close_positions(positions_descs):
    return interfaces.run_in_bot_main_loop(async_close_positions(positions_descs))


async def async_close_positions(positions_descs):
    removed_count = 0
    if positions_descs:
        for positions_desc in positions_descs:
            for exchange_manager in interfaces.get_exchange_managers():
                if trading_api.is_trader_existing_and_enabled(exchange_manager):
                    removed_count += 1 if (
                        await trading_api.close_position(
                            exchange_manager,
                            positions_desc["symbol"],
                            trading_enums.PositionSide(positions_desc["side"]),
                        )
                    ) else 0
    return removed_count
