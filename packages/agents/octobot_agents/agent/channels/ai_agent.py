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
import contextlib
import json
import typing

import octobot_commons.logging as logging

from octobot_agents.agent.channels.agent import (
    AbstractAgentChannel,
    AbstractAgentChannelConsumer,
    AbstractAgentChannelProducer,
)
from octobot_agents.constants import (
    AGENT_DEFAULT_MAX_TOKENS,
    AGENT_DEFAULT_MAX_RETRIES,
    AGENT_DEFAULT_TEMPERATURE,
    MEMORY_AGENT_ID_KEY,
)
from octobot_agents.storage import (
    AbstractMemoryStorage,
    create_memory_storage,
    get_memory_tools,
    execute_memory_tool,
)
from octobot_agents.enums import MemoryStorageType
import octobot_services.services as services
import octobot_services.enums as enums
import octobot_services.errors as services_errors

class AbstractAIAgentChannel(AbstractAgentChannel):
    """
    Channel for AI agents.
    
    Inherits from AbstractAgentChannel with no additional functionality.
    """
    __metaclass__ = abc.ABCMeta


class AbstractAIAgentChannelConsumer(AbstractAgentChannelConsumer):
    """
    Consumer for AI agent channels with input aggregation support.
    
    Can aggregate inputs from multiple producers before triggering the associated producer.
    Useful for agents that need to wait for multiple upstream agents to complete.
    """
    __metaclass__ = abc.ABCMeta
    
    def __init__(
        self,
        callback: typing.Optional[typing.Callable] = None,
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
    Producer for AI agents with LLM calling capabilities and optional memory management.
    
    Follows the same pattern as AbstractServiceFeed inheriting from
    AbstractServiceFeedChannelProducer.
    
    Provides common functionality for LLM calling, prompt management,
    and data formatting. Retry logic is handled by the service layer.
    Memory functionality is optional and can be enabled via ENABLE_MEMORY class variable
    or enable_memory constructor parameter.
    Subclasses should implement _get_default_prompt() and execute() methods.
    """
    
    AGENT_VERSION: str = "1.0.0"
    DEFAULT_MODEL: typing.Optional[str] = None
    DEFAULT_MAX_TOKENS: int = AGENT_DEFAULT_MAX_TOKENS
    DEFAULT_TEMPERATURE: float = AGENT_DEFAULT_TEMPERATURE
    MAX_RETRIES: int = AGENT_DEFAULT_MAX_RETRIES
    # Model policy for multi-model config: fast (analysts, debators) or reasoning (judge, final step). None = use self.model.
    MODEL_POLICY: typing.Optional[enums.AIModelPolicy] = None

    # Memory configuration
    ENABLE_MEMORY: bool = False
    MEMORY_SEARCH_LIMIT: int = 5
    MEMORY_STORAGE_ENABLED: bool = True
    MEMORY_AGENT_ID_KEY: str = MEMORY_AGENT_ID_KEY
    
    AGENT_CHANNEL: typing.Optional[typing.Type[AbstractAgentChannel]] = None
    AGENT_CONSUMER: typing.Optional[typing.Type[AbstractAIAgentChannelConsumer]] = None
    
    def __init__(
        self,
        channel: typing.Optional[AbstractAgentChannel],
        ai_service: typing.Optional[services.AbstractAIService] = None,
        model: typing.Optional[str] = None,
        max_tokens: typing.Optional[int] = None,
        temperature: typing.Optional[float] = None,
        enable_memory: typing.Optional[bool] = None,
    ):
        """
        Initialize the AI agent producer.
        
        Args:
            channel: The channel this producer is registered to.
            model: LLM model to use. Defaults to DEFAULT_MODEL.
            max_tokens: Maximum tokens for response. Defaults to DEFAULT_MAX_TOKENS.
            temperature: Temperature for LLM randomness. Defaults to DEFAULT_TEMPERATURE.
            enable_memory: Override class-level ENABLE_MEMORY setting.
        """
        super().__init__(channel)
        self.name = self.__class__.__name__
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens or self.DEFAULT_MAX_TOKENS
        self.temperature = temperature or self.DEFAULT_TEMPERATURE
        self._custom_prompt: typing.Optional[str] = None
        self.ai_service: services.AbstractAIService = None
        self.logger = logging.get_logger(f"{self.__class__.__name__}")
        
        # Initialize memory storage if memory is enabled
        memory_enabled = enable_memory if enable_memory is not None else self.ENABLE_MEMORY
        self.memory_manager: AbstractMemoryStorage = create_memory_storage(
            MemoryStorageType.JSON,
            agent_name=self.__class__.__name__,
            agent_version=self.AGENT_VERSION,
            enabled=memory_enabled,
            search_limit=self.MEMORY_SEARCH_LIMIT,
            storage_enabled=self.MEMORY_STORAGE_ENABLED,
            agent_id_key=self.MEMORY_AGENT_ID_KEY,
        )
    
    def has_memory_enabled(self) -> bool:
        """
        Check if memory is enabled for this agent.
        
        Returns:
            True if memory is enabled, False otherwise.
        """
        return self.memory_manager.is_enabled()
    
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
    async def execute(self, input_data: typing.Any, ai_service: services.AbstractAIService) -> typing.Any:
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
            agent_name: Agent name for filtering (defaults to name).
            agent_id: Agent id for filtering.
        """
        if self.channel is None:
            return
        await self.perform(
            result,
            agent_name=agent_name or self.name,
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
    
    @contextlib.contextmanager
    def _memory_tool_executor(self):
        """
        Context manager that provides a memory tool executor callback.
        
        Yields:
            A callable function that executes memory tools with the signature:
            (tool_name: str, arguments: dict) -> Any
        """
        def executor(tool_name: str, arguments: dict) -> typing.Any:
            return execute_memory_tool(self.memory_manager, tool_name, arguments)
        
        yield executor
    
    async def _call_llm(
        self,
        messages: list,
        llm_service: services.AbstractAIService,
        json_output: bool = True,
        response_schema: typing.Optional[typing.Any] = None,
        input_data: typing.Optional[typing.Any] = None,
        memory_query: typing.Optional[str] = None,
        tools: typing.Optional[list] = None,
        return_tool_calls: bool = False,
    ) -> typing.Any:
        """
        Common LLM calling method with error handling and optional memory.
        
        Automatically registers memory tools when memory is enabled. Memory retrieval is done
        via LLM tools (get_memory_summaries, get_memory_by_id).
        Custom tools can be provided and will be merged with memory tools if both are present.
        Retry logic is handled by the service layer via the retry_llm_completion decorator.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            llm_service: The LLM service instance.
            json_output: Whether to parse response as JSON.
            response_schema: Optional Pydantic model or JSON schema for structured output.
                            If None, uses the channel's OUTPUT_SCHEMA as default.
            input_data: Optional input data for memory retrieval (kept for backward compatibility).
            memory_query: Optional custom query for memory search (not used with tools).
            tools: Optional list of custom tools to provide to the LLM.
        
        Returns:
            Parsed JSON dict or raw string response.
        """
        # Register memory tools if memory is enabled, and merge with custom tools
        all_tools = []
        if self.memory_manager.is_enabled():
            all_tools.extend(get_memory_tools(self.memory_manager, llm_service))
        if tools:
            all_tools.extend(tools)
        
        # Use channel's output schema as default if not explicitly provided
        effective_schema = response_schema
        if effective_schema is None and self.AGENT_CHANNEL is not None:
            effective_schema = self.AGENT_CHANNEL.get_output_schema()

        # Resolve model from policy if set (use class attribute MODEL_POLICY)
        effective_model = self.model
        if self.MODEL_POLICY is not None:
            policy_model = llm_service.get_model_for_policy(self.MODEL_POLICY.value)
            if policy_model:
                effective_model = policy_model

        # Call LLM with automatic tool calling orchestration if tools are available
        # Retry logic is handled by the service layer decorator
        if all_tools:
            # Use context manager to get executor and keep it open for the entire call
            try:
                with self._memory_tool_executor() as executor:
                    # Call LLM with automatic tool calling orchestration
                    return await llm_service.get_completion_with_tools(
                        messages=messages,
                        tool_executor=executor if not return_tool_calls else None,
                        model=effective_model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        json_output=json_output,
                        response_schema=effective_schema,
                        tools=all_tools,
                        return_tool_calls=return_tool_calls,
                    )
            except services_errors.InvalidRequestError as e:
                # Check if error is due to tool support
                error_message = str(e).lower()
                if "does not support tools" in error_message or "does not support" in error_message and "tool" in error_message:
                    # Model doesn't support tools - fall back to regular completion
                    self.logger.warning(
                        f"Model {self.model} does not support tools. "
                        f"Falling back to regular completion without memory tools. "
                        f"Error: {e}"
                    )
                    # Fall through to regular get_completion below
                else:
                    # Different error - re-raise it
                    raise
            except Exception as e:
                # Check if it's a tool support error from the underlying API
                error_message = str(e).lower()
                if "does not support tools" in error_message or "does not support" in error_message and "tool" in error_message:
                    # Model doesn't support tools - fall back to regular completion
                    self.logger.warning(
                        f"Model {self.model} does not support tools. "
                        f"Falling back to regular completion without memory tools. "
                        f"Error: {e}"
                    )
                    # Fall through to regular get_completion below
                else:
                    # Different error - re-raise it
                    raise
        
        # No tools or fallback from tool error - use regular get_completion
        response = await llm_service.get_completion(
            messages=messages,
            model=effective_model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            json_output=json_output,
            response_schema=effective_schema,
            tools=None,
        )
        return llm_service.parse_completion_response(
            response,
            json_output=json_output
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
    
    async def _get_relevant_memories(
        self,
        query: str,
        input_data: typing.Any,
        limit: typing.Optional[int] = None,
    ) -> typing.List[dict]:
        """
        Retrieve relevant memories for the current context.
        
        Note: With tool-based approach, memories are retrieved via LLM tools.
        This method is kept for backward compatibility but may not be used.
        
        Args:
            query: Search query for finding relevant memories.
            input_data: Current input data (may contain agent_id).
            limit: Maximum number of memories to retrieve (defaults to MEMORY_SEARCH_LIMIT).
            
        Returns:
            List of memory dictionaries with 'memory' and 'metadata' keys.
        """
        return await self.memory_manager.search_memories(query, input_data, limit=limit)
    
    def _format_memories_for_prompt(self, memories: typing.List[dict]) -> str:
        """
        Format memories for inclusion in prompts.
        
        Delegates to memory manager.
        
        Args:
            memories: List of memory dictionaries.
            
        Returns:
            Formatted string with memories, or empty string if none.
        """
        return self.memory_manager.format_memories_for_prompt(memories)
    
    async def _store_execution_memory(
        self,
        input_data: typing.Any,
        output: typing.Any,
        user_message: typing.Optional[str] = None,
        assistant_message: typing.Optional[str] = None,
        metadata: typing.Optional[dict] = None,
    ) -> None:
        """
        Store memory from agent execution.
        
        Note: Memory storage is now handled by MemoryAgent, not automatically after LLM calls.
        This method is kept for backward compatibility but should not be called automatically.
        
        Args:
            input_data: The input data that was processed.
            output: The agent's output/result.
            user_message: Optional user message (auto-built if not provided).
            assistant_message: Optional assistant message (auto-built if not provided).
            metadata: Optional metadata to attach.
        """
        # Memory storage is now handled by MemoryAgent
        # This method is kept for manual memory storage if needed
        await self.memory_manager.store_execution_memory(
            input_data, output, user_message, assistant_message, metadata
        )
