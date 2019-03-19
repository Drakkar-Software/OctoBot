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

import json
from flask import request, jsonify

from interfaces.trading_util import get_open_orders, cancel_all_open_orders, cancel_order
from . import api
from interfaces.web.util.flask_util import get_rest_reply


@api.route("/orders", methods=['GET', 'POST'])
def orders():
    if request.method == 'GET':
        real_open_orders, simulated_open_orders = get_open_orders()

        return json.dumps({"real_open_orders": real_open_orders, "simulated_open_orders": simulated_open_orders})
    elif request.method == "POST":
        result = ""
        request_data = request.get_json()
        action = request.args.get("action")
        if action == "cancel_order":
            if cancel_order(request_data):
                result = "Order cancelled"
            else:
                return get_rest_reply('Impossible to cancel order: order not found.', 500)
        elif action == "cancel_all_orders":
            cancel_all_open_orders()
            result = "All orders are now cancelled"
        return jsonify(result)
