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

import octobot_commons.authentication
import octobot.community.errors
import octobot_services.interfaces.util as interfaces_util
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.util as util


def register(blueprint):
    @blueprint.route('/get_config_currency', methods=["GET"])
    @login.login_required_when_activated
    def get_config_currency():
        return flask.jsonify(models.format_config_symbols(interfaces_util.get_edited_config()))


    @blueprint.route('/get_all_currencies/<exchange>', methods=["GET"])
    @login.login_required_when_activated
    def get_all_currencies(exchange):
        return flask.jsonify(models.get_all_currencies([exchange]))


    @blueprint.route('/get_all_symbols/<exchange>')
    @login.login_required_when_activated
    def get_all_symbols(exchange):
        return flask.jsonify(models.get_symbol_list([exchange]))


    @blueprint.route('/set_config_currency', methods=["POST"])
    @login.login_required_when_activated
    def set_config_currency():
        request_data = flask.request.get_json()
        success, reply = models.update_config_currencies(
            request_data["currencies"],
            replace=(request_data.get("action", "update") == "replace")
        )
        return util.get_rest_reply(flask.jsonify(reply)) if success else util.get_rest_reply(reply, 500)


    @blueprint.route('/change_reference_market_on_config_currencies', methods=["POST"])
    @login.login_required_when_activated
    def change_reference_market_on_config_currencies():
        request_data = flask.request.get_json()
        success, reply = models.change_reference_market_on_config_currencies(request_data["old_base_currency"],
                                                                             request_data["new_base_currency"])
        return util.get_rest_reply(flask.jsonify(reply)) if success else util.get_rest_reply(reply, 500)


    @blueprint.route('/display_config', methods=["POST"])
    @login.login_required_when_activated
    def display_config():
        request_data = flask.request.get_json()
        success = False
        message = "nothing to do"
        if "color_mode" in request_data:
            success, message = models.set_color_mode(request_data["color_mode"])
        if "time_frame" in request_data:
            success, message = models.set_display_timeframe(request_data["time_frame"])
        if "display_orders" in request_data:
            success, message = models.set_display_orders(request_data["display_orders"])
        return util.get_rest_reply(flask.jsonify(message), 200 if success else 500)


    @blueprint.route('/hide_announcement<key>', methods=["POST"])
    @login.login_required_when_activated
    def hide_announcement(key):
        models.set_display_announcement(key, False)
        return util.get_rest_reply(flask.jsonify(""), 200)


    @blueprint.route('/start_copy_trading', methods=["POST"])
    @login.login_required_when_activated
    def start_copy_trading():
        try:
            copy_id = flask.request.get_json()["copy_id"]
            profile_id = flask.request.get_json()["profile_id"]
            if models.get_current_profile().profile_id != profile_id:
                models.select_profile(profile_id)
            response = f"{models.get_current_profile().name} profile selected"
            success, config_resp = models.update_copied_trading_id(copy_id)
            response = f"{response}, {config_resp}"
            return util.get_rest_reply(flask.jsonify(response)) if success else util.get_rest_reply(response, 500)
        except Exception as e:
            return util.get_rest_reply(f"Unexpected error : {e}", 500)


    @blueprint.route('/trading_strategies_tentacles_details<backtestable_only>', methods=["GET"])
    @login.login_required_when_activated
    def trading_strategies_tentacles_details(backtestable_only):
        missing_tentacles = set()
        media_url = flask.url_for("tentacle_media", _external=True)
        evaluators = {}
        for evals in models.get_evaluator_detailed_config(media_url, missing_tentacles).values():
            if isinstance(evals, dict):
                evaluators.update(evals)
        strategy_config = models.get_strategy_config(
            media_url, missing_tentacles, with_trading_modes=True, whitelist=None, backtestable_only=backtestable_only
        )
        return flask.jsonify({
            "trading_modes": strategy_config[models.TRADING_MODES_KEY],
            "strategies": strategy_config[models.STRATEGIES_KEY],
            "evaluators": evaluators,
        })


    @blueprint.route('/tradingview_confirm_email_content', methods=["GET"])
    @login.login_required_when_activated
    def tradingview_confirm_email_content():
        try:
            return util.get_rest_reply(
                flask.jsonify(models.get_last_email_address_confirm_code_email_content()), 200
            )
        except octobot_commons.authentication.AuthenticationRequired:
            return util.get_rest_reply(flask.jsonify("authentication required"), 401)


    @blueprint.route('/trigger_wait_for_email_address_confirm_code_email', methods=["POST"])
    @login.login_required_when_activated
    def trigger_wait_for_email_address_confirm_code_email():
        try:
            models.wait_for_email_address_confirm_code_email()
            return util.get_rest_reply(flask.jsonify(""), 200)
        except octobot.community.errors.ExtensionRequiredError as err:
            return util.get_rest_reply(flask.jsonify(str(err)), 401)

