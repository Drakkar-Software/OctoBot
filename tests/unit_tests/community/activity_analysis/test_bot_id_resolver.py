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
import json
import os
import uuid

import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration

import octobot.community.activity_analysis.bot_id_resolver as bot_id_resolver
import octobot.constants as constants


def _write_config_file(config_path: str, config_data: dict) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file)


def _minimal_configuration(tmp_path, *, metrics: dict | None = None) -> configuration.Configuration:
    user_root = tmp_path / commons_constants.USER_FOLDER
    user_root.mkdir()
    config_path = user_root / commons_constants.CONFIG_FILE
    config_data = {
        commons_constants.CONFIG_METRICS: metrics or {
            commons_constants.CONFIG_ENABLED_OPTION: True,
        },
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


class TestEnsureActivityBotId:
    def test_creates_uuid_when_missing(self, tmp_path):
        config = _minimal_configuration(tmp_path)
        resolution = bot_id_resolver.ensure_activity_bot_id(config)
        assert resolution.was_created is True
        uuid.UUID(resolution.bot_id)
        assert (
            config.config[commons_constants.CONFIG_METRICS][commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID]
            == resolution.bot_id
        )

    def test_reuses_existing_activity_bot_id(self, tmp_path):
        config = _minimal_configuration(
            tmp_path,
            metrics={
                commons_constants.CONFIG_ENABLED_OPTION: True,
                commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID: "existing-bot-id",
            },
        )
        resolution = bot_id_resolver.ensure_activity_bot_id(config)
        assert resolution.was_created is False
        assert resolution.bot_id == "existing-bot-id"

    def test_creates_new_id_when_activity_bot_id_cleared(self, tmp_path):
        config = _minimal_configuration(
            tmp_path,
            metrics={
                commons_constants.CONFIG_ENABLED_OPTION: True,
                commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID: "",
            },
        )
        resolution = bot_id_resolver.ensure_activity_bot_id(config)
        assert resolution.was_created is True
        uuid.UUID(resolution.bot_id)
