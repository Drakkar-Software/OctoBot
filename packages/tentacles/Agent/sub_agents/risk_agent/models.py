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
Pydantic models for risk agent outputs.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

import octobot_agents.models as agent_models


class RiskMetrics(agent_models.AgentBaseModel):
    """Portfolio risk metrics."""
    __strict_json_schema__ = True
    overall_risk_level: str = Field(
        description="Overall risk level: 'low', 'medium', 'high', 'critical'."
    )
    concentration_risk: float = Field(
        ge=0.0,
        le=1.0,
        description="Risk from over-concentration in few assets (0-1)."
    )
    volatility_exposure: float = Field(
        ge=0.0,
        le=1.0,
        description="Exposure to volatile assets (0-1)."
    )
    liquidity_risk: float = Field(
        ge=0.0,
        le=1.0,
        description="Risk from illiquid positions (0-1)."
    )
    
    @field_validator("overall_risk_level")
    def validate_risk_level(cls, v: str) -> str:
        allowed_levels = ["low", "medium", "high", "critical"]
        v_lower = v.lower()
        if v_lower not in allowed_levels:
            raise ValueError(f"Risk level must be one of {allowed_levels}")
        return v_lower


class RiskAssessmentOutput(agent_models.AgentBaseModel):
    """Output from the risk assessment agent."""
    __strict_json_schema__ = True
    
    metrics: RiskMetrics = Field(description="Calculated risk metrics.")
    recommendations: List[str] = Field(
        description="Risk mitigation recommendations."
    )
    max_allocation_per_asset: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Maximum recommended allocation percentage per asset."
    )
    min_cash_reserve: Optional[float] = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum recommended cash/stablecoin reserve (0-1)."
    )
    reasoning: str = Field(description="Explanation of the risk assessment.")
