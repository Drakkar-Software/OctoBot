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

import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot_services.errors as errors

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
    "o", # the whole o-series does not support temperature parameter
]
MINIMAL_PARAMS_MODELS = [
    "gpt-5", # does not support temperature parameter
]
SYSTEM = "system"
USER = "user"


class GPTService(services.AbstractService):
    BACKTESTING_ENABLED = True
    DEFAULT_MODEL = "gpt-3.5-turbo"
    NO_TOKEN_LIMIT_VALUE = -1

    def get_fields_description(self):
        if self._env_secret_key is None:
            return {
                services_constants.CONFIG_OPENAI_SECRET_KEY: "Your openai API secret key",
                services_constants.CONFIG_LLM_CUSTOM_BASE_URL: (
                    "Custom LLM base url to use. Leave empty to use openai.com. For Ollama models, "
                    "add /v1 to the url (such as: http://localhost:11434/v1)"
                ),
            }
        return {}

    def get_default_value(self):
        if self._env_secret_key is None:
            return {
                services_constants.CONFIG_OPENAI_SECRET_KEY: "",
                services_constants.CONFIG_LLM_CUSTOM_BASE_URL: "",
            }
        return {}

    def __init__(self):
        super().__init__()
        logging.getLogger("openai").setLevel(logging.WARNING)
        self._env_secret_key: str = os.getenv(services_constants.ENV_OPENAI_SECRET_KEY, None) or None
        self.model: str = os.getenv(services_constants.ENV_GPT_MODEL, self.DEFAULT_MODEL)
        self.stored_signals: tree.BaseTree = tree.BaseTree()
        self.models: list[str] = []
        self._env_daily_token_limit: int = int(os.getenv(
            services_constants.ENV_GPT_DAILY_TOKENS_LIMIT,
            self.NO_TOKEN_LIMIT_VALUE)
        )
        self._daily_tokens_limit: int = self._env_daily_token_limit
        self.consumed_daily_tokens: int = 1
        self.last_consumed_token_date: datetime.date = None

    @staticmethod
    def create_message(role, content, model: str = None):
        if role == SYSTEM and model in NO_SYSTEM_PROMPT_MODELS:
            commons_logging.get_logger(GPTService.__name__).debug(
                f"Overriding prompt to use {USER} instead of {SYSTEM} for {model}"
            )
            return {"role": USER, "content": content}
        return {"role": role, "content": content}

    async def get_chat_completion(
        self,
        messages,
        model=None,
        max_tokens=3000,
        n=1,
        stop=None,
        temperature=0.5,
        exchange: str = None,
        symbol: str = None,
        time_frame: str = None,
        version: str = None,
        candle_open_time: float = None,
        use_stored_signals: bool = False,
    ) -> str:
        if use_stored_signals:
            return self._get_signal_from_stored_signals(exchange, symbol, time_frame, version, candle_open_time)
        if self.use_stored_signals_only():
            signal = await self._fetch_signal_from_stored_signals(exchange, symbol, time_frame, version, candle_open_time)
            if not signal:
                # should not happen
                self.logger.error(
                    f"Missing ChatGPT signal from stored signals on {symbol} {time_frame} "
                    f"for timestamp: {candle_open_time} with version: {version}"
                )
            return signal
        return await self._get_signal_from_gpt(messages, model, max_tokens, n, stop, temperature)

    def _get_client(self) -> openai.AsyncOpenAI:
        return openai.AsyncOpenAI(
            api_key=self._get_api_key(),
            base_url=self._get_base_url(),
        )

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

    async def _get_signal_from_gpt(
        self,
        messages,
        model=None,
        max_tokens=3000,
        n=1,
        stop=None,
        temperature=0.5
    ):
        self._ensure_rate_limit()
        try:
            model = model or self.model
            supports_params = not self._is_minimal_params_model(model)
            if not supports_params:
                self.logger.info(
                    f"The {model} model does not support every required parameter, results might not be as accurate "
                    f"as with other models."
                )
            completions = await self._get_client().chat.completions.create(
                model=model,
                max_completion_tokens=max_tokens,
                n=n,
                stop=stop,
                temperature=temperature if supports_params else openai.NOT_GIVEN,
                messages=messages
            )
            self._update_token_usage(completions.usage.total_tokens)
            return completions.choices[0].message.content
        except (
            openai.BadRequestError, openai.UnprocessableEntityError # error in request
        )as err:
            if "does not support 'system' with this model" in str(err):
                desc = err.message
                err_message = (
                    f"The \"{model}\" model can't be used with {SYSTEM} prompts. "
                    f"It should be added to NO_SYSTEM_PROMPT_MODELS: {desc}"
            )
            else:
                err_message = f"Error when running request with model {model} (invalid request): {err}"
            raise errors.InvalidRequestError(err_message) from err
        except openai.NotFoundError as err:
            self.logger.error(f"Model {model} not found: {err}. Available models: {', '.join(self.models)}")
            self.creation_error_message = str(err)
        except openai.AuthenticationError as err:
            self.logger.error(f"Invalid OpenAI api key: {err}")
            self.creation_error_message = str(err)
        except Exception as err:
            raise errors.InvalidRequestError(
                f"Unexpected error when running request with model {model}: {err}"
            ) from err

    def _get_signal_from_stored_signals(
        self,
        exchange: str,
        symbol: str,
        time_frame: str,
        version: str,
        candle_open_time: float,
    ) -> str:
        try:
            return self.stored_signals.get_node([exchange, symbol, time_frame, version, candle_open_time]).node_value
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
                exchange, symbol, commons_enums.TimeFrames(time_frame), candle_open_time, version
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
                signal,
                str,
                [exchange, symbol, tf, version, candle_open_time]
            )

    def has_signal_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        min_timestamp: float,
        max_timestamp: float,
        version: str
    ):
        for ts in (min_timestamp, max_timestamp):
            if self._get_signal_from_stored_signals(
                exchange, symbol, time_frame.value, version, time_frame_manager.get_last_timeframe_time(time_frame, ts)
            ) == "":
                return False
        return True

    async def _fetch_and_store_history(
        self, authenticator, exchange_name, symbol, time_frame, version, min_timestamp: float, max_timestamp: float
    ):
        # no need to fetch a particular exchange
        signals_by_candle_open_time = await authenticator.get_gpt_signals_history(
            None, symbol, time_frame,
            time_frame_manager.get_last_timeframe_time(time_frame, min_timestamp),
            time_frame_manager.get_last_timeframe_time(time_frame, max_timestamp),
            version
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

    @staticmethod
    def is_setup_correctly(config):
        return True

    async def fetch_gpt_history(
        self, exchange_name: str, symbols: list, time_frames: list,
        version: str, start_timestamp: float, end_timestamp: float
    ):
        authenticator = authentication.Authenticator.instance()
        coros = [
            self._fetch_and_store_history(
                authenticator, exchange_name, symbol, time_frame, version, start_timestamp, end_timestamp
            )
            for symbol in symbols
            for time_frame in time_frames
            if not self.has_signal_history(exchange_name, symbol, time_frame, start_timestamp, end_timestamp, version)
        ]
        if coros:
            await asyncio.gather(*coros)

    def clear_signal_history(self):
        self.stored_signals.clear()

    def allow_token_limit_update(self):
        return self._env_daily_token_limit == self.NO_TOKEN_LIMIT_VALUE

    def apply_daily_token_limit_if_possible(self, updated_limit: int):
        # do not allow updating daily_tokens_limit when set from environment variables
        if self.allow_token_limit_update():
            self._daily_tokens_limit = updated_limit

    def _supported_history_url(self):
        return f"{community.IdentifiersProvider.COMMUNITY_URL}/features/chatgpt-trading"

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
        self.logger.debug(f"Consumed {consumed_tokens} tokens. {self.consumed_daily_tokens} consumed tokens today.")

    def check_required_config(self, config):
        if self._env_secret_key is not None or self.use_stored_signals_only() or self._get_base_url():
            return True
        try:
            config_key = config[services_constants.CONFIG_OPENAI_SECRET_KEY]
            return bool(config_key) and config_key not in commons_constants.DEFAULT_CONFIG_VALUES
        except KeyError:
            return False

    def has_required_configuration(self):
        try:
            if self.use_stored_signals_only():
                return True
            return self.check_required_config(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES].get(services_constants.CONFIG_GPT, {})
            )
        except KeyError:
            return False

    def get_required_config(self):
        return [] if self._env_secret_key else [services_constants.CONFIG_OPENAI_SECRET_KEY]

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
        key = (
            self._env_secret_key or
            self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_GPT].get(
                services_constants.CONFIG_OPENAI_SECRET_KEY, None
            )
        )
        if key and not fields_utils.has_invalid_default_config_value(key):
            return key
        if self._get_base_url():
            # no key and custom base url: use random key
            return uuid.uuid4().hex
        return key

    def _get_base_url(self):
        value = self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_GPT].get(
            services_constants.CONFIG_LLM_CUSTOM_BASE_URL
        )
        if fields_utils.has_invalid_default_config_value(value):
            return None
        return value or None

    async def prepare(self) -> None:
        try:
            if self.use_stored_signals_only():
                self.logger.info(f"Skipping GPT - OpenAI models fetch as self.use_stored_signals_only() is True")
                return
            if self._get_base_url():
                self.logger.info(f"Using custom LLM url: {self._get_base_url()}")
            fetched_models = await self._get_client().models.list()
            if fetched_models.data:
                self.logger.info(f"Fetched {len(fetched_models.data)} models")
                self.models = [d.id for d in fetched_models.data]
            else:
                self.logger.info("No fetched models")
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
        except openai.AuthenticationError as err:
            self.logger.error(f"Invalid OpenAI api key: {err}")
            self.creation_error_message = str(err)
        except Exception as err:
            self.logger.exception(err, True, f"Unexpected error when initializing GPT service: {err}")

    def _is_healthy(self):
        return self.use_stored_signals_only() or (self._get_api_key() and self.models)

    def get_successful_startup_message(self):
        return f"GPT configured and ready. {len(self.models)} AI models are available. " \
               f"Using {'stored signals' if self.use_stored_signals_only() else self.models}.", \
            self._is_healthy()

    def use_stored_signals_only(self):
        return not self.config

    async def stop(self):
        pass
