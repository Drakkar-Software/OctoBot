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
import jsonschema
import pytest

import octobot_commons.json_util as json_util

import octobot.constants as constants


def _minimal_root_config() -> dict:
    return {
        "backtesting": {"files": []},
        "exchanges": {},
        "services": {"web": {"auto-open-in-web-browser": True}},
        "notification": {
            "global-info": True,
            "price-alerts": True,
            "trades": True,
            "other": True,
            "notification-type": ["web"],
        },
    }


def _minimal_valid_config_with_legacy_metrics() -> dict:
    config = _minimal_root_config()
    config["metrics"] = {
        "enabled": True,
        "metrics-bot-id": "6393bc1fcecc3c2aedbaac69",
        "activity_bot_id": "0069ef71-2d1d-4891-80c0-37839d30e6d7",
        "onboarding_state": {
            "distinct_automation_count": 59,
            "onboarding_complete": True,
            "onboarding_milestones": {
                "external_interface_connected": True,
                "first_automation_started": True,
                "node_wallet_configured": True,
            },
            "tracked_automation_ids": ["automation-id-1"],
        },
    }
    return config


def _pre_automation_journal_section() -> dict:
    return {
        "install_id": "0069ef71-2d1d-4891-80c0-37839d30e6d7",
        "onboarding_started_at": 1000.0,
    }


def _post_automation_journal_section() -> dict:
    return {
        "install_id": "0069ef71-2d1d-4891-80c0-37839d30e6d7",
        "onboarding_started_at": 1000.0,
        "first_automation_started_at": 500.0,
        "connection_sequence": 1,
        "last_user_data_pull_at": 1500.0,
        "tracked_automation_ids": ["automation-id-1"],
    }


class TestValidateLegacyMetricsConfig:
    def test_accepts_nested_metrics_object(self):
        json_util.validate(
            _minimal_valid_config_with_legacy_metrics(),
            constants.CONFIG_FILE_SCHEMA,
        )


class TestValidateJournalConfig:
    def test_accepts_config_without_journal_key(self):
        json_util.validate(
            _minimal_root_config(),
            constants.CONFIG_FILE_SCHEMA,
        )

    def test_accepts_pre_automation_journal_shape(self):
        config = _minimal_root_config()
        config["journal"] = _pre_automation_journal_section()
        json_util.validate(config, constants.CONFIG_FILE_SCHEMA)

    def test_accepts_post_automation_journal_shape(self):
        config = _minimal_root_config()
        config["journal"] = _post_automation_journal_section()
        json_util.validate(config, constants.CONFIG_FILE_SCHEMA)

    def test_accepts_explicit_null_optional_timestamps(self):
        config = _minimal_root_config()
        config["journal"] = {
            **_pre_automation_journal_section(),
            "first_automation_started_at": None,
            "last_user_data_pull_at": None,
        }
        json_util.validate(config, constants.CONFIG_FILE_SCHEMA)

    def test_accepts_journal_with_legacy_metrics(self):
        config = _minimal_valid_config_with_legacy_metrics()
        config["journal"] = _post_automation_journal_section()
        json_util.validate(config, constants.CONFIG_FILE_SCHEMA)


class TestValidateJournalConfigRejectsInvalidTypes:
    def test_rejects_string_connection_sequence(self):
        config = _minimal_root_config()
        config["journal"] = {
            **_post_automation_journal_section(),
            "connection_sequence": "0",
        }
        with pytest.raises(jsonschema.ValidationError):
            json_util.validate(config, constants.CONFIG_FILE_SCHEMA)

    def test_rejects_non_array_tracked_automation_ids(self):
        config = _minimal_root_config()
        config["journal"] = {
            **_post_automation_journal_section(),
            "tracked_automation_ids": "automation-id-1",
        }
        with pytest.raises(jsonschema.ValidationError):
            json_util.validate(config, constants.CONFIG_FILE_SCHEMA)

    def test_rejects_tracked_automation_ids_with_non_string_items(self):
        config = _minimal_root_config()
        config["journal"] = {
            **_post_automation_journal_section(),
            "tracked_automation_ids": [1, 2],
        }
        with pytest.raises(jsonschema.ValidationError):
            json_util.validate(config, constants.CONFIG_FILE_SCHEMA)

    def test_rejects_string_first_automation_started_at(self):
        config = _minimal_root_config()
        config["journal"] = {
            **_post_automation_journal_section(),
            "first_automation_started_at": "500.0",
        }
        with pytest.raises(jsonschema.ValidationError):
            json_util.validate(config, constants.CONFIG_FILE_SCHEMA)
