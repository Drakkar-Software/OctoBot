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
"""
Abstract judge agent interface and base channel classes for debate phases.

Judge agents decide whether a debate should continue or exit and optionally
provide a synthesis summary when exiting.
"""
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


class AbstractJudgeAgent(abc.ABC):
    """
    Base interface for all judge agents.

    Judge agents are used in debate phases: they receive debate history
    (messages from debator agents) and decide whether to continue the debate
    or exit with an optional synthesis summary.
    """

    def __init__(self):
        """Initialize the judge agent."""
        self.logger = None  # Will be set by subclasses

    @abc.abstractmethod
    async def execute(
        self,
        input_data: typing.Union[typing.Dict[str, typing.Any], models.JudgeInput],
        ai_service: abstract_ai_service.AbstractAIService,
    ) -> models.JudgeDecision:
        """
        Execute judge decision on debate state.

        Args:
            input_data: Contains debate_history (list of {agent_name, message, round}),
                        debator_agent_names, current_round, max_rounds, and optional
                        _initial_state for context.
            ai_service: The AI service instance (for AI judge agents).

        Returns:
            JudgeDecision with decision ("continue" or "exit"), reasoning, and optional summary.
        """
        raise NotImplementedError("execute must be implemented by subclasses")


class JudgeAgentChannel(AbstractAgentChannel):
    """Base channel for judge agents."""
    __slots__ = ()
    OUTPUT_SCHEMA = models.JudgeDecision


class JudgeAgentConsumer(AbstractAgentChannelConsumer):
    """Base consumer for judge agent channels."""
    __slots__ = ()


class JudgeAgentProducer(AbstractAgentChannelProducer, AbstractJudgeAgent):
    """Base producer for judge agents. Subclasses implement execute()."""
    __slots__ = ()

    AGENT_CHANNEL = JudgeAgentChannel
    AGENT_CONSUMER = JudgeAgentConsumer

    def __init__(self, channel: typing.Optional[JudgeAgentChannel] = None):
        AbstractJudgeAgent.__init__(self)
        AbstractAgentChannelProducer.__init__(self, channel)
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


# -----------------------------------------------------------------------------
# AI channel classes (inherit from base AND AI abstracts)
# -----------------------------------------------------------------------------


class AIJudgeAgentChannel(JudgeAgentChannel, AbstractAIAgentChannel):
    """AI channel for judge agents."""
    __slots__ = ()


class AIJudgeAgentConsumer(JudgeAgentConsumer, AbstractAIAgentChannelConsumer):
    """AI consumer for judge agent channels."""
    __slots__ = ()


class AIJudgeAgentProducer(JudgeAgentProducer, AbstractAIAgentChannelProducer):
    """AI producer for judge agents. Tentacles extend this and implement execute() with LLM."""
    __slots__ = ()

    AGENT_CHANNEL = AIJudgeAgentChannel
    AGENT_CONSUMER = AIJudgeAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[AIJudgeAgentChannel] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        **kwargs,
    ):
        AbstractJudgeAgent.__init__(self)
        AbstractAIAgentChannelProducer.__init__(
            self, channel, model=model, max_tokens=max_tokens, temperature=temperature, **kwargs
        )
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)
