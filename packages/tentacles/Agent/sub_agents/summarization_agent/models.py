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

"""
Pydantic models for summarization agent outputs.
"""
from pydantic import BaseModel, Field

import octobot_agents.models as agent_models


class SummarizationOutput(agent_models.AgentBaseModel):
    __strict_json_schema__ = True
    """Output from the summarization agent."""
    eval_note: float = Field(
        ge=-1.0,
        le=1.0,
        description="Final evaluation score from -1 (strong sell) to 1 (strong buy)."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level of the final analysis (0-1)."
    )
    description: str = Field(
        description="Comprehensive summary of market analysis including key consensus points, overall outlook (bullish/bearish/mixed), key recommendations, and identified risks."
    )
