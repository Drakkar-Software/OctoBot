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

from flask import request, jsonify

from interfaces.web import server_instance
from interfaces.web.models.interface_settings import add_watched_symbol, remove_watched_symbol
from interfaces.web.util.flask_util import get_rest_reply


@server_instance.route("/watched_symbols")
@server_instance.route('/watched_symbols', methods=['POST'])
def watched_symbols():
    if request.method == 'POST':
        result = False
        request_data = request.get_json()
        symbol = request_data["symbol"]
        action = request_data["action"]
        action_desc = "added to"
        if action == 'add':
            result = add_watched_symbol(symbol)
        elif action == 'remove':
            result = remove_watched_symbol(symbol)
            action_desc = "removed from"
        if result:
            return get_rest_reply(jsonify(f"{symbol} {action_desc} watched markets"))
        else:
            return get_rest_reply(f'Error: {symbol} not {action_desc} watched markets.', 500)
