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
import decimal

import octobot_commons.constants as constants

import octobot_services.interfaces as interfaces
import octobot_trading
import octobot_trading.api as trading_api


def _merge_portfolio_values(portfolio1, portfolio2):
    for key, value in portfolio2.items():
        if key in portfolio1:
            portfolio1[key] += value
        else:
            portfolio1[key] = value
    return portfolio1


def get_portfolio_holdings():
    real_currency_portfolio = {}
    simulated_currency_portfolio = {}

    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):

            trader_currencies_values = trading_api.get_current_holdings_values(exchange_manager)
            if trading_api.is_trader_simulated(exchange_manager):
                _merge_portfolio_values(simulated_currency_portfolio, trader_currencies_values)
            else:
                _merge_portfolio_values(real_currency_portfolio, trader_currencies_values)
    return real_currency_portfolio, simulated_currency_portfolio


def get_portfolio_current_value():
    simulated_value = 0
    real_value = 0
    has_real_trader = False
    has_simulated_trader = False

    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):

            current_value = trading_api.get_current_portfolio_value(exchange_manager)

            # current_value might be 0 if no trades have been made / canceled => use origin value
            if current_value == 0:
                current_value = trading_api.get_origin_portfolio_value(exchange_manager)

            if trading_api.is_trader_simulated(exchange_manager):
                simulated_value += current_value
                has_simulated_trader = True
            else:
                real_value += current_value
                has_real_trader = True

    return has_real_trader, has_simulated_trader, real_value, simulated_value


def _get_portfolios():
    simulated_portfolios = []
    real_portfolios = []

    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            if trading_api.is_trader_simulated(exchange_manager):
                simulated_portfolios.append(trading_api.get_portfolio(exchange_manager))
            else:
                real_portfolios.append(trading_api.get_portfolio(exchange_manager))
    return real_portfolios, simulated_portfolios


def _merge_portfolios(base_portfolio, to_merge_portfolio):
    for currency, asset in to_merge_portfolio.items():
        if currency not in base_portfolio:
            base_portfolio[currency] = {
                constants.PORTFOLIO_AVAILABLE: decimal.Decimal(0),
                constants.PORTFOLIO_TOTAL: decimal.Decimal(0)
            }

        base_portfolio[currency][constants.PORTFOLIO_AVAILABLE] += asset.available
        base_portfolio[currency][constants.PORTFOLIO_TOTAL] += asset.total


def get_global_portfolio_currencies_amounts():
    real_portfolios, simulated_portfolios = _get_portfolios()
    real_global_portfolio = {}
    simulated_global_portfolio = {}

    for portfolio in simulated_portfolios:
        _merge_portfolios(simulated_global_portfolio, portfolio)

    for portfolio in real_portfolios:
        _merge_portfolios(real_global_portfolio, portfolio)

    return real_global_portfolio, simulated_global_portfolio


def get_global_portfolio_currencies_values() -> dict:
    return trading_api.get_global_portfolio_currencies_values(
        interfaces.get_exchange_managers()
        )
                

def trigger_portfolios_refresh():
    return interfaces.run_in_bot_main_loop(async_trigger_portfolios_refresh())


async def async_trigger_portfolios_refresh():
    at_least_one = False
    for exchange_manager in interfaces.get_exchange_managers():
        if trading_api.is_trader_existing_and_enabled(exchange_manager):
            at_least_one = True
            await trading_api.refresh_real_trader_portfolio(exchange_manager)

    if not at_least_one:
        raise RuntimeError("no real trader to update.")
