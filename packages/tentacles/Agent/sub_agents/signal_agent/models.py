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
from enum import Enum
from typing import List, Literal
from pydantic import BaseModel, Field, AliasChoices, field_validator, model_validator

from octobot_agents.models import AgentBaseModel


class SignalDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ConsensusLevel(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    CONFLICTING = "conflicting"


class MarketOutlook(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


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
    direction: SignalDirection = Field(
        description="Synthesized direction: 'bullish', 'bearish', or 'neutral'. Must be one of these exact values."
    )
    strength: float = Field(
        description="Signal strength as a number between 0.0 and 1.0. Must be a float, NOT a string like 'strong'.",
        ge=0.0,
        le=1.0
    )
    consensus_level: ConsensusLevel = Field(
        description="Level of agreement between signals: 'strong', 'moderate', 'weak', or 'conflicting'. "
                   "This is different from 'strength' - do NOT confuse them."
    )
    trading_instruction: str = Field(
        description="Clear trading instruction derived from signals. Must be a descriptive string."
    )

    @field_validator("consensus_level", mode="before")
    def normalize_consensus_level(cls, v):
        try:
            level = v.lower().strip()
            if level in {"neutral", "none", "no", "null", "n/a", "na", "unknown"}:
                level = ConsensusLevel.WEAK.value
            if level not in {item.value for item in ConsensusLevel}:
                raise ValueError(f"consensus_level must be one of {[item.value for item in ConsensusLevel]}")
            return level
        except AttributeError:
            pass
        return v

    @field_validator("direction", mode="before")
    def normalize_direction(cls, v):
        try:
            direction = v.lower().strip()
        except AttributeError:
            return v
        if direction in {"stable", "flat", "sideways", "range", "ranging"}:
            direction = SignalDirection.NEUTRAL.value
        if direction not in {item.value for item in SignalDirection}:
            raise ValueError(f"direction must be one of {[item.value for item in SignalDirection]}")
        return direction


class SignalSynthesisOutput(AgentBaseModel):
    """Output from the signal manager agent - synthesizes all signals."""
    __strict_json_schema__ = True

    synthesized_signals: List[SynthesizedSignal] = Field(
        description="List of synthesized signals per asset.",
        validation_alias=AliasChoices("synthesized_signals", "signals")
    )
    market_outlook: MarketOutlook = Field(
        description="Overall market outlook: 'bullish', 'bearish', 'neutral', 'mixed'."
    )
    summary: str = Field(
        description="Summary of the synthesized signals without making decisions."
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data):
        if isinstance(data, str):
            recovered = cls.recover_json_from_error(data)
            if recovered:
                return recovered
        if isinstance(data, dict):
            if "error" in data:
                recovered = cls.recover_json_from_error(data.get("error"))
                if recovered:
                    return recovered
            # Unwrap accidental wrapper payloads.
            synthesis = data.get("synthesis")
            if isinstance(synthesis, dict):
                data = synthesis
            # Some models return a single synthesized-signal object instead of
            # the required synthesis wrapper.
            if (
                "synthesized_signals" not in data
                and "signals" not in data
                and {"asset", "direction", "strength", "consensus_level", "trading_instruction"} <= set(data.keys())
            ):
                return {
                    "synthesized_signals": [data],
                    "market_outlook": "neutral",
                    "summary": "Recovered from malformed synthesis output.",
                }
        return data

    @model_validator(mode="after")
    def ensure_synthesis_present(self):
        if not self.synthesized_signals:
            raise ValueError("synthesized_signals must not be empty")
        return self

    @field_validator("market_outlook", mode="before")
    def normalize_market_outlook(cls, v):
        try:
            outlook = v.lower().strip()
        except AttributeError:
            return v
        allowed = {item.value for item in MarketOutlook}
        if outlook in allowed:
            return outlook
        for value in allowed:
            if outlook.startswith(value):
                return value
        has_bullish = "bullish" in outlook
        has_bearish = "bearish" in outlook
        if has_bullish and has_bearish:
            return MarketOutlook.MIXED.value
        if "neutral" in outlook or "stable" in outlook or "sideways" in outlook:
            return MarketOutlook.NEUTRAL.value
        if has_bullish:
            return MarketOutlook.BULLISH.value
        if has_bearish:
            return MarketOutlook.BEARISH.value
        raise ValueError(f"market_outlook must be one of {[item.value for item in MarketOutlook]}")
