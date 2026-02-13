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
import typing

import octobot_commons.logging as logging

import octobot_agents.agent.channels.agent as agent_channels
import octobot_agents.agent.channels.ai_agent as ai_agent_channels
import octobot_agents.models as models
import octobot_services.services.abstract_ai_service as abstract_ai_service


class MemoryAgentMixin:
    """
    Mixin that provides memory agent functionality.

    Memory agents are responsible for managing agent memories based on critic analysis.
    """

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
    ) -> typing.Optional[ai_agent_channels.AbstractAIAgentChannelProducer]:
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


class MemoryAgentChannel(agent_channels.AbstractAgentChannel):
    OUTPUT_SCHEMA = models.MemoryOperation


class MemoryAgentConsumer(agent_channels.AbstractAgentChannelConsumer):
    pass


class MemoryAgentProducer(MemoryAgentMixin, agent_channels.AbstractAgentChannelProducer):

    AGENT_CHANNEL = MemoryAgentChannel
    AGENT_CONSUMER = MemoryAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[MemoryAgentChannel] = None,
        self_improving: bool = True,
        **kwargs,
    ):
        super().__init__(channel, **kwargs)
        self.self_improving = self_improving
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


class AIMemoryAgentChannel(MemoryAgentChannel, ai_agent_channels.AbstractAIAgentChannel):
    pass


class AIMemoryAgentConsumer(MemoryAgentConsumer, ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class AIMemoryAgentProducer(MemoryAgentProducer, ai_agent_channels.AbstractAIAgentChannelProducer):

    AGENT_CHANNEL = AIMemoryAgentChannel
    AGENT_CONSUMER = AIMemoryAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[AIMemoryAgentChannel] = None,
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
            **kwargs
        )
        self.name = self.__class__.__name__
