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

import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration

import octobot.community.activity_analysis.config_path_binding as config_path_binding
import octobot.constants as constants


def _write_config_file(config_path: str, config_data: dict) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file)


def _minimal_configuration(
    tmp_path,
    *,
    metrics_enabled: bool = True,
    community: dict | None = None,
) -> configuration.Configuration:
    user_root = tmp_path / commons_constants.USER_FOLDER
    user_root.mkdir()
    config_path = user_root / commons_constants.CONFIG_FILE
    config_data = {
        commons_constants.CONFIG_METRICS: {
            commons_constants.CONFIG_ENABLED_OPTION: metrics_enabled,
        },
        constants.CONFIG_COMMUNITY: community or {},
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


class TestGetBoundConfigPath:
    def test_normalizes_to_absolute_path(self, tmp_path):
        relative_config_path = os.path.join("user", commons_constants.CONFIG_FILE)
        bound_path = config_path_binding.get_bound_config_path(relative_config_path)
        assert os.path.isabs(bound_path)
        assert bound_path.endswith(os.path.join("user", commons_constants.CONFIG_FILE))


class TestPathBindingIsStale:
    def test_true_when_stored_path_missing(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        assert config_path_binding.path_binding_is_stale(None, config_path) is True

    def test_true_when_config_path_changed(self, tmp_path):
        first_path = str(tmp_path / "first" / commons_constants.CONFIG_FILE)
        second_path = str(tmp_path / "second" / commons_constants.CONFIG_FILE)
        stored_path = config_path_binding.get_bound_config_path(first_path)
        assert config_path_binding.path_binding_is_stale(stored_path, second_path) is True

    def test_false_when_config_path_unchanged(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        stored_path = config_path_binding.get_bound_config_path(config_path)
        assert config_path_binding.path_binding_is_stale(stored_path, config_path) is False


class TestFingerprintConfigPath:
    def test_returns_stable_sha256_hex(self, tmp_path):
        config_path = str(tmp_path / commons_constants.CONFIG_FILE)
        first_fingerprint = config_path_binding.fingerprint_config_path(config_path)
        second_fingerprint = config_path_binding.fingerprint_config_path(config_path)
        assert first_fingerprint == second_fingerprint
        assert len(first_fingerprint) == 64


class TestEnsureConfigPathFingerprint:
    def test_creates_fingerprint_when_missing(self, tmp_path):
        config = _minimal_configuration(tmp_path)
        resolution = config_path_binding.ensure_config_path_fingerprint(config)
        assert resolution.was_regenerated is True
        expected_fingerprint = config_path_binding.fingerprint_config_path(config.config_path)
        assert resolution.value == expected_fingerprint
        assert (
            config.config[constants.CONFIG_COMMUNITY][constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER]
            == expected_fingerprint
        )

    def test_reuses_fingerprint_when_path_matches(self, tmp_path):
        config = _minimal_configuration(tmp_path)
        fingerprint = config_path_binding.fingerprint_config_path(config.config_path)
        config.config[constants.CONFIG_COMMUNITY] = {
            constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER: fingerprint,
        }
        resolution = config_path_binding.ensure_config_path_fingerprint(config)
        assert resolution.was_regenerated is False
        assert resolution.value == fingerprint

    def test_regenerates_when_config_path_fingerprint_is_stale(self, tmp_path):
        config = _minimal_configuration(
            tmp_path,
            community={
                constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER: "old-fingerprint",
            },
        )
        resolution = config_path_binding.ensure_config_path_fingerprint(config)
        assert resolution.was_regenerated is True
        expected_fingerprint = config_path_binding.fingerprint_config_path(config.config_path)
        assert resolution.value == expected_fingerprint
        assert resolution.value != "old-fingerprint"
