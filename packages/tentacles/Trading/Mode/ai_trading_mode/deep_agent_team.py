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
Deep Agent Trading Team.

Uses LangChain Deep Agents with the supervisor pattern for trading decisions:
- Manager agent orchestrates specialized worker agents
- Workers: Signal, Bull Research, Bear Research, Risk Judge, Distribution
- Skills for extensible trading strategies
- Long-term memory via /memories/ path for market insights

This is the Deep Agent version of the TradingAgentTeam in team.py.
Instead of DAG-based execution, the Deep Agent supervisor handles orchestration.

See:
- https://docs.langchain.com/oss/python/deepagents/subagents
- https://docs.langchain.com/oss/python/deepagents/skills
"""
from __future__ import annotations

import typing
import json
import logging

import octobot_commons.constants as common_constants

from octobot_agents.team.channels.deep_agents_team import (
    AbstractDeepAgentsTeamChannel,
    AbstractDeepAgentsTeamChannelConsumer,
    AbstractDeepAgentsTeamChannelProducer,
)
from octobot_agents.agent.channels.deep_agent import (
    DEEP_AGENTS_AVAILABLE,
    build_dictionary_subagent,
)
from octobot_agents.constants import MEMORIES_PATH_PREFIX
import octobot_services.services.abstract_ai_service as abstract_ai_service

logger = logging.getLogger(__name__)


# =============================================================================
# Worker Agent Prompts
# =============================================================================

SIGNAL_AGENT_INSTRUCTIONS = """
You are a Signal Analysis AI expert for cryptocurrency trading.

Your responsibilities:
1. Analyze market signals from multiple sources (price, volume, order flow)
2. Identify potential trading opportunities
3. Generate preliminary signal assessments

For each cryptocurrency, analyze:
- Price trends and momentum
- Volume patterns and anomalies
- Order book imbalances
- Recent news and events impact

Output your analysis as JSON with:
{
    "signals": [
        {
            "symbol": "BTC/USDT",
            "signal_type": "bullish" | "bearish" | "neutral",
            "strength": 0.0-1.0,
            "confidence": 0.0-1.0,
            "key_factors": ["factor1", "factor2"],
            "description": "..."
        }
    ],
    "market_overview": "General market conditions summary"
}

Save important signal patterns to /memories/signals/ for future reference.
"""

BULL_RESEARCH_INSTRUCTIONS = """
You are a Bull Research AI analyst advocating for bullish positions.

Your role in the team:
1. Receive signals from the Signal agent
2. Make the strongest possible case FOR buying/holding
3. Identify all potential upside catalysts
4. Challenge bearish arguments with counterpoints

Research focus:
- Bullish technical patterns (breakouts, support holds, trend continuations)
- Positive fundamental factors (adoption, partnerships, development activity)
- Market sentiment shifts that favor bulls
- Historical patterns that preceded rallies

Output your analysis as JSON with:
{
    "bull_case": {
        "thesis": "Main bullish argument",
        "catalysts": ["catalyst1", "catalyst2"],
        "price_targets": {"short_term": ..., "medium_term": ...},
        "confidence": 0.0-1.0,
        "risk_factors": ["risk1", "risk2"]
    },
    "counterarguments_to_bears": ["counter1", "counter2"]
}

Be thorough but honest - acknowledge weaknesses in the bull case.
"""

BEAR_RESEARCH_INSTRUCTIONS = """
You are a Bear Research AI analyst advocating for bearish/cautious positions.

Your role in the team:
1. Receive signals from the Signal agent
2. Make the strongest possible case for SELLING/reducing exposure
3. Identify all potential downside risks
4. Challenge bullish arguments with counterpoints

Research focus:
- Bearish technical patterns (breakdowns, resistance fails, trend reversals)
- Negative fundamental factors (regulatory, competition, technical issues)
- Market sentiment that favors bears
- Historical patterns that preceded corrections

Output your analysis as JSON with:
{
    "bear_case": {
        "thesis": "Main bearish argument",
        "risks": ["risk1", "risk2"],
        "price_targets": {"support_levels": [...], "worst_case": ...},
        "confidence": 0.0-1.0,
        "catalysts_for_downside": ["catalyst1"]
    },
    "counterarguments_to_bulls": ["counter1", "counter2"]
}

Be thorough but honest - acknowledge weaknesses in the bear case.
"""

RISK_JUDGE_INSTRUCTIONS = """
You are a Risk Judge AI that evaluates bull vs bear arguments objectively.

Your role in the team:
1. Review both Bull Research and Bear Research analyses
2. Weigh the strength of each side's arguments
3. Identify which case is more compelling and why
4. Provide a balanced risk assessment

Evaluation criteria:
- Quality of evidence presented
- Logical consistency of arguments
- Historical accuracy of similar predictions
- Risk/reward asymmetry
- Current market regime context

Output your analysis as JSON with:
{
    "judgment": {
        "winner": "bull" | "bear" | "neutral",
        "confidence": 0.0-1.0,
        "reasoning": "Detailed explanation of judgment",
        "bull_score": 0.0-1.0,
        "bear_score": 0.0-1.0,
        "key_deciding_factors": ["factor1", "factor2"]
    },
    "risk_assessment": {
        "overall_risk": "low" | "medium" | "high",
        "risk_factors": ["factor1", "factor2"],
        "recommended_position_size_modifier": 0.5-1.5
    }
}

Be impartial - your job is to find truth, not favor either side.
"""

DISTRIBUTION_AGENT_INSTRUCTIONS = """
You are a Portfolio Distribution AI that makes final allocation decisions.

Your role in the team:
1. Receive the Risk Judge's assessment
2. Consider the original signal analysis
3. Determine optimal portfolio allocation
4. Provide actionable trading recommendations

Decision factors:
- Risk Judge's verdict and confidence
- Signal strength and quality
- Current portfolio state
- Market liquidity conditions
- Risk management constraints

Output your analysis as JSON with:
{
    "distribution": {
        "allocations": [
            {
                "symbol": "BTC/USDT",
                "action": "buy" | "sell" | "hold",
                "target_percentage": 0.0-100.0,
                "quantity_change": ...,
                "reason": "..."
            }
        ],
        "total_risk_exposure": 0.0-1.0
    },
    "execution_plan": {
        "priority_order": ["symbol1", "symbol2"],
        "timing_recommendation": "immediate" | "limit_order" | "wait",
        "notes": "..."
    }
}

Always respect risk limits and never recommend over-leveraging.
Save distribution decisions to /memories/distributions/ for tracking.
"""

MANAGER_INSTRUCTIONS = """
You coordinate the AI Trading Team to make informed trading decisions.

Your team:
- signal_analyst: Analyzes market signals and opportunities
- bull_researcher: Makes the case for bullish positions
- bear_researcher: Makes the case for bearish positions  
- risk_judge: Evaluates bull vs bear arguments objectively
- distribution_agent: Makes final allocation decisions

Workflow:
1. Use write_todos to plan your approach
2. Send market data to signal_analyst first
3. Pass signal output to both bull_researcher AND bear_researcher
4. Send both research outputs to risk_judge for evaluation
5. Pass judge's verdict + signals to distribution_agent for final allocation
6. Return the distribution result

Important:
- Ensure each worker receives the context it needs from previous workers
- Save important market insights to /memories/market_insights/
- If any worker provides low-confidence output, consider requesting clarification
"""


class DeepAgentTradingTeamChannel(AbstractDeepAgentsTeamChannel):
    """Channel for DeepAgentTradingTeam outputs."""
    pass


class DeepAgentTradingTeamConsumer(AbstractDeepAgentsTeamChannelConsumer):
    """Consumer for DeepAgentTradingTeam outputs."""
    pass


class DeepAgentTradingTeam(AbstractDeepAgentsTeamChannelProducer):
    """
    Trading team using LangChain Deep Agents with supervisor pattern.
    
    This is the Deep Agent version of TradingAgentTeam. Instead of DAG-based
    execution with channel producers, the Deep Agent supervisor handles
    orchestration of worker subagents.
    
    Features:
    - Supervisor pattern for natural language orchestration
    - Subagent context isolation for cleaner execution
    - Skills for extensible trading strategies
    - Long-term memory for market insights
    
    Usage:
        team = DeepAgentTradingTeam(ai_service=llm_service)
        result = await team.run(market_data)
    """
    
    TEAM_NAME = "DeepAgentTradingTeam"
    TEAM_CHANNEL = DeepAgentTradingTeamChannel
    TEAM_CONSUMER = DeepAgentTradingTeamConsumer
    
    MAX_ITERATIONS = 15
    ENABLE_DEBATE = True  # Enable bull vs bear debate with risk judge
    
    def __init__(
        self,
        ai_service: typing.Optional[abstract_ai_service.AbstractAIService] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        channel: typing.Optional[DeepAgentTradingTeamChannel] = None,
        team_id: typing.Optional[str] = None,
        include_signal: bool = True,
        include_bull_bear: bool = True,
        include_risk_judge: bool = True,
        skills: list[str] | None = None,
    ):
        """
        Initialize the Deep Agent trading team.
        
        Args:
            ai_service: The LLM service instance.
            model: LLM model to use.
            max_tokens: Maximum tokens for LLM responses.
            temperature: Temperature for LLM randomness.
            channel: Optional output channel.
            team_id: Unique identifier for this team instance.
            include_signal: Include signal analysis worker.
            include_bull_bear: Include bull/bear research workers.
            include_risk_judge: Include risk judge worker.
            skills: Optional list of skill directories.
        """
        self.include_signal = include_signal
        self.include_bull_bear = include_bull_bear
        self.include_risk_judge = include_risk_judge
        
        super().__init__(
            channel=channel,
            ai_service=ai_service,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            team_name=self.TEAM_NAME,
            team_id=team_id,
            skills=skills,
        )
    
    def get_worker_definitions(self) -> list[dict[str, typing.Any]]:
        """Get worker subagent definitions for the trading team."""
        workers = []
        
        if self.include_signal:
            workers.append({
                "name": "signal_analyst",
                "description": "Analyzes market signals and identifies trading opportunities",
                "instructions": SIGNAL_AGENT_INSTRUCTIONS,
            })
        
        if self.include_bull_bear:
            workers.append({
                "name": "bull_researcher",
                "description": "Makes the bullish case for positions, identifies upside catalysts",
                "instructions": BULL_RESEARCH_INSTRUCTIONS,
            })
            workers.append({
                "name": "bear_researcher",
                "description": "Makes the bearish case, identifies downside risks",
                "instructions": BEAR_RESEARCH_INSTRUCTIONS,
            })
        
        if self.include_risk_judge:
            workers.append({
                "name": "risk_judge",
                "description": "Evaluates bull vs bear arguments and provides risk assessment",
                "instructions": RISK_JUDGE_INSTRUCTIONS,
            })
        
        # Always include distribution agent
        workers.append({
            "name": "distribution_agent",
            "description": "Makes final portfolio allocation decisions",
            "instructions": DISTRIBUTION_AGENT_INSTRUCTIONS,
        })
        
        return workers
    
    def get_manager_instructions(self) -> str:
        """Get the manager/supervisor instructions."""
        return MANAGER_INSTRUCTIONS
    
    def get_critic_config(self) -> dict[str, typing.Any] | None:
        """Get critic configuration for debate mode."""
        if not self.ENABLE_DEBATE:
            return None
        return {
            "name": "trading_critic",
            "description": "Critiques trading decisions and identifies blind spots",
            "instructions": (
                "Critique the trading analysis and decisions. Look for:\n"
                "- Confirmation bias in research\n"
                "- Missing risk factors\n"
                "- Over-confidence in predictions\n"
                "- Logical inconsistencies\n"
                "Suggest improvements to the analysis."
            ),
        }
    
    def _build_input_message(self, initial_data: typing.Dict[str, typing.Any]) -> str:
        """Build the input message for the trading supervisor."""
        portfolio = initial_data.get("portfolio", {})
        market_data = initial_data.get("market_data", initial_data)
        strategy = initial_data.get("strategy", {})
        
        data_str = json.dumps({
            "portfolio": portfolio,
            "market_data": market_data,
            "strategy": strategy,
        }, indent=2, default=str)
        
        return f"""
Analyze the market and provide trading recommendations.

Current State:
{data_str}

Workflow:
1. Start with signal_analyst to identify opportunities
2. Have bull_researcher and bear_researcher debate the outlook
3. Let risk_judge evaluate the arguments
4. Have distribution_agent make final allocations

Return the final distribution decision as JSON.
Save important insights to /memories/trading_insights/ for future reference.
""".strip()
    
    def _parse_result(self, result: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """Parse the Deep Agent result into trading output."""
        try:
            messages = result.get("messages", [])
            if not messages:
                return {
                    "distribution": None,
                    "error": "No response from agent",
                }
            
            # Get the last assistant message
            last_message = messages[-1]
            content = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
            
            # Try to parse as JSON
            try:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    parsed = json.loads(json_str)
                    
                    return {
                        "distribution": parsed.get("distribution"),
                        "execution_plan": parsed.get("execution_plan"),
                        "raw_output": parsed,
                    }
            except json.JSONDecodeError:
                pass
            
            # Fallback
            return {
                "distribution": None,
                "raw_output": content,
            }
            
        except Exception as e:
            logger.error(f"Error parsing result: {e}")
            return {
                "distribution": None,
                "error": str(e),
            }
    
    async def run_with_portfolio(
        self,
        portfolio: dict,
        market_data: dict,
        strategy: dict | None = None,
    ) -> dict:
        """
        Convenience method to run the team with structured trading data.
        
        Args:
            portfolio: Current portfolio state.
            market_data: Market data for analysis.
            strategy: Optional strategy configuration.
        
        Returns:
            Dict with distribution recommendations.
        """
        initial_data = {
            "portfolio": portfolio,
            "market_data": market_data,
            "strategy": strategy or {},
        }
        
        return await self.run(initial_data)


def create_trading_team(
    ai_service: typing.Optional[abstract_ai_service.AbstractAIService] = None,
    model: typing.Optional[str] = None,
    skills: list[str] | None = None,
) -> DeepAgentTradingTeam:
    """
    Factory function to create a Deep Agent trading team.
    
    Args:
        ai_service: The LLM service instance.
        model: LLM model to use.
        skills: Optional skill directories.
    
    Returns:
        Configured DeepAgentTradingTeam instance.
    """
    return DeepAgentTradingTeam(
        ai_service=ai_service,
        model=model,
        skills=skills,
    )
