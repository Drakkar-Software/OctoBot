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
import tentacles.Services.Interfaces.web_interface.util as util


def register(blueprint):
    @blueprint.route("/watched_symbols")
    @blueprint.route('/watched_symbols', methods=['POST'])
    @login.login_required_when_activated
    def watched_symbols():
        if flask.request.method == 'POST':
            result = False
            request_data = flask.request.get_json()
            symbol = request_data["symbol"]
            action = request_data["action"]
            action_desc = "added to"
            if action == 'add':
                result = models.add_watched_symbol(symbol)
            elif action == 'remove':
                result = models.remove_watched_symbol(symbol)
                action_desc = "removed from"
            if result:
                return util.get_rest_reply(flask.jsonify(f"{symbol} {action_desc} watched markets"))
            else:
                return util.get_rest_reply(f'Error: {symbol} not {action_desc} watched markets.', 500)
