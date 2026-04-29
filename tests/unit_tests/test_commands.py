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
import pytest
import mock

import octobot.commands as commands
import octobot.constants as constants


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestInstallDefaultTentacles:
    """Tests for INSTALL_DEFAULT_TENTACLES env var behavior."""

    async def test_install_or_update_tentacles_passes_only_additional_false_by_default(self):
        config = mock.Mock()
        config.load_profiles = mock.Mock()
        with mock.patch(
            "octobot.commands.install_all_tentacles", new_callable=mock.AsyncMock
        ) as mock_install, mock.patch(
            "octobot_tentacles_manager.api.load_tentacles", return_value=True
        ):
            await commands.install_or_update_tentacles(config, ["https://extra.com/pkg.zip"], False)
            mock_install.assert_awaited_once_with(
                additional_tentacles_package_urls=["https://extra.com/pkg.zip"],
                only_additional=False,
            )

    async def test_install_or_update_tentacles_passes_only_additional_true(self):
        config = mock.Mock()
        config.load_profiles = mock.Mock()
        with mock.patch(
            "octobot.commands.install_all_tentacles", new_callable=mock.AsyncMock
        ) as mock_install, mock.patch(
            "octobot_tentacles_manager.api.load_tentacles", return_value=True
        ):
            await commands.install_or_update_tentacles(config, ["https://extra.com/pkg.zip"], True)
            mock_install.assert_awaited_once_with(
                additional_tentacles_package_urls=["https://extra.com/pkg.zip"],
                only_additional=True,
            )

    async def test_internal_install_respects_install_default_true(self):
        community_auth = mock.Mock()
        community_auth.get_saved_package_urls = mock.Mock(return_value=["https://saved.com/pkg.zip"])
        config = mock.Mock()
        with mock.patch("octobot.constants.INSTALL_DEFAULT_TENTACLES", True), \
             mock.patch(
                 "octobot.commands.install_or_update_tentacles", new_callable=mock.AsyncMock
             ) as mock_install:
            await commands._install_or_update_tentacles(community_auth, config)
            mock_install.assert_awaited_once_with(config, ["https://saved.com/pkg.zip"], False)

    async def test_internal_install_respects_install_default_false(self):
        community_auth = mock.Mock()
        community_auth.get_saved_package_urls = mock.Mock(return_value=["https://saved.com/pkg.zip"])
        config = mock.Mock()
        with mock.patch("octobot.constants.INSTALL_DEFAULT_TENTACLES", False), \
             mock.patch(
                 "octobot.commands.install_or_update_tentacles", new_callable=mock.AsyncMock
             ) as mock_install:
            await commands._install_or_update_tentacles(community_auth, config)
            mock_install.assert_awaited_once_with(config, ["https://saved.com/pkg.zip"], True)

    async def test_install_all_tentacles_skips_base_urls_when_only_additional(self):
        additional_urls = ["https://custom.com/tentacles.zip"]
        with mock.patch(
            "octobot.configuration_manager.get_default_tentacles_url",
            return_value="https://default.octobot.online/tentacles.zip",
        ), mock.patch(
            "octobot.community.tentacles_packages.get_env_variable_tentacles_urls",
            return_value=[],
        ), mock.patch(
            "octobot.community.tentacles_packages.adapt_url_to_bot_version",
            side_effect=lambda url, _: url,
        ), mock.patch(
            "octobot_commons.aiohttp_util.ssl_fallback_aiohttp_client_session"
        ) as mock_session_ctx, mock.patch(
            "octobot_tentacles_manager.api.install_all_tentacles", new_callable=mock.AsyncMock
        ) as mock_api_install:
            mock_session_ctx.return_value.__aenter__ = mock.AsyncMock(return_value=mock.Mock())
            mock_session_ctx.return_value.__aexit__ = mock.AsyncMock(return_value=False)

            await commands.install_all_tentacles(
                additional_tentacles_package_urls=additional_urls,
                only_additional=True,
            )

            # Should only install the additional URL, not the default one
            assert mock_api_install.await_count == 1
            installed_url = mock_api_install.call_args_list[0].args[0]
            assert installed_url == "https://custom.com/tentacles.zip"

    async def test_install_all_tentacles_includes_base_urls_when_not_only_additional(self):
        additional_urls = ["https://custom.com/tentacles.zip"]
        with mock.patch(
            "octobot.configuration_manager.get_default_tentacles_url",
            return_value="https://default.octobot.online/tentacles.zip",
        ), mock.patch(
            "octobot.community.tentacles_packages.get_env_variable_tentacles_urls",
            return_value=[],
        ), mock.patch(
            "octobot.community.tentacles_packages.adapt_url_to_bot_version",
            side_effect=lambda url, _: url,
        ), mock.patch(
            "octobot_commons.aiohttp_util.ssl_fallback_aiohttp_client_session"
        ) as mock_session_ctx, mock.patch(
            "octobot_tentacles_manager.api.install_all_tentacles", new_callable=mock.AsyncMock
        ) as mock_api_install:
            mock_session_ctx.return_value.__aenter__ = mock.AsyncMock(return_value=mock.Mock())
            mock_session_ctx.return_value.__aexit__ = mock.AsyncMock(return_value=False)

            await commands.install_all_tentacles(
                additional_tentacles_package_urls=additional_urls,
                only_additional=False,
            )

            # Should install both default and additional URLs
            assert mock_api_install.await_count == 2
            installed_urls = [call.args[0] for call in mock_api_install.call_args_list]
            assert "https://default.octobot.online/tentacles.zip" in installed_urls
            assert "https://custom.com/tentacles.zip" in installed_urls

    async def test_install_all_tentacles_includes_env_variable_urls_in_base(self):
        env_urls = ["https://env-var.com/tentacles.zip"]
        with mock.patch(
            "octobot.configuration_manager.get_default_tentacles_url",
            return_value="https://default.octobot.online/tentacles.zip",
        ), mock.patch(
            "octobot.community.tentacles_packages.get_env_variable_tentacles_urls",
            return_value=env_urls,
        ), mock.patch(
            "octobot.community.tentacles_packages.adapt_url_to_bot_version",
            side_effect=lambda url, _: url,
        ), mock.patch(
            "octobot_commons.aiohttp_util.ssl_fallback_aiohttp_client_session"
        ) as mock_session_ctx, mock.patch(
            "octobot_tentacles_manager.api.install_all_tentacles", new_callable=mock.AsyncMock
        ) as mock_api_install:
            mock_session_ctx.return_value.__aenter__ = mock.AsyncMock(return_value=mock.Mock())
            mock_session_ctx.return_value.__aexit__ = mock.AsyncMock(return_value=False)

            # When only_additional=True, env variable URLs are part of base_urls and should be skipped
            await commands.install_all_tentacles(
                additional_tentacles_package_urls=[],
                only_additional=True,
            )
            assert mock_api_install.await_count == 0

    async def test_install_all_tentacles_no_additional_urls(self):
        with mock.patch(
            "octobot.configuration_manager.get_default_tentacles_url",
            return_value="https://default.octobot.online/tentacles.zip",
        ), mock.patch(
            "octobot.community.tentacles_packages.get_env_variable_tentacles_urls",
            return_value=[],
        ), mock.patch(
            "octobot.community.tentacles_packages.adapt_url_to_bot_version",
            side_effect=lambda url, _: url,
        ), mock.patch(
            "octobot_commons.aiohttp_util.ssl_fallback_aiohttp_client_session"
        ) as mock_session_ctx, mock.patch(
            "octobot_tentacles_manager.api.install_all_tentacles", new_callable=mock.AsyncMock
        ) as mock_api_install:
            mock_session_ctx.return_value.__aenter__ = mock.AsyncMock(return_value=mock.Mock())
            mock_session_ctx.return_value.__aexit__ = mock.AsyncMock(return_value=False)

            # Default behavior: installs default tentacles only
            await commands.install_all_tentacles(
                additional_tentacles_package_urls=[],
                only_additional=False,
            )
            assert mock_api_install.await_count == 1
            assert mock_api_install.call_args_list[0].args[0] == "https://default.octobot.online/tentacles.zip"

    async def test_update_or_repair_outdated_respects_install_default_false(self):
        community_auth = mock.Mock()
        tentacles_setup_config = mock.Mock()
        config = mock.Mock()
        config.profile = mock.Mock()
        config.profile.imported = False
        with mock.patch("octobot.constants.INSTALL_DEFAULT_TENTACLES", False), \
             mock.patch("octobot.constants.SHOULD_CHECK_TENTACLES", True), \
             mock.patch("octobot.constants.EXIT_BEFORE_TENTACLES_AUTO_REINSTALL", False), \
             mock.patch(
                 "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
                 return_value=([], [], False),
             ), mock.patch(
                 "octobot_tentacles_manager.api.are_tentacles_up_to_date", return_value=False
             ), mock.patch(
                 "octobot.commands.install_or_update_tentacles", new_callable=mock.AsyncMock, return_value=True
             ) as mock_install:
            await commands.update_or_repair_tentacles_if_necessary(
                community_auth, tentacles_setup_config, config
            )
            mock_install.assert_awaited_once_with(config, [], True)

    async def test_update_or_repair_outdated_respects_install_default_true(self):
        community_auth = mock.Mock()
        tentacles_setup_config = mock.Mock()
        config = mock.Mock()
        config.profile = mock.Mock()
        config.profile.imported = False
        with mock.patch("octobot.constants.INSTALL_DEFAULT_TENTACLES", True), \
             mock.patch("octobot.constants.SHOULD_CHECK_TENTACLES", True), \
             mock.patch("octobot.constants.EXIT_BEFORE_TENTACLES_AUTO_REINSTALL", False), \
             mock.patch(
                 "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
                 return_value=([], [], False),
             ), mock.patch(
                 "octobot_tentacles_manager.api.are_tentacles_up_to_date", return_value=False
             ), mock.patch(
                 "octobot.commands.install_or_update_tentacles", new_callable=mock.AsyncMock, return_value=True
             ) as mock_install:
            await commands.update_or_repair_tentacles_if_necessary(
                community_auth, tentacles_setup_config, config
            )
            mock_install.assert_awaited_once_with(config, [], False)

    async def test_update_or_repair_damaged_respects_install_default_false(self):
        community_auth = mock.Mock()
        tentacles_setup_config = mock.Mock()
        config = mock.Mock()
        config.profile = mock.Mock()
        config.profile.imported = False
        with mock.patch("octobot.constants.INSTALL_DEFAULT_TENTACLES", False), \
             mock.patch("octobot.constants.SHOULD_CHECK_TENTACLES", True), \
             mock.patch("octobot.constants.EXIT_BEFORE_TENTACLES_AUTO_REINSTALL", False), \
             mock.patch(
                 "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
                 return_value=([], [], False),
             ), mock.patch(
                 "octobot_tentacles_manager.api.are_tentacles_up_to_date", return_value=True
             ), mock.patch(
                 "octobot_tentacles_manager.api.load_tentacles", return_value=False
             ), mock.patch(
                 "octobot.commands.install_or_update_tentacles", new_callable=mock.AsyncMock, return_value=True
             ) as mock_install:
            await commands.update_or_repair_tentacles_if_necessary(
                community_auth, tentacles_setup_config, config
            )
            mock_install.assert_awaited_once_with(config, [], True)

    async def test_update_or_repair_damaged_respects_install_default_true(self):
        community_auth = mock.Mock()
        tentacles_setup_config = mock.Mock()
        config = mock.Mock()
        config.profile = mock.Mock()
        config.profile.imported = False
        with mock.patch("octobot.constants.INSTALL_DEFAULT_TENTACLES", True), \
             mock.patch("octobot.constants.SHOULD_CHECK_TENTACLES", True), \
             mock.patch("octobot.constants.EXIT_BEFORE_TENTACLES_AUTO_REINSTALL", False), \
             mock.patch(
                 "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
                 return_value=([], [], False),
             ), mock.patch(
                 "octobot_tentacles_manager.api.are_tentacles_up_to_date", return_value=True
             ), mock.patch(
                 "octobot_tentacles_manager.api.load_tentacles", return_value=False
             ), mock.patch(
                 "octobot.commands.install_or_update_tentacles", new_callable=mock.AsyncMock, return_value=True
             ) as mock_install:
            await commands.update_or_repair_tentacles_if_necessary(
                community_auth, tentacles_setup_config, config
            )
            mock_install.assert_awaited_once_with(config, [], False)
