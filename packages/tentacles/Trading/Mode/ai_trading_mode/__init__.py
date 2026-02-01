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

from .ai_index_trading import AIIndexTradingMode
from .ai_index_distribution import apply_ai_instructions

from .team import (
    TradingAgentTeamChannel,
    TradingAgentTeamConsumer,
    TradingAgentTeam,
)

from .deep_agent_team import (
    DeepAgentTradingTeamChannel,
    DeepAgentTradingTeamConsumer,
    DeepAgentTradingTeam,
    create_trading_team,
)
