from flask import jsonify

from interfaces.web import server_instance
from interfaces.web.models.dashboard import *


@server_instance.route('/dashboard/currency_price_graph_update/<exchange_name>/<symbol>/<time_frame>/<mode>',
                       methods=['GET', 'POST'])
def currency_price_graph_update(exchange_name, symbol, time_frame, mode="live"):
    backtesting = not mode == "live"
    return jsonify(get_currency_price_graph_update(exchange_name,
                                                   get_value_from_dict_or_string(symbol),
                                                   get_value_from_dict_or_string(time_frame, True),
                                                   backtesting=backtesting))
