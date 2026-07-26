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

from octobot import LONG_VERSION, VERSION


class TestOctobotVersionFormat:
    def test_long_version_matches_version(self):
        assert LONG_VERSION == VERSION

    def test_version_is_valid_pep440(self):
        parsed_version = packaging_version.parse(VERSION)
        assert parsed_version is not None

    def test_beta_suffix_is_prerelease(self):
        parsed_version = packaging_version.parse(VERSION)
        if "beta" in VERSION:
            assert parsed_version.is_prerelease

    def test_hyphenated_beta_matches_normalized_form(self):
        if "-beta" in VERSION:
            normalized_version = VERSION.replace("-beta", "b")
            assert packaging_version.parse(VERSION) == packaging_version.parse(normalized_version)
