#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import json
import os

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration
import octobot_commons.enums as commons_enums

import octobot.community.activity_analysis.metric_definitions as metric_definitions
import octobot.community.activity_analysis.metrics_connector as metrics_connector_module
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


class Test_emit_count:
    def test_delegates_typed_attributes(self, tmp_path):
        config = _minimal_config(tmp_path)
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=True,
            new_install=False,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        with mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count") as track_mock:
            metrics_connector_module.emit_count(config, attributes)
        track_mock.assert_called_once_with(attributes)

    def test_metrics_disabled_is_no_op(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=True,
            new_install=False,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        with mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count") as track_mock:
            metrics_connector_module.emit_count(config, attributes)
        track_mock.assert_not_called()

    def test_not_gated_by_onboarding_complete(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"onboarding_complete": True, "distinct_automation_count": 1},
        )
        attributes = metric_definitions.AccountValidatedAttributes(
            is_simulated=False,
            exchange_name="binance",
        )
        with mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count") as track_mock:
            metrics_connector_module.emit_count(config, attributes)
        track_mock.assert_called_once_with(attributes)


class Test_emit_onboarding_duration_gauge:
    def test_delegates_to_sentry_tracker(self, tmp_path):
        config = _minimal_config(tmp_path)
        attributes = metric_definitions.NodeWalletConfiguredAttributes()
        with mock.patch.object(
            metrics_connector_module.sentry_tracker,
            "track_onboarding_duration_gauge",
        ) as gauge_mock:
            metrics_connector_module.emit_onboarding_duration_gauge(config, 50.0, attributes)
        gauge_mock.assert_called_once_with(50.0, attributes)

    def test_metrics_disabled_is_no_op(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        attributes = metric_definitions.NodeWalletConfiguredAttributes()
        with mock.patch.object(
            metrics_connector_module.sentry_tracker,
            "track_onboarding_duration_gauge",
        ) as gauge_mock:
            metrics_connector_module.emit_onboarding_duration_gauge(config, 50.0, attributes)
        gauge_mock.assert_not_called()


class Test_init_tracker:
    def test_delegates_metrics_enabled_flag(self):
        with mock.patch.object(metrics_connector_module.sentry_tracker, "init_sentry_tracker") as init_mock:
            metrics_connector_module.init_tracker(metrics_enabled=False)
        init_mock.assert_called_once_with(metrics_enabled=False)


class Test_activity_tracking_is_active:
    def test_delegates_to_sentry_tracker(self):
        with mock.patch.object(
            metrics_connector_module.sentry_tracker,
            "activity_tracking_is_active",
            mock.Mock(return_value=True),
        ) as active_mock:
            assert metrics_connector_module.activity_tracking_is_active() is True
        active_mock.assert_called_once_with()


class Test_update_tracker_bot_id:
    def test_delegates_bot_id_to_sentry_tracker(self):
        with mock.patch.object(metrics_connector_module.sentry_tracker, "update_tracker_bot_id") as update_mock:
            metrics_connector_module.update_tracker_bot_id("bot-id")
        update_mock.assert_called_once_with("bot-id")


class Test_debug_logging:
    def test_successful_emit_count_logs_once(self, tmp_path):
        config = _minimal_config(tmp_path)
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=True,
            new_install=False,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(metrics_connector_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(
                    metrics_connector_module.sentry_tracker,
                    "get_tracker_bot_id",
                    return_value=None,
                ), \
                mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count") as track_mock:
            metrics_connector_module.emit_count(config, attributes)
        track_mock.assert_called_once_with(attributes)
        log_mock.assert_called_once_with(
            "emit_count",
            event=attributes.event.value,
            attributes=attributes.to_sentry_dict(None),
        )

    def test_successful_emit_count_does_not_log_when_debug_disabled(self, tmp_path):
        config = _minimal_config(tmp_path)
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=True,
            new_install=False,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        logger_mock = mock.Mock()
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", False), \
                mock.patch.object(
                    metrics_connector_module.metrics_debug.logging,
                    "get_logger",
                    return_value=logger_mock,
                ), \
                mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count") as track_mock:
            metrics_connector_module.emit_count(config, attributes)
        track_mock.assert_called_once_with(attributes)
        logger_mock.info.assert_not_called()

    def test_emit_count_skipped_when_metrics_disabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=True,
            new_install=False,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(metrics_connector_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count") as track_mock:
            metrics_connector_module.emit_count(config, attributes)
        track_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "emit_count_skipped",
            event=attributes.event.value,
            reason="metrics_disabled",
        )

    def test_emit_count_does_not_log_when_debug_disabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        attributes = metric_definitions.NodeProcessStartAttributes(
            wallet_configured=True,
            new_install=False,
            onboarding_complete=False,
            distribution="node",
            version="1.0.0",
        )
        logger_mock = mock.Mock()
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", False), \
                mock.patch.object(
                    metrics_connector_module.metrics_debug.logging,
                    "get_logger",
                    return_value=logger_mock,
                ), \
                mock.patch.object(metrics_connector_module.sentry_tracker, "track_usage_count"):
            metrics_connector_module.emit_count(config, attributes)
        logger_mock.info.assert_not_called()

    def test_emit_gauge_skipped_when_metrics_disabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        attributes = metric_definitions.NodeWalletConfiguredAttributes()
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(metrics_connector_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(
                    metrics_connector_module.sentry_tracker,
                    "track_onboarding_duration_gauge",
                ) as gauge_mock:
            metrics_connector_module.emit_onboarding_duration_gauge(config, 50.0, attributes)
        gauge_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "emit_gauge_skipped",
            event=attributes.event.value,
            reason="metrics_disabled",
            seconds=50.0,
        )

    def test_successful_emit_gauge_logs_once(self, tmp_path):
        config = _minimal_config(tmp_path)
        attributes = metric_definitions.NodeWalletConfiguredAttributes()
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(metrics_connector_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(
                    metrics_connector_module.sentry_tracker,
                    "get_tracker_bot_id",
                    return_value="bot-id",
                ), \
                mock.patch.object(
                    metrics_connector_module.sentry_tracker,
                    "track_onboarding_duration_gauge",
                ) as gauge_mock:
            metrics_connector_module.emit_onboarding_duration_gauge(config, 50.0, attributes)
        gauge_mock.assert_called_once_with(50.0, attributes)
        log_mock.assert_called_once_with(
            "emit_gauge",
            event=attributes.event.value,
            seconds=50.0,
            attributes=attributes.to_sentry_dict("bot-id"),
        )
