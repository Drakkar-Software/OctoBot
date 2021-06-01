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
import packaging.version

import octobot.constants as constants


class CommunityTentaclesPackage:
    def __init__(self, name, description, url, activated, images, download_url, versions, last_version):
        self.name: str = name
        self.description: str = description
        self.url: str = url
        self.activated: bool = activated
        self.images: typing.List[str] = images
        self.download_url: str = download_url
        self.uninstalled: bool = not self.is_installed()
        self.versions: typing.List[str] = versions
        self.last_version: str = last_version

    @staticmethod
    def from_community_dict(data):
        data_attributes = data["attributes"]
        return CommunityTentaclesPackage(
            data_attributes.get("name"),
            data_attributes.get("description"),
            f"{constants.OCTOBOT_COMMUNITY_URL}products/{data_attributes.get('product_slug')}",
            data_attributes.get("activated"),
            data["relationships"].get('images')['data'],
            f"{constants.OCTOBOT_COMMUNITY_URL}{data_attributes.get('download_path')}",
            data_attributes.get("versions"),
            data_attributes.get("last_version")
        )

    def get_latest_compatible_version(self):
        current_bot_version = packaging.version.parse(constants.LONG_VERSION)
        if packaging.version.parse(self.last_version) <= current_bot_version:
            return self.last_version
        available_versions = sorted([packaging.version.parse(version) for version in self.versions], reverse=True)
        for version in available_versions:
            if version <= current_bot_version:
                return version
        return None

    def is_installed(self):
        #TODO tmp
        import random
        return random.choice((True, False))
