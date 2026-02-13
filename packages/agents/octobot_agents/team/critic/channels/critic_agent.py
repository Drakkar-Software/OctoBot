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

import octobot_agents.models as models
import octobot_agents.agent.channels.agent as agent_channels
import octobot_agents.agent.channels.ai_agent as ai_agent_channels
import octobot_services.services.abstract_ai_service as abstract_ai_service


class CriticAgentMixin:
    """
    Mixin that provides critic agent functionality.

    Critic agents analyze team execution to find issues, improvements, errors, and inconsistencies.
    """

    async def execute(
        self,
        input_data: typing.Union[models.CriticInput, typing.Dict[str, typing.Any]],
        ai_service: abstract_ai_service.AbstractAIService
    ) -> models.CriticAnalysis:
        """
        Execute critic analysis of team execution.

        Args:
            input_data: Contains {"team_producer": team_producer, "execution_plan": ExecutionPlan, "execution_results": Dict, "agent_outputs": Dict, "execution_metadata": dict}
            ai_service: The AI service instance (for AI critic agents)

        Returns:
            CriticAnalysis with issues, improvements, errors, inconsistencies, and agent_improvements
        """
        raise NotImplementedError("execute must be implemented by subclasses")


class CriticAgentChannel(agent_channels.AbstractAgentChannel):
    OUTPUT_SCHEMA = models.CriticAnalysis


class CriticAgentConsumer(agent_channels.AbstractAgentChannelConsumer):
    pass


class CriticAgentProducer(CriticAgentMixin, agent_channels.AbstractAgentChannelProducer):

    AGENT_CHANNEL = CriticAgentChannel
    AGENT_CONSUMER = CriticAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[CriticAgentChannel] = None,
        self_improving: bool = True,
        **kwargs,
    ):
        super().__init__(channel, **kwargs)
        self.self_improving = self_improving
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


class AICriticAgentChannel(CriticAgentChannel, ai_agent_channels.AbstractAIAgentChannel):
    pass


class AICriticAgentConsumer(CriticAgentConsumer, ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class AICriticAgentProducer(CriticAgentProducer, ai_agent_channels.AbstractAIAgentChannelProducer):

    AGENT_CHANNEL = AICriticAgentChannel
    AGENT_CONSUMER = AICriticAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[AICriticAgentChannel] = None,
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
