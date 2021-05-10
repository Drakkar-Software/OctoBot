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
import typing
import octobot.constants as constants


class CommunityTentaclesPackage:
    def __init__(self, name, description, url, activated, images, download_url):
        self.name: str = name
        self.description: str = description
        self.url: str = url
        self.activated: bool = activated
        self.images: typing.List[str] = images
        self.download_url: str = download_url
        self.uninstalled: bool = not self.is_installed()

    @staticmethod
    def from_community_dict(data):
        data_attributes = data["attributes"]
        return CommunityTentaclesPackage(
            data_attributes.get("name"),
            data_attributes.get("description"),
            f"{constants.OCTOBOT_COMMUNITY_URL}products/{data_attributes.get('product_slug')}",
            data_attributes.get("activated"),
            data["relationships"].get('images')['data'],
            data_attributes.get("url")
        )

    def is_installed(self):
        #TODO tmp
        import random
        return random.choice((True, False))
