#  Drakkar-Software OctoBot
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

from interfaces import get_bot
from trading.trader.portfolio import Portfolio
from tools.timestamp_util import convert_timestamps_to_datetime


def get_traders(bot=None):
    if bot is None:
        bot = get_bot()
    return [trader for trader in bot.get_exchange_traders().values()] + \
           [trader for trader in bot.get_exchange_trader_simulators().values()]


def _merge_portfolio_in_first(portfolio1, portfolio2):
    for key, value in portfolio2.items():
        if key in portfolio1:
            portfolio1[key] += portfolio2[key]
        else:
            portfolio1[key] = portfolio2[key]
    return portfolio1


def get_portfolio_holdings():
    traders = get_traders()
    real_currency_portfolio = {}
    simulated_currency_portfolio = {}

    for trader in traders:
        if trader.is_enabled():
            trade_manager = trader.get_trades_manager()

            trader_currencies_values = get_bot().run_in_main_asyncio_loop(trade_manager.get_current_holdings_values())

            if trader.get_simulate():
                _merge_portfolio_in_first(simulated_currency_portfolio, trader_currencies_values)
            else:
                _merge_portfolio_in_first(real_currency_portfolio, trader_currencies_values)

    return real_currency_portfolio, simulated_currency_portfolio


def get_portfolio_current_value():
    simulated_value = 0
    real_value = 0
    traders = get_traders()
    has_real_trader = False
    has_simulated_trader = False

    for trader in traders:
        if trader.is_enabled():
            trade_manager = trader.get_trades_manager()

            get_bot().run_in_main_asyncio_loop(trade_manager.update_portfolio_and_currencies_current_value())

            current_value = trade_manager.get_portfolio_current_value()

            # current_value might be 0 if no trades have been made / canceled => use origin value
            if current_value == 0:
                current_value = trade_manager.get_portfolio_origin_value()

            if trader.get_simulate():
                simulated_value += current_value
                has_simulated_trader = True
            else:
                real_value += current_value
                has_real_trader = True

    return has_real_trader, has_simulated_trader, real_value, simulated_value


def has_real_and_or_simulated_traders():
    has_real_trader = False
    has_simulated_trader = False
    traders = get_traders()
    for trader in traders:
        if trader.enabled(trader.config):
            if trader.get_simulate():
                has_simulated_trader = True
            else:
                has_real_trader = True
    return has_real_trader, has_simulated_trader


def force_real_traders_refresh():
    at_least_one = False
    for trader in get_bot().get_exchange_traders().values():
        if trader.is_enabled():
            at_least_one = True
            get_bot().run_in_main_asyncio_loop(trader.force_refresh_orders_and_portfolio())

    if not at_least_one:
        raise RuntimeError("no real trader to update.")


def get_open_orders():
    simulated_open_orders = []
    real_open_orders = []
    traders = get_traders()

    for trader in traders:
        if trader.is_enabled():
            if trader.get_simulate():
                simulated_open_orders += trader.get_open_orders()
            else:
                real_open_orders += trader.get_open_orders()

    return real_open_orders, simulated_open_orders


def cancel_orders(orders_desc):
    removed_count = 0
    if orders_desc:
        for trader in get_traders():
            if trader.is_enabled():
                removed_count += get_bot().run_in_main_asyncio_loop(trader.cancel_orders_using_description(orders_desc))
    return removed_count


def cancel_all_open_orders(currency=None):
    for trader in get_traders():
        if trader.is_enabled():
            if currency is None:
                get_bot().run_in_main_asyncio_loop(trader.cancel_all_open_orders())
            else:
                get_bot().run_in_main_asyncio_loop(trader.cancel_all_open_orders_with_currency(currency))


def sell_all_currencies():
    orders = []
    for trader in get_traders():
        if trader.is_enabled():
            orders += get_bot().run_in_main_asyncio_loop(trader.sell_all_currencies())
    return orders


def sell_all(currency):
    orders = []
    for trader in get_traders():
        if trader.is_enabled():
            orders += get_bot().run_in_main_asyncio_loop(trader.sell_all(currency))
    return orders


def set_enable_trading(enable):
    for trader in get_traders():
        if trader.enabled(trader.config):
            trader.set_enabled(enable)


def _merge_trader_fees(current_fees, trader):
    current_fees_dict = current_fees if current_fees else {}
    for key, val in trader.get_trades_manager().get_total_paid_fees().items():
        if key in current_fees_dict:
            current_fees_dict[key] += val
        else:
            current_fees_dict[key] = val
    return current_fees_dict


def get_total_paid_fees(bot=None):
    real_trader_fees = None
    simulated_trader_fees = None

    traders = get_traders(bot)

    for trader in traders:
        if trader.is_enabled():
            if trader.get_simulate():
                simulated_trader_fees = _merge_trader_fees(simulated_trader_fees, trader)
            else:
                real_trader_fees = _merge_trader_fees(real_trader_fees, trader)

    return real_trader_fees, simulated_trader_fees


def get_trades_history(bot=None, symbol=None):
    simulated_trades_history = []
    real_trades_history = []
    traders = get_traders(bot)

    for trader in traders:
        if trader.is_enabled():
            if trader.get_simulate():
                simulated_trades_history += trader.get_trades_manager().select_trade_history(symbol)
            else:
                real_trades_history += trader.get_trades_manager().select_trade_history(symbol)

    return real_trades_history, simulated_trades_history


def set_risk(risk):
    traders = get_traders()
    result_risk = None

    for trader in traders:
        result_risk = trader.set_risk(risk)
    return result_risk


def get_risk():
    return next(iter(get_bot().get_exchange_traders().values())).get_risk()


def get_global_profitability():
    simulated_global_profitability = 0
    real_global_profitability = 0
    simulated_no_trade_profitability = 0
    real_no_trade_profitability = 0
    traders = get_traders()
    simulated_full_origin_value = 0
    real_full_origin_value = 0
    market_average_profitability = None
    has_real_trader = False
    has_simulated_trader = False

    for trader in traders:
        if trader.is_enabled():
            trade_manager = trader.get_trades_manager()

            # TODO : use other return values
            current_value, _, _, market_average_profitability, initial_portfolio_current_profitability = \
                get_bot().run_in_main_asyncio_loop(trade_manager.get_profitability(with_market=True))

            if trader.get_simulate():
                simulated_full_origin_value += trade_manager.get_portfolio_origin_value()
                simulated_global_profitability += current_value
                simulated_no_trade_profitability += initial_portfolio_current_profitability
                has_simulated_trader = True
            else:
                real_full_origin_value += trade_manager.get_portfolio_origin_value()
                real_global_profitability += current_value
                real_no_trade_profitability += initial_portfolio_current_profitability
                has_real_trader = True

    simulated_percent_profitability = simulated_global_profitability * 100 / simulated_full_origin_value \
        if simulated_full_origin_value > 0 else 0
    real_percent_profitability = real_global_profitability * 100 / real_full_origin_value \
        if real_full_origin_value > 0 else 0

    return has_real_trader, has_simulated_trader, \
        real_global_profitability, simulated_global_profitability, \
        real_percent_profitability, simulated_percent_profitability, \
        real_no_trade_profitability, simulated_no_trade_profitability, \
        market_average_profitability


def get_portfolios():
    simulated_portfolios = []
    real_portfolios = []
    traders = get_traders()

    for trader in traders:
        if trader.is_enabled():
            if trader.get_simulate():
                simulated_portfolios.append(trader.get_portfolio().get_portfolio())
            else:
                real_portfolios.append(trader.get_portfolio().get_portfolio())

    return real_portfolios, simulated_portfolios


def get_currencies_with_status():
    return {
        symbol_evaluator.get_symbol():
            {
                exchange.get_name():
                    [
                        ",".join([
                            dec.get_state().name
                            if dec.get_state() is not None else "N/A"
                            for dec in symbol_evaluator.get_deciders(exchange)
                        ]),
                        ",".join([
                            str(round(dec.get_final_eval(), 4))
                            if isinstance(dec.get_final_eval(), (int, float)) else "N/A"
                            for dec in symbol_evaluator.get_deciders(exchange)
                        ]),
                    ]
                for exchange in get_bot().get_exchanges_list().values()
                if symbol_evaluator.has_exchange(exchange)
            }
        for symbol_evaluator in get_bot().get_symbol_evaluator_list().values()}


def get_global_portfolio_currencies_amounts():
    real_portfolios, simulated_portfolios = get_portfolios()
    real_global_portfolio = {}
    simulated_global_portfolio = {}

    for portfolio in simulated_portfolios:
        for currency, amounts in portfolio.items():
            if currency not in simulated_global_portfolio:
                simulated_global_portfolio[currency] = {
                    Portfolio.TOTAL: 0,
                    Portfolio.AVAILABLE: 0
                }

            simulated_global_portfolio[currency][Portfolio.TOTAL] += amounts[Portfolio.TOTAL]
            simulated_global_portfolio[currency][Portfolio.AVAILABLE] = amounts[Portfolio.AVAILABLE]

    for portfolio in real_portfolios:
        for currency, amounts in portfolio.items():
            if currency not in real_global_portfolio:
                real_global_portfolio[currency] = {
                    Portfolio.TOTAL: 0,
                    Portfolio.AVAILABLE: 0
                }

            real_global_portfolio[currency][Portfolio.TOTAL] += amounts[Portfolio.TOTAL]
            real_global_portfolio[currency][Portfolio.AVAILABLE] = amounts[Portfolio.AVAILABLE]

    return real_global_portfolio, simulated_global_portfolio


def get_matrix_list():
    return {
        symbol_evaluator.get_symbol():
            {
                exchange.get_name(): symbol_evaluator.get_matrix(exchange)
                for exchange in get_bot().get_exchanges_list().values()
                if symbol_evaluator.has_exchange(exchange)
            }
        for symbol_evaluator in get_bot().get_symbol_evaluator_list().values()}
