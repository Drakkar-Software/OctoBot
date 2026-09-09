#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import json
import os

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration

import octobot.community.activity_analysis.metrics_config as metrics_config_module
import octobot.constants as constants


def _write_config_file(config_path: str, config_data: dict) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file)


def _minimal_config(
    tmp_path,
    *,
    metrics_enabled: bool = True,
    onboarding_state: dict | None = None,
) -> configuration.Configuration:
    user_root = tmp_path / commons_constants.USER_FOLDER
    user_root.mkdir()
    config_path = user_root / commons_constants.CONFIG_FILE
    metrics_section = {
        commons_constants.CONFIG_ENABLED_OPTION: metrics_enabled,
    }
    if onboarding_state is not None:
        metrics_section[commons_constants.CONFIG_METRICS_ONBOARDING_STATE] = onboarding_state
    config_data = {
        commons_constants.CONFIG_METRICS: metrics_section,
        constants.CONFIG_COMMUNITY: {},
    }
    _write_config_file(str(config_path), config_data)
    config = configuration.Configuration(
        str(config_path),
        str(user_root / commons_constants.PROFILES_FOLDER),
        constants.CONFIG_FILE_SCHEMA,
        constants.PROFILE_FILE_SCHEMA,
    )
    config.read(should_raise=False, activate_profile=False)
    return config


class Test_get_metrics_config:
    def test_returns_none_when_auth_uninitialized(self):
        with mock.patch.object(
            metrics_config_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=None),
        ):
            assert metrics_config_module.get_metrics_config() is None

    def test_returns_updated_config_after_auth_update(self):
        original_config = configuration.Configuration("", "")
        edited_config = configuration.Configuration("", "")
        with mock.patch.object(
            metrics_config_module.community_authentication.CommunityAuthentication,
            "_create_client",
            return_value=mock.Mock(),
        ):
            auth = metrics_config_module.community_authentication.CommunityAuthentication(
                config=original_config,
                use_as_singleton=False,
            )
        auth.update(edited_config)
        with mock.patch.object(
            metrics_config_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=auth),
        ):
            assert metrics_config_module.get_metrics_config() is edited_config


class Test_metrics_enabled:
    def test_false_when_config_missing(self):
        assert metrics_config_module.metrics_enabled(None) is False


class Test_resolve_enabled_config:
    def test_returns_none_when_metrics_disabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        assert metrics_config_module.resolve_enabled_config(config) is None
