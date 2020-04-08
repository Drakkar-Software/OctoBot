#  Drakkar-Software OctoBot
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
from enum import Enum


class CommunityFields(Enum):
    ID = "_id"
    CURRENT_SESSION = "currentsession"
    STARTED_AT = "startedat"
    UP_TIME = "uptime"
    SIMULATOR = "simulator"
    TRADER = "trader"
    EVAL_CONFIG = "evalconfig"
    PAIRS = "pairs"
    EXCHANGES = "exchanges"
    NOTIFICATIONS = "notifications"
    TYPE = "type"
    PLATFORM = "platform"
    REFERENCE_MARKET = "referencemarket"
    PORTFOLIO_VALUE = "portfoliovalue"
    PROFITABILITY = "profitability"
