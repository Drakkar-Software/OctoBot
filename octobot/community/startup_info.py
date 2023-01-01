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
    FORCED_PROFILE_URL = "forcedProfileUrl"
    SUBSCRIBED_PRODUCTS = "subscribedProducts"
    URL = "url"

    def __init__(self, forced_profile, subscribed_products):
        self.forced_profile = forced_profile
        self.subscribed_products = subscribed_products

    def get_forced_profile_url(self) -> list:
        return self.forced_profile[self.URL]

    def get_subscribed_products_urls(self) -> list:
        return [
            product[self.URL]
            for product in self.subscribed_products
        ]

    @staticmethod
    def from_dict(data):
        return StartupInfo(
            data[StartupInfo.FORCED_PROFILE_URL],
            data[StartupInfo.SUBSCRIBED_PRODUCTS]
        )

    def __str__(self):
        return f"forced_profile: {self.forced_profile}, subscribed_products: {self.subscribed_products}"
