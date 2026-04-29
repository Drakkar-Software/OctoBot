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

import octobot_services.api as services_api
import tentacles.Services.Interfaces.web_interface.login as login
import octobot_services.interfaces.util as interfaces_util


def register(blueprint):
    @blueprint.route("/user_command", methods=['POST'])
    @login.login_required_when_activated
    def user_command():
        request_data = flask.request.get_json()
        interfaces_util.run_in_bot_main_loop(
            services_api.send_user_command(
                interfaces_util.get_bot_api().get_bot_id(),
                request_data["subject"],
                request_data["action"],
                request_data["data"]
            )
        )
        return flask.jsonify(request_data)
