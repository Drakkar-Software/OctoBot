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

import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums
import octobot_trading.errors as errors


POSITION_DICT_DECIMAL_KEYS = [
    enums.ExchangeConstantsPositionColumns.QUANTITY.value,
    enums.ExchangeConstantsPositionColumns.SIZE.value,
    enums.ExchangeConstantsPositionColumns.NOTIONAL.value,
    enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value,
    enums.ExchangeConstantsPositionColumns.COLLATERAL.value,
    enums.ExchangeConstantsPositionColumns.LEVERAGE.value,
    enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value,
    enums.ExchangeConstantsPositionColumns.MARK_PRICE.value,
    enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value,
    enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value,
    enums.ExchangeConstantsPositionColumns.REALISED_PNL.value,
    enums.ExchangeConstantsPositionColumns.MAINTENANCE_MARGIN_RATE.value,
]


def create_position_instance_from_raw(trader, raw_position):
    """
    Creates a position instance from a raw position dictionary
    :param trader: the trader instance
    :param raw_position: the raw position dictionary
    :return: the created position
    """
    position_symbol_contract = trader.exchange_manager.exchange.get_pair_future_contract(
        raw_position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value)
    )
    position = create_position_from_type(trader, position_symbol_contract)
    position.update_from_raw(raw_position)
    return position


def create_position_instance_from_dict(trader, position_dict: dict):
    """
    Creates a position instance from a raw position dictionary
    :param trader: the trader instance
    :param position_dict: the raw position dictionary as from position.to_dict
    :return: the created position
    """
    raw_position = sanitize_raw_decimals(position_dict)
    return create_position_instance_from_raw(trader, raw_position)


def sanitize_raw_position(position_dict: dict):
    position_dict[enums.ExchangeConstantsPositionColumns.STATUS.value] = (
        personal_data.parse_position_status(position_dict))
    position_dict[enums.ExchangeConstantsPositionColumns.SIDE.value] = (
        personal_data.parse_position_side(position_dict))
    position_dict[enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value] = (
        personal_data.parse_position_margin_type(position_dict))
    position_dict[enums.ExchangeConstantsPositionColumns.POSITION_MODE.value] = (
        personal_data.parse_position_mode(position_dict))
    return sanitize_raw_decimals(position_dict)


def sanitize_raw_decimals(position_dict: dict):
    for key in POSITION_DICT_DECIMAL_KEYS:
        value = position_dict.get(key)
        if value is not None and value != "":
            position_dict[key] = decimal.Decimal(str(value))
    return position_dict


def create_position_from_type(trader, symbol_contract):
    """
    Creates a position instance from a position type
    :param trader: the trader instance
    :param symbol_contract: the position symbol contract
    :return: the created position
    """
    if symbol_contract.is_handled_contract():
        return personal_data.TraderPositionTypeClasses[symbol_contract.contract_type](trader, symbol_contract)
    raise errors.UnhandledContractError(f"{symbol_contract} is not supported")


def create_symbol_position(trader, symbol):
    """
    Creates a position for a specified symbol
    :param trader: the trader instance
    :param symbol: the position symbol
    :return: the created position
    """
    return create_position_instance_from_raw(trader, {
        enums.ExchangeConstantsPositionColumns.SYMBOL.value: symbol
    })
