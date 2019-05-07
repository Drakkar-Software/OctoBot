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

from tools.logging.logging_util import get_logger
from config import GITHUB_RAW_CONTENT_URL, ASSETS_BRANCH, GITHUB_REPOSITORY, EXTERNAL_RESOURCES_FILE


def get_external_resource(resource_key, catch_exception=False, default_response=""):
    try:
        external_resource_url = f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}" \
            f"/{ASSETS_BRANCH}/{EXTERNAL_RESOURCES_FILE}"
        external_resources = json.loads(requests.get(external_resource_url).text)
        return external_resources[resource_key]
    except Exception as e:
        if catch_exception:
            get_logger("ExternalResourcesManager")\
                .error(f"Exception when calling get_external_resource for {resource_key} key: {e}")
            return default_response
        else:
            raise e
