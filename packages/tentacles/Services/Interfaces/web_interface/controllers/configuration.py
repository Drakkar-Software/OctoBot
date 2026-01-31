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
import werkzeug
import os
from datetime import datetime

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_services.constants as services_constants
import tentacles.Services.Interfaces.web_interface.constants as constants
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
import octobot_backtesting.api as backtesting_api
import octobot_trading.api as trading_api
import octobot_services.interfaces.util as interfaces_util


def register(blueprint):
    @blueprint.route('/profile')
    @login.login_required_when_activated
    def profile():
        selected_profile = flask.request.args.get("select", None)
        next_url = flask.request.args.get("next", None)
        if selected_profile is not None and selected_profile != models.get_current_profile().profile_id:
            models.select_profile(selected_profile)
            current_profile = models.get_current_profile()
            flask.flash(
                f"Selected the {current_profile.name} profile", "success"
            )
        else:
            current_profile = models.get_current_profile()
        if next_url is not None:
            return flask.redirect(next_url)
        media_url = flask.url_for("tentacle_media", _external=True)
        display_config = interfaces_util.get_edited_config()

        missing_tentacles = set()
        profiles = models.get_profiles(commons_enums.ProfileType.LIVE)
        config_exchanges = display_config[commons_constants.CONFIG_EXCHANGES]
        enabled_exchange_types = models.get_enabled_exchange_types(config_exchanges)
        enabled_exchanges = trading_api.get_enabled_exchanges_names(display_config)
        display_intro = flask_util.BrowsingDataProvider.instance().get_and_unset_is_first_display(
            flask_util.BrowsingDataProvider.PROFILE
        )
        exchange_symbols = sorted(models.get_symbol_list(enabled_exchanges or config_exchanges))
        config_symbols = models.format_config_symbols(display_config)
        return flask.render_template(
            'profile.html',
             current_profile=current_profile,
             profiles=profiles,
             profiles_tentacles_details=models.get_profiles_tentacles_details(profiles),
             display_intro=display_intro,

             config_exchanges=config_exchanges,
             enabled_exchange_types=enabled_exchange_types,
             config_trading=display_config[commons_constants.CONFIG_TRADING],
             config_trader=display_config[commons_constants.CONFIG_TRADER],
             config_trader_simulator=display_config[commons_constants.CONFIG_SIMULATOR],
             config_symbols=config_symbols,
             config_reference_market=display_config[commons_constants.CONFIG_TRADING][
                 commons_constants.CONFIG_TRADER_REFERENCE_MARKET],

             real_trader_activated=interfaces_util.has_real_and_or_simulated_traders()[0],

             symbol_list_by_type=models.get_all_symbols_list_by_symbol_type(exchange_symbols, config_symbols),
             full_symbol_list=models.get_all_symbols_list(),
             evaluator_config=models.get_evaluator_detailed_config(media_url, missing_tentacles),
             strategy_config=models.get_strategy_config(media_url, missing_tentacles),
             evaluator_startup_config=models.get_evaluators_tentacles_startup_activation(),
             trading_startup_config=models.get_trading_tentacles_startup_activation(),
             missing_tentacles=missing_tentacles,

             in_backtesting=backtesting_api.is_backtesting_enabled(display_config),

             other_tentacles_config=models.get_extra_tentacles_config_desc(media_url,
                                                                           missing_tentacles),

             config_tentacles_by_group=models.get_tentacles_activation_desc_by_group(media_url,
                                                                                     missing_tentacles),

             exchanges_details=models.get_exchanges_details(config_exchanges),

             are_automations_enabled=models.are_automations_enabled(),
             automations_count=models.get_automations_count(),
        )


    @blueprint.route('/profiles_management/<action>', methods=["POST", "GET"])
    @login.login_required_when_activated
    def profiles_management(action):
        if action == "update":
            data = flask.request.get_json()
            success, err = models.update_profile(flask.request.get_json()["id"], data)
            if not success:
                return util.get_rest_reply(flask.jsonify(str(err)), code=400)
            return util.get_rest_reply(flask.jsonify(data))
        if action == "duplicate":
            profile_id = flask.request.args.get("profile_id")
            models.duplicate_profile(profile_id)
            flask.flash(f"New profile successfully created.", "success")
            return util.get_rest_reply(flask.jsonify("Profile created"))
        if action == "use_as_live":
            profile_id = flask.request.args.get("profile_id")
            models.convert_to_live_profile(profile_id)
            models.select_profile(profile_id)
            flask.flash(f"Profile successfully converted to live profile and selected.", "success")
            return flask.redirect(flask.url_for("profile"))
        if action == "remove":
            data = flask.request.get_json()
            to_remove_id = data["id"]
            removed_profile, err = models.remove_profile(to_remove_id)
            if err is not None:
                return util.get_rest_reply(flask.jsonify(str(err)), code=400)
            flask.flash(f"{removed_profile.name} profile removed.", "success")
            return util.get_rest_reply(flask.jsonify("Profile created"))
        next_url = flask.request.args.get("next", flask.url_for('profile'))
        if action == "import":
            file = flask.request.files['file']
            name = werkzeug.utils.secure_filename(flask.request.files['file'].filename)
            try:
                new_profile = models.import_profile(file, name)
                flask.flash(f"{new_profile.name} profile successfully imported.", "success")
            except Exception as err:
                flask.flash(f"Error when importing profile: {err}.", "danger")
            return flask.redirect(next_url)
        if action == "download":
            url = flask.request.form.get('inputProfileLink')
            strategy_id = flask.request.json.get('strategy_id')
            name = flask.request.json.get('name')
            description = flask.request.json.get('description')
            profile_id = ""
            try:
                if url:
                    new_profile = models.download_and_import_profile(url)
                else:
                    if None in (strategy_id, name):
                        raise RuntimeError("Both strategy_id and name are required to import a strategy")
                    authenticator = authentication.Authenticator.instance()
                    strategy = models.get_cloud_strategy(authenticator, strategy_id)
                    new_profile = models.import_strategy_as_profile(
                        authenticator, strategy, name, description
                    )
                    profile_id = new_profile.profile_id
                message = f"{new_profile.name} profile successfully imported."
                success = True
            except FileNotFoundError:
                message = f"Invalid profile url {url}"
                success = False
            except Exception as err:
                message = f"Error when importing profile: {err}"
                success = False
            if flask.request.method == "POST":
                return util.get_rest_reply(
                    flask.jsonify({"text": message, "profile_id": profile_id}),
                    code=200 if success else 400
                )
            flask.flash(f"{message}", "success" if success else "danger")
            return flask.redirect(next_url)
        if action == "export":
            profile_id = flask.request.args.get("profile_id")
            temp_file = os.path.abspath("profile")
            file_path = models.export_profile(profile_id, temp_file)
            name = models.get_profile_name(profile_id)
            return flask_util.send_and_remove_file(file_path, f"{name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip")


    @blueprint.route('/accounts')
    @login.login_required_when_activated
    def accounts():
        display_config = interfaces_util.get_edited_config()

        # service lists
        service_list = models.get_services_list()
        notifiers_list = models.get_notifiers_list()

        config_exchanges = display_config[commons_constants.CONFIG_EXCHANGES]
        return flask.render_template('accounts.html',
                                     ccxt_tested_exchanges=models.get_tested_exchange_list(),
                                     ccxt_simulated_tested_exchanges=models.get_simulated_exchange_list(),
                                     ccxt_other_exchanges=sorted(models.get_other_exchange_list()),
                                     exchanges_details=models.get_exchanges_details(config_exchanges),

                                     config_exchanges=config_exchanges,
                                     config_notifications=display_config[
                                         services_constants.CONFIG_CATEGORY_NOTIFICATION],
                                     config_services=display_config[services_constants.CONFIG_CATEGORY_SERVICES],

                                     services_list=service_list,
                                     notifiers_list=notifiers_list,
                                     )


    @blueprint.route('/config', methods=['POST'])
    @login.login_required_when_activated
    def config():
        next_url = flask.request.args.get("next", None)
        request_data = flask.request.get_json()
        success = True
        response = ""
        err_message = ""

        if request_data:

            # update trading config if required
            if constants.TRADING_CONFIG_KEY in request_data and request_data[constants.TRADING_CONFIG_KEY]:
                success = success and models.update_tentacles_activation_config(
                    request_data[constants.TRADING_CONFIG_KEY])
            else:
                request_data[constants.TRADING_CONFIG_KEY] = ""

            # update tentacles config if required
            if constants.TENTACLES_CONFIG_KEY in request_data and request_data[constants.TENTACLES_CONFIG_KEY]:
                success = success and models.update_tentacles_activation_config(
                    request_data[constants.TENTACLES_CONFIG_KEY])
            else:
                request_data[constants.TENTACLES_CONFIG_KEY] = ""

            # update evaluator config if required
            if constants.EVALUATOR_CONFIG_KEY in request_data and request_data[constants.EVALUATOR_CONFIG_KEY]:
                deactivate_others = False
                if constants.DEACTIVATE_OTHERS in request_data:
                    deactivate_others = request_data[constants.DEACTIVATE_OTHERS]
                success = success and models.update_tentacles_activation_config(
                    request_data[constants.EVALUATOR_CONFIG_KEY],
                    deactivate_others)
            else:
                request_data[constants.EVALUATOR_CONFIG_KEY] = ""

            # remove elements from global config if any to remove
            removed_elements_key = "removed_elements"
            if removed_elements_key in request_data and request_data[removed_elements_key]:
                update_success, err_message = models.update_global_config(request_data[removed_elements_key], delete=True)
                success = success and update_success
            else:
                request_data[removed_elements_key] = ""

            # update global config if required
            if constants.GLOBAL_CONFIG_KEY in request_data and request_data[constants.GLOBAL_CONFIG_KEY]:
                success, err_message = models.update_global_config(request_data[constants.GLOBAL_CONFIG_KEY])
            else:
                request_data[constants.GLOBAL_CONFIG_KEY] = ""

            response = {
                "evaluator_updated_config": request_data[constants.EVALUATOR_CONFIG_KEY],
                "trading_updated_config": request_data[constants.TRADING_CONFIG_KEY],
                "tentacle_updated_config": request_data[constants.TENTACLES_CONFIG_KEY],
                "global_updated_config": request_data[constants.GLOBAL_CONFIG_KEY],
                removed_elements_key: request_data[removed_elements_key]
            }

        if success:
            if request_data.get("restart_after_save", False):
                models.schedule_delayed_command(models.restart_bot)
            if next_url is not None:
                return flask.redirect(next_url)
            return util.get_rest_reply(flask.jsonify(response))
        else:
            return util.get_rest_reply(flask.jsonify(err_message), 500)


    @blueprint.route('/metrics_settings', methods=['POST'])
    @login.login_required_when_activated
    def metrics_settings():
        return util.get_rest_reply(flask.jsonify(models.activate_metrics(flask.request.get_json())))


    @blueprint.route('/beta_env_settings', methods=['POST'])
    @login.login_required_when_activated
    def beta_env_settings():
        return util.get_rest_reply(flask.jsonify(models.activate_beta_env(flask.request.get_json())))


    @blueprint.route('/config_actions', methods=['POST'])
    @login.login_required_when_activated
    def config_actions():
        # action = flask.request.args.get("action")
        return util.get_rest_reply("No specified action.", code=500)
