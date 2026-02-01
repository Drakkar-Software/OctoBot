#  Drakkar-Software OctoBot-Services
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
import abc
import asyncio
import functools
import json
import logging
import typing

from octobot_services.services.abstract_service import AbstractService
import octobot_services.enums as enums

class AbstractAIService(AbstractService, abc.ABC):
    DEFAULT_MODEL: typing.Optional[str] = None
    DEFAULT_MAX_TOKENS: int = 10000
    DEFAULT_TEMPERATURE: float = 0.5

    def __init__(self):
        super().__init__()
        self.model = self.DEFAULT_MODEL
        self.models: list[str] = []
        self.models_config: typing.Dict[str, str] = {}  # usage policy -> model name, e.g. {"fast": "gpt-4o-mini", "reasoning": "o4-mini"}
        self.ai_provider: typing.Optional[enums.AIProvider] = None
        self.auth_token: typing.Optional[str] = None
        self.api_key: typing.Optional[str] = None

    @staticmethod
    def retry_llm_completion(
        max_retries: int = 3,
        retry_delay: float = 0.0,
        retriable_exceptions: tuple = (json.JSONDecodeError, ValueError, KeyError, AttributeError),
    ):
        """
        Decorator to retry LLM completion methods on retriable exceptions.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 3).
            retry_delay: Delay in seconds between retries (default: 0.0).
            retriable_exceptions: Tuple of exception types that should trigger retries.
        
        Returns:
            Decorator function that wraps async methods with retry logic.
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs):
                logger = getattr(self, 'logger', None) or logging.getLogger(f"{self.__class__.__name__}.retry")
                last_exception = None
                
                for attempt in range(1, max_retries + 1):
                    try:
                        return await func(self, *args, **kwargs)
                    except retriable_exceptions as e:
                        last_exception = e
                        error_details = str(e)
                        
                        if attempt < max_retries:
                            logger.warning(
                                f"{func.__name__} failed on attempt {attempt}/{max_retries} "
                                f"for {self.__class__.__name__}: {error_details}. Retrying..."
                            )
                            if retry_delay > 0:
                                await asyncio.sleep(retry_delay)
                        else:
                            logger.error(
                                f"{func.__name__} failed on final attempt {attempt}/{max_retries} "
                                f"for {self.__class__.__name__}: {error_details}"
                            )
                            raise
                    except Exception:
                        # Non-retriable exceptions should be raised immediately
                        raise
                
                # Should not reach here, but just in case
                if last_exception:
                    raise last_exception
            
            return wrapper
        return decorator

    @retry_llm_completion()
    @abc.abstractmethod
    async def get_completion(
        self,
        messages: list,
        model: typing.Optional[str] = None,
        max_tokens: int = 10000,
        n: int = 1,
        stop: typing.Optional[typing.Union[str, list]] = None,
        temperature: float = 0.5,
        json_output: bool = False,
        response_schema: typing.Optional[typing.Any] = None,
        tools: typing.Optional[list] = None,
        tool_choice: typing.Optional[typing.Union[str, dict]] = None,
        use_octobot_mcp: typing.Optional[bool] = None,
    ) -> typing.Union[str, dict, None]:
        """
        Get a completion from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Model to use (defaults to service's default model).
            max_tokens: Maximum tokens in the response.
            n: Number of completions to generate.
            stop: Stop sequences.
            temperature: Sampling temperature (0-2).
            json_output: Whether to return JSON formatted output.
            response_schema: Optional Pydantic model or JSON schema dict 
                           for structured output validation.
            tools: Optional list of tool definitions for function calling.
                  Each tool should be a dict with 'type' and 'function' keys.
            tool_choice: Optional control for tool usage. Can be "auto", "none", 
                        or a dict specifying a specific tool.
            use_octobot_mcp: Optional bool to include OctoBot MCP server tools.
                            If True, automatically discovers and includes tools from OctoBot MCP interface.
                            If None, uses default behavior (does not include OctoBot MCP).
                            If False, explicitly excludes OctoBot MCP tools.
        
        Returns:
            str: The completion text when no tools are used or tool_choice is "none".
            dict: When tools are used and model makes tool calls, returns dict with:
                  - "content": str | None (may be None if only tool calls)
                  - "tool_calls": list of tool call dicts with id, type, function keys
            None: On error
        
        Raises:
            InvalidRequestError: If the request is malformed.
            RateLimitError: If rate limits are exceeded.
        """
        raise NotImplementedError("get_completion not implemented")
    
    @retry_llm_completion()
    @abc.abstractmethod
    async def get_completion_with_tools(
        self,
        messages: list,
        tool_executor: typing.Optional[typing.Callable[[str, dict], typing.Any]] = None,
        model: typing.Optional[str] = None,
        max_tokens: int = 10000,
        n: int = 1,
        stop: typing.Optional[typing.Union[str, list]] = None,
        temperature: float = 0.5,
        json_output: bool = False,
        response_schema: typing.Optional[typing.Any] = None,
        tools: typing.Optional[list] = None,
        tool_choice: typing.Optional[typing.Union[str, dict]] = None,
        use_octobot_mcp: typing.Optional[bool] = None,
        max_tool_iterations: int = 3,
        return_tool_calls: bool = False,
    ) -> typing.Any:
        """
        Get a completion from the LLM with automatic tool calling orchestration.
        
        This method handles the tool calling loop automatically:
        1. Calls get_completion with the provided parameters
        2. If the response contains tool_calls, executes them using tool_executor
        3. Appends tool results to messages and calls get_completion again
        4. Repeats until no tool_calls are present or max_tool_iterations is reached
        5. Returns the final parsed response
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            tool_executor: Optional callback function to execute tools.
                         Signature: (tool_name: str, arguments: dict) -> Any
                         If None, tool calls will not be executed (response returned as-is).
            model: Model to use (defaults to service's default model).
            max_tokens: Maximum tokens in the response.
            n: Number of completions to generate.
            stop: Stop sequences.
            temperature: Sampling temperature (0-2).
            json_output: Whether to parse response as JSON.
            response_schema: Optional Pydantic model or JSON schema dict 
                           for structured output validation.
            tools: Optional list of tool definitions for function calling.
                  Each tool should be a dict with 'type' and 'function' keys.
            tool_choice: Optional control for tool usage. Can be "auto", "none", 
                        or a dict specifying a specific tool.
            use_octobot_mcp: Optional bool to include OctoBot MCP server tools.
                            If True, automatically discovers and includes tools from OctoBot MCP interface.
                            If None, uses default behavior (does not include OctoBot MCP).
                            If False, explicitly excludes OctoBot MCP tools.
            max_tool_iterations: Maximum number of tool calling rounds (default: 3).
                                Prevents infinite loops if LLM keeps requesting tools.
        
        Returns:
            Final parsed response:
            - dict: If json_output=True, returns parsed JSON dict
            - str: If json_output=False, returns the content string
            - If tool_executor is None and tool_calls are present, returns dict with tool_calls
        
        Raises:
            InvalidRequestError: If the request is malformed.
            RateLimitError: If rate limits are exceeded.
            ValueError: If max_tool_iterations is exceeded or tool_executor is None when tool_calls are present.
        """
        raise NotImplementedError("get_completion_with_tools not implemented")
    
    @staticmethod
    @abc.abstractmethod
    def create_message(
        role: str, 
        content: str, 
        model: typing.Optional[str] = None
    ) -> dict:
        """
        Create a message dict for the LLM.
        
        Some models don't support certain roles (e.g., 'system'),
        so this method allows implementations to handle that.
        
        Args:
            role: The message role ('system', 'user', 'assistant').
            content: The message content.
            model: Optional model name to handle model-specific restrictions.
        
        Returns:
            A dict with 'role' and 'content' keys.
        """
        raise NotImplementedError("create_message not implemented")
    
    @staticmethod
    def parse_completion_response(
        response: typing.Union[str, dict, None],
        json_output: bool = False
    ) -> typing.Any:
        """
        Parse a completion response from get_completion().
        
        Handles both string responses and dict responses (with tool_calls).
        Extracts content and optionally parses JSON.
        
        Args:
            response: The response from get_completion(), can be str, dict, or None.
            json_output: Whether to parse the content as JSON.
        
        Returns:
            Parsed JSON dict if json_output=True, otherwise the content string.
        
        Raises:
            json.JSONDecodeError: If json_output=True and content is not valid JSON.
            ValueError: If response format is unexpected.
        """
        if response is None:
            raise ValueError("Response is None")
        
        # Extract content from response
        if isinstance(response, dict):
            response_stripped = response.get("content", "").strip() if response.get("content") else str(response).strip()
        else:
            response_stripped = response.strip() if isinstance(response, str) else str(response)
        
        # Parse JSON if requested
        if json_output:
            parsed_response = json.loads(response_stripped)
        else:
            parsed_response = response_stripped
        
        return parsed_response
    
    @staticmethod
    @abc.abstractmethod
    def handle_tool_calls(
        tool_calls: typing.List[dict],
        tool_executor: typing.Callable[[str, dict], typing.Any],
    ) -> typing.List[dict]:
        """
        Execute tool calls and format results for LLM message continuation.
        
        Takes a list of tool calls from an LLM response, executes them using
        the provided tool_executor callback, and returns formatted tool result
        messages ready to append to the conversation.
        
        Args:
            tool_calls: List of tool call dicts from LLM response, each with:
                - "id": Tool call ID
                - "function": Dict with "name" and "arguments" keys
            tool_executor: Callback function that executes a tool.
                Signature: (tool_name: str, arguments: dict) -> Any
                Should return the tool execution result (will be JSON-serialized).
        
        Returns:
            List of tool result message dicts, each with:
                - "tool_call_id": The original tool call ID
                - "role": "tool"
                - "name": Tool function name
                - "content": JSON-serialized tool result
        
        Raises:
            NotImplementedError: If the service doesn't support tool calls.
        """
        raise NotImplementedError("handle_tool_calls not implemented")
    
    def format_tool_definition(
        self,
        name: str,
        description: str,
        parameters: typing.Dict[str, typing.Any],
        tool_type: str = "function"
    ) -> typing.Dict[str, typing.Any]:
        """
        Format a tool definition into the standard OpenAI function calling format.
        
        This method can be overridden by concrete AI services to customize tool formatting.
        Use this instead of manually creating tool dictionaries to avoid format errors.
        
        Args:
            name: The function name (must be non-empty string).
            description: Description of what the tool does.
            parameters: JSON schema dict defining the tool's parameters.
            tool_type: The tool type (default: "function" for OpenAI compatibility).
        
        Returns:
            Properly formatted tool definition dict with 'type' and 'function' keys.
        
        Example:
            >>> service.format_tool_definition(
            ...     name="run_agent",
            ...     description="Execute a specific agent",
            ...     parameters={"type": "object", "properties": {"agent_name": {"type": "string"}}}
            ... )
            {
                "type": "function",
                "function": {
                    "name": "run_agent",
                    "description": "Execute a specific agent", 
                    "parameters": {"type": "object", "properties": {"agent_name": {"type": "string"}}}
                }
            }
        """
        if not name or not isinstance(name, str) or name.strip() == "":
            raise ValueError(f"Tool name must be a non-empty string, got: {name}")
        
        return {
            "type": tool_type,
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        }
    
    def get_model(self) -> str:
        return self.model

    def get_available_models(self) -> list:
        return self.models

    def get_model_for_policy(self, policy: str) -> typing.Optional[str]:
        """
        Return the model name for a given usage policy (e.g. "fast" or "reasoning").
        When models_config is set (e.g. {"fast": "gpt-4o-mini", "reasoning": "o4-mini"}),
        returns the model for that policy; otherwise returns None and callers should use get_model().
        """
        if not self.models_config:
            return None
        return self.models_config.get(policy)
