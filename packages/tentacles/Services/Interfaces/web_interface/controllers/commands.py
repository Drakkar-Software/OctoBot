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
    @blueprint.route('/commands/<cmd>', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def commands(cmd=None):
        if cmd == "restart":
            models.schedule_delayed_command(models.restart_bot, delay=0.1)
            return flask.jsonify("Success")

        elif cmd == "stop":
            models.schedule_delayed_command(models.stop_bot, delay=0.1)
            return flask.jsonify("Success")

        elif cmd == "update":
            models.schedule_delayed_command(models.update_bot, delay=0.1)
            return flask.jsonify("Update started")

        else:
            raise RuntimeError("Unknown command")
