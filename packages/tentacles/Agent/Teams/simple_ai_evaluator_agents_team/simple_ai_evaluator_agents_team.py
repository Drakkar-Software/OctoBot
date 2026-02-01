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
Simple AI Evaluator Agent Team.
Orchestrates TA, Sentiment, and RealTime agents feeding into a Summarization agent.

DAG Structure:
    TechnicalAnalysis ──┐
    SentimentAnalysis ──┼──> Summarization
    RealTimeAnalysis ───┘
"""
import typing

import octobot_commons.constants as common_constants

import octobot_agents as agent

from tentacles.Agent.sub_agents.technical_analysis_agent import (
    TechnicalAnalysisAIAgentChannel,
    TechnicalAnalysisAIAgentProducer,
)
from tentacles.Agent.sub_agents.sentiment_analysis_agent import (
    SentimentAnalysisAIAgentChannel,
    SentimentAnalysisAIAgentProducer,
)
from tentacles.Agent.sub_agents.real_time_analysis_agent import (
    RealTimeAnalysisAIAgentChannel,
    RealTimeAnalysisAIAgentProducer,
)
from tentacles.Agent.sub_agents.summarization_agent import (
    SummarizationAIAgentChannel,
    SummarizationAIAgentProducer,
)
from tentacles.Agent.sub_agents.default_critic_agent import DefaultAICriticAgentProducer
from tentacles.Agent.teams.default_manager_agent import AIPlanTeamManagerAgentProducer
from tentacles.Agent.sub_agents.default_memory_agent import DefaultAIMemoryAgentProducer


class SimpleAIEvaluatorAgentsTeamChannel(agent.AbstractAgentsTeamChannel):
    """Channel for SimpleAIEvaluatorAgentsTeam outputs."""
    pass


class SimpleAIEvaluatorAgentsTeamConsumer(agent.AbstractAgentsTeamChannelConsumer):
    """Consumer for SimpleAIEvaluatorAgentsTeam outputs."""
    pass


class SimpleAIEvaluatorAgentsTeam(agent.AbstractSyncAgentsTeamChannelProducer):
    """
    Sync team that orchestrates evaluator agents.
    
    Execution flow:
    1. TechnicalAnalysis, SentimentAnalysis, RealTimeAnalysis run in parallel
    2. Their outputs feed into Summarization
    3. Summarization produces final eval_note and description
    
    Usage:
        team = SimpleAIEvaluatorAgentsTeam(ai_service=llm_service)
        results = await team.run(aggregated_data)
        # results["SummarizationAgent"] contains the final output
    """
    
    TEAM_NAME = "SimpleAIEvaluatorAgentsTeam"
    TEAM_CHANNEL = SimpleAIEvaluatorAgentsTeamChannel
    TEAM_CONSUMER = SimpleAIEvaluatorAgentsTeamConsumer
    
    CriticAgentClass = DefaultAICriticAgentProducer
    MemoryAgentClass = DefaultAIMemoryAgentProducer
    ManagerAgentClass = AIPlanTeamManagerAgentProducer
    
    def __init__(
        self,
        ai_service: typing.Any,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        channel: SimpleAIEvaluatorAgentsTeamChannel | None = None,
        team_id: str | None = None,
        include_ta: bool = True,
        include_sentiment: bool = True,
        include_realtime: bool = True,
    ):
        """
        Initialize the evaluator agent team.
        
        Args:
            ai_service: The LLM service instance.
            model: LLM model to use for all agents.
            max_tokens: Maximum tokens for LLM responses.
            temperature: Temperature for LLM randomness.
            channel: Optional output channel for team results.
            team_id: Unique identifier for this team instance.
            include_ta: Whether to include TechnicalAnalysis agent.
            include_sentiment: Whether to include SentimentAnalysis agent.
            include_realtime: Whether to include RealTimeAnalysis agent.
        """
        # Create agent producers
        agents = []
        relations = []
        
        if include_ta:
            ta_producer = TechnicalAnalysisAIAgentProducer(
                channel=None,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            agents.append(ta_producer)
            relations.append((TechnicalAnalysisAIAgentChannel, SummarizationAIAgentChannel))
        
        if include_sentiment:
            sentiment_producer = SentimentAnalysisAIAgentProducer(
                channel=None,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            agents.append(sentiment_producer)
            relations.append((SentimentAnalysisAIAgentChannel, SummarizationAIAgentChannel))
        
        if include_realtime:
            realtime_producer = RealTimeAnalysisAIAgentProducer(
                channel=None,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            agents.append(realtime_producer)
            relations.append((RealTimeAnalysisAIAgentChannel, SummarizationAIAgentChannel))
        
        # Always include summarization as the terminal agent
        summarization_producer = SummarizationAIAgentProducer(
            channel=None,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        agents.append(summarization_producer)
        # Store reference for result lookup
        self.summarization_producer = summarization_producer
        
        super().__init__(
            channel=channel,
            agents=agents,
            relations=relations,
            ai_service=ai_service,
            team_name=self.TEAM_NAME,
            team_id=team_id,
            self_improving=True,
        )
    
    async def run_with_data(
        self,
        aggregated_data: dict,
        missing_data_types: list | None = None,
    ) -> tuple[float | str, str]:
        """
        Convenience method to run the team with aggregated evaluator data.
        
        Uses Deep Agent file system for context management between agents.
        Analysis results are saved to /analysis/* for cross-agent access.
        
        Args:
            aggregated_data: Dict mapping evaluator type to list of evaluations.
            missing_data_types: Optional list of missing evaluator types.
            
        Returns:
            Tuple of (eval_note, eval_note_description).
        """
        # Clear transient files from previous runs
        self.clear_transient_files()
        
        # Build input data for entry agents based on their type
        initial_data = {
            "aggregated_data": aggregated_data,
            "missing_data_types": missing_data_types or [],
        }
        
        # Run the team
        results = await self.run(initial_data)
        
        # Save analysis results to file system for debugging/audit
        for agent_name, result in results.items():
            self.save_analysis(agent_name.lower(), result)
        
        # Extract summarization result using the actual agent name
        summarization_result = results.get(self.summarization_producer.name)
        if summarization_result is None:
            return common_constants.START_PENDING_EVAL_NOTE, "Error: Summarization agent did not produce output"
        
        # Handle tuple result from SummarizationAIAgentProducer
        if isinstance(summarization_result, tuple):
            return summarization_result
        
        # Handle dict result
        try:
            eval_note = summarization_result.get("eval_note", common_constants.START_PENDING_EVAL_NOTE)
            description = summarization_result.get("eval_note_description", "")
            return eval_note, description
        except AttributeError:
            # Not a dict, return as-is
            return common_constants.START_PENDING_EVAL_NOTE, "Error: Unexpected result format from summarization agent"
