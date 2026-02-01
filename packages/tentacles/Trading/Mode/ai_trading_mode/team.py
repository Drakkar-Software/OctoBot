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
AI Trading Agent Team.
Orchestrates Signal, Bull/Bear Research agents, Risk Judge, and Distribution agents for portfolio management.

DAG Structure:
    Signal ──┬──> Bull Research ──┐
             │                    │
             └──────> Bear Research ──┼──> Risk Judge ───> Distribution
                                      │
                                      └───────────────────┘
             
The Distribution agent receives inputs from Signal and Risk Judge.
"""
import typing

import octobot_agents as agent

from tentacles.Agent.sub_agents.signal_agent import (
    SignalAIAgentChannel,
    SignalAIAgentProducer,
)
from tentacles.Agent.sub_agents.bull_bear_research_agent import (
    BullResearchAIAgentChannel,
    BullResearchAIAgentProducer,
    BearResearchAIAgentChannel,
    BearResearchAIAgentProducer,
)
from tentacles.Agent.sub_agents.risk_judge_agent import RiskJudgeAIAgentProducer
from octobot_agents.team.judge.channels.judge_agent import AIJudgeAgentChannel
from tentacles.Agent.sub_agents.distribution_agent import (
    DistributionAIAgentChannel,
    DistributionAIAgentProducer,
    DistributionOutput,
)
from tentacles.Agent.sub_agents.default_critic_agent import DefaultAICriticAgentProducer
from tentacles.Agent.teams.default_manager_agent import AIToolsTeamManagerAgentProducer
from tentacles.Agent.sub_agents.default_memory_agent import DefaultAIMemoryAgentProducer


class TradingAgentTeamChannel(agent.AbstractAgentsTeamChannel):
    """Channel for TradingAgentTeam outputs."""
    OUTPUT_SCHEMA = DistributionOutput


class TradingAgentTeamConsumer(agent.AbstractAgentsTeamChannelConsumer):
    """Consumer for TradingAgentTeam outputs."""
    pass


class TradingAgentTeam(agent.AbstractSyncAgentsTeamChannelProducer):
    """
    Sync team that orchestrates trading agents for portfolio distribution.
    
    Execution flow:
    1. Signal agent analyzes cryptocurrencies and generates signals
    2. Bull and Bear research agents debate the market outlook
    3. Risk judge evaluates the debate and provides risk assessment
    4. Distribution agent makes final allocation decisions
    
    Usage:
        team = TradingAgentTeam(ai_service=llm_service)
        results = await team.run(agent_state)
        distribution_output = results["DistributionAgent"]["distribution_output"]
    """
    
    TEAM_NAME = "TradingAgentTeam"
    TEAM_CHANNEL = TradingAgentTeamChannel
    TEAM_CONSUMER = TradingAgentTeamConsumer
    
    CriticAgentClass = DefaultAICriticAgentProducer
    MemoryAgentClass = DefaultAIMemoryAgentProducer
    ManagerAgentClass = AIToolsTeamManagerAgentProducer
    
    def __init__(
        self,
        ai_service: typing.Any,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        channel: typing.Optional[TradingAgentTeamChannel] = None,
        team_id: typing.Optional[str] = None,
    ):
        """
        Initialize the trading agent team.
        
        Args:
            ai_service: The LLM service instance.
            model: LLM model to use for all agents.
            max_tokens: Maximum tokens for LLM responses.
            temperature: Temperature for LLM randomness.
            channel: Optional output channel for team results.
            team_id: Unique identifier for this team instance.
        """
        # Create agent producers
        signal_producer = SignalAIAgentProducer(
            channel=None,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        bull_producer = BullResearchAIAgentProducer(
            channel=None,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        bear_producer = BearResearchAIAgentProducer(
            channel=None,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        risk_judge_producer = RiskJudgeAIAgentProducer(
            channel=None,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        distribution_producer = DistributionAIAgentProducer(
            channel=None,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        # Store reference for result lookup
        self.distribution_producer = distribution_producer
        
        agents = [signal_producer, bull_producer, bear_producer, risk_judge_producer, distribution_producer]
        
        # Define relations:
        # Signal -> Bull Research (Bull needs signal data)
        # Signal -> Bear Research (Bear needs signal data)
        # Bull Research -> Risk Judge (Judge evaluates bull arguments)
        # Bear Research -> Risk Judge (Judge evaluates bear arguments)
        # Signal -> Distribution (Distribution needs signal outputs)
        # Risk Judge -> Distribution (Distribution needs risk assessment)
        relations = [
            (SignalAIAgentChannel, BullResearchAIAgentChannel),
            (SignalAIAgentChannel, BearResearchAIAgentChannel),
            (BullResearchAIAgentChannel, AIJudgeAgentChannel),
            (BearResearchAIAgentChannel, AIJudgeAgentChannel),
            (SignalAIAgentChannel, DistributionAIAgentChannel),
            (AIJudgeAgentChannel, DistributionAIAgentChannel),
        ]
        
        super().__init__(
            channel=channel,
            agents=agents,
            relations=relations,
            ai_service=ai_service,
            team_name=self.TEAM_NAME,
            team_id=team_id,
            self_improving=True,
        )
    
    async def run_with_state(
        self,
        state: dict,
    ) -> typing.Optional["DistributionOutput"]:
        """
        Convenience method to run the team with an agent state dict.
        
        Args:
            state: Dict containing portfolio, strategy data, etc.
            
        Returns:
            DistributionOutput from the distribution agent, or None on error.
        """
        # Run the team
        results = await self.run(state)
        
        # Extract distribution result using the actual agent name
        distribution_result = results.get(self.distribution_producer.name)
        if distribution_result is None:
            return None
        
        # Handle nested result format from tools-driven manager
        # The result is wrapped as {"agent_name": "...", "result": actual_output}
        if isinstance(distribution_result, dict) and "result" in distribution_result:
            actual_result = distribution_result["result"]
        else:
            actual_result = distribution_result
        
        # The actual result should contain distribution_output
        if isinstance(actual_result, dict) and "distribution_output" in actual_result:
            return actual_result["distribution_output"]
        
        # Direct DistributionOutput object
        return actual_result
