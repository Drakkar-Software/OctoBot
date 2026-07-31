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
import mock
import pytest

import octobot.community.tentacles_packages as tentacles_packages
import octobot.constants as constants


class TestAdaptUrlToBotVersion:
    def test_replaces_version_placeholder_with_long_version(self):
        package_url = f"https://example.com/tentacles/{constants.VERSION_PLACEHOLDER}/any_platform.zip"
        adapted_url = tentacles_packages.adapt_url_to_bot_version(package_url, constants.LONG_VERSION)
        assert constants.VERSION_PLACEHOLDER not in adapted_url
        assert constants.LONG_VERSION in adapted_url
        assert adapted_url == f"https://example.com/tentacles/{constants.LONG_VERSION}/any_platform.zip"


class TestHasTentaclesToInstallAndUninstallTentaclesIfNecessary:
    pytestmark = pytest.mark.asyncio

    async def test_uses_package_operations_setup_config(self):
        community_auth = mock.Mock()
        setup_config = mock.Mock()
        community_auth.config = mock.Mock()
        community_auth.config.get_tentacles_setup_config_for_package_operations.return_value = setup_config
        with mock.patch(
            "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
            return_value=([], [], False),
        ) as get_packages_mock:
            result = await tentacles_packages.has_tentacles_to_install_and_uninstall_tentacles_if_necessary(
                community_auth
            )
        community_auth.config.get_tentacles_setup_config_for_package_operations.assert_called_once_with()
        community_auth.config.get_tentacles_config_path.assert_not_called()
        get_packages_mock.assert_called_once_with(community_auth, setup_config, constants.LONG_VERSION)
        assert result is False

    async def test_returns_false_when_config_is_none(self):
        community_auth = mock.Mock()
        community_auth.config = None
        with mock.patch(
            "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
        ) as get_packages_mock:
            result = await tentacles_packages.has_tentacles_to_install_and_uninstall_tentacles_if_necessary(
                community_auth
            )
        get_packages_mock.assert_not_called()
        assert result is False

    async def test_install_only_skips_uninstall(self):
        community_auth = mock.Mock()
        setup_config = mock.Mock()
        community_auth.config = mock.Mock()
        community_auth.config.get_tentacles_setup_config_for_package_operations.return_value = setup_config
        with mock.patch(
            "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
            return_value=(["https://premium.example/pkg.zip"], ["SomeTentacle"], False),
        ), mock.patch(
            "octobot.community.tentacles_packages.uninstall_tentacles",
            new_callable=mock.AsyncMock,
        ) as uninstall_mock:
            result = await tentacles_packages.has_tentacles_to_install_and_uninstall_tentacles_if_necessary(
                community_auth, install_only=True
            )
        uninstall_mock.assert_not_awaited()
        assert result is True
