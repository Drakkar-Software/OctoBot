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
import octobot.enums

import tentacles.Services.Interfaces.web_interface.advanced_controllers.configuration
import tentacles.Services.Interfaces.web_interface.advanced_controllers.home
import tentacles.Services.Interfaces.web_interface.advanced_controllers.matrix
import tentacles.Services.Interfaces.web_interface.advanced_controllers.strategy_optimizer
import tentacles.Services.Interfaces.web_interface.advanced_controllers.tentacles_management


def register(distribution: octobot.enums.OctoBotDistribution):
    blueprint = flask.Blueprint('advanced', __name__, url_prefix='/advanced', template_folder="../advanced_templates")
    if distribution is octobot.enums.OctoBotDistribution.DEFAULT:
        tentacles.Services.Interfaces.web_interface.advanced_controllers.configuration.register(blueprint)
        tentacles.Services.Interfaces.web_interface.advanced_controllers.home.register(blueprint)
        tentacles.Services.Interfaces.web_interface.advanced_controllers.matrix.register(blueprint)
        tentacles.Services.Interfaces.web_interface.advanced_controllers.strategy_optimizer.register(blueprint)
        tentacles.Services.Interfaces.web_interface.advanced_controllers.tentacles_management.register(blueprint)

    return blueprint


__all__ = [
    "register",
]
