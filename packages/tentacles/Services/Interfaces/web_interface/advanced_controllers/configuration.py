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

import tentacles.Services.Interfaces.web_interface.constants as constants
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.login as login


def register(blueprint):
    @blueprint.route("/evaluator_config")
    @blueprint.route('/evaluator_config', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def evaluator_config():
        if flask.request.method == 'POST':
            request_data = flask.request.get_json()
            success = True
            response = ""

            if request_data:
                # update evaluator config if required
                if constants.EVALUATOR_CONFIG_KEY in request_data and request_data[constants.EVALUATOR_CONFIG_KEY]:
                    success = success and models.update_tentacles_activation_config(
                        request_data[constants.EVALUATOR_CONFIG_KEY])

                response = {
                    "evaluator_updated_config": request_data[constants.EVALUATOR_CONFIG_KEY]
                }

            if success:
                if request_data.get("restart_after_save", False):
                    models.schedule_delayed_command(models.restart_bot)
                return util.get_rest_reply(flask.jsonify(response))
            else:
                return util.get_rest_reply('{"update": "ko"}', 500)
        else:
            media_url = flask.url_for("tentacle_media", _external=True)
            missing_tentacles = set()
            return flask.render_template(
                'advanced_evaluator_config.html',
                evaluator_config=models.get_evaluator_detailed_config(media_url, missing_tentacles),
                evaluator_startup_config=models.get_evaluators_tentacles_startup_activation(),
                missing_tentacles=missing_tentacles,
                current_profile=models.get_current_profile()
            )
