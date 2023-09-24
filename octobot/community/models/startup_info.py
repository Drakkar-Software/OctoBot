#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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


class StartupInfo:
    FORCED_PROFILE_URL = "forced_profile_url"
    SUBSCRIBED_PRODUCTS_URLS = "subscribed_products_urls"

    def __init__(self, forced_profile_url, subscribed_products_urls):
        self.forced_profile_url = forced_profile_url
        self.subscribed_products_urls = subscribed_products_urls

    @staticmethod
    def from_dict(data):
        return StartupInfo(
            data.get(StartupInfo.FORCED_PROFILE_URL),
            [
                url
                for url in data.get(StartupInfo.SUBSCRIBED_PRODUCTS_URLS, []) or []
                if url  # skip unset urls
            ]
        )

    def __str__(self):
        return f"forced_profile_url: {self.forced_profile_url}, " \
               f"subscribed_products_urls: {self.subscribed_products_urls}"
