# pylint: disable=W0703,W3101
#  Drakkar-Software OctoBot
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
import json
import requests

import octobot_commons.logging as logging_util
import octobot_commons.constants as constants


def _handle_exception(exception, resource_key, catch_exception, default_response):
    """
    Handle exception when fetching external resources
    :param exception: the exception
    :param resource_key: the resource key
    :param catch_exception: if exception should be caught
    :param default_response: the default response
    :return: the default response if an exception has been caught
    """
    if catch_exception:
        logging_util.get_logger("ExternalResourcesManager").warning(
            f"Exception when calling get_external_resource for {resource_key} key: {exception}"
        )
        return default_response
    raise exception


def get_external_resource(
    resource_key, catch_exception=False, default_response=""
) -> object:
    """
    Get an external resource
    :param resource_key: the resource key
    :param catch_exception: if exception should be caught
    :param default_response: the default response
    :return: the external resource key value
    """
    try:
        external_resources = json.loads(
            requests.get(constants.EXTERNAL_RESOURCE_URL).text
        )
        return external_resources[resource_key]
    except Exception as global_exception:
        return _handle_exception(
            global_exception, resource_key, catch_exception, default_response
        )


async def async_get_external_resource(
    resource_key, aiohttp_session, catch_exception=False, default_response=""
) -> object:
    """
    Get an external resource in async way
    :param resource_key: the resource key
    :param aiohttp_session: the aiohttp session
    :param catch_exception: if exception should be caught
    :param default_response: the default reponse
    :return: the external resource key value
    """
    try:
        async with aiohttp_session.get(constants.EXTERNAL_RESOURCE_URL) as resp:
            external_resources = json.loads(resp.text())
            return external_resources[resource_key]
    except Exception as global_exception:
        return _handle_exception(
            global_exception, resource_key, catch_exception, default_response
        )
