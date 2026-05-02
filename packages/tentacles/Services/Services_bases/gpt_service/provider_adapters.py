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
import os
import typing

import octobot_commons.logging as commons_logging
import octobot_services.enums as enums

_logger = commons_logging.get_logger("AIProviderAdapter")


class AIProviderAdapter:
    """Auto-configure LLM service credentials from environment variables for a specific provider.

    Each provider subclass declares its env var names and base URL. LLMService iterates
    PROVIDER_ADAPTERS at init time and uses the first adapter whose API key env var is set,
    provided no higher-priority env vars (OPENAI_SECRET_KEY, LLM_CUSTOM_BASE_URL) are present.
    """
    provider: enums.AIProvider
    api_key_env: str
    base_url: str
    model_env: typing.Optional[str] = None

    def can_auto_configure(self) -> bool:
        return bool(os.getenv(self.api_key_env))

    def get_api_key(self) -> typing.Optional[str]:
        return os.getenv(self.api_key_env) or None

    def get_base_url(self) -> str:
        return self.base_url

    def get_model(self, current_model: str) -> str:
        if self.model_env:
            return os.getenv(self.model_env, current_model)
        return current_model


class NvidiaAdapter(AIProviderAdapter):
    provider = enums.AIProvider.NVIDIA
    api_key_env = "NVIDIA_NIM_API_KEY"
    base_url = "https://integrate.api.nvidia.com/v1"
    model_env = "NVIDIA_NIM_MODEL"


PROVIDER_ADAPTERS: list[AIProviderAdapter] = [
    NvidiaAdapter(),
]


class AutoConfigResult(typing.NamedTuple):
    api_key: str
    base_url: str
    provider: enums.AIProvider
    model: typing.Optional[str]


def auto_configure(default_model: str, env_model_set: bool) -> typing.Optional[AutoConfigResult]:
    """Return credentials from the first provider adapter whose API key env var is set.

    Args:
        default_model: Current model name to pass to the adapter if no model env var is set.
        env_model_set: When True, model selection is skipped (a higher-priority env var already set it).

    Returns:
        AutoConfigResult with resolved credentials, or None if no adapter matched.
    """
    for adapter in PROVIDER_ADAPTERS:
        key_set = adapter.can_auto_configure()
        _logger.debug(
            f"Checking {adapter.provider.value} adapter "
            f"(env: {adapter.api_key_env}): {'key found' if key_set else 'no key'}"
        )
        if key_set:
            model = None if env_model_set else adapter.get_model(default_model)
            _logger.info(
                f"Auto-configured {adapter.provider.value} provider. "
                f"URL: {adapter.get_base_url()}"
                + (f", model: {model}" if model else "")
            )
            return AutoConfigResult(
                api_key=adapter.get_api_key(),
                base_url=adapter.get_base_url(),
                provider=adapter.provider,
                model=model,
            )
    _logger.debug(f"No provider adapter matched. Checked: {[a.provider.value for a in PROVIDER_ADAPTERS]}")
    return None
