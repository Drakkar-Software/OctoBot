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
import octobot_services.api.service_feeds as service_feeds_api
import octobot_services.managers as managers
import octobot_services.services as services
import octobot_services.interfaces as interfaces
import octobot_services.errors as errors
import octobot_commons.asyncio_tools as asyncio_tools


_SERVICE_ASYNC_LOCKS = {}


def _service_async_lock(service_class):
    try:
        return _SERVICE_ASYNC_LOCKS[service_class.__name__]
    except KeyError:
        _SERVICE_ASYNC_LOCKS[service_class.__name__] = asyncio_tools.RLock()
        return _SERVICE_ASYNC_LOCKS[service_class.__name__]


def get_available_services() -> list[type[services.AbstractService]]:
    return services.ServiceFactory.get_available_services()

def get_available_ai_services() -> list[type[services.AbstractAIService]]:
    return services.ServiceFactory.get_available_ai_services()

def get_available_web_search_services() -> list[type[services.AbstractWebSearchService]]:
    return services.ServiceFactory.get_available_web_search_services()

def is_service_class(klass) -> bool:
    return klass in get_available_services() + get_available_ai_services() + get_available_web_search_services()

def get_available_backtestable_services() -> list:
    return [
        service_class for service_class in services.ServiceFactory.get_available_services()
        if service_class.BACKTESTING_ENABLED
    ]

async def _get_available_service_instance(
    get_available_services_func,
    service_type_name: str,
    is_backtesting: bool = False,
    config = None
):
    available_services = get_available_services_func()
    for service_class in available_services:
        try:
            return await get_service(service_class, is_backtesting, config)
        except errors.CreationError:
            # Service is not running/initialized, skip it
            continue
    raise errors.CreationError(f"No {service_type_name} is currently running or available.")

async def get_ai_service(is_backtesting=False, config = None) -> services.AbstractAIService:
    return await _get_available_service_instance(
        get_available_ai_services,
        "AI service",
        is_backtesting,
        config
    )

async def get_web_search_service(is_backtesting=False, config = None) -> services.AbstractWebSearchService:
    return await _get_available_service_instance(
        get_available_web_search_services,
        "web search service",
        is_backtesting,
        config
    )


def is_service_available_in_backtesting(service_class) -> bool:
    return (
        service_class.BACKTESTING_ENABLED
        or service_feeds_api.is_service_used_by_backtestable_feed(service_class)
    )


async def get_service(service_class, is_backtesting, config=None):
    # prevent concurrent access when creating a service
    async with _service_async_lock(service_class):
        # Use provided config, or fall back to interface config 
        # when not backtesting as startup config shouldn't be used
        if config is None and not is_backtesting:
            config = interfaces.get_startup_config(dict_only=True)
        
        created, error_message = await create_service_factory(config).create_or_get_service(
            service_class,
            is_backtesting,
            config
        )
        if created:
            service = service_class.instance()
            if is_backtesting and not is_service_available_in_backtesting(service_class):
                raise errors.UnavailableInBacktestingError(
                    f"{service_class.__name__} service is not available in backtesting"
                )
            return service
    raise errors.CreationError(f"{service_class.__name__} service is not initialized: {error_message}")


def create_service_factory(config) -> services.ServiceFactory:
    return services.ServiceFactory(config)


async def stop_services() -> None:
    await managers.stop_services()
