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

import async_channel.enums as channel_enums
import async_channel.constants as channel_constants
import async_channel.channels as channels
import async_channel.consumer as consumer
import async_channel.producer as producer

import octobot_commons.logging as logging

from octobot_agents.constants import (
    AGENT_NAME_KEY,
    AGENT_ID_KEY,
    AGENT_DEFAULT_VERSION,
    AGENT_DEFAULT_MAX_RETRIES,
)


class AbstractAgentChannelConsumer(consumer.Consumer):
    """
    Abstract consumer for agent channels.
    
    Consumers receive agent execution results pushed by producers.
    """
    __metaclass__ = abc.ABCMeta


class AbstractAgentChannelProducer(producer.Producer):
    """
    Abstract producer for agent channels.
    
    Simple base class following the service feed pattern.
    Producers execute agent logic and push results to consumers.
    """
    __metaclass__ = abc.ABCMeta
    MAX_RETRIES: int = AGENT_DEFAULT_MAX_RETRIES


class AbstractAgentChannel(channels.Channel):
    """
    Abstract channel for agents with agent_name and agent_id filtering.
    
    Agent tentacles should inherit from this class and define their own channel.
    Example:
        class TechnicalAnalysisAIAgentChannel(AbstractAgentChannel):
            OUTPUT_SCHEMA = TechnicalAnalysisOutput
    """
    __metaclass__ = abc.ABCMeta
    
    PRODUCER_CLASS = AbstractAgentChannelProducer
    CONSUMER_CLASS = AbstractAgentChannelConsumer
    
    VERSION = AGENT_DEFAULT_VERSION
    
    OUTPUT_SCHEMA: typing.Optional[typing.Type] = None
    
    DEFAULT_PRIORITY_LEVEL = channel_enums.ChannelConsumerPriorityLevels.HIGH.value
    
    def __init__(
        self,
        team_name: typing.Optional[str] = None,
        team_id: typing.Optional[str] = None,
    ):
        """
        Initialize the agent channel.
        
        Args:
            team_name: Optional name of the team this channel belongs to.
            team_id: Optional unique identifier for the team instance.
        """
        super().__init__()
        self.team_name = team_name
        self.team_id = team_id
        self.logger = logging.get_logger(self.__class__.__name__)
    
    @classmethod
    def get_output_schema(cls) -> typing.Optional[typing.Type]:
        """
        Get the Pydantic model class for this channel's output.
        
        Override OUTPUT_SCHEMA in subclasses to define the expected output format.
        This schema is used by _call_llm() as the default response_schema.
        
        Returns:
            The Pydantic BaseModel class, or None if not defined.
        """
        return cls.OUTPUT_SCHEMA
    
    async def new_consumer(
        self,
        callback: typing.Callable = None,
        consumer_instance: "AbstractAgentChannelConsumer" = None,
        size: int = 0,
        priority_level: int = DEFAULT_PRIORITY_LEVEL,
        agent_name: str = channel_constants.CHANNEL_WILDCARD,
        agent_id: str = channel_constants.CHANNEL_WILDCARD,
        **kwargs,
    ) -> "AbstractAgentChannelConsumer":
        """
        Create a new consumer for this channel.
        
        Args:
            callback: Method to call when consuming queue data.
            consumer_instance: Existing consumer instance to use.
            size: Queue size (0 = unlimited).
            priority_level: Consumer priority level.
            agent_name: Filter by agent name (wildcard = all agents).
            agent_id: Filter by agent id (wildcard = all instances).
            **kwargs: Additional arguments.
            
        Returns:
            The created consumer instance.
        """
        consumer_inst = (
            consumer_instance
            if consumer_instance
            else self.CONSUMER_CLASS(callback, size=size, priority_level=priority_level)
        )
        await self._add_new_consumer_and_run(
            consumer_inst,
            agent_name=agent_name,
            agent_id=agent_id,
            **kwargs,
        )
        await self._check_producers_state()
        return consumer_inst
    
    def get_filtered_consumers(
        self,
        agent_name: str = channel_constants.CHANNEL_WILDCARD,
        agent_id: str = channel_constants.CHANNEL_WILDCARD,
    ) -> list:
        """
        Get consumers matching the specified filters.
        
        Args:
            agent_name: Filter by agent name.
            agent_id: Filter by agent id.
            
        Returns:
            List of matching consumer instances.
        """
        return self.get_consumer_from_filters({
            AGENT_NAME_KEY: agent_name,
            AGENT_ID_KEY: agent_id,
        })
    
    async def _add_new_consumer_and_run(
        self,
        consumer_inst: "AbstractAgentChannelConsumer",
        agent_name: str = channel_constants.CHANNEL_WILDCARD,
        agent_id: str = channel_constants.CHANNEL_WILDCARD,
        **kwargs,
    ) -> None:
        """
        Add consumer to the channel and start it.
        
        Args:
            consumer_inst: The consumer instance to add.
            agent_name: Agent name filter for this consumer.
            agent_id: Agent id filter for this consumer.
        """
        self.add_new_consumer(
            consumer_inst,
            {
                AGENT_NAME_KEY: agent_name,
                AGENT_ID_KEY: agent_id,
            },
        )
        await consumer_inst.run(with_task=not self.is_synchronized)
        self.logger.debug(
            f"Consumer started for agent_name={agent_name}, agent_id={agent_id}: {consumer_inst}"
        )
