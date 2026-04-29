#  Drakkar-Software OctoBot-Interfaces
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
import flask

import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models


def register(blueprint):
    @blueprint.route(
        '/dashboard/currency_price_graph_update/<exchange_id>/<symbol>/<time_frame>/<mode>')
    @login.login_required_when_activated
    def currency_price_graph_update(exchange_id, symbol, time_frame, mode="live"):
        in_backtesting = mode != "live"
        display_orders = flask.request.args.get("display_orders", "true") == "true"
        return flask.jsonify(models.get_currency_price_graph_update(exchange_id,
                                                                    models.get_value_from_dict_or_string(symbol),
                                                                    time_frame,
                                                                    backtesting=in_backtesting,
                                                                    ignore_orders=not display_orders))


    @blueprint.route('/dashboard/first_symbol')
    @login.login_required_when_activated
    def first_symbol():
        return flask.jsonify(models.get_first_symbol_data())


    @blueprint.route('/dashboard/watched_symbol/<symbol>')
    @login.login_required_when_activated
    def watched_symbol(symbol):
        return flask.jsonify(models.get_watched_symbol_data(symbol))
