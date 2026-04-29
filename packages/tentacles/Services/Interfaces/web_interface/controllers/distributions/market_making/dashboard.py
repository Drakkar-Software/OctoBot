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
import time
import flask

import octobot_commons.authentication as authentication
import octobot_services.interfaces.util as interfaces_util
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util
import tentacles.Services.Interfaces.web_interface.constants as web_constants
import octobot.constants as constants
import octobot_commons.constants
import octobot_commons.enums


def register(blueprint):
    @blueprint.route("/")
    @blueprint.route("/home")
    @login.login_required_when_activated
    def home():
        if flask.request.args.get("reset_tutorials", "False").lower() == "true":
            flask_util.BrowsingDataProvider.instance().set_first_displays(True)
        if models.accepted_terms():
            display_intro = flask_util.BrowsingDataProvider.instance().get_and_unset_is_first_display(
                flask_util.BrowsingDataProvider.get_distribution_key(
                    models.get_distribution(),
                    flask_util.BrowsingDataProvider.HOME,
                )
            )
            all_time_frames = models.get_all_watched_time_frames()
            display_time_frame = models.get_display_timeframe()
            display_orders = models.get_display_orders()
            sandbox_exchanges = models.get_sandbox_exchanges()
            past_launch_time = (
                web_constants.PRODUCT_HUNT_ANNOUNCEMENT_DAY
                + (
                    octobot_commons.enums.TimeFramesMinutes[octobot_commons.enums.TimeFrames.ONE_DAY]
                    * octobot_commons.constants.MINUTE_TO_SECONDS
                )
            )
            is_launching = (
               web_constants.PRODUCT_HUNT_ANNOUNCEMENT_DAY
               <= time.time()
               <= past_launch_time
            )

            display_ph_launch = (
                models.get_display_announcement(web_constants.PRODUCT_HUNT_ANNOUNCEMENT) or is_launching
            ) and not time.time() > past_launch_time
            return flask.render_template(
                'distributions/market_making/dashboard.html',
                display_intro=display_intro,
                reference_unit=interfaces_util.get_reference_market(),
                display_time_frame=display_time_frame,
                display_orders=display_orders,
                all_time_frames=all_time_frames,
                sandbox_exchanges=sandbox_exchanges,
                display_ph_launch=display_ph_launch,
                is_launching=is_launching,
            )
        else:
            return flask.redirect(flask.url_for("terms"))

    @blueprint.route("/welcome")
    def welcome():
        # used in terms page
        return flask.redirect(flask.url_for("home"))
