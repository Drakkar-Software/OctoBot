#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import abc
import typing
from typing import TYPE_CHECKING, Optional

import octobot_commons.logging as logging

from octobot_agents.agent.channels.agent import (
    AbstractAgentChannel,
    AbstractAgentChannelConsumer,
    AbstractAgentChannelProducer,
)
from octobot_agents.agent.channels.ai_agent import (
    AbstractAIAgentChannel,
    AbstractAIAgentChannelConsumer,
    AbstractAIAgentChannelProducer,
)
import octobot_agents.models as models
import octobot_services.services.abstract_ai_service as abstract_ai_service


class AbstractMemoryAgent(abc.ABC):
    """
    Base interface for all memory agents.

    Memory agents are responsible for managing agent memories based on critic analysis.
    """

    def __init__(self, self_improving: bool = True):
        """Initialize the memory agent."""
        self.self_improving = self_improving
        self.logger = None  # Will be set by subclasses

    @abc.abstractmethod
    async def execute(
        self,
        input_data: typing.Union[models.MemoryInput, typing.Dict[str, typing.Any]],
        ai_service: abstract_ai_service.AbstractAIService
    ) -> models.MemoryOperation:
        """
        Execute memory operations based on critic analysis.

        Args:
            input_data: Contains {"critic_analysis": CriticAnalysis, "agent_outputs": Dict, "execution_metadata": dict}
            ai_service: The AI service instance (for AI memory agents)

        Returns:
            MemoryOperation with list of operations performed
        """
        raise NotImplementedError("execute must be implemented by subclasses")

    @staticmethod
    def _get_agent_from_team(
        team_producer: typing.Optional[typing.Any],
        agent_name: str
    ) -> Optional["AbstractAIAgentChannelProducer"]:
        """
        Get agent instance from team producer (manager or regular agent).

        Args:
            team_producer: The team producer instance.
            agent_name: Name of the agent to retrieve.

        Returns:
            The agent instance if found, None otherwise.
        """
        if not team_producer:
            return None
        manager = team_producer.get_manager()
        if manager and manager.name == agent_name:
            return manager
        return team_producer.get_agent_by_name(agent_name)

    @staticmethod
    def _collect_all_agent_names(
        agent_outputs: typing.Dict[str, typing.Any],
        team_producer: typing.Optional[typing.Any]
    ) -> typing.Set[str]:
        """
        Collect all agent names from outputs and team producer.

        Args:
            agent_outputs: Dict of agent outputs.
            team_producer: The team producer instance.

        Returns:
            Set of all agent names.
        """
        all_agent_names = set(agent_outputs.keys())
        if team_producer:
            manager = team_producer.get_manager()
            if manager:
                try:
                    all_agent_names.add(manager.name)
                except AttributeError:
                    pass
        return all_agent_names


# -----------------------------------------------------------------------------
# Base (non-AI) channel classes
# -----------------------------------------------------------------------------


class MemoryAgentChannel(AbstractAgentChannel):
    """Base channel for memory agents."""
    __slots__ = ()
    OUTPUT_SCHEMA = models.MemoryOperation


class MemoryAgentConsumer(AbstractAgentChannelConsumer):
    """Base consumer for memory agent channels."""
    __slots__ = ()


class MemoryAgentProducer(AbstractAgentChannelProducer, AbstractMemoryAgent):
    """Base producer for memory agents. Subclasses implement execute()."""
    __slots__ = ()

    AGENT_CHANNEL = MemoryAgentChannel
    AGENT_CONSUMER = MemoryAgentConsumer

    def __init__(self, channel: Optional[MemoryAgentChannel] = None, self_improving: bool = True):
        AbstractMemoryAgent.__init__(self, self_improving=self_improving)
        AbstractAgentChannelProducer.__init__(self, channel)
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


# -----------------------------------------------------------------------------
# AI channel classes (inherit from base AND AI abstracts)
# -----------------------------------------------------------------------------


class AIMemoryAgentChannel(MemoryAgentChannel, AbstractAIAgentChannel):
    """AI channel for memory agents."""
    __slots__ = ()


class AIMemoryAgentConsumer(MemoryAgentConsumer, AbstractAIAgentChannelConsumer):
    """AI consumer for memory agent channels."""
    __slots__ = ()


class AIMemoryAgentProducer(MemoryAgentProducer, AbstractAIAgentChannelProducer):
    """AI producer for memory agents. Tentacles extend this and implement execute() with LLM."""
    __slots__ = ()

    AGENT_CHANNEL = AIMemoryAgentChannel
    AGENT_CONSUMER = AIMemoryAgentConsumer

    def __init__(
        self,
        channel: Optional[AIMemoryAgentChannel] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        self_improving: bool = True,
        **kwargs,
    ):
        AbstractMemoryAgent.__init__(self, self_improving=self_improving)
        AbstractAIAgentChannelProducer.__init__(
            self, channel, model=model, max_tokens=max_tokens, temperature=temperature, **kwargs
        )
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


if TYPE_CHECKING:
    from octobot_agents.agent.channels.ai_agent import AbstractAIAgentChannelProducer
