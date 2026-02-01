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
Pydantic models for signal agent outputs.
"""
from typing import List, Literal
from pydantic import BaseModel, Field, AliasChoices

from octobot_agents.models import AgentBaseModel


class SignalRecommendation(AgentBaseModel):
    """A trading signal recommendation for an asset."""
    __strict_json_schema__ = True
    action: Literal["buy", "sell", "hold", "increase", "decrease"] = Field(
        description="Trading action: 'buy', 'sell', 'hold', 'increase', 'decrease'."
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence level of the signal (0 to 1)."
    )
    reasoning: str = Field(
        description="Explanation of why this signal was generated."
    )


class CryptoSignalOutput(AgentBaseModel):
    """Output from a cryptocurrency signal agent."""
    __strict_json_schema__ = True
    
    cryptocurrency: str = Field(description="The cryptocurrency being analyzed.")
    signal: SignalRecommendation = Field(description="The trading signal for this cryptocurrency.")
    market_context: str = Field(description="Brief description of current market context.")
    key_factors: List[str] = Field(
        default_factory=list,
        description="Key factors influencing this signal."
    )


class SynthesizedSignal(AgentBaseModel):
    """A synthesized signal for an asset combining multiple signal sources.
    
    Strict schema enforcement: All fields are required with correct types.
    The LLM must return the exact format specified.
    """
    __strict_json_schema__ = True
    asset: str = Field(
        description="The asset symbol (e.g., 'BTC', 'ETH'). Must be a string.",
        validation_alias=AliasChoices("asset", "symbol")
    )
    direction: Literal["bullish", "bearish", "neutral"] = Field(
        description="Synthesized direction: 'bullish', 'bearish', or 'neutral'. Must be one of these exact values."
    )
    strength: float = Field(
        description="Signal strength as a number between 0.0 and 1.0. Must be a float, NOT a string like 'strong'.",
        ge=0.0,
        le=1.0
    )
    consensus_level: Literal["strong", "moderate", "weak", "conflicting"] = Field(
        description="Level of agreement between signals: 'strong', 'moderate', 'weak', or 'conflicting'. "
                   "This is different from 'strength' - do NOT confuse them."
    )
    trading_instruction: str = Field(
        description="Clear trading instruction derived from signals. Must be a descriptive string."
    )


class SignalSynthesisOutput(AgentBaseModel):
    """Output from the signal manager agent - synthesizes all signals."""
    __strict_json_schema__ = True
    
    synthesized_signals: List[SynthesizedSignal] = Field(
        description="List of synthesized signals per asset.",
        validation_alias=AliasChoices("synthesized_signals", "signals")
    )
    market_outlook: Literal["bullish", "bearish", "neutral", "mixed"] = Field(
        description="Overall market outlook: 'bullish', 'bearish', 'neutral', 'mixed'."
    )
    summary: str = Field(
        description="Summary of the synthesized signals without making decisions."
    )
