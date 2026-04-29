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

import octobot_commons.authentication as authentication
import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.enums as commons_enums
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.controllers.community_authentication as community_authentication
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
import octobot_services.interfaces.util as interfaces_util
import octobot_trading.api as trading_api


def register(blueprint):
    @blueprint.route("/profiles_selector")
    @login.login_required_when_activated
    def profiles_selector():
        reboot = flask.request.args.get("reboot", "false").lower() == "true"
        onboarding = flask.request.args.get("onboarding", 'false').lower() == "true"
        use_cloud = flask.request.args.get("use_cloud", 'false').lower() == "true"
        models.wait_for_login_if_processing()

        # skip profile selector when forced profile
        if onboarding and models.get_forced_profile() is not None:
            return flask.redirect(flask.url_for("trading_type_selector", reboot=reboot, onboarding=onboarding))

        profiles = models.get_profiles(commons_enums.ProfileType.LIVE)
        current_profile = models.get_current_profile()
        display_config = interfaces_util.get_edited_config()

        config_exchanges = display_config[commons_constants.CONFIG_EXCHANGES]

        enabled_exchanges = trading_api.get_enabled_exchanges_names(display_config)
        media_url = flask.url_for("tentacle_media", _external=True)
        missing_tentacles = set()

        logged_in_email = None
        form = community_authentication.CommunityLoginForm(flask.request.form) \
            if flask.request.form else community_authentication.CommunityLoginForm()
        authenticator = authentication.Authenticator.instance()
        try:
            logged_in_email = authenticator.get_logged_in_email()
        except (authentication.AuthenticationRequired, authentication.UnavailableError, authentication.AuthenticationError):
            pass
        cloud_strategies = []
        try:
            cloud_strategies = models.get_cloud_strategies(authenticator)
        except Exception as err:
            # don't crash the page if this request fails
            commons_logging.get_logger("profile_selector").exception(
                err, True, f"Error when fetching cloud strategies: {err}"
            )
        display_intro = flask_util.BrowsingDataProvider.instance().get_and_unset_is_first_display(
            flask_util.BrowsingDataProvider.PROFILE_SELECTOR
        )
        return flask.render_template(
            'profiles_selector.html',
            show_nab_bar=not onboarding,
            onboarding=onboarding,
            read_only=True,
            use_cloud=use_cloud,
            reboot=reboot,
            display_intro=display_intro,

            current_logged_in_email=logged_in_email,
            selected_user_bot=models.get_selected_user_bot(),
            can_logout=models.can_logout(),
            form=form,

            current_profile=current_profile,
            profiles=profiles.values(),
            profiles_tentacles_details=models.get_profiles_tentacles_details(profiles),

            cloud_strategies=cloud_strategies,

            evaluator_config=models.get_evaluator_detailed_config(media_url, missing_tentacles),
            strategy_config=models.get_strategy_config(media_url, missing_tentacles),

            config_exchanges=config_exchanges,

            symbol_list=sorted(models.get_symbol_list(enabled_exchanges or config_exchanges)),
        )
