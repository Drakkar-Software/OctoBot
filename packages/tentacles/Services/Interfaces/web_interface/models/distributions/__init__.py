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

from tentacles.Services.Interfaces.web_interface.models.distributions import market_making
from tentacles.Services.Interfaces.web_interface.models.distributions import prediction_market

from tentacles.Services.Interfaces.web_interface.models.distributions.market_making import (
    save_market_making_configuration,
    get_market_making_services,
)
from tentacles.Services.Interfaces.web_interface.models.distributions.prediction_market import (
    save_prediction_market_configuration,
    get_prediction_market_services,
)

__all__ = [
    "save_market_making_configuration",
    "get_market_making_services",
    "save_prediction_market_configuration",
    "get_prediction_market_services",
]
