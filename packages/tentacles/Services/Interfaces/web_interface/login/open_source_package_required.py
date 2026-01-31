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
import functools

import octobot.constants as constants
import tentacles.Services.Interfaces.web_interface.models as models


def open_source_package_required(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if models.has_open_source_package():
            return func(*args, **kwargs)
        flask.flash(f"The {constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME} is required to use this page")
        return flask.redirect(flask.url_for('extensions'))
    return decorated_view
