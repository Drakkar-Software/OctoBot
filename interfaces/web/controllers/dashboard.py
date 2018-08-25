from flask import jsonify

from interfaces.web import server_instance
from interfaces.web.models.dashboard import get_currency_price_graph_update, get_value_from_dict_or_string, \
    get_first_symbol_data
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


@server_instance.route('/dashboard/profitability',
                       methods=['GET', 'POST'])
def profitability():
    has_real_trader, has_simulated_trader, \
        real_global_profitability, simulated_global_profitability, \
        real_percent_profitability, simulated_percent_profitability, \
        market_average_profitability = get_global_profitability()
    profitability_data = {"market_average_profitability": market_average_profitability}
    if has_real_trader:
        profitability_data["bot_real_profitability"] = real_percent_profitability
    if has_simulated_trader:
        profitability_data["bot_simulated_profitability"] = simulated_percent_profitability
    return jsonify(profitability_data)
