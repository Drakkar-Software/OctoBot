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
Pydantic models for sentiment analysis agent outputs.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

import octobot_agents.models as agent_models


class SentimentMetrics(agent_models.AgentBaseModel):
    __strict_json_schema__ = True
    """Sentiment analysis metrics."""
    sentiment_score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Sentiment score from -1 (very negative) to 1 (very positive)."
    )
    
    @field_validator("sentiment_score")
    def validate_score(cls, v: float) -> float:
        return max(-1.0, min(1.0, v))


class SentimentAnalysisOutput(agent_models.AgentBaseModel):
    """Output from the sentiment analysis agent."""
    __strict_json_schema__ = True
    
    eval_note: float = Field(
        ge=-1.0,
        le=1.0,
        description="Evaluation score from -1 (very negative) to 1 (very positive)."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level of the sentiment analysis (0-1)."
    )
    description: str = Field(
        description="Summary description of the sentiment analysis."
    )
    sentiment_score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Detailed sentiment score from -1 to 1. Same as eval_note."
    )
    sources_analyzed: Optional[List[str]] = Field(
        default=None,
        description="Data sources used for sentiment analysis. Leave empty if none identified."
    )
    key_mentions: Optional[List[str]] = Field(
        default=None,
        description="Key mentions or topics driving sentiment. Leave empty if none."
    )
    market_implications: Optional[str] = Field(
        default=None,
        description="Implications of sentiment for market direction. Leave empty if unclear."
    )
    recommendations: Optional[List[str]] = Field(
        default=None,
        description="Trading recommendations based on sentiment. Leave empty if none."
    )
