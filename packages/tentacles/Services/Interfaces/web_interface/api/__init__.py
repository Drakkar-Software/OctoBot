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

import tentacles.Services.Interfaces.web_interface.api.config
import tentacles.Services.Interfaces.web_interface.api.exchanges
import tentacles.Services.Interfaces.web_interface.api.feedback
import tentacles.Services.Interfaces.web_interface.api.metadata
import tentacles.Services.Interfaces.web_interface.api.trading
import tentacles.Services.Interfaces.web_interface.api.user_commands
import tentacles.Services.Interfaces.web_interface.api.bots
import tentacles.Services.Interfaces.web_interface.api.webhook
import tentacles.Services.Interfaces.web_interface.api.tentacles_packages
import tentacles.Services.Interfaces.web_interface.api.dsl

from tentacles.Services.Interfaces.web_interface.api.webhook import (
    has_webhook,
    register_webhook
)



def register(distribution: octobot.enums.OctoBotDistribution):
    blueprint = flask.Blueprint('api', __name__, url_prefix='/api', template_folder="")
    if distribution is octobot.enums.OctoBotDistribution.DEFAULT:
        tentacles.Services.Interfaces.web_interface.api.feedback.register(blueprint)
        tentacles.Services.Interfaces.web_interface.api.bots.register(blueprint)
        tentacles.Services.Interfaces.web_interface.api.webhook.register(blueprint)
        tentacles.Services.Interfaces.web_interface.api.tentacles_packages.register(blueprint)

    elif distribution is octobot.enums.OctoBotDistribution.MARKET_MAKING:
        pass

    elif distribution is octobot.enums.OctoBotDistribution.PREDICTION_MARKET:
        pass

    # common routes
    tentacles.Services.Interfaces.web_interface.api.config.register(blueprint)
    tentacles.Services.Interfaces.web_interface.api.exchanges.register(blueprint)
    tentacles.Services.Interfaces.web_interface.api.metadata.register(blueprint)
    tentacles.Services.Interfaces.web_interface.api.trading.register(blueprint)
    tentacles.Services.Interfaces.web_interface.api.user_commands.register(blueprint)
    tentacles.Services.Interfaces.web_interface.api.dsl.register(blueprint)
    return blueprint


__all__ = [
    "has_webhook",
    "register_webhook",
    "register",
]
