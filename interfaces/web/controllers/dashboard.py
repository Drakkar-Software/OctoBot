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

from flask import jsonify

from interfaces.web import server_instance
from interfaces.web.models.dashboard import get_currency_price_graph_update, get_value_from_dict_or_string, \
    get_first_symbol_data, get_watched_symbol_data
from interfaces.trading_util import get_global_profitability


@server_instance.route('/dashboard/currency_price_graph_update/<exchange_name>/<symbol>/<time_frame>/<mode>',
                       methods=['GET', 'POST'])
def currency_price_graph_update(exchange_name, symbol, time_frame, mode="live"):
    backtesting = mode != "live"
    return jsonify(get_currency_price_graph_update(exchange_name,
                                                   get_value_from_dict_or_string(symbol),
                                                   get_value_from_dict_or_string(time_frame, True),
                                                   backtesting=backtesting))


@server_instance.route('/dashboard/first_symbol',
                       methods=['GET', 'POST'])
def first_symbol():
    return jsonify(get_first_symbol_data())


@server_instance.route('/dashboard/watched_symbol/<symbol>',
                       methods=['GET', 'POST'])
def watched_symbol(symbol):
    return jsonify(get_watched_symbol_data(symbol))


@server_instance.route('/dashboard/profitability',
                       methods=['GET', 'POST'])
def profitability():
    has_real_trader, has_simulated_trader, \
        _, _, \
        real_percent_profitability, simulated_percent_profitability, \
        market_average_profitability = get_global_profitability()
    profitability_data = {"market_average_profitability": market_average_profitability}
    if has_real_trader:
        profitability_data["bot_real_profitability"] = real_percent_profitability
    if has_simulated_trader:
        profitability_data["bot_simulated_profitability"] = simulated_percent_profitability
    return jsonify(profitability_data)
