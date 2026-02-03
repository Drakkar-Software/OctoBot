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
import octobot.enums

import tentacles.Services.Interfaces.web_interface.controllers.octobot_authentication
import tentacles.Services.Interfaces.web_interface.controllers.community_authentication
import tentacles.Services.Interfaces.web_interface.controllers.backtesting
import tentacles.Services.Interfaces.web_interface.controllers.commands
import tentacles.Services.Interfaces.web_interface.controllers.about
import tentacles.Services.Interfaces.web_interface.controllers.community
import tentacles.Services.Interfaces.web_interface.controllers.configuration
import tentacles.Services.Interfaces.web_interface.controllers.tentacles_config
import tentacles.Services.Interfaces.web_interface.controllers.dashboard
import tentacles.Services.Interfaces.web_interface.controllers.errors
import tentacles.Services.Interfaces.web_interface.controllers.octobot_help
import tentacles.Services.Interfaces.web_interface.controllers.home
import tentacles.Services.Interfaces.web_interface.controllers.interface_settings
import tentacles.Services.Interfaces.web_interface.controllers.logs
import tentacles.Services.Interfaces.web_interface.controllers.medias
import tentacles.Services.Interfaces.web_interface.controllers.terms
import tentacles.Services.Interfaces.web_interface.controllers.trading
import tentacles.Services.Interfaces.web_interface.controllers.portfolio
import tentacles.Services.Interfaces.web_interface.controllers.profiles
import tentacles.Services.Interfaces.web_interface.controllers.automation
import tentacles.Services.Interfaces.web_interface.controllers.reboot
import tentacles.Services.Interfaces.web_interface.controllers.welcome
import tentacles.Services.Interfaces.web_interface.controllers.robots
import tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making
import tentacles.Services.Interfaces.web_interface.controllers.distributions.prediction_market
import tentacles.Services.Interfaces.web_interface.controllers.dsl


def register(blueprint, distribution: octobot.enums.OctoBotDistribution):
    if distribution is octobot.enums.OctoBotDistribution.DEFAULT:
        tentacles.Services.Interfaces.web_interface.controllers.community_authentication.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.backtesting.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.about.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.community.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.configuration.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.tentacles_config.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.dashboard.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.octobot_help.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.home.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.interface_settings.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.logs.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.trading.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.portfolio.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.profiles.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.automation.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.welcome.register(blueprint)
        tentacles.Services.Interfaces.web_interface.controllers.dsl.register(blueprint)
    elif distribution is octobot.enums.OctoBotDistribution.MARKET_MAKING:
        tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.register(blueprint)
    elif distribution is octobot.enums.OctoBotDistribution.PREDICTION_MARKET:
        tentacles.Services.Interfaces.web_interface.controllers.distributions.prediction_market.register(blueprint)
    # common routes
    tentacles.Services.Interfaces.web_interface.controllers.octobot_authentication.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.robots.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.reboot.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.terms.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.errors.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.commands.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.medias.register(blueprint)


__all__ = [
    "register",
]
