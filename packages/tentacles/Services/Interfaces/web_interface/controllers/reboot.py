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
    @blueprint.route("/wait_reboot")
    @login.login_required_when_activated
    def wait_reboot():
        trading_delay_info = flask.request.args.get("trading_delay_info", 'false').lower() == "true"
        next_url = flask.request.args.get("next", flask.url_for("home", trading_delay_info=trading_delay_info))
        reboot = flask.request.args.get("reboot", "false").lower() == "true"
        onboarding = flask.request.args.get("onboarding", 'false').lower() == "true"

        if reboot:
            return_val = flask.render_template(
                'wait_reboot.html',
                show_nab_bar=not onboarding,
                onboarding=onboarding,
                next_url=next_url,
                current_profile_name=models.get_current_profile().name,
            )
            if not models.is_rebooting():
                reboot_delay = 2
                # schedule reboot now that the page render has been computed
                models.restart_bot(delay=reboot_delay)
        else:
            return_val = flask.redirect(next_url)
        return return_val
