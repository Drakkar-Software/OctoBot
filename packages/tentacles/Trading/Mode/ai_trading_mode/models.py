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
Models for AI Trading Mode deep_agent_team.

These models define the inputs and outputs for the Deep Agent trading team,
ensuring consistent validation of trading signals, research, and allocation decisions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PortfolioState(BaseModel):
    """Current portfolio state for trading analysis."""
    model_config = ConfigDict(extra="allow")
    
    total_value: Optional[float] = Field(default=None, description="Total portfolio value")
    positions: Dict[str, float] = Field(default_factory=dict, description="Current positions by symbol")
    cash_available: Optional[float] = Field(default=None, description="Available cash for trading")
    margin_available: Optional[float] = Field(default=None, description="Available margin")


class StrategyConfig(BaseModel):
    """Trading strategy configuration."""
    model_config = ConfigDict(extra="allow")
    
    max_position_size: Optional[float] = Field(default=0.1, description="Maximum position size (0-1)")
    max_daily_loss: Optional[float] = Field(default=0.02, description="Maximum daily loss threshold")
    risk_per_trade: Optional[float] = Field(default=0.01, description="Risk per trade (0-1)")
    preferred_symbols: Optional[List[str]] = Field(default=None, description="Preferred trading symbols")
    min_trade_amount: Optional[float] = Field(default=None, description="Minimum trade amount")


class TradingTeamInput(BaseModel):
    """Input data for Deep Agent trading team execution."""
    model_config = ConfigDict(extra="allow")
    
    portfolio: PortfolioState = Field(..., description="Current portfolio state")
    market_data: Dict[str, Any] = Field(..., description="Market data for analysis")
    strategy: Optional[StrategyConfig] = Field(default=None, description="Trading strategy configuration")


class Signal(BaseModel):
    """Single trading signal."""
    model_config = ConfigDict(extra="forbid")
    
    symbol: str = Field(..., description="Trading symbol (e.g., 'BTC/USDT')")
    signal_type: str = Field(..., description="Signal type: 'bullish', 'bearish', or 'neutral'")
    strength: float = Field(..., ge=0.0, le=1.0, description="Signal strength (0-1)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in signal (0-1)")
    key_factors: List[str] = Field(default_factory=list, description="Key factors influencing signal")
    description: str = Field(..., description="Signal description and rationale")


class SignalAnalysisOutput(BaseModel):
    """Output from signal analysis agent."""
    model_config = ConfigDict(extra="allow")
    
    signals: List[Signal] = Field(default_factory=list, description="List of signals")
    market_overview: str = Field(default="", description="General market conditions summary")


class ResearchArgument(BaseModel):
    """Single research argument."""
    model_config = ConfigDict(extra="forbid")
    
    symbol: str = Field(..., description="Trading symbol")
    thesis: str = Field(..., description="Main thesis or argument")
    evidence: List[str] = Field(default_factory=list, description="Supporting evidence")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in argument")


class ResearchOutput(BaseModel):
    """Output from bull/bear research agents."""
    model_config = ConfigDict(extra="allow")
    
    position: str = Field(..., description="Position taken: 'bullish' or 'bearish'")
    arguments: List[ResearchArgument] = Field(default_factory=list, description="Main arguments")
    overall_thesis: str = Field(default="", description="Overall thesis summary")
    risk_assessment: str = Field(default="", description="Risk assessment for this position")


class RiskJudgment(BaseModel):
    """Risk judgment comparing bull and bear arguments."""
    model_config = ConfigDict(extra="forbid")
    
    verdict: str = Field(..., description="Verdict: 'bullish', 'bearish', or 'neutral'")
    bull_score: float = Field(..., ge=0.0, le=1.0, description="Score for bullish case (0-1)")
    bear_score: float = Field(..., ge=0.0, le=1.0, description="Score for bearish case (0-1)")
    key_risks: List[str] = Field(default_factory=list, description="Key risks identified")
    recommended_position_sizing: Dict[str, float] = Field(
        default_factory=dict, 
        description="Recommended position sizing by symbol"
    )
    rationale: str = Field(default="", description="Detailed rationale for verdict")


class Allocation(BaseModel):
    """Single portfolio allocation decision."""
    model_config = ConfigDict(extra="forbid")
    
    symbol: str = Field(..., description="Trading symbol")
    action: str = Field(..., description="Action: 'buy', 'sell', or 'hold'")
    target_percentage: float = Field(..., ge=0.0, le=100.0, description="Target allocation percentage")
    quantity_change: Optional[float] = Field(default=None, description="Quantity change for execution")
    reason: str = Field(default="", description="Reason for this allocation")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence in allocation")


class ExecutionPlan(BaseModel):
    """Execution plan for trading decisions."""
    model_config = ConfigDict(extra="allow")
    
    priority_order: List[str] = Field(default_factory=list, description="Order of execution by symbol")
    timing_recommendation: str = Field(
        default="immediate",
        description="Timing: 'immediate', 'limit_order', or 'wait'"
    )
    notes: str = Field(default="", description="Additional execution notes")


class DistributionOutput(BaseModel):
    """Output from distribution/allocation agent."""
    model_config = ConfigDict(extra="forbid")
    
    allocations: List[Allocation] = Field(..., description="Portfolio allocation decisions")
    total_risk_exposure: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Total risk exposure (0-1)"
    )
    execution_plan: Optional[ExecutionPlan] = Field(default=None, description="Execution plan")


class TradingTeamResult(BaseModel):
    """Final result from Deep Agent trading team."""
    model_config = ConfigDict(extra="allow")
    
    distribution: Optional[DistributionOutput] = Field(
        default=None,
        description="Final distribution/allocation decisions"
    )
    execution_plan: Optional[ExecutionPlan] = Field(
        default=None,
        description="Execution plan for trades"
    )
    raw_output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw output from the agent"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )
