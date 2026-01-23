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
Abstract agent channel classes for pub/sub communication between agents and consumers.

Follows the same pattern as AbstractServiceFeedChannel in octobot_services.
Agent tentacles should inherit from these abstract classes and define their own
Channel, Producer, and Consumer classes.

Hierarchy:
- Base classes: AbstractAgentChannelConsumer, AbstractAgentChannelProducer, AbstractAgentChannel
- AI-specific: AbstractAIAgentChannelConsumer, AbstractAIAgentChannelProducer
"""
import abc
import json
import typing

import async_channel.enums as channel_enums
import async_channel.constants as channel_constants
import async_channel.channels as channels
import async_channel.consumer as consumer
import async_channel.producer as producer

import octobot_commons.logging as logging


# =============================================================================
# Base Agent Channel Classes (Simple, like ServiceFeed pattern)
# =============================================================================


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
    
    # Keys for agent/team data structures
    AGENT_NAME_KEY = "agent_name"
    AGENT_ID_KEY = "agent_id"
    TEAM_NAME_KEY = "team_name"
    TEAM_ID_KEY = "team_id"
    RESULT_KEY = "result"
    
    # Output schema - override in subclasses with Pydantic model class
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
            self.AGENT_NAME_KEY: agent_name,
            self.AGENT_ID_KEY: agent_id,
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
                self.AGENT_NAME_KEY: agent_name,
                self.AGENT_ID_KEY: agent_id,
            },
        )
        await consumer_inst.run(with_task=not self.is_synchronized)
        self.logger.debug(
            f"Consumer started for agent_name={agent_name}, agent_id={agent_id}: {consumer_inst}"
        )


# =============================================================================
# AI Agent Channel Classes (with LLM capabilities)
# =============================================================================


class AbstractAIAgentChannelConsumer(AbstractAgentChannelConsumer):
    """
    Consumer for AI agent channels with input aggregation support.
    
    Can aggregate inputs from multiple producers before triggering the associated producer.
    Useful for agents that need to wait for multiple upstream agents to complete.
    """
    __metaclass__ = abc.ABCMeta
    
    def __init__(
        self,
        callback: typing.Callable = None,
        size: int = 0,
        priority_level: int = AbstractAgentChannel.DEFAULT_PRIORITY_LEVEL,
        expected_inputs: int = 1,
    ):
        """
        Initialize the AI agent consumer.
        
        Args:
            callback: Method to call when consuming queue data.
            size: Queue size (0 = unlimited).
            priority_level: Consumer priority level.
            expected_inputs: Number of inputs to aggregate before triggering.
        """
        super().__init__(callback, size=size, priority_level=priority_level)
        self.expected_inputs = expected_inputs
        self.received_inputs: typing.Dict[str, typing.Any] = {}
        self.producer: typing.Optional["AbstractAIAgentChannelProducer"] = None
    
    def set_producer(self, producer_instance: "AbstractAIAgentChannelProducer") -> None:
        """Set the producer to trigger when inputs are ready."""
        self.producer = producer_instance
    
    def is_ready(self) -> bool:
        """Check if all expected inputs have been received."""
        return len(self.received_inputs) >= self.expected_inputs
    
    def add_input(self, source_name: str, data: typing.Any) -> None:
        """
        Add input data from a source.
        
        Args:
            source_name: Name of the source agent.
            data: The data received from the source.
        """
        self.received_inputs[source_name] = data
    
    def get_aggregated_inputs(self) -> typing.Dict[str, typing.Any]:
        """Get all received inputs."""
        return self.received_inputs.copy()
    
    def clear_inputs(self) -> None:
        """Clear all received inputs."""
        self.received_inputs.clear()


class AbstractAIAgentChannelProducer(AbstractAgentChannelProducer, abc.ABC):
    """
    Producer for AI agents with LLM calling capabilities.
    
    Follows the same pattern as AbstractServiceFeed inheriting from
    AbstractServiceFeedChannelProducer.
    
    Provides common functionality for LLM calling, prompt management,
    retry logic, and data formatting. Subclasses should implement
    _get_default_prompt() and execute() methods.
    """
    
    # Class-level defaults (can be overridden by subclasses)
    AGENT_NAME: str = "AbstractAIAgent"
    AGENT_VERSION: str = "1.0.0"
    DEFAULT_MODEL: typing.Optional[str] = None
    DEFAULT_MAX_TOKENS: int = 10000
    DEFAULT_TEMPERATURE: float = 0.3
    MAX_RETRIES: int = 3
    
    # Override in subclasses with dedicated channel and consumer classes
    AGENT_CHANNEL: typing.Optional[typing.Type[AbstractAgentChannel]] = None
    AGENT_CONSUMER: typing.Optional[typing.Type[AbstractAIAgentChannelConsumer]] = None
    
    def __init__(
        self,
        channel: typing.Optional[AbstractAgentChannel],
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
    ):
        """
        Initialize the AI agent producer.
        
        Args:
            channel: The channel this producer is registered to.
            model: LLM model to use. Defaults to DEFAULT_MODEL.
            max_tokens: Maximum tokens for response. Defaults to DEFAULT_MAX_TOKENS.
            temperature: Temperature for LLM randomness. Defaults to DEFAULT_TEMPERATURE.
        """
        super().__init__(channel)
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self.temperature = temperature or self.DEFAULT_TEMPERATURE
        self._custom_prompt: typing.Optional[str] = None
        self.ai_service: typing.Any = None
        self.logger = logging.get_logger(f"{self.__class__.__name__}")
    
    @property
    def prompt(self) -> str:
        """Get the agent's prompt, allowing override via config."""
        return self._custom_prompt or self._get_default_prompt()
    
    @prompt.setter
    def prompt(self, value: str) -> None:
        """Allow custom prompt override."""
        self._custom_prompt = value
    
    @abc.abstractmethod
    def _get_default_prompt(self) -> str:
        """
        Return the default prompt for this agent type.
        
        Subclasses must implement this to provide their system prompt.
        
        Returns:
            The default system prompt string.
        """
        raise NotImplementedError("_get_default_prompt not implemented")
    
    @abc.abstractmethod
    async def execute(self, input_data: typing.Any, ai_service: typing.Any) -> typing.Any:
        """
        Execute the agent's primary function.
        
        Args:
            input_data: The input data for the agent to process.
            ai_service: The AI service instance (AbstractAIService).
            
        Returns:
            The agent's output, type depends on the specific agent.
        """
        raise NotImplementedError("execute not implemented")
    
    async def push(
        self,
        result: typing.Any,
        agent_name: typing.Optional[str] = None,
        agent_id: typing.Optional[str] = None,
    ) -> None:
        """
        Push a result to filtered consumers.
        
        Args:
            result: The result data to push.
            agent_name: Agent name for filtering (defaults to AGENT_NAME).
            agent_id: Agent id for filtering.
        """
        if self.channel is None:
            return
        await self.perform(
            result,
            agent_name=agent_name or self.AGENT_NAME,
            agent_id=agent_id or "",
        )
    
    async def perform(
        self,
        result: typing.Any,
        agent_name: str,
        agent_id: str,
    ) -> None:
        """
        Send result to matching consumers.
        
        Args:
            result: The result data to send.
            agent_name: Agent name for consumer filtering.
            agent_id: Agent id for consumer filtering.
        """
        if self.channel is None:
            return
        for consumer_instance in self.channel.get_filtered_consumers(
            agent_name=agent_name,
            agent_id=agent_id,
        ):
            await consumer_instance.queue.put({
                "agent_name": agent_name,
                "agent_id": agent_id,
                "result": result,
            })
    
    async def _call_llm(
        self,
        messages: list,
        llm_service: typing.Any,
        json_output: bool = True,
        response_schema: typing.Optional[typing.Any] = None,
    ) -> typing.Any:
        """
        Common LLM calling method with error handling and automatic retries.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            llm_service: The LLM service instance.
            json_output: Whether to parse response as JSON.
            response_schema: Optional Pydantic model or JSON schema for structured output.
                            If None, uses the channel's OUTPUT_SCHEMA as default.
            
        Returns:
            Parsed JSON dict or raw string response.
            
        Raises:
            RuntimeError: If all retries are exhausted.
        """
        # Use channel's output schema as default if not explicitly provided
        effective_schema = response_schema
        if effective_schema is None and self.AGENT_CHANNEL is not None:
            effective_schema = self.AGENT_CHANNEL.get_output_schema()
        
        last_exception = None
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = await llm_service.get_completion(
                    messages=messages,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    json_output=json_output,
                    response_schema=effective_schema,
                )
                if json_output:
                    return json.loads(response.strip())
                return response.strip()
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError) as e:
                last_exception = e
                if attempt < self.MAX_RETRIES:
                    self.logger.warning(
                        f"LLM call failed on attempt {attempt}/{self.MAX_RETRIES} "
                        f"for agent {self.AGENT_NAME}: {str(e)}. Retrying..."
                    )
                else:
                    self.logger.error(
                        f"LLM call failed on final attempt {attempt}/{self.MAX_RETRIES} "
                        f"for agent {self.AGENT_NAME}: {str(e)}"
                    )
        
        # All retries exhausted
        raise RuntimeError(
            f"LLM call failed for agent {self.AGENT_NAME} after {self.MAX_RETRIES} retries: {str(last_exception)}"
        )
    
    def format_data(self, data: typing.Any, default_message: str = "No data available.") -> str:
        """
        Format data for inclusion in prompts.
        
        Args:
            data: Data to format (dict, list, or other JSON-serializable type).
            default_message: Message to return if data is empty/None.
            
        Returns:
            JSON-formatted string or default message.
        """
        if not data:
            return default_message
        return json.dumps(data, indent=2, default=str)
