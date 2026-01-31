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

import octobot.community as community
import tentacles.Services.Interfaces.web_interface.login as login
import tentacles.Services.Interfaces.web_interface.models as models
import tentacles.Services.Interfaces.web_interface.util as util


def register(blueprint):
    @blueprint.route("/select_bot", methods=['POST'])
    @login.login_required_when_activated
    def select_bot():
        if not models.can_select_bot():
            return util.get_rest_reply(flask.jsonify("Can't select bot on this setup"), 500)
        models.select_bot(flask.request.get_json())
        bot = models.get_selected_user_bot()
        flask.flash(f"Selected {bot['name']} bot", "success")
        return flask.jsonify(bot)


    @blueprint.route("/create_bot", methods=['POST'])
    @login.login_required_when_activated
    def create_bot():
        if not models.can_select_bot():
            return util.get_rest_reply(flask.jsonify("Can't create bot on this setup"), 500)
        new_bot = models.create_new_bot()
        models.select_bot(community.CommunityUserAccount.get_bot_id(new_bot))
        bot = models.get_selected_user_bot()
        flask.flash(f"Created and selected {bot['name']} bot", "success")
        return flask.jsonify(bot)
