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

import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.constants as commons_constants
import octobot_trading.modes.script_keywords as script_keywords
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums


#todo clear
def is_current_contract_inverse(context, symbol=None, side=trading_enums.PositionSide.BOTH.value):
    return script_keywords.get_position(context, symbol=symbol, side=side).symbol_contract.is_inverse_contract()


# returns negative values when in a short position
def open_position_size(
        context,
        side=trading_enums.PositionSide.BOTH.value,
        symbol=None,
        amount_type=commons_constants.PORTFOLIO_TOTAL
):
    symbol = symbol or context.symbol
    if context.exchange_manager.is_future:
        return script_keywords.get_position(context, symbol, side).size
    currency = symbol_util.parse_symbol(context.symbol).base
    portfolio = context.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    return portfolio.get_currency_portfolio(currency).total if amount_type == commons_constants.PORTFOLIO_TOTAL \
        else portfolio.get_currency_portfolio(currency).available
    # todo handle reference market change
    # todo handle futures: its account balance from exchange
    # todo handle futures and return negative for shorts


def is_position_open(
        context,
        side=None
):
    if side is None:
        long_open = open_position_size(context, side="long") != trading_constants.ZERO
        short_open = open_position_size(context, side="short") != trading_constants.ZERO
        return True if long_open or short_open else False
    else:
        return open_position_size(context, side=side) != trading_constants.ZERO


def is_position_long(
        context,
):
    return script_keywords.get_position(context).is_long()


def is_position_short(
        context,
):
    return script_keywords.get_position(context).is_short()
