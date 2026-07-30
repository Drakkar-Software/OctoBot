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
import packaging.version as packaging_version

import octobot.constants as constants
import octobot.community.models.community_tentacles_package as community_tentacles_package


def _create_package(last_version, versions):
    return community_tentacles_package.CommunityTentaclesPackage(
        name="test-package",
        description="test",
        url="https://example.com",
        activated=True,
        images=[],
        download_url="https://example.com/download",
        versions=versions,
        last_version=last_version,
    )


class TestGetLatestCompatibleVersion:
    def test_returns_last_version_when_equal_to_bot_version(self):
        package = _create_package(constants.LONG_VERSION, [constants.LONG_VERSION])
        assert package.get_latest_compatible_version() == constants.LONG_VERSION

    def test_returns_compatible_version_when_last_version_is_newer(self):
        current_bot_version = packaging_version.parse(constants.LONG_VERSION)
        older_compatible_version = f"{current_bot_version.major - 1}.0.0"
        package = _create_package("99.0.0", [older_compatible_version, "99.0.0"])
        assert package.get_latest_compatible_version() == packaging_version.parse(older_compatible_version)

    def test_returns_none_when_all_versions_are_newer_than_bot(self):
        package = _create_package("99.0.0", ["99.0.0", "100.0.0"])
        assert package.get_latest_compatible_version() is None
