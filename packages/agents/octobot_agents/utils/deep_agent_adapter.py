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

import typing
import logging

import octobot_services.services as services

try:
    from langchain.chat_models import init_chat_model
except ImportError:
    logging.getLogger(__name__).warning("deepagents not available - Deep Agent features disabled")


def create_model_for_deep_agent(
    ai_service: services.AbstractAIService,
    default_model: typing.Optional[str] = None,
) -> typing.Any:    
    model_name = default_model
    if ai_service and ai_service.model:
        model_name = ai_service.model
    
    model = f"{ai_service.ai_provider.value}:{model_name}"
    model_kwargs = {"model": model}

    if ai_service and ai_service.ai_provider:
        model_kwargs["model_provider"] = ai_service.ai_provider.value
    
    if ai_service and ai_service.api_key:
        model_kwargs["api_key"] = ai_service.api_key
    
    if ai_service and ai_service.auth_token:
        if "api_key" not in model_kwargs:
            model_kwargs["api_key"] = ai_service.auth_token
        model_kwargs["auth_token"] = ai_service.auth_token
    
    return init_chat_model(**model_kwargs)
