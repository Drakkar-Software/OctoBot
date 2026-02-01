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
Deep Agent Evaluator Team.

Uses LangChain Deep Agents with the supervisor pattern:
- Manager agent orchestrates worker agents
- Workers: TA, Sentiment, RealTime analysis
- Summarization as final synthesis
- Long-term memory via /memories/ path

Inherits from AbstractDeepAgentsTeamChannelProducer for proper integration.
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


# Worker agent prompts
TECHNICAL_ANALYSIS_INSTRUCTIONS = """
You are a Technical Analysis AI expert. Analyze technical evaluator signals:

1. Examine TA signals: RSI, MACD, moving averages, Bollinger Bands, volume patterns, price action
2. Assess trend strength and direction
3. Consider timeframe context (longer timeframes more significant)
4. Evaluate indicator convergence/divergence

Output your analysis as JSON with:
- eval_note: float -1 (strong sell) to 1 (strong buy)
- confidence: float 0-1
- description: detailed explanation
- trend: "uptrend"/"downtrend"/"ranging" if clear
- key_indicators: list of important indicators
"""

SENTIMENT_ANALYSIS_INSTRUCTIONS = """
You are a Sentiment Analysis AI expert. Analyze market sentiment signals:

1. Review news sentiment, social media trends, fear/greed indicators
2. Assess overall market mood
3. Consider sentiment extremes and reversals
4. Evaluate consensus vs contrarian signals

Output your analysis as JSON with:
- eval_note: float -1 (very bearish) to 1 (very bullish)
- confidence: float 0-1
- description: detailed explanation
- sentiment_summary: overall market mood
"""

REALTIME_ANALYSIS_INSTRUCTIONS = """
You are a Real-Time Market Analysis AI expert. Analyze live market data:

1. Review order book imbalances, recent trades
2. Assess immediate price momentum
3. Consider liquidity conditions
4. Evaluate short-term price drivers

Output your analysis as JSON with:
- eval_note: float -1 (bearish momentum) to 1 (bullish momentum)
- confidence: float 0-1
- description: detailed explanation
- momentum: "strong"/"moderate"/"weak"
"""

SUMMARIZATION_INSTRUCTIONS = """
You are a Market Analysis Summarizer. Synthesize analyses from TA, Sentiment, and RealTime agents.

1. Weigh each analysis by confidence and relevance
2. Resolve conflicting signals with clear reasoning
3. Produce a final consensus recommendation

Output your synthesis as JSON with:
- eval_note: float -1 to 1 (final recommendation)
- eval_note_description: comprehensive summary
- confidence: float 0-1 (overall confidence)
- key_factors: list of main decision factors
"""

MANAGER_INSTRUCTIONS = """
You are the Evaluator Team Manager. Coordinate market analysis agents.

Your team:
- technical_analysis: Analyzes technical indicators
- sentiment_analysis: Analyzes market sentiment
- realtime_analysis: Analyzes live market data
- summarization: Synthesizes all analyses

Workflow:
1. Use write_todos to plan your approach
2. Delegate to technical_analysis, sentiment_analysis, realtime_analysis (can run in parallel concept)
3. After all three complete, send their outputs to summarization
4. Return the final synthesized result

Remember to save important insights to /memories/ for future reference.
"""


class DeepAgentEvaluatorTeamChannel(AbstractDeepAgentsTeamChannel):
    """Channel for DeepAgentEvaluatorTeam outputs."""
    pass


class DeepAgentEvaluatorTeamConsumer(AbstractDeepAgentsTeamChannelConsumer):
    """Consumer for DeepAgentEvaluatorTeam outputs."""
    pass


class DeepAgentEvaluatorTeam(AbstractDeepAgentsTeamChannelProducer):
    """
    Evaluator team using LangChain Deep Agents with supervisor pattern.
    
    Inherits from AbstractDeepAgentsTeamChannelProducer which handles:
    - Deep Agent creation with supervisor pattern
    - Worker subagent orchestration
    - Memory backend via /memories/ path
    
    Usage:
        team = DeepAgentEvaluatorTeam(ai_service=llm_service)
        result = await team.run(aggregated_data)
        eval_note, description = team.parse_evaluator_result(result)
    """
    
    TEAM_NAME = "DeepAgentEvaluatorTeam"
    TEAM_CHANNEL = DeepAgentEvaluatorTeamChannel
    TEAM_CONSUMER = DeepAgentEvaluatorTeamConsumer
    
    MAX_ITERATIONS = 10
    ENABLE_DEBATE = False
    
    def __init__(
        self,
        ai_service: typing.Optional[abstract_ai_service.AbstractAIService] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        channel: typing.Optional[DeepAgentEvaluatorTeamChannel] = None,
        team_id: typing.Optional[str] = None,
        include_ta: bool = True,
        include_sentiment: bool = True,
        include_realtime: bool = True,
        enable_debate: bool = False,
    ):
        """
        Initialize the Deep Agent evaluator team.
        
        Args:
            ai_service: The LLM service instance.
            model: LLM model to use.
            max_tokens: Maximum tokens for LLM responses.
            temperature: Temperature for LLM randomness.
            channel: Optional output channel.
            team_id: Unique identifier for this team instance.
            include_ta: Include technical analysis worker.
            include_sentiment: Include sentiment analysis worker.
            include_realtime: Include realtime analysis worker.
            enable_debate: Enable debate workflow with critic.
        """
        self.include_ta = include_ta
        self.include_sentiment = include_sentiment
        self.include_realtime = include_realtime
        self.ENABLE_DEBATE = enable_debate
        
        super().__init__(
            channel=channel,
            ai_service=ai_service,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            team_name=self.TEAM_NAME,
            team_id=team_id,
        )
    
    def get_worker_definitions(self) -> list[dict[str, typing.Any]]:
        """Get worker subagent definitions for the evaluator team."""
        workers = []
        
        if self.include_ta:
            workers.append({
                "name": "technical_analysis",
                "instructions": TECHNICAL_ANALYSIS_INSTRUCTIONS,
            })
        
        if self.include_sentiment:
            workers.append({
                "name": "sentiment_analysis",
                "instructions": SENTIMENT_ANALYSIS_INSTRUCTIONS,
            })
        
        if self.include_realtime:
            workers.append({
                "name": "realtime_analysis",
                "instructions": REALTIME_ANALYSIS_INSTRUCTIONS,
            })
        
        # Always include summarization
        workers.append({
            "name": "summarization",
            "instructions": SUMMARIZATION_INSTRUCTIONS,
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
            "name": "critic",
            "instructions": (
                "Critique the analysis, identify weaknesses in the reasoning, "
                "check for confirmation bias, and suggest improvements."
            ),
        }
    
    def _build_input_message(self, initial_data: typing.Dict[str, typing.Any]) -> str:
        """Build the input message for the supervisor."""
        aggregated_data = initial_data.get("aggregated_data", initial_data)
        missing_data_types = initial_data.get("missing_data_types", [])
        
        data_str = json.dumps(aggregated_data, indent=2, default=str)
        
        message = f"""
Analyze the following market data and provide a trading recommendation.

Market Data:
{data_str}
"""
        
        if missing_data_types:
            message += f"\nNote: Missing data types: {', '.join(missing_data_types)}"
        
        message += """

Coordinate with your team:
1. Send relevant data to technical_analysis, sentiment_analysis, realtime_analysis
2. Collect their analyses
3. Send all analyses to summarization for final synthesis
4. Return the final recommendation as JSON with eval_note and eval_note_description

Save any important market insights to /memories/market_insights/ for future reference.
"""
        return message
    
    def _parse_result(self, result: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """Parse the Deep Agent result."""
        try:
            messages = result.get("messages", [])
            if not messages:
                return {
                    "eval_note": common_constants.START_PENDING_EVAL_NOTE,
                    "eval_note_description": "No response from agent",
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
                    
                    eval_note = parsed.get("eval_note", common_constants.START_PENDING_EVAL_NOTE)
                    if isinstance(eval_note, (int, float)):
                        eval_note = max(-1, min(1, float(eval_note)))
                    
                    return {
                        "eval_note": eval_note,
                        "eval_note_description": parsed.get(
                            "eval_note_description",
                            parsed.get("description", content)
                        ),
                        "confidence": parsed.get("confidence", 0),
                        "key_factors": parsed.get("key_factors", []),
                    }
            except json.JSONDecodeError:
                pass
            
            # Fallback
            return {
                "eval_note": common_constants.START_PENDING_EVAL_NOTE,
                "eval_note_description": content,
            }
            
        except Exception as e:
            logger.error(f"Error parsing result: {e}")
            return {
                "eval_note": common_constants.START_PENDING_EVAL_NOTE,
                "eval_note_description": f"Error: {str(e)}",
            }
    
    async def run_with_data(
        self,
        aggregated_data: dict,
        missing_data_types: list | None = None,
    ) -> tuple[float | str, str]:
        """
        Convenience method to run the team with aggregated evaluator data.
        
        Args:
            aggregated_data: Dict mapping evaluator type to evaluations.
            missing_data_types: Optional list of missing data types.
        
        Returns:
            Tuple of (eval_note, eval_note_description).
        """
        initial_data = {
            "aggregated_data": aggregated_data,
            "missing_data_types": missing_data_types or [],
        }
        
        result = await self.run(initial_data)
        
        eval_note = result.get("eval_note", common_constants.START_PENDING_EVAL_NOTE)
        description = result.get("eval_note_description", "")
        
        return eval_note, description


def create_evaluator_team(
    ai_service: typing.Optional[abstract_ai_service.AbstractAIService] = None,
    model: typing.Optional[str] = None,
    include_ta: bool = True,
    include_sentiment: bool = True,
    include_realtime: bool = True,
    enable_debate: bool = False,
) -> DeepAgentEvaluatorTeam:
    """
    Factory function to create a Deep Agent evaluator team.
    
    Args:
        ai_service: The LLM service instance.
        model: LLM model to use.
        include_ta: Include technical analysis worker.
        include_sentiment: Include sentiment analysis worker.
        include_realtime: Include realtime analysis worker.
        enable_debate: Enable debate workflow.
    
    Returns:
        Configured DeepAgentEvaluatorTeam instance.
    """
    return DeepAgentEvaluatorTeam(
        ai_service=ai_service,
        model=model,
        include_ta=include_ta,
        include_sentiment=include_sentiment,
        include_realtime=include_realtime,
        enable_debate=enable_debate,
    )
