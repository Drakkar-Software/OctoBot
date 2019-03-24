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

import datetime

from flask import render_template, request, jsonify

from interfaces.trading_util import get_open_orders, get_trades_history, get_global_portfolio_currencies_amounts, \
    get_currencies_with_status, get_portfolio_current_value, get_portfolio_holdings, has_real_and_or_simulated_traders
from interfaces import get_reference_market
from interfaces.web import server_instance
from trading.trader.portfolio import Portfolio
from interfaces.web.models.configuration import get_in_backtesting_mode
from interfaces.web.models.trading import get_exchange_time_frames, get_evaluation
from interfaces.web.models.interface_settings import get_watched_symbols


@server_instance.route("/portfolio")
def portfolio():
    has_real_trader, has_simulated_trader = has_real_and_or_simulated_traders()

    real_portfolio, simulated_portfolio = get_global_portfolio_currencies_amounts()

    filtered_real_portfolio = {currency: amounts
                               for currency, amounts in real_portfolio.items()
                               if amounts[Portfolio.TOTAL] > 0}
    filtered_simulated_portfolio = {currency: amounts
                                    for currency, amounts in simulated_portfolio.items()
                                    if amounts[Portfolio.TOTAL] > 0}

    _, _, portfolio_real_current_value, portfolio_simulated_current_value = get_portfolio_current_value()
    reference_market = get_reference_market()

    return render_template('portfolio.html',
                           has_real_trader=has_real_trader,
                           has_simulated_trader=has_simulated_trader,
                           simulated_portfolio=filtered_simulated_portfolio,
                           real_portfolio=filtered_real_portfolio,
                           simulated_total_value=round(portfolio_simulated_current_value, 8),
                           real_total_value=round(portfolio_real_current_value, 8),
                           reference_unit=reference_market
                           )


@server_instance.route("/portfolio_holdings")
def portfolio_holdings():
    result = {}
    real_portfolio_holdings, simulated_portfolio_holdings = get_portfolio_holdings()
    result["real_portfolio_holdings"] = real_portfolio_holdings
    result["simulated_portfolio_holdings"] = simulated_portfolio_holdings
    return jsonify(result)


@server_instance.route("/symbol_market_status")
@server_instance.route('/symbol_market_status', methods=['GET', 'POST'])
def symbol_market_status():
    exchange = request.args["exchange"]
    symbol = request.args["symbol"]
    symbol_time_frames, exchange = get_exchange_time_frames(exchange)
    time_frames = list(symbol_time_frames)
    time_frames.reverse()
    symbol_evaluation = get_evaluation(symbol, exchange)
    return render_template('symbol_market_status.html',
                           symbol=symbol,
                           exchange=exchange,
                           symbol_evaluation=symbol_evaluation,
                           time_frames=time_frames,
                           backtesting_mode=get_in_backtesting_mode())


@server_instance.route("/trading")
def trading():
    real_open_orders, simulated_open_orders = get_open_orders()
    return render_template('trading.html',
                           real_open_orders=real_open_orders,
                           simulated_open_orders=simulated_open_orders,
                           watched_symbols=get_watched_symbols(),
                           pairs_with_status=get_currencies_with_status())


@server_instance.route("/trades")
def trades():
    real_trades_history, simulated_trades_history = get_trades_history()
    return render_template('trades.html',
                           real_trades_history=real_trades_history,
                           simulated_trades_history=simulated_trades_history)


@server_instance.context_processor
def utility_processor():
    def convert_timestamp(str_time):
        return datetime.datetime.fromtimestamp(str_time).strftime('%Y-%m-%d %H:%M:%S')

    def convert_type(order_type):
        return order_type.name

    return dict(convert_timestamp=convert_timestamp, convert_type=convert_type)
