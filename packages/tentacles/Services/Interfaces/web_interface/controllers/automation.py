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
import octobot_commons.authentication as authentication
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
import octobot.automation as bot_automation
import octobot.constants as constants
import octobot.errors as errors


def register(blueprint):
    @blueprint.route("/automations", methods=["POST", "GET"])
    @login.login_required_when_activated
    def automations():
        if not models.are_automations_enabled():
            return flask.redirect(flask.url_for("home"))
        if flask.request.method == 'POST':
            action = flask.request.args.get("action")
            success = True
            response = ""
            tentacle_name = bot_automation.Automation.get_name()
            tentacle_class = bot_automation.Automation
            restart = False
            if action == "save":
                request_data = flask.request.get_json()
                success, response = models.update_tentacle_config(
                    tentacle_name,
                    request_data,
                    tentacle_class=tentacle_class
                )
            if action == "start":
                restart = True
            elif action == "factory_reset":
                success, response = models.reset_automation_config_to_default()
                restart = True
            if restart:
                try:
                    models.restart_global_automations()
                except errors.InvalidAutomationConfigError as err:
                    return util.get_rest_reply(
                        f"Invalid automation configuration: {err}", 400
                    )
            if success:
                return util.get_rest_reply(flask.jsonify(response))
            else:
                return util.get_rest_reply(response, 500)

        display_intro = flask_util.BrowsingDataProvider.instance().get_and_unset_is_first_display(
            flask_util.BrowsingDataProvider.AUTOMATIONS
        )
        all_events, all_conditions, all_actions = models.get_all_automation_steps()
        form_to_display = constants.AUTOMATION_FEEDBACK_FORM_ID
        try:
            user_id = models.get_user_account_id()
            display_feedback_form = models.has_at_least_one_running_automation() and not models.has_filled_form(form_to_display)
        except authentication.AuthenticationRequired:
            # no authenticated user: don't display form
            user_id = None
            display_feedback_form = False
        return flask.render_template(
            'automations.html',
            profile_name=models.get_current_profile().name,
            events=all_events,
            conditions=all_conditions,
            actions=all_actions,
            display_intro=display_intro,
            user_id=user_id,
            form_to_display=form_to_display,
            display_feedback_form=display_feedback_form,
        )


    @blueprint.route('/automations_edit_details')
    @login.login_required_when_activated
    def automations_edit_details():
        if not models.are_automations_enabled():
            return flask.redirect(flask.url_for("home"))
        try:
            return util.get_rest_reply(
                models.get_tentacle_config_and_edit_display(
                    bot_automation.Automation.get_name(),
                    tentacle_class=bot_automation.Automation
                )
            )
        except Exception as e:
            commons_logging.get_logger("automations_edit_details").exception(e)
            return util.get_rest_reply(str(e), 500)
