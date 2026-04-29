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
Pydantic models for technical analysis agent outputs.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

import octobot_agents.models as agent_models


class TechnicalAnalysisOutput(agent_models.AgentBaseModel):
    __strict_json_schema__ = True
    """Output from the technical analysis agent."""
    eval_note: float = Field(
        ge=-1.0,
        le=1.0,
        description="Evaluation score from -1 (strong sell) to 1 (strong buy)."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level of the analysis (0-1)."
    )
    description: str = Field(
        description="Summary description of the technical analysis."
    )
    trend: Optional[str] = Field(
        default=None,
        description="Current market trend: 'uptrend', 'downtrend', 'sideways'. Leave empty if unclear."
    )
    support_level: Optional[float] = Field(
        default=None,
        description="Identified support level price. Leave empty if no clear support identified."
    )
    resistance_level: Optional[float] = Field(
        default=None,
        description="Identified resistance level price. Leave empty if no clear resistance identified."
    )
    key_indicators: Optional[List[str]] = Field(
        default=None,
        description="Key technical indicators analyzed. Leave empty if no relevant indicators."
    )
    recommendations: Optional[List[str]] = Field(
        default=None,
        description="Trading recommendations based on technical analysis. Leave empty if no specific recommendations."
    )
    
    @field_validator("trend")
    def validate_trend(cls, v: str) -> str:
        if v is None:
            return None
        allowed_trends = ["uptrend", "downtrend", "sideways"]
        v_lower = v.lower()
        if v_lower not in allowed_trends:
            raise ValueError(f"Trend must be one of {allowed_trends}")
        return v_lower
