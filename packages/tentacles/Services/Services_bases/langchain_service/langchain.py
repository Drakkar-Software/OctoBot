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
import datetime
import json
import logging
import os
import typing
import uuid

import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot_services.errors as errors
import octobot_services.enums as enums

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.configuration.fields_utils as fields_utils

import octobot.constants as constants


# Global LangChain imports with fallback
LANGCHAIN_AVAILABLE = False
LANGCHAIN_CORE_AVAILABLE = False

SystemMessage = None
HumanMessage = None
AIMessage = None
ToolMessage = None

try:
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).debug("langchain_core not available")

try:
    from langchain.chat_models import init_chat_model
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).debug("langchain not available - init_chat_model disabled")

# Provider-specific client classes (imported on demand)
LANGCHAIN_CLIENTS: typing.Dict[enums.AIProvider, typing.Any] = {}

SYSTEM = "system"
USER = "user"
ASSISTANT = "assistant"

NO_SYSTEM_PROMPT_MODELS = ["o1-mini"]


def _get_langchain_client(provider: enums.AIProvider):
    if provider in LANGCHAIN_CLIENTS:
        return LANGCHAIN_CLIENTS[provider]
    
    try:
        if provider == enums.AIProvider.OPENAI:
            from langchain_openai import ChatOpenAI
            LANGCHAIN_CLIENTS[provider] = ChatOpenAI
        elif provider == enums.AIProvider.ANTHROPIC:
            from langchain_anthropic import ChatAnthropic
            LANGCHAIN_CLIENTS[provider] = ChatAnthropic
        elif provider == enums.AIProvider.OLLAMA:
            from langchain_ollama import ChatOllama
            LANGCHAIN_CLIENTS[provider] = ChatOllama
        elif provider == enums.AIProvider.GOOGLE:
            from langchain_google_genai import ChatGoogleGenerativeAI
            LANGCHAIN_CLIENTS[provider] = ChatGoogleGenerativeAI
        elif provider == enums.AIProvider.MICROSOFT:
            from langchain_openai import AzureChatOpenAI
            LANGCHAIN_CLIENTS[provider] = AzureChatOpenAI
        elif provider == enums.AIProvider.AMAZON:
            from langchain_aws import ChatBedrock
            LANGCHAIN_CLIENTS[provider] = ChatBedrock
        elif provider == enums.AIProvider.OTHER:
            from langchain_openai import ChatOpenAI
            LANGCHAIN_CLIENTS[provider] = ChatOpenAI
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
        
        return LANGCHAIN_CLIENTS[provider]
    except ImportError as err:
        raise ImportError(
            f"LangChain package for {provider.value} is not installed. "
            f"Install it with: pip install langchain-{provider.value}"
        ) from err


class LangChainService(services.AbstractAIService):
    """
    LangChain-based AI service implementing AbstractAIService.
    
    Supports multiple AI providers through LangChain's unified interface:
    - OpenAI (langchain-openai)
    - Anthropic (langchain-anthropic)
    - Ollama (langchain-ollama)
    - Google (langchain-google-genai)
    - Microsoft Azure (langchain-openai with Azure)
    - Amazon Bedrock (langchain-aws)
    - Other (OpenAI-compatible APIs)
    """
    
    BACKTESTING_ENABLED = True
    NO_TOKEN_LIMIT_VALUE = -1
    HTTP_TIMEOUT = 300.0

    def get_fields_description(self):
        if self._env_secret_key is None:
            return {
                services_constants.CONFIG_LANGCHAIN_AI_PROVIDER: (
                    "AI provider to use (openai, anthropic, ollama, google, microsoft, amazon, other)"
                ),
                services_constants.CONFIG_LANGCHAIN_API_KEY: (
                    "Your API key for the selected AI provider"
                ),
                services_constants.CONFIG_LANGCHAIN_CUSTOM_BASE_URL: (
                    "Custom base URL for the AI provider API. Required for Ollama and 'other' providers. "
                    "Example for Ollama: http://localhost:11434"
                ),
                services_constants.CONFIG_LANGCHAIN_MODEL: (
                    "LLM model to use. Can be overridden by LANGCHAIN_MODEL environment variable."
                ),
                services_constants.CONFIG_LANGCHAIN_MODEL_FAST: (
                    "Model for 'fast' policy (e.g. analysts, debators). Leave empty to use main model."
                ),
                services_constants.CONFIG_LANGCHAIN_MODEL_REASONING: (
                    "Model for 'reasoning' policy (e.g. judge, distribution). Leave empty to use main model."
                ),
                services_constants.CONFIG_LANGCHAIN_DAILY_TOKENS_LIMIT: (
                    f"Daily token limit (default: {self.NO_TOKEN_LIMIT_VALUE} for no limit). "
                    "Can be overridden by LANGCHAIN_DAILY_TOKEN_LIMIT environment variable."
                ),
            }
        return {}

    def get_default_value(self):
        if self._env_secret_key is None:
            return {
                services_constants.CONFIG_LANGCHAIN_AI_PROVIDER: enums.AIProvider.OPENAI.value,
                services_constants.CONFIG_LANGCHAIN_MODEL: "",
                services_constants.CONFIG_LANGCHAIN_MODEL_FAST: "",
                services_constants.CONFIG_LANGCHAIN_MODEL_REASONING: "",
                services_constants.CONFIG_LANGCHAIN_DAILY_TOKENS_LIMIT: self.NO_TOKEN_LIMIT_VALUE,
            }
        return {}

    def __init__(self):
        super().__init__()
        logging.getLogger("langchain").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        self._env_secret_key: typing.Optional[str] = (
            os.getenv(services_constants.ENV_LANGCHAIN_API_KEY, None) or None
        )
        
        env_model = os.getenv(services_constants.ENV_LANGCHAIN_MODEL, None)
        self.model: typing.Optional[str] = env_model
        self.models: list[str] = []
        
        env_daily_token_limit_str = os.getenv(
            services_constants.ENV_LANGCHAIN_DAILY_TOKENS_LIMIT, None
        )
        if env_daily_token_limit_str:
            self._env_daily_token_limit: int = int(env_daily_token_limit_str)
        else:
            self._env_daily_token_limit: int = self.NO_TOKEN_LIMIT_VALUE
        
        self._daily_tokens_limit: int = self._env_daily_token_limit
        self.consumed_daily_tokens: int = 0
        self.last_consumed_token_date: typing.Optional[datetime.date] = None
        
        self._client: typing.Any = None
        self.ai_provider: enums.AIProvider = enums.AIProvider.OPENAI
        self._base_url: typing.Optional[str] = None

    def _load_model_from_config(self):
        if os.getenv(services_constants.ENV_LANGCHAIN_MODEL, None):
            return
        try:
            config_model = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LANGCHAIN_MODEL)
            if config_model and not fields_utils.has_invalid_default_config_value(config_model):
                self.model = config_model
        except (KeyError, TypeError):
            pass

    def _load_models_config(self):
        self.models_config = {}
        try:
            svc_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(self.get_type()) or {}
            fast_model = svc_config.get(services_constants.CONFIG_LANGCHAIN_MODEL_FAST)
            reasoning_model = svc_config.get(services_constants.CONFIG_LANGCHAIN_MODEL_REASONING)
            if fast_model and not fields_utils.has_invalid_default_config_value(fast_model):
                self.models_config["fast"] = fast_model
            if reasoning_model and not fields_utils.has_invalid_default_config_value(reasoning_model):
                self.models_config["reasoning"] = reasoning_model
        except (KeyError, TypeError):
            pass

    def _load_token_limit_from_config(self):
        if os.getenv(services_constants.ENV_LANGCHAIN_DAILY_TOKENS_LIMIT, None):
            return
        try:
            config_limit = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LANGCHAIN_DAILY_TOKENS_LIMIT)
            if (
                config_limit is not None
                and not fields_utils.has_invalid_default_config_value(config_limit)
            ):
                self._daily_tokens_limit = int(config_limit) if isinstance(config_limit, str) else config_limit
        except (KeyError, TypeError, ValueError):
            pass

    def _load_ai_provider_from_config(self):
        try:
            svc_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(self.get_type()) or {}
            ai_provider_str = svc_config.get(services_constants.CONFIG_LANGCHAIN_AI_PROVIDER)
            if ai_provider_str and not fields_utils.has_invalid_default_config_value(ai_provider_str):
                try:
                    self.ai_provider = enums.AIProvider(ai_provider_str.lower())
                except ValueError:
                    self.logger.warning(f"Invalid AI provider: {ai_provider_str}, defaulting to openai")
                    self.ai_provider = enums.AIProvider.OPENAI
        except (KeyError, TypeError):
            pass

    def _get_api_key(self) -> typing.Optional[str]:
        key = self._env_secret_key
        if key:
            return key
        try:
            key = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LANGCHAIN_API_KEY)
            if key and not fields_utils.has_invalid_default_config_value(key):
                return key
        except (KeyError, TypeError):
            pass
        
        if self.ai_provider == enums.AIProvider.OLLAMA:
            return None
        
        if self._get_base_url():
            return uuid.uuid4().hex
        return None

    def _get_base_url(self) -> typing.Optional[str]:
        if self._base_url:
            return self._base_url
        try:
            value = self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                self.get_type()
            ].get(services_constants.CONFIG_LANGCHAIN_CUSTOM_BASE_URL)
            if value and not fields_utils.has_invalid_default_config_value(value):
                return value
        except (KeyError, TypeError):
            pass
        return None

    def _create_client(self, model: typing.Optional[str] = None) -> typing.Any:
        ChatModelClass = _get_langchain_client(self.ai_provider)
        api_key = self._get_api_key()
        base_url = self._get_base_url()
        use_model = model or self.model
        
        kwargs = {
            "model": use_model,
            "timeout": self.HTTP_TIMEOUT,
        }
        
        if self.ai_provider == enums.AIProvider.OPENAI:
            kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
        elif self.ai_provider == enums.AIProvider.ANTHROPIC:
            kwargs["api_key"] = api_key
            if base_url:
                kwargs["base_url"] = base_url
            kwargs["model_name"] = kwargs.pop("model")
        elif self.ai_provider == enums.AIProvider.OLLAMA:
            kwargs.pop("timeout", None)
            kwargs["base_url"] = base_url or "http://localhost:11434"
        elif self.ai_provider == enums.AIProvider.GOOGLE:
            kwargs["google_api_key"] = api_key
            kwargs.pop("timeout", None)
        elif self.ai_provider == enums.AIProvider.MICROSOFT:
            kwargs["api_key"] = api_key
            if base_url:
                kwargs["azure_endpoint"] = base_url
            kwargs["deployment_name"] = use_model
            kwargs["api_version"] = "2024-02-15-preview"
        elif self.ai_provider == enums.AIProvider.AMAZON:
            kwargs.pop("timeout", None)
            kwargs["model_id"] = kwargs.pop("model")
        elif self.ai_provider == enums.AIProvider.OTHER:
            kwargs["api_key"] = api_key or "not-needed"
            if base_url:
                kwargs["base_url"] = base_url
        
        return ChatModelClass(**kwargs)

    def _get_client(self) -> typing.Any:
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def get_chat_model(
        self,
        model: typing.Optional[str] = None,
        temperature: typing.Optional[float] = None,
        max_tokens: typing.Optional[int] = None,
        **kwargs
    ) -> typing.Any:
        """
        Get a LangChain chat model instance for use with agents or other LangChain components.
        """
        if not LANGCHAIN_CORE_AVAILABLE:
            raise ImportError(
                "LangChain core is not available. Install it with: pip install langchain-core"
            )
        
        use_model = model or self.model
        client = self._create_client(model=use_model)
        
        if temperature is not None:
            client.temperature = temperature
        if max_tokens is not None:
            client.max_tokens = max_tokens
        
        for key, value in kwargs.items():
            setattr(client, key, value)
        
        return client

    def init_chat_model(
        self,
        model: typing.Optional[str] = None,
        **kwargs
    ) -> typing.Any:
        """
        Initialize a chat model using LangChain's init_chat_model for deep agent compatibility.
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain init_chat_model is not available. "
                "Install it with: pip install langchain"
            )
        
        use_model = model or self.model
        
        model_kwargs = {
            "model": use_model,
            **kwargs
        }
        
        if self.ai_provider:
            model_kwargs["model_provider"] = self.ai_provider.value
        
        if "api_key" not in kwargs:
            api_key = self._get_api_key()
            if api_key:
                model_kwargs["api_key"] = api_key
        
        if self.auth_token and "auth_token" not in kwargs:
            model_kwargs["auth_token"] = self.auth_token
        
        base_url = self._get_base_url()
        if base_url and "base_url" not in kwargs:
            model_kwargs["base_url"] = base_url
        
        return init_chat_model(**model_kwargs)

    def _convert_messages_to_langchain(self, messages: list) -> list:
        if not LANGCHAIN_CORE_AVAILABLE:
            raise ImportError(
                "LangChain core is not available. Install it with: pip install langchain-core"
            )
        
        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == SYSTEM:
                langchain_messages.append(SystemMessage(content=content))
            elif role == USER:
                langchain_messages.append(HumanMessage(content=content))
            elif role == ASSISTANT:
                langchain_messages.append(AIMessage(content=content))
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                langchain_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
        
        return langchain_messages

    def _convert_tool_to_langchain(self, tool: dict) -> dict:
        return tool

    @staticmethod
    def create_message(role: str, content: str, model: typing.Optional[str] = None) -> dict:
        if role == SYSTEM and model in NO_SYSTEM_PROMPT_MODELS:
            commons_logging.get_logger(LangChainService.__name__).debug(
                f"Overriding prompt to use {USER} instead of {SYSTEM} for {model}"
            )
            return {"role": USER, "content": content}
        return {"role": role, "content": content}

    @staticmethod
    def handle_tool_calls(
        tool_calls: typing.List[dict],
        tool_executor: typing.Callable[[str, dict], typing.Any],
    ) -> typing.List[dict]:
        tool_results = []
        
        for tool_call in tool_calls:
            function_info = tool_call.get("function", {})
            function_name = function_info.get("name")
            arguments_str = function_info.get("arguments", "{}")
            
            try:
                arguments = json.loads(arguments_str)
            except (json.JSONDecodeError, TypeError):
                arguments = {}
            
            try:
                result = tool_executor(function_name, arguments)
            except Exception as e:
                result = {"error": str(e)}
            
            tool_results.append({
                "tool_call_id": tool_call.get("id"),
                "role": "tool",
                "name": function_name,
                "content": json.dumps(result),
            })
        
        return tool_results

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

    def _update_token_usage(self, consumed_tokens: int):
        self.consumed_daily_tokens += consumed_tokens
        self.logger.debug(
            f"Consumed {consumed_tokens} tokens. {self.consumed_daily_tokens} consumed tokens today."
        )

    def _extract_tool_calls_from_response(self, response) -> typing.Optional[list]:
        tool_calls = []
        
        if response.tool_calls:
            for tc in response.tool_calls:
                tc_id = tc["id"] if isinstance(tc, dict) else tc.id
                tc_name = tc["name"] if isinstance(tc, dict) else tc.name
                tc_args = tc["args"] if isinstance(tc, dict) else tc.args
                tool_calls.append({
                    "id": tc_id,
                    "type": "function",
                    "function": {
                        "name": tc_name,
                        "arguments": json.dumps(tc_args),
                    }
                })
        elif response.additional_kwargs.get('tool_calls'):
            for tc in response.additional_kwargs['tool_calls']:
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "type": tc.get("type", "function"),
                    "function": tc.get("function", {}),
                })
        
        return tool_calls if tool_calls else None

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
        middleware: typing.Optional[typing.List[typing.Callable]] = None,
    ) -> typing.Union[str, dict, None]:
        self._ensure_rate_limit()
        
        try:
            client = self._get_client()
            langchain_messages = self._convert_messages_to_langchain(messages)
            invoke_kwargs = {}
            
            client.temperature = temperature
            client.max_tokens = max_tokens
            
            if stop:
                invoke_kwargs["stop"] = stop if isinstance(stop, list) else [stop]
            
            if tools:
                langchain_tools = [self._convert_tool_to_langchain(t) for t in tools]
                client = client.bind_tools(langchain_tools)
                
                if tool_choice == "none":
                    client = self._get_client()
            
            if middleware:
                for mw in middleware:
                    client = mw(client, langchain_messages, invoke_kwargs)
            
            if json_output and response_schema:
                try:
                    client = client.with_structured_output(response_schema)
                    response = await client.ainvoke(langchain_messages, **invoke_kwargs)
                    return response.model_dump() if hasattr(response, 'model_dump') else response
                except Exception as e:
                    self.logger.warning(f"Structured output failed, falling back: {e}")
            
            response = await client.ainvoke(langchain_messages, **invoke_kwargs)
            
            if response.response_metadata:
                usage = response.response_metadata.get('usage', {}) or response.response_metadata.get('token_usage', {})
                if usage:
                    total_tokens = usage.get('total_tokens', 0)
                    if total_tokens:
                        self._update_token_usage(total_tokens)
            
            tool_calls = self._extract_tool_calls_from_response(response)
            if tool_calls:
                return {
                    "content": response.content,
                    "tool_calls": tool_calls
                }
            
            content = response.content
            
            if json_output and content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass
            
            return content
            
        except ImportError as err:
            self.logger.error(f"Missing LangChain dependency: {err}")
            raise errors.InvalidRequestError(str(err)) from err
        except Exception as err:
            self.logger.error(f"Error in LangChain completion: {err}")
            raise errors.InvalidRequestError(
                f"Error when running request with model {model or self.model}: {err}"
            ) from err

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
        conversation_messages = list(messages)
        response = None
        
        for iteration in range(max_tool_iterations):
            response = await self.get_completion(
                messages=conversation_messages,
                model=model,
                max_tokens=max_tokens,
                n=n,
                stop=stop,
                temperature=temperature,
                json_output=False,
                response_schema=response_schema,
                tools=tools,
                tool_choice=tool_choice,
                use_octobot_mcp=use_octobot_mcp,
                middleware=middleware,
            )
            
            if isinstance(response, dict) and response.get("tool_calls"):
                tool_calls = response.get("tool_calls", [])
                
                if return_tool_calls and tool_calls:
                    tool_call = tool_calls[0]
                    function_info = tool_call.get("function", {})
                    tool_name = function_info.get("name")
                    arguments_str = function_info.get("arguments", "{}")
                    
                    try:
                        arguments = json.loads(arguments_str)
                    except (json.JSONDecodeError, TypeError):
                        arguments = {}
                    
                    return {
                        "tool_name": tool_name,
                        "arguments": arguments
                    }
                
                if tool_executor is None:
                    if json_output:
                        return self.parse_completion_response(response, json_output=True)
                    return response
                
                tool_results = self.handle_tool_calls(tool_calls, tool_executor)
                
                conversation_messages.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": tool_calls,
                })
                
                conversation_messages.extend(tool_results)
                continue
            
            return self.parse_completion_response(response, json_output=json_output)
        
        if isinstance(response, dict) and response.get("tool_calls"):
            raise ValueError(
                f"Maximum tool calling iterations ({max_tool_iterations}) reached."
            )
        
        if return_tool_calls:
            return None
        return self.parse_completion_response(response, json_output=json_output)

    @staticmethod
    def is_setup_correctly(config):
        return True

    @staticmethod
    def get_is_enabled(config):
        return True

    def allow_token_limit_update(self):
        return self._env_daily_token_limit == self.NO_TOKEN_LIMIT_VALUE

    def apply_daily_token_limit_if_possible(self, updated_limit: int):
        if self.allow_token_limit_update():
            self._daily_tokens_limit = updated_limit

    def check_required_config(self, config):
        if self.ai_provider == enums.AIProvider.OLLAMA:
            return True
        if self._env_secret_key is not None or self._get_base_url():
            return True
        try:
            config_key = config.get(services_constants.CONFIG_LANGCHAIN_API_KEY)
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
        if self.ai_provider == enums.AIProvider.OLLAMA:
            return []
        return (
            [] if self._env_secret_key else [services_constants.CONFIG_LANGCHAIN_API_KEY]
        )

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/langchain"

    def get_type(self) -> str:
        return services_constants.CONFIG_LANGCHAIN

    def get_website_url(self):
        return "https://python.langchain.com/"

    def get_logo(self):
        return "https://python.langchain.com/img/brand/wordmark.png"

    async def prepare(self) -> None:
        try:
            self._load_ai_provider_from_config()
            self._load_model_from_config()
            self._load_models_config()
            self._load_token_limit_from_config()
            
            if self._get_base_url():
                self.logger.debug(f"Using custom base URL: {self._get_base_url()}")
            
            self.logger.info(
                f"LangChain service configured with provider: {self.ai_provider.value}, "
                f"model: {self.model}"
            )
            
            try:
                _ = self._get_client()
                self.models = [self.model] if self.model else []
            except ImportError as err:
                self.logger.error(
                    f"Failed to initialize LangChain client for {self.ai_provider.value}: {err}. "
                    f"Make sure the required package is installed."
                )
                self.creation_error_message = str(err)
            except Exception as err:
                self.logger.error(f"Failed to create LangChain client: {err}")
                self.creation_error_message = str(err)
                
        except Exception as err:
            self.logger.exception(
                err, True, f"Unexpected error when initializing LangChain service: {err}"
            )

    def _is_healthy(self):
        return self._client is not None or self._get_api_key() or self.ai_provider == enums.AIProvider.OLLAMA

    def get_successful_startup_message(self):
        return (
            f"LangChain configured with {self.ai_provider.value} provider. Using model: {self.model}.",
            self._is_healthy(),
        )

    async def stop(self):
        self._client = None
