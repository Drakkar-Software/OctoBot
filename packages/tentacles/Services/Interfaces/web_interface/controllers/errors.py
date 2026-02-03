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

import octobot_commons.logging as bot_logging
import tentacles.Services.Interfaces.web_interface.util as util

APP_JSON_CONTENT_TYPE = "application/json"


def register(blueprint):
    @blueprint.errorhandler(404)
    def not_found(_):
        if flask.request.content_type == APP_JSON_CONTENT_TYPE:
            return util.get_rest_reply("We are sorry, but this doesn't exist", 404)
        return flask.render_template("404.html"), 404

    @blueprint.errorhandler(500)
    def internal_error(error):
        bot_logging.get_logger("WebInterfaceErrorHandler").exception(error.original_exception, True,
                                                                     f"Error when displaying page: "
                                                                     f"{error.original_exception}")
        if flask.request.content_type == APP_JSON_CONTENT_TYPE:
            return util.get_rest_reply(f"We are sorry, but an unexpected error occurred: {error.original_exception} "
                                       f"({error.original_exception.__class__.__name__})", 500)
        return flask.render_template("500.html",
                                     error=error.original_exception), 500
