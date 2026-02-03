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
import octobot_services.constants as services_constants
import octobot_services.interfaces.util as interfaces_util
import tentacles.Services.Interfaces.web_interface.constants as constants
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.models.distributions.prediction_market as models_prediction_market
import tentacles.Services.Interfaces.web_interface.enums as enums
import tentacles.Services.Interfaces.web_interface.util as util
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
import octobot_trading.api as trading_api


def register(blueprint):
    @blueprint.route('/configuration')
    @blueprint.route('/configuration/<profile_id>')
    @login.login_required_when_activated
    def configuration(profile_id=None):
        requested_profile_id = profile_id
        current_profile = models.get_current_profile()
        
        if requested_profile_id and requested_profile_id != current_profile.profile_id:
            # Show profile switch UI for non-current profile
            requested_profile = models.get_profile(requested_profile_id)
            return flask.render_template(
                'distributions/prediction_market/configuration.html',
                show_profile_switch=True,
                requested_profile=requested_profile,
                current_profile=current_profile,
                current_profile_id=requested_profile_id,
                display_intro=False,
            )
        
        # Show normal configuration for current profile
        display_intro = flask_util.BrowsingDataProvider.instance().get_and_unset_is_first_display(
            flask_util.BrowsingDataProvider.get_distribution_key(
                models.get_distribution(),
                flask_util.BrowsingDataProvider.CONFIGURATION,
            )
        )
        display_config = interfaces_util.get_edited_config()
        enabled_exchanges = trading_api.get_enabled_exchanges_names(display_config)
        config_symbols = models.get_enabled_trading_pairs()
        first_symbol_pair = next(iter(config_symbols)) if config_symbols else []
        config_exchanges = models.get_json_exchange_config(display_config)
        trading_mode = models.get_config_activated_trading_mode()
        media_url = flask.url_for("tentacle_media", _external=True)
        tentacle_docs = ""
        trading_mode_name = trading_mode.get_name() if trading_mode else "Missing trading mode"
        if trading_mode:
            tentacle_docs = models.get_tentacle_documentation(trading_mode.get_name(), media_url)
        return flask.render_template(
            'distributions/prediction_market/configuration.html',
            show_profile_switch=False,
            selected_exchange=enabled_exchanges[0] if enabled_exchanges else (config_exchanges[0][models.NAME] if config_exchanges else None),
            config_exchanges=config_exchanges,
            exchanges_schema=models.get_json_exchanges_schema(models.get_tested_exchange_list(), enums.ExchangeConnectionType.WALLET),

            selected_pair=first_symbol_pair,
            trading_mode_name=trading_mode_name,
            tentacle_docs=tentacle_docs,

            simulated_portfolio=models.get_json_simulated_portfolio(display_config),
            portfolio_schema=models.JSON_PORTFOLIO_SCHEMA,
            trading_simulator_schema=models.JSON_TRADING_SIMULATOR_SCHEMA,
            config_trading_simulator=models.get_json_trading_simulator_config(display_config),
            reference_market=interfaces_util.get_reference_market(),

            current_profile_id=current_profile.profile_id,
            display_intro=display_intro,
        )

    @blueprint.route('/interfaces')
    @login.login_required_when_activated
    def interfaces():
        display_config = interfaces_util.get_edited_config()

        # service lists
        service_list = models_prediction_market.get_prediction_market_services()
        services_config = {
            service: config
            for service, config in display_config[services_constants.CONFIG_CATEGORY_SERVICES].items()
            if service in service_list
        }
        notifiers_list = models.get_notifiers_list()

        return flask.render_template(
            'distributions/prediction_market/interfaces.html',
            config_notifications=display_config[
             services_constants.CONFIG_CATEGORY_NOTIFICATION],
            config_services=services_config,
            services_list=service_list,
            notifiers_list=notifiers_list,
        )



    @blueprint.route('/interface_config', methods=['POST'])
    @login.login_required_when_activated
    def interface_config():
        next_url = flask.request.args.get("next", None)
        request_data = flask.request.get_json()
        success = True
        response = ""
        err_message = ""

        if request_data:
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

    @blueprint.route('/configuration', methods=['POST'])
    @login.login_required_when_activated
    def save_prediction_market_config():
        request_data = flask.request.get_json()
        success = False
        response = "Restart to apply."
        err_message = None
        try:
            models_prediction_market.save_prediction_market_configuration(
                request_data["exchange"],
                request_data["tradingPair"],
                request_data["exchangesConfig"],
                request_data["tradingSimulatorConfig"],
                request_data["simulatedPortfolioConfig"],
                request_data["tradingModeName"],
                request_data["tradingModeConfig"],
            )
            success = True
        except Exception as e:
            err_message = f"Failed to save prediction market configuration: {e.__class__.__name__}: {e}"
            commons_logging.get_logger("save_prediction_market_config").exception(
                e, True, f"{err_message} ({e.__class__.__name__})"
            )
        if success:
            return util.get_rest_reply(flask.jsonify(response))
        else:
            return util.get_rest_reply(flask.jsonify(err_message), 500)

    @blueprint.route('/profile')
    @login.login_required_when_activated
    def profile():
        selected_profile = flask.request.args.get("select", None)
        next_url = flask.request.args.get("next", flask.url_for('configuration'))
        if selected_profile is not None and selected_profile != models.get_current_profile().profile_id:
            models.select_profile(selected_profile)
            current_profile = models.get_current_profile()
            flask.flash(
                f"Selected the {current_profile.name} profile", "success"
            )
        return flask.redirect(next_url)
