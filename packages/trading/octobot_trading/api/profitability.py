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

import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.util as util


def get_profitability_stats(exchange_manager) -> tuple:
    port_profit = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_profitability
    return port_profit.profitability, \
        port_profit.profitability_percent, \
        port_profit.profitability_diff, \
        port_profit.market_profitability_percent, \
        port_profit.initial_portfolio_current_profitability


def get_origin_portfolio_value(exchange_manager) -> float:
    return exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_origin_value


def get_current_portfolio_value(exchange_manager) -> float:
    return exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value


def get_current_crypto_currency_value(exchange_manager, currency) -> decimal.Decimal:
    try:
        return exchange_manager.exchange_personal_data.portfolio_manager. \
            portfolio_value_holder.current_crypto_currencies_values[currency]
    except KeyError:
        try:
            # try using last prices by trading pair
            return exchange_manager.exchange_personal_data.portfolio_manager. \
                portfolio_value_holder.value_converter.convert_currency_value_using_last_prices(
                    constants.ONE,
                    currency,
                    exchange_manager.exchange_personal_data.portfolio_manager.reference_market
                )
        except errors.MissingPriceDataError as err:
            raise KeyError from err


def get_currency_ref_market_value(exchange_manager, currency):
    try:
        return exchange_manager.exchange_personal_data.portfolio_manager. \
            portfolio_value_holder.value_converter.evaluate_value(currency, constants.ONE) or None
    except errors.MissingPriceDataError:
        return None


def get_current_holdings_values(exchange_manager) -> dict:
    return exchange_manager.exchange_personal_data.portfolio_manager.\
        portfolio_value_holder.get_current_holdings_values()


def get_reference_market(config) -> str:
    return util.get_reference_market(config)


def get_initializing_currencies_prices(exchange_manager) -> set:
    return set() if exchange_manager.exchange_personal_data.portfolio_manager is None else \
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.initializing_symbol_prices
