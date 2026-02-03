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

import octobot.disclaimer as disclaimer
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.flask_util as flask_util


def register(blueprint):
    @blueprint.route("/terms")
    @login.login_required_when_activated
    def terms():
        return flask.render_template("terms.html",
                                     disclaimer=disclaimer.DISCLAIMER,
                                     accepted_terms=models.accepted_terms())


    @blueprint.route("/accept_terms")
    @login.login_required_when_activated
    def accept_terms():
        next_url = flask.request.args.get("next", None)
        if flask.request.args.get("accept_terms", None) == "True":
            models.accept_terms(True)
            flask_util.BrowsingDataProvider.instance().set_first_displays(True)
            return flask.redirect(next_url or flask.url_for("home"))
        return flask.redirect(flask.url_for("terms"))
