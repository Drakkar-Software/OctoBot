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

import octobot_commons.logging as commons_logging
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.util as util


def register(blueprint):
    @blueprint.route('/config_tentacle', methods=['GET', 'POST'])
    @login.login_required_when_activated
    def config_tentacle():
        if flask.request.method == 'POST':
            tentacle_name = flask.request.args.get("name")
            action = flask.request.args.get("action")
            profile_id = flask.request.args.get("profile_id")
            restart = flask.request.args.get("restart", "false") == "true"
            tentacles_setup_config = models.get_tentacles_setup_config_from_profile_id(profile_id) if profile_id else None
            success = True
            response = ""
            reload_config = False
            if action == "update":
                request_data = flask.request.get_json()
                success, response = models.update_tentacle_config(
                    tentacle_name, request_data, tentacles_setup_config=tentacles_setup_config
                )
                reload_config = True
            elif action == "factory_reset":
                success, response = models.reset_config_to_default(
                    tentacle_name, tentacles_setup_config=tentacles_setup_config
                )
                reload_config = True
            if flask.request.args.get("reload"):
                try:
                    models.reload_scripts()
                except Exception as e:
                    success = False
                    response = str(e)
            if reload_config and success:
                try:
                    models.reload_tentacle_config(tentacle_name)
                except Exception as e:
                    success = False
                    response = f"Error when reloading configuration {e}"
            if success:
                if restart:
                    models.schedule_delayed_command(models.restart_bot)
                return util.get_rest_reply(flask.jsonify(response))
            else:
                return util.get_rest_reply(response, 500)
        else:
            if flask.request.args:
                tentacle_name = flask.request.args.get("name")
                missing_tentacles = set()
                media_url = flask.url_for("tentacle_media", _external=True)
                tentacle_class, tentacle_type, tentacle_desc = models.get_tentacle_from_string(tentacle_name, media_url)
                is_strategy = tentacle_type == "strategy"
                is_trading_mode = tentacle_type == "trading mode"
                evaluator_config = None
                strategy_config = None
                requirements = tentacle_desc.get(models.REQUIREMENTS_KEY, [])
                wildcard_requirements = requirements == ["*"]
                if is_strategy and wildcard_requirements:
                    evaluator_config = models.get_evaluator_detailed_config(
                        media_url, missing_tentacles, single_strategy=tentacle_name
                    )
                elif is_trading_mode and len(requirements) > 1:
                    strategy_config = models.get_strategy_config(
                        media_url, missing_tentacles, with_trading_modes=False,
                        whitelist=None if wildcard_requirements else requirements
                    )
                evaluator_startup_config = models.get_evaluators_tentacles_startup_activation() \
                    if evaluator_config or strategy_config else None
                tentacle_commands = models.get_tentacle_user_commands(tentacle_class)
                is_trading_strategy_configuration = models.is_trading_strategy_configuration(tentacle_type)
                return flask.render_template(
                    'config_tentacle.html',
                    name=tentacle_name,
                    tentacle_type=tentacle_type,
                    tentacle_class=tentacle_class,
                    tentacle_desc=tentacle_desc,
                    evaluator_startup_config=evaluator_startup_config,
                    strategy_config=strategy_config,
                    evaluator_config=evaluator_config,
                    is_trading_strategy_configuration=is_trading_strategy_configuration,
                    activated_trading_mode=models.get_config_activated_trading_mode()
                    if is_trading_strategy_configuration else None,
                    data_files=models.get_data_files_with_description() if is_trading_strategy_configuration else None,
                    missing_tentacles=missing_tentacles,
                    user_commands=tentacle_commands,
                    current_profile=models.get_current_profile()
                )
            else:
                return flask.render_template('config_tentacle.html')


    @blueprint.route('/config_tentacle_edit_details/<tentacle>')
    @login.login_required_when_activated
    def config_tentacle_edit_details(tentacle):
        try:
            profile_id = flask.request.args.get("profile", None)
            return util.get_rest_reply(
                models.get_tentacle_config_and_edit_display(tentacle, profile_id=profile_id)
            )
        except Exception as e:
            commons_logging.get_logger("configuration").exception(e)
            return util.get_rest_reply(str(e), 500)


    @blueprint.route('/config_tentacles', methods=['POST'])
    @login.login_required_when_activated
    def config_tentacles():
        action = flask.request.args.get("action")
        profile_id = flask.request.args.get("profile_id")
        tentacles_setup_config = models.get_tentacles_setup_config_from_profile_id(profile_id) if profile_id else None
        success = True
        response = ""
        if action == "update":
            request_data = flask.request.get_json()
            responses = []
            for tentacle, tentacle_config in request_data.items():
                update_success, update_response = models.update_tentacle_config(
                    tentacle, tentacle_config, tentacles_setup_config=tentacles_setup_config
                )
                success = update_success and success
                responses.append(update_response)
            response = ", ".join(responses)
        if success and flask.request.args.get("reload"):
            try:
                models.reload_activated_tentacles_config()
            except Exception as e:
                success = False
                response = str(e)
        if success:
            return util.get_rest_reply(flask.jsonify(response))
        else:
            return util.get_rest_reply(response, 500)
