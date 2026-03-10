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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_trading.constants as constants
import octobot_trading.enums as enums
import octobot_trading.util.test_tools.exchange_data as exchange_data_import


def _get_positions_symbols(exchange_data: exchange_data_import.ExchangeData) -> set[str]:
    return set(get_positions_by_symbol(exchange_data))


def _get_orders_symbols(exchange_data: exchange_data_import.ExchangeData) -> set[str]:
    return set(
        order[constants.STORAGE_ORIGIN_VALUE][enums.ExchangeConstantsOrderColumns.SYMBOL.value]
        for order in exchange_data.orders_details.open_orders + exchange_data.orders_details.missing_orders
        if order.get(constants.STORAGE_ORIGIN_VALUE, {}).get(
            enums.ExchangeConstantsOrderColumns.SYMBOL.value
        )
    )


def get_orders_and_positions_symbols(exchange_data: exchange_data_import.ExchangeData) -> set[str]:
    return _get_orders_symbols(exchange_data).union(_get_positions_symbols(exchange_data))


def get_positions_by_symbol(exchange_data: exchange_data_import.ExchangeData) -> dict[str, list[dict]]:
    return {
        position_details.position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]:
            [
                symbol_position_details.position
                for symbol_position_details in exchange_data.positions
                if symbol_position_details.position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value) ==
                   position_details.position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]
            ]
        for position_details in exchange_data.positions
        if enums.ExchangeConstantsPositionColumns.SYMBOL.value in position_details.position
    }
