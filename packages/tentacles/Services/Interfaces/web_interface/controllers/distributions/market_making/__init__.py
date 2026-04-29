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
import tentacles.Services.Interfaces.web_interface.controllers.portfolio
import tentacles.Services.Interfaces.web_interface.controllers.logs
import tentacles.Services.Interfaces.web_interface.controllers.dashboard
import tentacles.Services.Interfaces.web_interface.controllers.tentacles_config
import tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.dashboard
import tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.configuration
import tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.cloud


def register(blueprint):
    tentacles.Services.Interfaces.web_interface.controllers.portfolio.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.logs.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.dashboard.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.tentacles_config.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.dashboard.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.configuration.register(blueprint)
    tentacles.Services.Interfaces.web_interface.controllers.distributions.market_making.cloud.register(blueprint)


__all__ = [
    "register",
]
