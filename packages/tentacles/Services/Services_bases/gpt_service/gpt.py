#  Drakkar-Software OctoBot-Tentacles
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
import asyncio
import os
import typing
import uuid
import openai
import logging
import datetime
import json

from openai.lib._pydantic import to_strict_json_schema

MCP_AVAILABLE = False
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot_services.errors as errors
import octobot_services.enums as enums
import octobot_services.interfaces.util as interfaces_util
from octobot_services.services.abstract_ai_service import AbstractAIService

import octobot_commons.constants as commons_constants
import octobot_commons.enums as commons_enums
import octobot_commons.logging as commons_logging
import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.authentication as authentication
import octobot_commons.tree as tree
import octobot_commons.configuration.fields_utils as fields_utils

import octobot.constants as constants
import octobot.community as community


NO_SYSTEM_PROMPT_MODELS = [
    "o1-mini",
]
MINIMAL_PARAMS_SERIES_MODELS = [
    "o",  # the whole o-series does not support temperature parameter
]
MINIMAL_PARAMS_MODELS = [
    # Empty for now - gpt-5 base models should be checked via _is_of_series instead
    # This list is for exact model name prefixes only
]
SYSTEM = "system"
USER = "user"

REASONING_EFFORT_LOW = "low"
REASONING_EFFORT_MEDIUM = "medium"
REASONING_EFFORT_HIGH = "high"
REASONING_EFFORT_VALUES = (REASONING_EFFORT_LOW, REASONING_EFFORT_MEDIUM, REASONING_EFFORT_HIGH)


class LLMService(services.AbstractAIService):
    BACKTESTING_ENABLED = True

    DEFAULT_MODEL = None
    NO_TOKEN_LIMIT_VALUE = -1
    HTTP_TIMEOUT = 300.0  # HTTP client timeout in seconds

    def get_fields_description(self):
        if self._env_secret_key is None:
            fields = {
                services_constants.CONFIG_OPENAI_SECRET_KEY: "Your openai API secret key",
                services_constants.CONFIG_LLM_CUSTOM_BASE_URL: (
                    "Custom LLM base url to use. Leave empty to use openai.com. For Ollama models, "
                    "add /v1 to the url (such as: http://localhost:11434/v1)"
                ),
                services_constants.CONFIG_LLM_MODEL: (
                    f"LLM model to use (default: {self.DEFAULT_MODEL}). "
                    "Can be overridden by GPT_MODEL environment variable."
                ),
                services_constants.CONFIG_LLM_MODEL_FAST: (
                    "Model for 'fast' policy (e.g. analysts, debators). Leave empty to use main model."
                ),
                services_constants.CONFIG_LLM_MODEL_REASONING: (
                    "Model for 'reasoning' policy (e.g. judge, distribution). Leave empty to use main model."
                ),
                services_constants.CONFIG_LLM_DAILY_TOKENS_LIMIT: (
                    f"Daily token limit (default: {self.NO_TOKEN_LIMIT_VALUE} for no limit). "
                    "Can be overridden by GPT_DAILY_TOKEN_LIMIT environment variable."
                ),
                services_constants.CONFIG_LLM_SHOW_REASONING: (
                    "Show model thinking/reasoning. When enabled, uses Responses API for better reasoning access. "
                    "Default: False."
                ),
                services_constants.CONFIG_LLM_REASONING_EFFORT: (
                    "Reasoning effort level for models that support reasoning. "
                    "Values: 'low', 'medium', 'high', or empty for default. "
                    "If configured, the model will be treated as reasoning-capable."
                ),
                services_constants.CONFIG_LLM_MCP_SERVERS: (
                    "List of MCP (Model Context Protocol) server configurations. "
                    "Each server config should include: name (optional), transport ('stdio', 'http', or 'sse'), "
                    "and either 'command'/'args' for stdio or 'url' for http/sse. "
                    "Example: [{'name': 'filesystem', 'transport': 'stdio', 'command': 'npx', "
                    "'args': ['-y', '@modelcontextprotocol/server-filesystem']}]"
                ),
                services_constants.CONFIG_LLM_AUTO_INJECT_MCP_TOOLS: (
                    "Automatically inject discovered MCP tools into all completions. "
                    "When enabled, tools from configured MCP servers are automatically available. "
                    "Default: True."
                ),
                services_constants.CONFIG_LLM_AI_PROVIDER: "AI provider to use (openai, anthropic, local, other)",
                services_constants.CONFIG_LLM_AUTH_TOKEN: "Authentication token for the AI service"
            }
            return fields
        return {}

    def get_default_value(self):
        if self._env_secret_key is None:
            return {
                services_constants.CONFIG_LLM_MODEL: self.DEFAULT_MODEL,
                services_constants.CONFIG_LLM_MODEL_FAST: "",
                services_constants.CONFIG_LLM_MODEL_REASONING: "",
                services_constants.CONFIG_LLM_DAILY_TOKENS_LIMIT: self.NO_TOKEN_LIMIT_VALUE,
                services_constants.CONFIG_LLM_SHOW_REASONING: False,
                services_constants.CONFIG_LLM_REASONING_EFFORT: "",
                services_constants.CONFIG_LLM_MCP_SERVERS: [],
                services_constants.CONFIG_LLM_AUTO_INJECT_MCP_TOOLS: True,
                services_constants.CONFIG_LLM_AI_PROVIDER: "",
                services_constants.CONFIG_LLM_AUTH_TOKEN: "",
            }
        return {}

    def __init__(self):
        super().__init__()
        logging.getLogger("openai").setLevel(logging.WARNING)
        self._env_secret_key: typing.Optional[str] = (
            os.getenv(services_constants.ENV_OPENAI_SECRET_KEY, None) or None
        )
        # Model priority: env var > config > default
        env_model = os.getenv(services_constants.ENV_GPT_MODEL, None)
        self.model: str = env_model or self.DEFAULT_MODEL

        self.models: list[str] = []

        # Daily token limit priority: env var > config > default
        env_daily_token_limit_str = os.getenv(
            services_constants.ENV_GPT_DAILY_TOKENS_LIMIT, None
        )
        if env_daily_token_limit_str:
            self._env_daily_token_limit: int = int(env_daily_token_limit_str)
        else:
            self._env_daily_token_limit: int = self.NO_TOKEN_LIMIT_VALUE

        self._daily_tokens_limit: int = self._env_daily_token_limit
        self.consumed_daily_tokens: int = 1
        self.last_consumed_token_date: typing.Optional[datetime.date] = None
        
        self._client: typing.Optional[openai.AsyncOpenAI] = None
        
        # MCP discovered tools cache
        self._mcp_tools: list[dict] = []
        self._mcp_clients: list[typing.Any] = []
        self._octobot_mcp_tools: typing.Optional[list] = None

        self.ai_provider = enums.AIProvider.OPENAI

    def _load_model_from_config(self):
        """Load model from config if not overridden by environment variable."""
        if os.getenv(services_constants.ENV_GPT_MODEL, None):
            # Environment variable takes precedence
            return
        try:
            config_model = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LLM_MODEL)
            if config_model and not fields_utils.has_invalid_default_config_value(
                config_model
            ):
                self.model = config_model
        except (KeyError, TypeError):
            pass

    def _load_models_config(self):
        """Load fast/reasoning model config for policy-based model selection."""
        self.models_config = {}
        try:
            svc_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(self.get_type()) or {}
            fast_model = svc_config.get(services_constants.CONFIG_LLM_MODEL_FAST)
            reasoning_model = svc_config.get(services_constants.CONFIG_LLM_MODEL_REASONING)
            if fast_model and not fields_utils.has_invalid_default_config_value(fast_model):
                self.models_config["fast"] = fast_model
            if reasoning_model and not fields_utils.has_invalid_default_config_value(reasoning_model):
                self.models_config["reasoning"] = reasoning_model
        except (KeyError, TypeError):
            pass

    def _load_token_limit_from_config(self):
        """Load daily token limit from config if not overridden by environment variable."""
        if os.getenv(services_constants.ENV_GPT_DAILY_TOKENS_LIMIT, None):
            # Environment variable takes precedence
            return
        try:
            config_limit = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LLM_DAILY_TOKENS_LIMIT)
            if (
                config_limit is not None
                and not fields_utils.has_invalid_default_config_value(config_limit)
            ):
                if isinstance(config_limit, str):
                    self._daily_tokens_limit = int(config_limit)
                else:
                    self._daily_tokens_limit = config_limit
        except (KeyError, TypeError, ValueError):
            pass

    def _load_show_reasoning_from_config(self) -> bool:
        """Load show_reasoning setting from config."""
        try:
            config_show_reasoning = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LLM_SHOW_REASONING)
            if config_show_reasoning is not None:
                if isinstance(config_show_reasoning, str):
                    return config_show_reasoning.lower() in ("true", "1", "yes")
                return bool(config_show_reasoning)
        except (KeyError, TypeError):
            pass
        return False

    def _load_reasoning_effort_from_config(self) -> typing.Optional[str]:
        """Load reasoning_effort setting from config.
        
        Returns:
            str: "low", "medium", "high", or None if not configured
        """
        try:
            config_reasoning_effort = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LLM_REASONING_EFFORT)
            if config_reasoning_effort is not None:
                if isinstance(config_reasoning_effort, str):
                    effort = config_reasoning_effort.strip().lower()
                    if effort in REASONING_EFFORT_VALUES:
                        return effort
                    elif effort == "":
                        return None
                # Try to convert other types
                effort_str = str(config_reasoning_effort).lower()
                return effort_str if effort_str in REASONING_EFFORT_VALUES else None
        except (KeyError, TypeError):
            pass
        return None

    def _should_auto_inject_mcp_tools(self) -> bool:
        """Check if MCP tools should be auto-injected."""
        try:
            config_auto_inject = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LLM_AUTO_INJECT_MCP_TOOLS)
            if config_auto_inject is not None:
                if isinstance(config_auto_inject, str):
                    return config_auto_inject.lower() in ("true", "1", "yes")
                return bool(config_auto_inject)
        except (KeyError, TypeError):
            pass
        return True  # Default to True

    def _load_mcp_servers_from_config(self) -> list:
        """Load MCP server configurations from config.
        
        Returns:
            List of MCP server configuration dicts
        """
        try:
            mcp_servers = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LLM_MCP_SERVERS)
            if mcp_servers is not None:
                # Try to convert to list using duck typing
                try:
                    return list(mcp_servers)
                except TypeError:
                    pass
        except (KeyError, TypeError):
            pass
        return []

    def _load_ai_config_from_config(self):
        try:
            svc_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ]
            self.api_key = self._get_api_key()

            ai_provider_str = svc_config.get(services_constants.CONFIG_LLM_AI_PROVIDER)
            if ai_provider_str and not fields_utils.has_invalid_default_config_value(ai_provider_str):
                try:
                    self.ai_provider = enums.AIProvider(ai_provider_str.lower())
                except ValueError:
                    self.logger.warning(f"Invalid AI provider: {ai_provider_str}")
            
            auth_token = svc_config.get(services_constants.CONFIG_LLM_AUTH_TOKEN)
            if auth_token and not fields_utils.has_invalid_default_config_value(auth_token):
                self.auth_token = auth_token
                
        except (KeyError, TypeError):
            pass

    def _extract_tool_attr(self, tool, attr_name: str, default=''):
        """Extract attribute from tool (object or dict) using duck typing.
        
        Args:
            tool: Tool object (dict or object with attributes)
            attr_name: Name of the attribute to extract
            default: Default value if attribute not found
        
        Returns:
            Attribute value or default
        """
        try:
            return tool.get(attr_name, default)
        except AttributeError:
            try:
                return getattr(tool, attr_name, default)
            except AttributeError:
                return default

    def _extract_tools_list(self, tools_result):
        """Extract tools list from various response formats using duck typing.
        
        Args:
            tools_result: Response from list_tools() (object, dict, or list)
        
        Returns:
            List of tools
        """
        try:
            return tools_result.tools
        except AttributeError:
            pass
        
        try:
            return tools_result['tools']
        except (TypeError, KeyError):
            pass
        
        try:
            return list(tools_result)
        except TypeError:
            pass
        
        return []

    def _convert_mcp_tool_to_openai(self, mcp_tool: dict) -> dict:
        """Convert MCP tool format to OpenAI function format.
        
        Args:
            mcp_tool: MCP tool dict with 'name', 'description', 'inputSchema'
        
        Returns:
            OpenAI tool format dict with 'type' and 'function' keys
        """
        tool_name = mcp_tool.get("name", "")
        tool_description = mcp_tool.get("description", "")
        input_schema = mcp_tool.get("inputSchema", {})
        parameters = input_schema.copy() if input_schema else {}
        
        return {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters,
            }
        }

    async def _discover_mcp_tools(self) -> list:
        """Discover tools from configured MCP servers.
        
        Returns:
            List of OpenAI-formatted tool definitions
        """
        if not MCP_AVAILABLE:
            self.logger.warning(
                "MCP Python SDK not available. Install with: pip install mcp"
            )
            return []
        
        mcp_servers = self._load_mcp_servers_from_config()
        if not mcp_servers:
            return []
        
        discovered_tools = []
        
        for server_config in mcp_servers:
            server_name = server_config.get("name", "unknown")
            transport = server_config.get("transport", "stdio")
            
            try:
                if transport != "stdio":
                    # Only stdio transport is currently supported
                    if transport in ("http", "sse"):
                        self.logger.warning(
                            f"MCP server '{server_name}': {transport} transport not yet implemented. "
                            "Only stdio transport is currently supported."
                        )
                    else:
                        self.logger.warning(
                            f"MCP server '{server_name}': Unknown transport '{transport}'. "
                            "Supported: 'stdio', 'http', 'sse'"
                        )
                    continue
                
                # Handle stdio transport
                command = server_config.get("command")
                if not command:
                    self.logger.warning(
                        f"MCP server '{server_name}': stdio transport requires 'command'"
                    )
                    continue
                
                # Ensure args is a list
                args = server_config.get("args", [])
                try:
                    args = list(args)
                except TypeError:
                    args = []
                
                # Create stdio server parameters
                server_params = StdioServerParameters(
                    command=command,
                    args=args,
                )
                
                # Connect and discover tools
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        
                        # List available tools
                        tools_result = await session.list_tools()
                        
                        # Extract tools list using duck typing
                        tools_list = self._extract_tools_list(tools_result)
                        
                        for mcp_tool in tools_list:
                            # Extract tool information using duck typing
                            tool_name = self._extract_tool_attr(mcp_tool, 'name', '')
                            if not tool_name:
                                continue
                            
                            tool_description = self._extract_tool_attr(mcp_tool, 'description', '')
                            tool_schema = self._extract_tool_attr(mcp_tool, 'inputSchema', {})
                            
                            openai_tool = self._convert_mcp_tool_to_openai({
                                "name": tool_name,
                                "description": tool_description or "",
                                "inputSchema": tool_schema or {},
                            })
                            discovered_tools.append(openai_tool)
                            self.logger.debug(
                                f"Discovered MCP tool '{tool_name}' from server '{server_name}'"
                            )
                    
            except Exception as err:
                self.logger.warning(
                    f"Failed to discover tools from MCP server '{server_name}': {err}. "
                    "Continuing without tools from this server."
                )
                continue
        
        if discovered_tools:
            self.logger.info(
                f"Discovered {len(discovered_tools)} tools from {len(mcp_servers)} MCP server(s)"
            )
        
        return discovered_tools

    async def _discover_octobot_mcp_tools(self) -> list:
        if self._octobot_mcp_tools is not None:
            return self._octobot_mcp_tools
        
        if not MCP_AVAILABLE:
            self.logger.warning(
                "MCP Python SDK not available. Install with: pip install mcp"
            )
            discovered_tools = []
            self._octobot_mcp_tools = discovered_tools
            return discovered_tools
        
        try:
            import tentacles.Services.Interfaces.mcp_interface.mcp_interface as mcp_interface_module
            MCPInterface = mcp_interface_module.MCPInterface
            
            bot_api = interfaces_util.get_bot_api()
            if not bot_api:
                self.logger.warning("bot_api not available, cannot discover OctoBot MCP tools")
                discovered_tools = []
                self._octobot_mcp_tools = discovered_tools
                return discovered_tools
            
            mcp_interface = bot_api.get_interface(MCPInterface)
            if not mcp_interface:
                self.logger.debug("MCPInterface not found or not running")
                discovered_tools = []
                self._octobot_mcp_tools = discovered_tools
                return discovered_tools
            
            connection_info = mcp_interface.get_connection_info()
            transport = connection_info.get("transport")
            
            if transport != "http":
                self.logger.warning(f"Unsupported transport type: {transport}. Only HTTP transport is supported.")
                discovered_tools = []
                self._octobot_mcp_tools = discovered_tools
                return discovered_tools
            
            # For HTTP transport, we can connect
            url = connection_info.get("url")
            if not url:
                self.logger.warning("MCP interface HTTP URL not available")
                discovered_tools = []
                self._octobot_mcp_tools = discovered_tools
                return discovered_tools
            
            # Try to connect via HTTP and discover tools
            # Note: HTTP transport support may vary by MCP SDK version
            self.logger.warning(
                f"HTTP transport for OctoBot MCP not yet fully implemented. "
                f"URL: {url}. "
                "HTTP client connection needs to be implemented."
            )
            discovered_tools = []
            self._octobot_mcp_tools = discovered_tools
            return discovered_tools
                
        except ImportError:
            self.logger.debug("MCPInterface not available (interface may not be installed)")
            discovered_tools = []
            self._octobot_mcp_tools = discovered_tools
            return discovered_tools
        except Exception as err:
            self.logger.warning(
                f"Failed to discover OctoBot MCP tools: {err}. "
                "Continuing without OctoBot MCP tools."
            )
            discovered_tools = []
            self._octobot_mcp_tools = discovered_tools
            return discovered_tools

    @staticmethod
    def create_message(role, content, model: typing.Optional[str] = None):
        if role == SYSTEM and model in NO_SYSTEM_PROMPT_MODELS:
            commons_logging.get_logger(LLMService.__name__).debug(
                f"Overriding prompt to use {USER} instead of {SYSTEM} for {model}"
            )
            return {"role": USER, "content": content}
        return {"role": role, "content": content}

    @staticmethod
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
        """
        tool_results = []
        
        for tool_call in tool_calls:
            function_info = tool_call.get("function", {})
            function_name = function_info.get("name")
            arguments_str = function_info.get("arguments", "{}")
            
            # Parse arguments JSON
            try:
                arguments = json.loads(arguments_str)
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            
            # Execute tool
            try:
                result = tool_executor(function_name, arguments)
            except Exception as e:
                # Handle errors gracefully
                result = {"error": str(e)}
            
            # Format tool result message
            tool_results.append({
                "tool_call_id": tool_call.get("id"),
                "role": "tool",
                "name": function_name,
                "content": json.dumps(result),
            })
        
        return tool_results

    async def _prepare_tools_for_api(
        self,
        tools: typing.Optional[list],
        use_octobot_mcp: typing.Optional[bool],
    ) -> list:
        """Prepare and merge tools for API call.
        
        Args:
            tools: Optional list of tool definitions.
            use_octobot_mcp: Optional bool to include OctoBot MCP server tools.
        
        Returns:
            List of effective tools (merged with MCP tools if enabled).
        """
        effective_tools = list(tools) if tools is not None else []
        
        # Auto-inject MCP tools if enabled
        if self._should_auto_inject_mcp_tools() and self._mcp_tools:
            effective_tools = effective_tools + self._mcp_tools.copy()
        
        # Add OctoBot MCP tools if requested
        if use_octobot_mcp:
            octobot_mcp_tools = await self._discover_octobot_mcp_tools()
            if octobot_mcp_tools:
                effective_tools = effective_tools + octobot_mcp_tools
        
        return effective_tools

    def _ensure_json_in_messages(self, messages: list) -> list:
        """Ensure the word 'json' appears in at least one message.
        
        When using response_format with type 'json_object', the API requires
        the word 'json' to appear somewhere in the messages. This method
        checks and adds it if needed.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
        
        Returns:
            Messages list (potentially modified) with 'json' word present.
        """
        # Check if 'json' appears in any message content (case-insensitive)
        has_json = any(
            "json" in str(msg.get("content", "")).lower()
            for msg in messages
        )
        
        if not has_json:
            # Find the first system message, or create one
            system_msg_index = None
            for i, msg in enumerate(messages):
                if msg.get("role") == "system":
                    system_msg_index = i
                    break
            
            if system_msg_index is not None:
                # Append to existing system message
                existing_content = messages[system_msg_index].get("content", "")
                messages[system_msg_index] = {
                    "role": "system",
                    "content": f"{existing_content}\n\nYou must respond with valid JSON."
                }
            else:
                # Prepend a new system message
                messages.insert(0, {
                    "role": "system",
                    "content": "You must respond with valid JSON."
                })
        
        return messages
    
    def _prepare_json_response_format(
        self,
        json_output: bool,
        response_schema: typing.Optional[typing.Any],
    ) -> typing.Optional[dict]:
        """Prepare JSON response format for API call.
        
        Args:
            json_output: Whether to return JSON format.
            response_schema: Optional Pydantic model or JSON schema dict.
        
        Returns:
            Response format dict or None if json_output is False.
        """
        if not json_output:
            return None
        
        if response_schema is not None:
            use_strict = False
            try:
                schema = to_strict_json_schema(response_schema)
                try:
                    # __strict_json_schema__ only exists on AgentBaseModel
                    use_strict = schema.__strict_json_schema__
                except AttributeError:
                    pass
            except AttributeError:
                # response_schema is already a dict (no model_json_schema method)
                schema = response_schema
            
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.get("title", "response"),
                    "schema": schema,
                    "strict": use_strict,
                }
            }
        else:
            # Fallback to basic JSON object format
            return {"type": "json_object"}

    def _prepare_chat_completion_kwargs(
        self,
        messages: list,
        model: str,
        max_tokens: int,
        n: int,
        stop,
        temperature: float,
        supports_params: bool,
        has_reasoning_config: bool,
        reasoning_effort: typing.Optional[str],
        effective_tools: list,
        tool_choice: typing.Optional[typing.Union[str, dict]],
        json_output: bool,
        response_schema: typing.Optional[typing.Any],
    ) -> dict:
        """Prepare API kwargs for chat completion call.
        
        Args:
            messages: List of message dicts.
            model: Model name.
            max_tokens: Maximum tokens in response.
            n: Number of completions.
            stop: Stop sequences.
            temperature: Sampling temperature.
            supports_params: Whether model supports all parameters.
            has_reasoning_config: Whether reasoning is configured.
            reasoning_effort: Reasoning effort level if configured.
            effective_tools: List of tools to include.
            tool_choice: Tool choice setting.
            json_output: Whether to return JSON format.
            response_schema: Optional response schema.
        
        Returns:
            Complete api_kwargs dict for chat.completions.create.
        """
        api_kwargs = {
            "model": model,
            "max_completion_tokens": max_tokens,
            "n": n,
            "stop": stop,
            "temperature": temperature if supports_params else openai.NOT_GIVEN,
            "messages": messages,
        }
        
        # Add reasoning_effort if configured
        if has_reasoning_config:
            api_kwargs["reasoning_effort"] = reasoning_effort
        
        # Add tools to API call if provided
        if effective_tools:
            api_kwargs["tools"] = effective_tools
            # Set tool_choice if provided, otherwise default to "auto"
            if tool_choice is not None:
                api_kwargs["tool_choice"] = tool_choice
            elif not json_output:  # Don't set tool_choice if json_output is True
                api_kwargs["tool_choice"] = "auto"
        
        # Add JSON response format if needed
        response_format = self._prepare_json_response_format(json_output, response_schema)
        if response_format:
            api_kwargs["response_format"] = response_format
            # When using json_object format, ensure "json" appears in messages
            if response_format.get("type") == "json_object":
                messages = self._ensure_json_in_messages(messages)
                api_kwargs["messages"] = messages
        
        return api_kwargs

    def _process_chat_completion_response(
        self,
        completions,
        model: str,
    ) -> typing.Union[str, dict]:
        """Process chat completion response and extract content/tool_calls.
        
        Args:
            completions: Completions object from API.
            model: Model name for error messages.
        
        Returns:
            str: Content string if no tool calls.
            dict: Dict with 'content' and 'tool_calls' keys if tool calls present.
        
        Raises:
            InvalidRequestError: If response is empty or has no content.
        """
        if completions.usage is not None:
            self._update_token_usage(completions.usage.total_tokens)
        
        if not completions.choices:
            raise errors.InvalidRequestError(
                f"Empty response from model {model}: no choices returned"
            )
        
        message = completions.choices[0].message
        message_content = message.content
        
        # Check for tool calls
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                tool_calls.append({
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    }
                })
        
        # If tool calls are present, return structured response
        if tool_calls:
            return {
                "content": message_content,
                "tool_calls": tool_calls
            }
        
        # If no content and no tool calls, raise error
        if message_content is None:
            raise errors.InvalidRequestError(
                f"Empty content in response from model {model}. "
                "This may occur when tool calls are present or the model returned no content."
            )
        
        return message_content

    @AbstractAIService.retry_llm_completion()
    async def get_completion(
        self,
        messages,
        model=None,
        max_tokens=10000,
        n=1,
        stop=None,
        temperature=0.5,
        json_output=False,
        response_schema=None,
        reasoning_effort: typing.Optional[str] = None,
        show_reasoning: typing.Optional[bool] = None,
        tools: typing.Optional[list] = None,
        tool_choice: typing.Optional[typing.Union[str, dict]] = None,
        use_octobot_mcp: typing.Optional[bool] = None,
        middleware: typing.Optional[typing.List[typing.Callable]] = None,
    ) -> typing.Union[str, dict, None]:
        """Get a completion from the LLM.
        
        Args:
            messages: List of message dicts
            model: Model to use
            max_tokens: Max tokens in response
            n: Number of completions
            stop: Stop sequences
            temperature: Sampling temperature
            json_output: Return JSON format
            response_schema: Optional Pydantic model or JSON schema dict for structured output.
                           If provided with json_output=True, enforces the response to match schema.
            reasoning_effort: Set reasoning effort if model supports reasoning.
                            Values: "low", "medium", "high", or None to use config/default.
                            If configured (via parameter or config), model is treated as reasoning-capable.
            show_reasoning: If True and reasoning_effort is configured, returns reasoning summary.
                          If None, uses config value. Default: False.
            tools: Optional list of tool definitions for function calling.
                  Each tool should be a dict with 'type' and 'function' keys.
            tool_choice: Optional control for tool usage. Can be "auto", "none", 
                        or a dict specifying a specific tool.
            use_octobot_mcp: Optional bool to include OctoBot MCP server tools.
                            If True, automatically discovers and includes tools from OctoBot MCP interface.
                            If None, uses default behavior (does not include OctoBot MCP).
                            If False, explicitly excludes OctoBot MCP tools.
        
        Returns:
            str: Content when no tools are used or tool_choice is "none"
            dict: When tools are used and model makes tool calls, returns dict with:
                  - "content": str | None (may be None if only tool calls)
                  - "tool_calls": list of tool call dicts with id, type, function keys
            dict: {"content": str, "reasoning": str} when show_reasoning=True and reasoning available
            None: On error
        """
        self._ensure_rate_limit()
        try:
            model = model or self.model
            
            # Load reasoning_effort from config if not provided as parameter
            if reasoning_effort is None:
                reasoning_effort = self._load_reasoning_effort_from_config()
            
            # Determine if we should show reasoning
            if show_reasoning is None:
                show_reasoning = self._load_show_reasoning_from_config()
            
            # If reasoning_effort is configured, treat model as reasoning-capable
            has_reasoning_config = reasoning_effort is not None and reasoning_effort in REASONING_EFFORT_VALUES
            
            # Use Responses API when reasoning is configured and show_reasoning is enabled
            # BUT skip if tools are involved (Responses API may not support tools)
            # AND only if the model/endpoint supports Responses API
            if has_reasoning_config and show_reasoning and not tools and self._should_use_responses_api(model):
                try:
                    return await self._get_completion_with_responses_api(
                        messages, model, max_tokens, n, stop, temperature,
                        json_output, response_schema, reasoning_effort
                    )
                except (AttributeError, errors.InvalidRequestError) as err:
                    # Fall back to Chat Completions if Responses API fails
                    self.logger.warning(
                        f"Responses API failed for {model}: {err}. "
                        "Falling back to Chat Completions API."
                    )
                    # Continue with Chat Completions below
            
            supports_params = not self._is_minimal_params_model(model)
            if not supports_params:
                self.logger.debug(
                    f"The {model} model does not support every required parameter, results might not be as accurate "
                    f"as with other models."
                )
            
            effective_tools = await self._prepare_tools_for_api(tools, use_octobot_mcp)
            
            api_kwargs = self._prepare_chat_completion_kwargs(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                n=n,
                stop=stop,
                temperature=temperature,
                supports_params=supports_params,
                has_reasoning_config=has_reasoning_config,
                reasoning_effort=reasoning_effort,
                effective_tools=effective_tools,
                tool_choice=tool_choice,
                json_output=json_output,
                response_schema=response_schema,
            )

            completions = await self._get_client().chat.completions.create(**api_kwargs)
            return self._process_chat_completion_response(completions, model)
        except (
            openai.BadRequestError,
            openai.UnprocessableEntityError,  # error in request
        ) as err:
            if "does not support 'system' with this model" in str(err):
                # v2 compatibility: use getattr to safely access message attribute
                desc = getattr(err, 'message', str(err))
                err_message = (
                    f'The "{model}" model can\'t be used with {SYSTEM} prompts. '
                    f"It should be added to NO_SYSTEM_PROMPT_MODELS: {desc}"
                )
            else:
                err_message = f"Error when running request with model {model} (invalid request): {err}"
            raise errors.InvalidRequestError(err_message) from err
        except openai.NotFoundError as err:
            self.logger.error(
                f"Model {model} not found: {err}. Available models: {', '.join(self.models)}"
            )
            self.creation_error_message = str(err)
        except openai.AuthenticationError as err:
            self.logger.error(f"Invalid OpenAI api key: {err}")
            self.creation_error_message = str(err)
        except Exception as err:
            raise errors.InvalidRequestError(
                f"Unexpected error when running request with model {model}: {err}"
            ) from err

    def _execute_tool_calls_and_append(
        self,
        tool_calls: list,
        tool_executor: typing.Callable[[str, dict], typing.Any],
        conversation_messages: list,
    ) -> None:
        """Execute tool calls and append results to conversation messages.
        
        Args:
            tool_calls: List of tool call dicts.
            tool_executor: Callback function to execute tools.
            conversation_messages: List of messages to append tool results to (modified in place).
        """
        # Execute tools and get formatted results
        tool_results = self.handle_tool_calls(tool_calls, tool_executor)
        
        # Append tool results to conversation
        conversation_messages.extend(tool_results)

    @AbstractAIService.retry_llm_completion()
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
        middleware: typing.Optional[typing.List[typing.Callable]] = None,
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
        # Create a copy of messages to avoid mutating the original
        conversation_messages = list(messages)
        
        for iteration in range(max_tool_iterations):
            # Call get_completion
            response = await self.get_completion(
                messages=conversation_messages,
                model=model,
                max_tokens=max_tokens,
                n=n,
                stop=stop,
                temperature=temperature,
                json_output=False,  # Don't parse JSON yet, need to check for tool_calls
                response_schema=response_schema,
                tools=tools,
                tool_choice=tool_choice,
                use_octobot_mcp=use_octobot_mcp,
            )
            
            # Check if response contains tool_calls
            if isinstance(response, dict) and response.get("tool_calls"):
                tool_calls = response.get("tool_calls", [])
                
                # If return_tool_calls=True, normalize and return first tool call
                if return_tool_calls and tool_calls:
                    tool_call = tool_calls[0]  # Take first tool call
                    function_info = tool_call.get("function", {})
                    tool_name = function_info.get("name")
                    arguments_str = function_info.get("arguments", "{}")
                    
                    # Parse arguments JSON
                    try:
                        arguments = json.loads(arguments_str)
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}
                    
                    return {
                        "tool_name": tool_name,
                        "arguments": arguments
                    }
                
                # If no tool_executor provided, return response as-is
                if tool_executor is None:
                    if json_output:
                        return self.parse_completion_response(response, json_output=True)
                    return response
                
                # Execute tools and append results to conversation
                self._execute_tool_calls_and_append(tool_calls, tool_executor, conversation_messages)
                
                # Continue loop to call LLM again with tool results
                continue
            
            # No tool_calls, we have the final response
            # Parse it according to json_output setting
            return self.parse_completion_response(response, json_output=json_output)
        
        # Max iterations reached - this shouldn't happen in normal operation
        # Return the last response we got
        if isinstance(response, dict) and response.get("tool_calls"):
            raise ValueError(
                f"Maximum tool calling iterations ({max_tool_iterations}) reached. "
                "The LLM may be stuck in a loop requesting tools. "
                "Consider increasing max_tool_iterations or checking tool implementations."
            )
        
        # Fallback: parse and return the last response
        if return_tool_calls:
            # When return_tool_calls=True, no tool calls were found, return None
            return None
        return self.parse_completion_response(response, json_output=json_output)

    def _get_client(self) -> openai.AsyncOpenAI:
        """Get or create a cached AsyncOpenAI client instance.
        
        The client is cached and reused for connection pooling efficiency.
        
        Returns:
            openai.AsyncOpenAI: Cached client instance
        """
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._get_api_key(),
                base_url=self._get_base_url(),
                timeout=self.HTTP_TIMEOUT,
            )
        return self._client

    def get_chat_model(
        self,
        model: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None,
        max_tokens: typing.Optional[int] = None,
        **kwargs
    ) -> typing.Any:
        """
        Get a chat model instance for use with agents or other LLM components.
        
        For OpenAI-based services, this returns the AsyncOpenAI client.
        For LangChain integration, use init_chat_model() instead.
        
        Args:
            model: Optional model override (stored for reference, client uses self.model).
            temperature: Optional temperature override (not applied to OpenAI client directly).
            max_tokens: Optional max_tokens override (not applied to OpenAI client directly).
            **kwargs: Additional keyword arguments (ignored for OpenAI).
        
        Returns:
            openai.AsyncOpenAI: The OpenAI client instance.
        """
        return self._get_client()

    def _convert_messages_to_responses_input(self, messages: list) -> list:
        """Convert chat messages to Responses API input format.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
        
        Returns:
            List of input items for Responses API, each with 'type' and 'text' keys.
        """
        input_items = []
        for msg in messages:
            role = msg.get("role", "user")
            
            # Skip tool role messages - Responses API doesn't support them in input format
            if role == "tool":
                continue
            
            # Get content, handling None values
            content = msg.get("content")
            if content is None:
                # If content is None, skip this message unless it's a system message
                # (system messages might have empty content but should still be included)
                if role == "system":
                    content = ""
                else:
                    # Skip messages with None content (e.g., assistant messages with only tool_calls)
                    continue
            
            # Ensure content is a string
            if not isinstance(content, str):
                content = str(content) if content is not None else ""
            
            # Skip empty content messages (except system messages)
            if not content and role != "system":
                continue
            
            if role == "system":
                # For system messages, prepend to first user message or add as separate text
                if input_items and input_items[-1].get("type") == "input_text":
                    # Prepend system message to last text input
                    input_items[-1]["text"] = f"System: {content}\n\n{input_items[-1]['text']}"
                else:
                    input_items.append({
                        "type": "input_text",
                        "text": f"System: {content}"
                    })
            elif role in ("user", "assistant"):
                input_items.append({
                    "type": "input_text",
                    "text": content
                })
        
        return input_items

    def _validate_responses_input_items(self, input_items: list, model: str) -> list:
        """Validate and filter input items for Responses API.
        
        Args:
            input_items: List of input items to validate.
            model: Model name for error messages.
        
        Returns:
            List of validated input items.
        
        Raises:
            InvalidRequestError: If no valid items remain after validation.
        """
        validated_input_items = []
        for item in input_items:
            # Check that item has required "type" field
            if not isinstance(item, dict) or "type" not in item:
                self.logger.warning(f"Skipping invalid input item (missing type): {item}")
                continue
            
            item_type = item.get("type")
            
            # Validate input_text items
            if item_type == "input_text":
                if "text" not in item:
                    self.logger.warning(f"Skipping invalid input_text item (missing text): {item}")
                    continue
                text = item.get("text")
                # Ensure text is a string and not None
                if not isinstance(text, str):
                    if text is None:
                        self.logger.warning(f"Skipping input_text item with None text: {item}")
                        continue
                    text = str(text)
                    item["text"] = text
                # Skip empty text items (except if it's the only item, which shouldn't happen)
                if not text.strip() and len(validated_input_items) > 0:
                    self.logger.debug(f"Skipping empty input_text item: {item}")
                    continue
            
            # Add validated item
            validated_input_items.append(item)
        
        # Ensure we have at least one valid input item
        if not validated_input_items:
            raise errors.InvalidRequestError(
                f"No valid input items after validation for model {model}. "
                "All messages may have been filtered out."
            )
        
        return validated_input_items

    def _extract_responses_api_result(self, response, model: str) -> typing.Union[str, dict]:
        """Extract content and reasoning from Responses API response.
        
        Args:
            response: Response object from Responses API.
            model: Model name for logging and error messages.
        
        Returns:
            str: Content string if no reasoning available.
            dict: Dict with 'content' and 'reasoning' keys if reasoning is available.
        
        Raises:
            InvalidRequestError: If content is empty.
        """
        # Extract content and reasoning from response
        content = None
        reasoning_summary = None
        
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                # Handle different output item types
                item_type = getattr(output_item, 'type', None)
                
                if item_type == 'text':
                    # Extract text content
                    content = getattr(output_item, 'text', None)
                    if content is None:
                        # Try alternative attribute names
                        content = getattr(output_item, 'content', None)
                
                elif item_type == 'reasoning':
                    # Extract reasoning summary
                    summary = getattr(output_item, 'summary', None)
                    if summary:
                        if isinstance(summary, list) and len(summary) > 0:
                            # Summary is a list of summary items
                            first_summary = summary[0]
                            reasoning_summary = getattr(first_summary, 'text', None) or str(first_summary)
                        elif hasattr(summary, 'text'):
                            reasoning_summary = summary.text
                        else:
                            reasoning_summary = str(summary)
        
        # Update token usage if available
        if hasattr(response, 'usage') and response.usage:
            total_tokens = getattr(response.usage, 'total_tokens', None)
            if total_tokens:
                self._update_token_usage(total_tokens)
        
        # Log reasoning if available
        if reasoning_summary:
            self.logger.info(
                f"Model reasoning summary for {model} ({len(reasoning_summary)} chars): "
                f"{reasoning_summary[:200]}{'...' if len(reasoning_summary) > 200 else ''}"
            )
        
        if content is None:
            raise errors.InvalidRequestError(
                f"Empty content in response from model {model} via Responses API."
            )
        
        # Return dict with content and reasoning if reasoning is available
        if reasoning_summary:
            return {
                "content": content,
                "reasoning": reasoning_summary
            }
        return content

    async def _get_completion_with_responses_api(
        self,
        messages,
        model: str,
        max_tokens: int,
        n: int,
        stop,
        temperature: float,
        json_output: bool,
        response_schema,
        reasoning_effort: typing.Optional[str],
    ) -> typing.Union[str, dict]:
        """Get completion using Responses API for better reasoning access.
        
        This method is used for reasoning models when show_reasoning is enabled.
        The Responses API provides better access to reasoning summaries.
        """
        try:
            # Convert messages to Responses API format
            input_items = self._convert_messages_to_responses_input(messages)
            
            # Validate and filter input items
            validated_input_items = self._validate_responses_input_items(input_items, model)

            responses_kwargs = {
                "model": model,
                "input": validated_input_items,
                "max_output_tokens": max_tokens,
            }
            
            if reasoning_effort and reasoning_effort in REASONING_EFFORT_VALUES:
                responses_kwargs["reasoning"] = {"effort": reasoning_effort}
            
            response = await self._get_client().responses.create(**responses_kwargs)
            return self._extract_responses_api_result(response, model)
            
        except AttributeError as err:
            # Responses API might not be available in all SDK versions
            self.logger.warning(
                f"Responses API not available or error occurred: {err}. "
                "Falling back to Chat Completions API."
            )
            # Fall through to regular Chat Completions
            raise
        except openai.APIError as err:
            # Handle OpenAI/Mistral API errors with more detail
            error_code = getattr(err, 'status_code', None)
            error_message = str(err)
            error_body = getattr(err, 'body', None)
            
            # Log detailed error information
            self.logger.error(
                f"Responses API error for model {model}: "
                f"code={error_code}, message={error_message}, body={error_body}"
            )
            
            # Check for specific error types that indicate Responses API is not supported
            if error_code == 400:
                error_str = str(err).lower()
                if "cannot determine type" in error_str or "type of 'item'" in error_str:
                    self.logger.warning(
                        f"Responses API format not supported by endpoint for model {model}. "
                        "This may indicate the endpoint doesn't support Responses API. "
                        "Falling back to Chat Completions API."
                    )
                else:
                    self.logger.warning(
                        f"Responses API request error for {model}: {err}. "
                        "Falling back to Chat Completions API."
                    )
            else:
                self.logger.warning(
                    f"Responses API error for {model} (code {error_code}): {err}. "
                    "Falling back to Chat Completions API."
                )
            
            # Raise as InvalidRequestError to trigger fallback
            raise errors.InvalidRequestError(
                f"Error when using Responses API with model {model}: {err}"
            ) from err
        except Exception as err:
            self.logger.error(
                f"Unexpected error using Responses API for model {model}: {err}",
            )
            raise errors.InvalidRequestError(
                f"Error when using Responses API with model {model}: {err}"
            ) from err

    def _is_of_series(self, model: str, series: str) -> bool:
        if model.startswith(series) and len(model) > 1:
            # avoid false positive: check if the next character is a number (ex: o3 model)
            try:
                int(model[len(series)])
                return True
            except ValueError:
                return False
        return False

    def _is_minimal_params_model(self, model: str) -> bool:
        for minimal_params_series in MINIMAL_PARAMS_SERIES_MODELS:
            if self._is_of_series(model, minimal_params_series):
                return True
        for minimal_params_model in MINIMAL_PARAMS_MODELS:
            if model.startswith(minimal_params_model):
                return True
        return False

    def _should_use_responses_api(self, model: str) -> bool:
        """Check if Responses API should be used for the given model.
        
        The Responses API may not be supported by:
        - GGUF models (local quantized models)
        - Ollama endpoints
        - Other local/compatible API servers
        
        Args:
            model: Model name to check.
        
        Returns:
            bool: True if Responses API should be attempted, False otherwise.
        """
        if not model:
            return False
        
        model_lower = model.lower()
        
        # Skip Responses API for GGUF models (local quantized models)
        if "gguf" in model_lower:
            self.logger.debug(
                f"Skipping Responses API for GGUF model {model} "
                "(Responses API not supported by local GGUF models)"
            )
            return False        
        return True

    @staticmethod
    def is_setup_correctly(config):
        return True

    @staticmethod
    def get_is_enabled(config):
        return True

    def allow_token_limit_update(self):
        return self._env_daily_token_limit == self.NO_TOKEN_LIMIT_VALUE

    def apply_daily_token_limit_if_possible(self, updated_limit: int):
        # do not allow updating daily_tokens_limit when set from environment variables
        if self.allow_token_limit_update():
            self._daily_tokens_limit = updated_limit

    def _ensure_rate_limit(self):
        if self.last_consumed_token_date != datetime.date.today():
            self.consumed_daily_tokens = 0
            self.last_consumed_token_date = datetime.date.today()
        if self._daily_tokens_limit == self.NO_TOKEN_LIMIT_VALUE:
            return
        if self.consumed_daily_tokens >= self._daily_tokens_limit:
            raise errors.RateLimitError(
                f"Daily rate limit reached (used {self.consumed_daily_tokens} out of {self._daily_tokens_limit})"
            )

    def _update_token_usage(self, consumed_tokens):
        self.consumed_daily_tokens += consumed_tokens
        self.logger.debug(
            f"Consumed {consumed_tokens} tokens. {self.consumed_daily_tokens} consumed tokens today."
        )

    def check_required_config(self, config):
        if self._env_secret_key is not None or self._get_base_url():
            return True
        try:
            config_key = config[services_constants.CONFIG_OPENAI_SECRET_KEY]
            return (
                bool(config_key)
                and config_key not in commons_constants.DEFAULT_CONFIG_VALUES
            )
        except KeyError:
            return False

    def has_required_configuration(self):
        try:
            return self.check_required_config(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(
                    self.get_type(), {}
                )
            )
        except KeyError:
            return False

    def get_required_config(self):
        return (
            [] if self._env_secret_key else [services_constants.CONFIG_OPENAI_SECRET_KEY]
        )

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/chatgpt"

    def get_type(self) -> str:
        return services_constants.CONFIG_GPT

    def get_website_url(self):
        return "https://platform.openai.com/overview"

    def get_logo(self):
        return "https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg"

    def _get_api_key(self):
        key = self._env_secret_key or self.config[
            services_constants.CONFIG_CATEGORY_SERVICES
        ][self.get_type()].get(services_constants.CONFIG_OPENAI_SECRET_KEY, None)
        if key and not fields_utils.has_invalid_default_config_value(key):
            return key
        if self._get_base_url():
            # no key and custom base url: use random key
            return uuid.uuid4().hex
        return key

    def _get_base_url(self):
        value = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
            self.get_type()
        ].get(services_constants.CONFIG_LLM_CUSTOM_BASE_URL)
        if fields_utils.has_invalid_default_config_value(value):
            return None
        return value or None

    async def prepare(self) -> None:
        try:
            # Load model and token limit from config (with env var precedence)
            self._load_model_from_config()
            self._load_models_config()
            self._load_token_limit_from_config()
            self._load_ai_config_from_config()

            if self._get_base_url():
                self.logger.debug(f"Using custom LLM url: {self._get_base_url()}")
            fetched_models = await self._get_client().models.list()
            if fetched_models.data:
                self.logger.debug(f"Fetched {len(fetched_models.data)} models")
                self.models = [d.id for d in fetched_models.data]
            else:
                self.logger.warning("No fetched models")
                self.models = []
            if self.model not in self.models:
                if self._get_base_url():
                    self.logger.info(
                        f"Custom LLM available models are: {self.models}. "
                        f"Please select one of those in your evaluator configuration."
                    )
                else:
                    self.logger.warning(
                        f"Warning: the default '{self.model}' model is not in available LLM models from the "
                        f"selected LLM provider. "
                        f"Available models are: {self.models}. Please select an available model when configuring your "
                        f"evaluators."
                    )
            
            # Discover MCP tools if configured
            try:
                self._mcp_tools = await self._discover_mcp_tools()
            except Exception as err:
                self.logger.warning(
                    f"Error discovering MCP tools: {err}. Continuing without MCP tools."
                )
                self._mcp_tools = []
        except openai.AuthenticationError as err:
            self.logger.error(f"Invalid OpenAI api key: {err}")
            self.creation_error_message = str(err)
        except Exception as err:
            self.logger.exception(
                err, True, f"Unexpected error when initializing LLM service: {err}"
            )

    def _is_healthy(self):
        return self._get_api_key() and self.models

    def get_successful_startup_message(self):
        return (
            f"LLM configured and ready. {len(self.models)} AI models are available. Using {self.models}.",
            self._is_healthy(),
        )

    def use_stored_signals_only(self):
        return not self.config

    async def stop(self):
        # Clean up cached OpenAI client
        if self._client is not None:
            try:
                # AsyncOpenAI has a close() method to properly close the underlying aiohttp session
                if hasattr(self._client, 'close'):
                    await self._client.close()
            except Exception as err:
                self.logger.debug(f"Error closing OpenAI client: {err}")
            finally:
                self._client = None
        
        # Clean up MCP clients if any
        for client in self._mcp_clients:
            try:
                if hasattr(client, 'close'):
                    await client.close()
            except Exception as err:
                self.logger.debug(f"Error closing MCP client: {err}")
        self._mcp_clients.clear()
        self._mcp_tools.clear()


class LLMSignalService(LLMService):
    """LLM service for managing signals generation and storage."""

    def get_fields_description(self):
        fields = super().get_fields_description()
        # LLMSignalService uses the same config as LLMService for backward compatibility
        return fields

    def get_default_value(self):
        return super().get_default_value()

    def __init__(self):
        super().__init__()
        self.stored_signals: tree.BaseTree = tree.BaseTree()

    async def get_chat_completion(
        self,
        messages,
        model=None,
        max_tokens=3000,
        n=1,
        stop=None,
        temperature=0.5,
        exchange: typing.Optional[str] = None,
        symbol: typing.Optional[str] = None,
        time_frame: typing.Optional[str] = None,
        version: typing.Optional[str] = None,
        candle_open_time: typing.Optional[float] = None,
        use_stored_signals: bool = False,
    ) -> str:
        """Get a signal from stored signals or GPT."""
        if use_stored_signals:
            return self._get_signal_from_stored_signals(
                exchange, symbol, time_frame, version, candle_open_time
            )
        if self.use_stored_signals_only():
            signal = await self._fetch_signal_from_stored_signals(
                exchange, symbol, time_frame, version, candle_open_time
            )
            if not signal:
                # should not happen
                self.logger.error(
                    f"Missing ChatGPT signal from stored signals on {symbol} {time_frame} "
                    f"for timestamp: {candle_open_time} with version: {version}"
                )
            return signal
        return await self._get_signal_from_gpt(
            messages, model, max_tokens, n, stop, temperature
        )

    async def _get_signal_from_gpt(
        self, messages, model=None, max_tokens=3000, n=1, stop=None, temperature=0.5
    ):
        """Get a signal from GPT."""
        return await self.get_completion(
            messages, model, max_tokens, n, stop, temperature
        )

    def _get_signal_from_stored_signals(
        self,
        exchange: str,
        symbol: str,
        time_frame: str,
        version: str,
        candle_open_time: float,
    ) -> str:
        try:
            return self.stored_signals.get_node(
                [exchange, symbol, time_frame, version, candle_open_time]
            ).node_value
        except tree.NodeExistsError:
            return ""

    async def _fetch_signal_from_stored_signals(
        self,
        exchange: str,
        symbol: str,
        time_frame: str,
        version: str,
        candle_open_time: float,
    ) -> typing.Optional[str]:
        authenticator = authentication.Authenticator.instance()
        try:
            return await authenticator.get_gpt_signal(
                exchange,
                symbol,
                commons_enums.TimeFrames(time_frame),
                candle_open_time,
                version,
            )
        except Exception as err:
            self.logger.exception(err, True, f"Error when fetching gpt signal: {err}")

    def store_signal_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        version: str,
        signals_by_candle_open_time,
    ):
        tf = time_frame.value
        for candle_open_time, signal in signals_by_candle_open_time.items():
            self.stored_signals.set_node_at_path(
                signal, str, [exchange, symbol, tf, version, candle_open_time]
            )

    def has_signal_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        min_timestamp: float,
        max_timestamp: float,
        version: str,
    ):
        for ts in (min_timestamp, max_timestamp):
            if (
                self._get_signal_from_stored_signals(
                    exchange,
                    symbol,
                    time_frame.value,
                    version,
                    time_frame_manager.get_last_timeframe_time(time_frame, ts),
                )
                == ""
            ):
                return False
        return True

    async def _fetch_and_store_history(
        self,
        authenticator,
        exchange_name,
        symbol,
        time_frame,
        version,
        min_timestamp: float,
        max_timestamp: float,
    ):
        # no need to fetch a particular exchange
        signals_by_candle_open_time = await authenticator.get_gpt_signals_history(
            None,
            symbol,
            time_frame,
            time_frame_manager.get_last_timeframe_time(time_frame, min_timestamp),
            time_frame_manager.get_last_timeframe_time(time_frame, max_timestamp),
            version,
        )
        if signals_by_candle_open_time:
            self.logger.info(
                f"Fetched {len(signals_by_candle_open_time)} ChatGPT signals "
                f"history for {symbol} {time_frame} on any exchange."
            )
        else:
            self.logger.error(
                f"No ChatGPT signal history for {symbol} on {time_frame.value} for any exchange with {version}. "
                f"Please check {self._supported_history_url()} to get the list of supported signals history."
            )
        self.store_signal_history(
            exchange_name, symbol, time_frame, version, signals_by_candle_open_time
        )

    async def fetch_gpt_history(
        self,
        exchange_name: str,
        symbols: list,
        time_frames: list,
        version: str,
        start_timestamp: float,
        end_timestamp: float,
    ):
        authenticator = authentication.Authenticator.instance()
        coros = [
            self._fetch_and_store_history(
                authenticator,
                exchange_name,
                symbol,
                time_frame,
                version,
                start_timestamp,
                end_timestamp,
            )
            for symbol in symbols
            for time_frame in time_frames
            if not self.has_signal_history(
                exchange_name,
                symbol,
                time_frame,
                start_timestamp,
                end_timestamp,
                version,
            )
        ]
        if coros:
            await asyncio.gather(*coros)

    def clear_signal_history(self):
        self.stored_signals.clear()

    def _supported_history_url(self):
        return f"{community.IdentifiersProvider.COMMUNITY_URL}/features/chatgpt-trading"

    def check_required_config(self, config):
        if (
            self._env_secret_key is not None
            or self.use_stored_signals_only()
            or self._get_base_url()
        ):
            return True
        try:
            config_key = config[services_constants.CONFIG_OPENAI_SECRET_KEY]
            return (
                bool(config_key)
                and config_key not in commons_constants.DEFAULT_CONFIG_VALUES
            )
        except KeyError:
            return False

    def has_required_configuration(self):
        try:
            if self.use_stored_signals_only():
                return True
            return self.check_required_config(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(
                    services_constants.CONFIG_GPT, {}
                )
            )
        except KeyError:
            return False

    def _is_healthy(self):
        return self.use_stored_signals_only() or (self._get_api_key() and self.models)

    def get_successful_startup_message(self):
        return (
            f"GPT configured and ready. {len(self.models)} AI models are available. "
            f"Using {'stored signals' if self.use_stored_signals_only() else self.models}.",
            self._is_healthy(),
        )

    async def prepare(self) -> None:
        try:
            if self.use_stored_signals_only():
                self.logger.info(
                    f"Skipping GPT - OpenAI models fetch as self.use_stored_signals_only() is True"
                )
                # Still discover MCP tools even in stored signals mode
                try:
                    self._mcp_tools = await self._discover_mcp_tools()
                except Exception as err:
                    self.logger.warning(
                        f"Error discovering MCP tools: {err}. Continuing without MCP tools."
                    )
                    self._mcp_tools = []
                return

            # Call parent prepare to handle model loading and MCP discovery
            await super().prepare()
        except openai.AuthenticationError as err:
            self.logger.error(f"Invalid OpenAI api key: {err}")
            self.creation_error_message = str(err)
        except Exception as err:
            self.logger.exception(
                err, True, f"Unexpected error when initializing GPT service: {err}"
            )


# Backward compatibility: keep GPTService as an alias for LLMSignalService
GPTService = LLMSignalService
