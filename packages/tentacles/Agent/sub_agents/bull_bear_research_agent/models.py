#  Drakkar-Software OctoBot-Tentacles
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

"""Output models for bull/bear research debate agents."""
from typing import Optional
from octobot_agents.models import AgentBaseModel


class ResearchDebateOutput(AgentBaseModel):
    """Output from a research debate agent (bull or bear): message for the debate."""
    __strict_json_schema__ = True
    message: str
    reasoning: Optional[str] = None
