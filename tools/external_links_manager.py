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

from config import GITHUB_RAW_CONTENT_URL, ASSETS_BRANCH, GITHUB_REPOSITORY, EXTERNAL_LINKS_FILE


def get_external_link(link_key):
    external_links_url = f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{ASSETS_BRANCH}/{EXTERNAL_LINKS_FILE}"
    external_links = json.loads(requests.get(external_links_url).text)
    return external_links[link_key]
