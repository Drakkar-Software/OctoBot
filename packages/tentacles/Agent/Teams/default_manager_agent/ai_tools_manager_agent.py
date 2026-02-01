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
AI tools team manager agent - uses LLM with tools to decide execution flow.
"""
import typing
from typing import TYPE_CHECKING

from octobot_agents.team.manager import (
    AIToolsManagerAgentChannel,
    AIToolsManagerAgentConsumer,
    AIToolsManagerAgentProducer,
    AbstractTeamManagerAgent,
)

if TYPE_CHECKING:
    from octobot_agents.models import ManagerInput


class AIToolsTeamManagerAgentChannel(AIToolsManagerAgentChannel):
    """Channel for AI tools team manager."""
    __slots__ = ()


class AIToolsTeamManagerAgentConsumer(AIToolsManagerAgentConsumer):
    """Consumer for AI tools team manager."""
    __slots__ = ()


class AIToolsTeamManagerAgentProducer(AIToolsManagerAgentProducer):
    """
    AI tools team manager agent - uses LLM with tools to decide execution flow.
    
    Inherits from AIToolsManagerAgentProducer. Has Channel, Producer, Consumer components (as all AI agents do).
    """
    
    AGENT_CHANNEL: typing.Type[AIToolsManagerAgentChannel] = AIToolsTeamManagerAgentChannel
    AGENT_CONSUMER: typing.Type[AIToolsManagerAgentConsumer] = AIToolsTeamManagerAgentConsumer
    
    def __init__(
        self,
        channel: typing.Optional[AIToolsTeamManagerAgentChannel] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        max_tool_calls: typing.Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            max_tool_calls=max_tool_calls,
            **kwargs,
        )
    
    def _get_default_prompt(self) -> str:
        """
        Return the default prompt for the AI tools team manager.
        
        Returns:
            The default system prompt string.
        """
        return """You are a tools-driven team execution manager for an agent team system.
Your role is to analyze the team structure, current state, and any instructions,
then coordinate execution using available tools. You have access to tools to run agents and debates.

Available tools:
- run_agent: Execute a specific agent by name
- run_debate: Run a debate between multiple agents with a judge
- finish: Complete execution and return current results

Use these tools to coordinate the team execution. Call finish when you have sufficient results."""