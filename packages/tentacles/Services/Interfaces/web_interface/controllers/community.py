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
import octobot.constants as constants
import octobot_services.interfaces.util as interfaces_util
import octobot.community.errors
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models


def register(blueprint):
    @blueprint.route("/community")
    @login.login_required_when_activated
    def community():
        authenticator = authentication.Authenticator.instance()
        logged_in_email = None
        use_preview = not authenticator.can_authenticate()
        all_user_bots = []
        try:
            models.wait_for_login_if_processing()
            logged_in_email = authenticator.get_logged_in_email()
            all_user_bots = models.get_all_user_bots()
        except authentication.AuthenticationError as err:
            # force logout and redirect to login
            flask.flash(f"Your session expired, please re-authenticate to your account.", "error")
            interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().logout())
            return flask.redirect('community_login')
        except (authentication.AuthenticationRequired, authentication.UnavailableError):
            # not authenticated
            pass
        except Exception as e:
            flask.flash(f"Error when contacting the community server: {e}", "error")
        if logged_in_email is None and not use_preview:
            return flask.redirect('community_login')
        strategies = models.get_cloud_strategies(authenticator)
        return flask.render_template(
            'community.html',
            current_logged_in_email=logged_in_email,
            role=authenticator.user_account.supports.support_role,
            is_donor=bool(authenticator.user_account.supports.is_donor()),
            strategies=strategies,
            current_bots_stats=models.get_current_octobots_stats(),
            all_user_bots=all_user_bots,
            selected_user_bot=models.get_selected_user_bot(),
            can_logout=models.can_logout(),
            can_select_bot=models.can_select_bot(),
            has_owned_packages_to_install=models.has_owned_packages_to_install(),
        )


    @blueprint.route("/community_metrics")
    @login.login_required_when_activated
    def community_metrics():
        return flask.redirect("/")
        can_get_metrics = models.can_get_community_metrics()
        display_metrics = models.get_community_metrics_to_display() if can_get_metrics else None
        return flask.render_template('community_metrics.html',
                                     can_get_metrics=can_get_metrics,
                                     community_metrics=display_metrics
                                     )

    @blueprint.route("/extensions")
    @login.login_required_when_activated
    def extensions():
        refresh_packages = flask.request.args.get("refresh_packages") if flask.request.args else "false"
        loop = flask.request.args.get("loop") if flask.request.args else "false"
        authenticator = authentication.Authenticator.instance()
        logged_in_email = None
        try:
            models.wait_for_login_if_processing()
            logged_in_email = authenticator.get_logged_in_email()
            if refresh_packages.lower() == "true":
                models.update_owned_packages()
        except (authentication.AuthenticationRequired, authentication.UnavailableError, authentication.AuthenticationError):
            pass
        except Exception as e:
            flask.flash(f"Error when contacting the community server: {e}", "error")
        return flask.render_template(
            'extensions.html',
            current_logged_in_email=logged_in_email,
            is_community_authenticated=logged_in_email is not None,
            price=constants.OCTOBOT_EXTENSION_PACKAGE_1_PRICE,
            auto_refresh_packages=refresh_packages and loop == "true",
            has_owned_packages_to_install=models.has_owned_packages_to_install(),
        )

    @blueprint.route("/tradingview_email_config")
    @login.login_required_when_activated
    def tradingview_email_config():
        models.wait_for_login_if_processing()
        return flask.render_template(
            'tradingview_email_config.html',
            is_community_authenticated=authentication.Authenticator.instance().is_logged_in(),
            tradingview_email_address=models.get_tradingview_email_address(),
        )
