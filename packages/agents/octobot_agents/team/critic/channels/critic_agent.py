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

import octobot_commons.logging as logging

import octobot_agents.models as models
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
import octobot_services.services.abstract_ai_service as abstract_ai_service


class AbstractCriticAgent(abc.ABC):
    """
    Base interface for all critic agents.

    Critic agents analyze team execution to find issues, improvements, errors, and inconsistencies.
    """

    def __init__(self, self_improving: bool = True):
        """Initialize the critic agent."""
        self.self_improving = self_improving
        self.logger = None  # Will be set by subclasses

    @abc.abstractmethod
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


# -----------------------------------------------------------------------------
# Base (non-AI) channel classes
# -----------------------------------------------------------------------------


class CriticAgentChannel(AbstractAgentChannel):
    """Base channel for critic agents."""
    __slots__ = ()
    OUTPUT_SCHEMA = models.CriticAnalysis


class CriticAgentConsumer(AbstractAgentChannelConsumer):
    """Base consumer for critic agent channels."""
    __slots__ = ()


class CriticAgentProducer(AbstractAgentChannelProducer, AbstractCriticAgent):
    """Base producer for critic agents. Subclasses implement execute()."""
    __slots__ = ()

    AGENT_CHANNEL = CriticAgentChannel
    AGENT_CONSUMER = CriticAgentConsumer

    def __init__(self, channel: typing.Optional[CriticAgentChannel] = None, self_improving: bool = True):
        AbstractCriticAgent.__init__(self, self_improving=self_improving)
        AbstractAgentChannelProducer.__init__(self, channel)
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


# -----------------------------------------------------------------------------
# AI channel classes (inherit from base AND AI abstracts)
# -----------------------------------------------------------------------------


class AICriticAgentChannel(CriticAgentChannel, AbstractAIAgentChannel):
    """AI channel for critic agents."""
    __slots__ = ()


class AICriticAgentConsumer(CriticAgentConsumer, AbstractAIAgentChannelConsumer):
    """AI consumer for critic agent channels."""
    __slots__ = ()


class AICriticAgentProducer(CriticAgentProducer, AbstractAIAgentChannelProducer):
    """AI producer for critic agents. Tentacles extend this and implement execute() with LLM."""
    __slots__ = ()

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
        AbstractCriticAgent.__init__(self, self_improving=self_improving)
        AbstractAIAgentChannelProducer.__init__(
            self, channel, model=model, max_tokens=max_tokens, temperature=temperature, **kwargs
        )
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)
