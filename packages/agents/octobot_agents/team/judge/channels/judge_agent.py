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
import typing

import octobot_commons.logging as logging

import octobot_agents.models as models
import octobot_agents.agent.channels.agent as agent_channels
import octobot_agents.agent.channels.ai_agent as ai_agent_channels
import octobot_services.services.abstract_ai_service as abstract_ai_service


class JudgeAgentMixin:
    """
    Mixin that provides judge agent functionality.

    Judge agents are used in debate phases: they receive debate history
    (messages from debator agents) and decide whether to continue the debate
    or exit with an optional synthesis summary.
    """

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


class JudgeAgentChannel(agent_channels.AbstractAgentChannel):
    OUTPUT_SCHEMA = models.JudgeDecision


class JudgeAgentConsumer(agent_channels.AbstractAgentChannelConsumer):
    pass


class JudgeAgentProducer(JudgeAgentMixin, agent_channels.AbstractAgentChannelProducer):
    AGENT_CHANNEL = JudgeAgentChannel
    AGENT_CONSUMER = JudgeAgentConsumer

    def __init__(
        self,
        channel: typing.Optional[JudgeAgentChannel] = None,
        **kwargs,
    ):
        super().__init__(channel, **kwargs)
        self.name = self.__class__.__name__
        self.logger = logging.get_logger(self.__class__.__name__)


class AIJudgeAgentChannel(JudgeAgentChannel, ai_agent_channels.AbstractAIAgentChannel):
    pass


class AIJudgeAgentConsumer(JudgeAgentConsumer, ai_agent_channels.AbstractAIAgentChannelConsumer):
    pass


class AIJudgeAgentProducer(JudgeAgentProducer, ai_agent_channels.AbstractAIAgentChannelProducer):
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
        super().__init__(
            channel=channel,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        self.name = self.__class__.__name__
