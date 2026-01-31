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
    @blueprint.route("/are_compatible_accounts", methods=['POST'])
    @login.login_required_when_activated
    def are_compatible_accounts():
        request_data = flask.request.get_json()
        return flask.jsonify(models.are_compatible_accounts(request_data))


    @blueprint.route("/first_exchange_details")
    @login.login_required_when_activated
    def first_exchange_details():
        exchange_name = flask.request.args.get('exchange_name', None)
        try:
            exchange_manager, exchange_name, exchange_id = models.get_first_exchange_data(exchange_name)
            return util.get_rest_reply(
                {
                    "exchange_name": exchange_name,
                    "exchange_id": exchange_id
                },
                200
            )
        except KeyError as e:
            return util.get_rest_reply(str(e), 404)
