#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import mock
import pytest

import tentacles.Services.Interfaces.web_interface.models.configuration as configuration_model


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestPersistProfileTentaclesChanges:
    def test_sync_profile_calls_config_save(self):
        edited_tentacles = [mock.Mock(name="edited-tentacle")]
        edited_profile_data = mock.Mock()
        edited_profile_data.tentacles = edited_tentacles
        edited_profile = mock.Mock()
        edited_profile.get_profile_data.return_value = edited_profile_data

        active_profile_data = mock.Mock()
        active_profile_data.tentacles = []
        active_profile = mock.Mock()
        active_profile.is_profile_data_tentacle_backed.return_value = True
        active_profile.get_profile_data.return_value = active_profile_data

        tentacles_setup_config = mock.Mock()
        tentacles_setup_config.profile = edited_profile

        config = mock.Mock()
        config.profile = active_profile

        with mock.patch.object(
            configuration_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), mock.patch.object(
            configuration_model.tentacles_manager_api,
            "save_tentacles_setup_configuration",
            mock.Mock(),
        ) as save_setup_mock:
            configuration_model._persist_profile_tentacles_changes(tentacles_setup_config)

        assert active_profile_data.tentacles == edited_tentacles
        active_profile.bind_tentacles_setup_config.assert_called_once_with(tentacles_setup_config)
        config.save.assert_called_once_with(save_profile=True)
        save_setup_mock.assert_not_called()

    def test_filesystem_profile_calls_save_tentacles_setup(self):
        profile = mock.Mock()
        profile.is_profile_data_tentacle_backed.return_value = False
        config = mock.Mock()
        config.profile = profile
        tentacles_setup_config = mock.Mock()

        with mock.patch.object(
            configuration_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ), mock.patch.object(
            configuration_model.tentacles_manager_api,
            "save_tentacles_setup_configuration",
            mock.Mock(),
        ) as save_setup_mock:
            configuration_model._persist_profile_tentacles_changes(tentacles_setup_config)

        save_setup_mock.assert_called_once_with(tentacles_setup_config)
        config.save.assert_not_called()

    def test_leaves_startup_copy_unchanged(self):
        startup_setup = mock.Mock(name="startup-setup")
        original_startup_profile = mock.Mock(name="startup-profile")
        startup_setup.profile = original_startup_profile

        edited_tentacles = [mock.Mock(name="edited-tentacle")]
        edited_profile_data = mock.Mock()
        edited_profile_data.tentacles = edited_tentacles
        edited_profile = mock.Mock()
        edited_profile.get_profile_data.return_value = edited_profile_data

        active_profile_data = mock.Mock()
        active_profile_data.tentacles = []
        active_profile = mock.Mock()
        active_profile.is_profile_data_tentacle_backed.return_value = True
        active_profile.get_profile_data.return_value = active_profile_data

        tentacles_setup_config = mock.Mock(name="edited-setup")
        tentacles_setup_config.profile = edited_profile

        config = mock.Mock()
        config.profile = active_profile

        with mock.patch.object(
            configuration_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ):
            configuration_model._persist_profile_tentacles_changes(tentacles_setup_config)

        active_profile.bind_tentacles_setup_config.assert_called_once_with(tentacles_setup_config)
        assert startup_setup.profile is original_startup_profile
        assert tentacles_setup_config is not startup_setup


class TestUpdateTentaclesActivationConfig:
    def test_persists_sync_profile(self):
        tentacles_setup_config = mock.Mock()
        with mock.patch.object(
            configuration_model.interfaces_util,
            "get_edited_tentacles_config",
            mock.Mock(return_value=tentacles_setup_config),
        ), mock.patch.object(
            configuration_model.tentacles_manager_api,
            "update_activation_configuration",
            mock.Mock(return_value=True),
        ), mock.patch.object(
            configuration_model,
            "_persist_profile_tentacles_changes",
            mock.Mock(),
        ) as persist_mock, mock.patch.object(
            configuration_model.tentacles_manager_api,
            "save_tentacles_setup_configuration",
            mock.Mock(),
        ) as save_setup_mock:
            result = configuration_model.update_tentacles_activation_config(
                {"IndexTradingMode": "true"}
            )

        assert result is True
        persist_mock.assert_called_once_with(tentacles_setup_config)
        save_setup_mock.assert_not_called()


class TestLoadMarketUnknownExchange:
    async def test_skips_unknown_exchange_without_exception(self):
        results = []
        logger = mock.Mock()
        with mock.patch.object(
            configuration_model,
            "auto_filled_exchanges",
            mock.Mock(return_value=[]),
        ), mock.patch.object(
            configuration_model,
            "_get_logger",
            mock.Mock(return_value=logger),
        ):
            await configuration_model._load_market("earn_curve", results)
        assert results == []
        logger.warning.assert_called_once()
        logger.exception.assert_not_called()


class TestGetOctobotDisplayName:
    def test_returns_configured_name_when_set(self):
        config = mock.Mock()
        config.octobot_name.return_value = "My Automation"
        with mock.patch.object(
            configuration_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ):
            assert configuration_model.get_octobot_display_name() == "My Automation"

    def test_returns_octobot_when_unset(self):
        config = mock.Mock()
        config.octobot_name.return_value = None
        with mock.patch.object(
            configuration_model.interfaces_util,
            "get_edited_config",
            mock.Mock(return_value=config),
        ):
            assert configuration_model.get_octobot_display_name() == "OctoBot"
