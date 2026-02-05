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
Pydantic models for distribution agent outputs.
"""
from typing import Dict, List
from pydantic import BaseModel, Field, field_validator, AliasChoices, model_validator

from octobot_agents.models import AgentBaseModel

from .constants import (
    INSTRUCTION_ACTION,
    INSTRUCTION_SYMBOL,
    INSTRUCTION_WEIGHT,
    ACTION_REDUCE_EXPOSURE,
    ACTION_INCREASE_EXPOSURE,
    ACTION_ADD_TO_DISTRIBUTION,
    ACTION_REMOVE_FROM_DISTRIBUTION,
    ACTION_UPDATE_RATIO,
)


class AssetDistribution(AgentBaseModel):
    """Distribution allocation for a single asset.
    
    Strict schema enforcement: All fields are required with correct types.
    The LLM must return the exact format specified.
    """
    __strict_json_schema__ = True
    asset: str = Field(description="Asset symbol (e.g., 'BTC', 'ETH', 'USD'). Must be a string.")
    percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Allocation percentage as a number between 0.0 and 100.0. Must be a float.",
        validation_alias=AliasChoices("percentage", "target_percentage", "target_allocation", "allocation", "weight", "ratio")
    )
    action: str = Field(
        description="Action to take. Must be one of: 'increase', 'decrease', 'maintain', 'add', 'remove'."
    )
    explanation: str = Field(
        description="Explanation for this allocation. Must be a descriptive string explaining the reasoning."
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_missing_action(cls, data):
        try:
            if "action" not in data:
                data["action"] = "maintain"
        except Exception:
            return data
        return data
    
    @field_validator("action")
    def validate_action(cls, v: str) -> str:
        allowed_actions = ["increase", "decrease", "maintain", "add", "remove"]
        v_lower = v.lower()
        if v_lower not in allowed_actions:
            raise ValueError(f"Action must be one of {allowed_actions}")
        return v_lower


class DistributionOutput(AgentBaseModel):
    """Output from the distribution agent - final portfolio distribution."""
    __strict_json_schema__ = True
    
    distributions: List[AssetDistribution] = Field(
        description="Target distribution for each asset.",
        validation_alias=AliasChoices("distributions", "allocations")
    )
    rebalance_urgency: str = Field(
        description="Urgency of rebalancing: 'immediate', 'soon', 'low', 'none'."
    )
    reasoning: str = Field(
        description="Overall reasoning for the distribution decisions."
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data):
        wrapper_keys = {"distributions", "allocations", "rebalance_urgency", "reasoning"}
        percentage_keys = {"percentage", "target_percentage", "target_allocation", "allocation", "weight", "ratio"}
        recovered_reasoning = "Recovered from malformed distribution output."

        if isinstance(data, list):
            return {
                "distributions": data,
                "rebalance_urgency": "none",
                "reasoning": recovered_reasoning,
            }
        if isinstance(data, str):
            recovered = cls.recover_json_from_error(data)
            if recovered:
                return recovered
        if isinstance(data, dict):
            if "error" in data:
                recovered = cls.recover_json_from_error(data.get("error"))
                if recovered:
                    return recovered
                if not (wrapper_keys & set(data.keys())):
                    return {
                        "distributions": [],
                        "rebalance_urgency": "none",
                        "reasoning": "",
                    }
            has_wrapper_fields = bool(wrapper_keys & set(data.keys()))
            is_single_distribution = (
                "asset" in data
                and bool(percentage_keys & set(data.keys()))
            )
            if not has_wrapper_fields and is_single_distribution:
                return {
                    "distributions": [data],
                    "rebalance_urgency": "none",
                    "reasoning": recovered_reasoning,
                }
            if "distributions" in data or "allocations" in data:
                data.setdefault("rebalance_urgency", "none")
                data.setdefault("reasoning", recovered_reasoning)
        return data
    
    @field_validator("rebalance_urgency")
    def validate_urgency(cls, v: str) -> str:
        allowed_urgency = ["immediate", "soon", "low", "none"]
        v_lower = v.lower()
        if v_lower not in allowed_urgency:
            raise ValueError(f"Urgency must be one of {allowed_urgency}")
        return v_lower
    
    def get_distribution_dict(self) -> Dict[str, float]:
        """Convert distributions to a simple dict format."""
        return {d.asset: d.percentage for d in self.distributions}
    
    def get_ai_instructions(self) -> List[dict]:
        """Convert distributions to AI instruction format for ai_index_distribution."""
        instructions = []
        for dist in self.distributions:
            if dist.action == "increase":
                instructions.append({
                    INSTRUCTION_ACTION: ACTION_INCREASE_EXPOSURE,
                    INSTRUCTION_SYMBOL: dist.asset,
                    INSTRUCTION_WEIGHT: dist.percentage,
                })
            elif dist.action == "decrease":
                instructions.append({
                    INSTRUCTION_ACTION: ACTION_REDUCE_EXPOSURE,
                    INSTRUCTION_SYMBOL: dist.asset,
                    INSTRUCTION_WEIGHT: dist.percentage,
                })
            elif dist.action == "add":
                instructions.append({
                    INSTRUCTION_ACTION: ACTION_ADD_TO_DISTRIBUTION,
                    INSTRUCTION_SYMBOL: dist.asset,
                    INSTRUCTION_WEIGHT: dist.percentage,
                })
            elif dist.action == "remove":
                instructions.append({
                    INSTRUCTION_ACTION: ACTION_REMOVE_FROM_DISTRIBUTION,
                    INSTRUCTION_SYMBOL: dist.asset,
                })
            elif dist.action == "maintain":
                instructions.append({
                    INSTRUCTION_ACTION: ACTION_UPDATE_RATIO,
                    INSTRUCTION_SYMBOL: dist.asset,
                    INSTRUCTION_WEIGHT: dist.percentage,
                })
        
        return instructions
