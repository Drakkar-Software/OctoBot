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
    def __init__(self, name, url, activated, images, download_url):
        self.name: str = name
        self.url: str = url
        self.activated: bool = activated
        self.images: typing.List[str] = images
        self.download_url: str = download_url

    @staticmethod
    def from_community_dict(data):
        data_attributes = data["attributes"]
        return CommunityTentaclesPackage(
            data_attributes["name"],
            f"{constants.OCTOBOT_COMMUNITY_URL}products/{data_attributes['product_slug']}",
            data_attributes["activated"],
            data["relationships"]['images']['data'],
            data_attributes["url"],
        )
