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
Models for simple AI evaluator agents team.

These models are specific to the simple_ai_evaluator_agents_team tentacle
and define the validated output structure for deep agent evaluation results.
"""

from typing import Any, List, Optional, Union
import pydantic
from pydantic import BaseModel, ConfigDict, Field


class DeepAgentEvaluationResult(BaseModel):
    """Validated output structure for Deep Agent evaluation results.
    
    Enforces consistent output format across all deep agent evaluations.
    Used for post-processing validation (not request-time schema binding).
    
    This model is specific to simple_ai_evaluator_agents_team and ensures
    that agent outputs always conform to the expected structure.
    """
    model_config = ConfigDict(extra="forbid")
    
    eval_note: Union[int, float] = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Evaluation note from -1 (strong sell) to 1 (strong buy)"
    )
    eval_note_description: str = Field(
        ...,
        description="Detailed explanation of the evaluation"
    )
    confidence: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the evaluation (0-1)"
    )
    trend: Optional[str] = Field(
        default=None,
        description="Market trend assessment (e.g., 'uptrend', 'downtrend', 'ranging')"
    )
    risk_level: Optional[str] = Field(
        default=None,
        description="Risk assessment (e.g., 'low', 'medium', 'high')"
    )
    key_factors: Optional[List[str]] = Field(
        default=None,
        description="Key factors influencing the evaluation"
    )
    recommendation: Optional[str] = Field(
        default=None,
        description="Trading recommendation or action items"
    )
    
    @pydantic.model_validator(mode="before")
    @classmethod
    def normalize_eval_note(cls, data: Any) -> Any:
        """Normalize eval_note to valid float range.
        
        Ensures eval_note is always within [-1.0, 1.0] range.
        """
        if isinstance(data, dict) and "eval_note" in data:
            eval_note = data["eval_note"]
            if eval_note is not None:
                try:
                    eval_note = float(eval_note)
                    data["eval_note"] = max(-1.0, min(1.0, eval_note))
                except (ValueError, TypeError):
                    data["eval_note"] = 0.0
        return data
