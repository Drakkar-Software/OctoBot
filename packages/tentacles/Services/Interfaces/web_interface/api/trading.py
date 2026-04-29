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

import octobot_services.interfaces.util as interfaces_util
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models


def register(blueprint):
    @blueprint.route("/orders", methods=['GET', 'POST'])
    @login.login_required_when_activated
    def orders():
        if flask.request.method == 'GET':
            return flask.jsonify(models.get_all_orders_data())
        elif flask.request.method == "POST":
            result = ""
            request_data = flask.request.get_json()
            action = flask.request.args.get("action")
            if action == "cancel_order":
                if interfaces_util.cancel_orders([request_data]):
                    result = "Order cancelled"
                else:
                    return util.get_rest_reply('Impossible to cancel order: order not found.', 500)
            elif action == "cancel_orders":
                removed_count = interfaces_util.cancel_orders(request_data)
                result = f"{removed_count} orders cancelled"
            return flask.jsonify(result)


    @blueprint.route("/trades", methods=['GET'])
    @login.login_required_when_activated
    def trades():
        return flask.jsonify(models.get_all_trades_data())


    @blueprint.route("/positions", methods=['GET', 'POST'])
    @login.login_required_when_activated
    def positions():
        if flask.request.method == 'GET':
            return flask.jsonify(models.get_all_positions_data())
        elif flask.request.method == "POST":
            result = ""
            request_data = flask.request.get_json()
            action = flask.request.args.get("action")
            if action == "close_position":
                if interfaces_util.close_positions([request_data]):
                    result = "Position closed"
                else:
                    return util.get_rest_reply('Impossible to close position: position already closed.', 500)
            return flask.jsonify(result)


    @blueprint.route("/refresh_portfolio", methods=['POST'])
    @login.login_required_when_activated
    def refresh_portfolio():
        try:
            interfaces_util.trigger_portfolios_refresh()
            return flask.jsonify("Portfolio(s) refreshed")
        except RuntimeError:
            return util.get_rest_reply("No portfolio to refresh", 500)


    @blueprint.route("/currency_list", methods=['GET'])
    @login.login_required_when_activated
    def currency_list():
        return flask.jsonify(models.get_all_symbols_list())


    @blueprint.route("/historical_portfolio_value", methods=['GET'])
    @login.login_required_when_activated
    def historical_portfolio_value():
        currency = flask.request.args.get("currency", "USDT")
        time_frame = flask.request.args.get("time_frame")
        from_timestamp = flask.request.args.get("from_timestamp")
        to_timestamp = flask.request.args.get("to_timestamp")
        exchange = flask.request.args.get("exchange")
        try:
            return flask.jsonify(models.get_portfolio_historical_values(currency, time_frame,
                                                                        from_timestamp, to_timestamp,
                                                                        exchange))
        except KeyError:
            return util.get_rest_reply("No exchange portfolio", 404)


    @blueprint.route("/pnl_history", methods=['GET'])
    @login.login_required_when_activated
    def pnl_history():
        exchange = flask.request.args.get("exchange")
        symbol = flask.request.args.get("symbol")
        quote = flask.request.args.get("quote")
        since = flask.request.args.get("since")
        scale = flask.request.args.get("scale", "")
        return flask.jsonify(
            models.get_pnl_history(
                exchange=exchange,
                quote=quote,
                symbol=symbol,
                since=since,
                scale=scale,
            )
        )


    @blueprint.route("/clear_orders_history", methods=['POST'])
    @login.login_required_when_activated
    def clear_orders_history():
        return util.get_rest_reply(models.clear_exchanges_orders_history())


    @blueprint.route("/clear_trades_history", methods=['POST'])
    @login.login_required_when_activated
    def clear_trades_history():
        return util.get_rest_reply(models.clear_exchanges_trades_history())


    @blueprint.route("/clear_portfolio_history", methods=['POST'])
    @login.login_required_when_activated
    def clear_portfolio_history():
        return flask.jsonify(models.clear_exchanges_portfolio_history())


    @blueprint.route("/clear_transactions_history", methods=['POST'])
    @login.login_required_when_activated
    def clear_transactions_history():
        return flask.jsonify(models.clear_exchanges_transactions_history())
