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
    @blueprint.route("/register_submitted_form", methods=['POST'])
    @login.login_required_when_activated
    def register_submitted_form():
        request_data = flask.request.get_json()
        form_id = request_data["form_id"]
        user_id = request_data["user_id"]
        success, message = models.register_user_submitted_form(user_id, form_id)
        return util.get_rest_reply(flask.jsonify(message), 200 if success else 500)
