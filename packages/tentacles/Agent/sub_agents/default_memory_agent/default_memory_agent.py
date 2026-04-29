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

import typing

import octobot_agents.agent.memory as memory
import octobot_agents.models as agent_models


class DefaultMemoryAgentChannel(memory.MemoryAgentChannel):
    pass


class DefaultMemoryAgentConsumer(memory.MemoryAgentConsumer):
    pass


class DefaultMemoryAgentProducer(memory.MemoryAgentProducer):
    """
    Default memory agent - simple rule-based memory management.
    
    Inherits from MemoryAgentProducer. Uses simple heuristics instead of LLM.
    
    Note: This is a basic rule-based memory agent with limited learning capabilities.
    For advanced memory management (transformation of feedback into structured instructions),
    use DefaultAIMemoryAgentProducer which uses LLM-based analysis.
    """
    
    AGENT_CHANNEL = DefaultMemoryAgentChannel
    AGENT_CONSUMER = DefaultMemoryAgentConsumer
    
    def __init__(
        self,
        channel: typing.Optional[memory.MemoryAgentChannel] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        self_improving: bool = True,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            self_improving=self_improving,
            **kwargs,
        )
    
    async def execute(
        self,
        input_data: typing.Union[agent_models.MemoryInput, typing.Dict[str, typing.Any]],
        ai_service: typing.Any,
    ) -> agent_models.MemoryOperation:
        """
        Execute memory operations using simple heuristics.
        
        Args:
            input_data: Contains memory input data
            ai_service: The AI service instance (not used in rule-based approach)
            
        Returns:
            MemoryOperation with results
        """
        # Extract critic analysis if available
        critic_analysis = input_data.get("critic_analysis") if isinstance(input_data, dict) else None
        
        if not critic_analysis:
            return agent_models.MemoryOperation(
                success=False,
                operations=[],
                memory_ids=[],
                agent_updates={},
                agents_processed=[],
                agents_skipped=[],
                message="No critic analysis provided",
            )
        
        # Convert to model if needed
            critic_analysis = agent_models.CriticAnalysis.model_validate_or_self(critic_analysis)
        
        # Get agent improvements
        agent_improvements = critic_analysis.get_agent_improvements()
        
        if not agent_improvements:
            return agent_models.MemoryOperation(
                success=True,
                operations=[],
                memory_ids=[],
                agent_updates={},
                agents_processed=[],
                agents_skipped=[],
                message="No agents need memory updates",
            )
        
        return agent_models.MemoryOperation(
            success=True,
            operations=["heuristic_processed"],
            memory_ids=[],
            agent_updates={},
            agents_processed=list(agent_improvements.keys()),
            agents_skipped=[],
            message=f"Rule-based processing completed for {len(agent_improvements)} agents",
        )
