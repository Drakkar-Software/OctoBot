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

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration

import octobot.community.activity_analysis.activity_metrics as activity_metrics_module
import octobot.community.activity_analysis.bot_id_resolver as bot_id_resolver
import octobot.constants as constants
import octobot.enums as enums


def _write_config_file(config_path: str, config_data: dict) -> None:
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file)


def _minimal_config(
    tmp_path,
    *,
    metrics_enabled: bool = True,
    community: dict | None = None,
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


def _activity_metrics(config: configuration.Configuration) -> activity_metrics_module.ActivityMetrics:
    octobot_api = mock.Mock()
    octobot_api.get_edited_config.return_value = config
    octobot_api.get_aiohttp_session.return_value = mock.AsyncMock()
    octobot_api.get_exchange_manager_ids.return_value = []
    return activity_metrics_module.ActivityMetrics(octobot_api)


class TestActivityMetricsInitializeTracker:
    def test_delegates_metrics_enabled_to_tracker(self):
        config = mock.Mock()
        config.get_metrics_enabled.return_value = False
        with mock.patch.object(activity_metrics_module.metrics_connector, "init_tracker") as init_mock:
            activity_metrics_module.ActivityMetrics.initialize_tracker(config)
        init_mock.assert_called_once_with(metrics_enabled=False)


class TestActivityMetricsSetupActivityTracking:
    def test_skips_bot_id_and_tracker_when_metrics_disabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        manager = _activity_metrics(config)
        with mock.patch.object(activity_metrics_module.bot_id_resolver, "ensure_activity_bot_id") as ensure_mock, \
                mock.patch.object(activity_metrics_module.metrics_connector, "update_tracker_bot_id") as update_mock, \
                mock.patch.object(activity_metrics_module.usage_metrics, "record_node_process_start") as record_mock:
            manager.setup_activity_tracking(enums.OctoBotDistribution.NODE)
        ensure_mock.assert_not_called()
        update_mock.assert_not_called()
        record_mock.assert_not_called()

    def test_calls_record_node_process_start_for_node_distribution_when_bot_id_created(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=True)
        manager = _activity_metrics(config)
        bot_id_resolution = bot_id_resolver.BotIdResolution("bot-id", True)
        with mock.patch.object(activity_metrics_module.bot_id_resolver, "ensure_activity_bot_id", mock.Mock(return_value=bot_id_resolution)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "activity_tracking_is_active", mock.Mock(return_value=True)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "update_tracker_bot_id") as update_mock, \
                mock.patch.object(activity_metrics_module.usage_metrics, "record_node_process_start") as record_mock:
            manager.setup_activity_tracking(enums.OctoBotDistribution.NODE)
        update_mock.assert_called_once_with("bot-id")
        record_mock.assert_called_once()
        assert record_mock.call_args.kwargs["was_new_install"] is True
        assert record_mock.call_args.kwargs["config"] is config

    def test_does_not_emit_node_process_start_for_non_node_distribution(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=True)
        manager = _activity_metrics(config)
        bot_id_resolution = bot_id_resolver.BotIdResolution("bot-id", True)
        with mock.patch.object(activity_metrics_module.bot_id_resolver, "ensure_activity_bot_id", mock.Mock(return_value=bot_id_resolution)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "activity_tracking_is_active", mock.Mock(return_value=True)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "update_tracker_bot_id") as update_mock, \
                mock.patch.object(activity_metrics_module.usage_metrics, "record_node_process_start") as record_mock:
            manager.setup_activity_tracking(enums.OctoBotDistribution.DEFAULT)
        update_mock.assert_called_once_with("bot-id")
        record_mock.assert_not_called()

    def test_does_not_emit_node_process_start_when_tracker_inactive(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=True)
        manager = _activity_metrics(config)
        bot_id_resolution = bot_id_resolver.BotIdResolution("bot-id", False)
        with mock.patch.object(activity_metrics_module.bot_id_resolver, "ensure_activity_bot_id", mock.Mock(return_value=bot_id_resolution)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "activity_tracking_is_active", mock.Mock(return_value=False)), \
                mock.patch.object(activity_metrics_module.usage_metrics, "record_node_process_start") as record_mock:
            manager.setup_activity_tracking(enums.OctoBotDistribution.NODE)
        record_mock.assert_not_called()

    def test_deferred_node_process_start_after_metrics_enabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        manager = _activity_metrics(config)
        with mock.patch.object(activity_metrics_module.bot_id_resolver, "ensure_activity_bot_id") as ensure_mock, \
                mock.patch.object(activity_metrics_module.usage_metrics, "record_node_process_start") as record_mock:
            manager.setup_activity_tracking(enums.OctoBotDistribution.NODE)
        ensure_mock.assert_not_called()
        record_mock.assert_not_called()

        config.config[commons_constants.CONFIG_METRICS][commons_constants.CONFIG_ENABLED_OPTION] = True
        manager.enabled = True
        bot_id_resolution = bot_id_resolver.BotIdResolution("bot-id", True)
        with mock.patch.object(activity_metrics_module.bot_id_resolver, "ensure_activity_bot_id", mock.Mock(return_value=bot_id_resolution)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "activity_tracking_is_active", mock.Mock(return_value=True)), \
                mock.patch.object(activity_metrics_module.metrics_connector, "update_tracker_bot_id"), \
                mock.patch.object(activity_metrics_module.usage_metrics, "record_node_process_start") as record_mock:
            manager.setup_activity_tracking(enums.OctoBotDistribution.NODE)
        record_mock.assert_called_once()


class TestActivityMetricsStartCommunityTask:
    @pytest.mark.asyncio
    async def test_runs_stuck_evaluator_and_authenticated_bot_update_loop(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            metrics_enabled=True,
            onboarding_state={"reconcile_automations_pending": False},
        )
        manager = _activity_metrics(config)
        sleep_calls = 0

        async def sleep_side_effect(*_args, **_kwargs):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 2:
                manager.keep_running = False

        with mock.patch.object(
            activity_metrics_module.usage_metrics,
            "ensure_onboarding_state_for_config",
        ), mock.patch.object(
            manager,
            "_update_authenticated_bot",
            mock.AsyncMock(),
        ) as update_mock, \
                mock.patch.object(
                    activity_metrics_module.usage_metrics,
                    "complete_reconcile_automations",
                    mock.AsyncMock(),
                ) as reconcile_mock, \
                mock.patch.object(
                    activity_metrics_module.onboarding_metrics,
                    "run_stuck_no_external_interface_background_evaluator",
                ) as stuck_mock, \
                mock.patch.object(activity_metrics_module.common_constants, "TIMER_BETWEEN_METRICS_UPTIME_UPDATE", 0), \
                mock.patch.object(activity_metrics_module.asyncio, "sleep", side_effect=sleep_side_effect):
            await manager.start_community_task()
        assert reconcile_mock.await_count >= 2
        stuck_mock.assert_called()
        update_mock.assert_called()


class TestActivityMetricsOnboardingInit:
    @pytest.mark.asyncio
    async def test_calls_ensure_onboarding_state_before_loop(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=True)
        manager = _activity_metrics(config)

        async def sleep_side_effect(*_args, **_kwargs):
            manager.keep_running = False

        ensure_mock = mock.Mock()
        reconcile_mock = mock.AsyncMock()

        async def reconcile_side_effect(*_args, **_kwargs):
            ensure_mock.assert_called_once_with(config)

        reconcile_mock.side_effect = reconcile_side_effect

        with mock.patch.object(
            activity_metrics_module.usage_metrics,
            "ensure_onboarding_state_for_config",
            ensure_mock,
        ), mock.patch.object(
            activity_metrics_module.usage_metrics,
            "complete_reconcile_automations",
            reconcile_mock,
        ), mock.patch.object(
            activity_metrics_module.asyncio,
            "sleep",
            side_effect=sleep_side_effect,
        ):
            await manager.start_community_task()
        ensure_mock.assert_called_once_with(config)
        reconcile_mock.assert_awaited_once()


class TestActivityMetricsReconcileRetry:
    @pytest.mark.asyncio
    async def test_uses_short_sleep_while_reconcile_pending(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            metrics_enabled=True,
            onboarding_state={"reconcile_automations_pending": True},
        )
        manager = _activity_metrics(config)
        sleep_durations: list[float] = []

        async def sleep_side_effect(duration, *_args, **_kwargs):
            sleep_durations.append(duration)
            manager.keep_running = False

        with mock.patch.object(
            activity_metrics_module.usage_metrics,
            "ensure_onboarding_state_for_config",
        ), mock.patch.object(
            activity_metrics_module.usage_metrics,
            "complete_reconcile_automations",
            mock.AsyncMock(),
        ), mock.patch.object(
            activity_metrics_module.constants,
            "METRICS_RECONCILE_RETRY_SECONDS",
            15.0,
        ), mock.patch.object(
            activity_metrics_module.asyncio,
            "sleep",
            side_effect=sleep_side_effect,
        ):
            await manager.start_community_task()
        assert sleep_durations == [15.0]
        assert manager._reconcile_retry_attempts == 1

    @pytest.mark.asyncio
    async def test_resets_retry_counter_when_pending_clears(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            metrics_enabled=True,
            onboarding_state={"reconcile_automations_pending": True},
        )
        manager = _activity_metrics(config)
        sleep_durations: list[float] = []
        reconcile_calls = 0

        async def reconcile_side_effect(*_args, **_kwargs):
            nonlocal reconcile_calls
            reconcile_calls += 1
            if reconcile_calls >= 2:
                activity_metrics_module.onboarding_metrics.get_onboarding_state(
                    config,
                ).reconcile_automations_pending = False

        async def sleep_side_effect(duration, *_args, **_kwargs):
            sleep_durations.append(duration)
            if len(sleep_durations) >= 2:
                manager.keep_running = False

        with mock.patch.object(
            activity_metrics_module.usage_metrics,
            "ensure_onboarding_state_for_config",
        ), mock.patch.object(
            activity_metrics_module.usage_metrics,
            "complete_reconcile_automations",
            mock.AsyncMock(side_effect=reconcile_side_effect),
        ), mock.patch.object(
            activity_metrics_module.constants,
            "METRICS_RECONCILE_RETRY_SECONDS",
            15.0,
        ), mock.patch.object(
            activity_metrics_module.common_constants,
            "TIMER_BETWEEN_METRICS_UPTIME_UPDATE",
            999.0,
        ), mock.patch.object(
            activity_metrics_module.asyncio,
            "sleep",
            side_effect=sleep_side_effect,
        ):
            await manager.start_community_task()
        assert sleep_durations[:2] == [15.0, 999.0]
        assert manager._reconcile_retry_attempts == 0

    @pytest.mark.asyncio
    async def test_falls_back_to_long_sleep_after_max_retries(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            metrics_enabled=True,
            onboarding_state={"reconcile_automations_pending": True},
        )
        manager = _activity_metrics(config)
        sleep_durations: list[float] = []

        async def sleep_side_effect(duration, *_args, **_kwargs):
            sleep_durations.append(duration)
            if len(sleep_durations) >= 3:
                manager.keep_running = False

        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(
                    activity_metrics_module.usage_metrics,
                    "ensure_onboarding_state_for_config",
                ), \
                mock.patch.object(
                    activity_metrics_module.metrics_debug,
                    "log_activity",
                ) as log_mock, \
                mock.patch.object(
                    activity_metrics_module.usage_metrics,
                    "complete_reconcile_automations",
                    mock.AsyncMock(),
                ), mock.patch.object(
                    activity_metrics_module.constants,
                    "METRICS_RECONCILE_RETRY_SECONDS",
                    10.0,
                ), mock.patch.object(
                    activity_metrics_module.constants,
                    "METRICS_RECONCILE_MAX_RETRY_ATTEMPTS",
                    2,
                ), mock.patch.object(
                    activity_metrics_module.common_constants,
                    "TIMER_BETWEEN_METRICS_UPTIME_UPDATE",
                    500.0,
                ), mock.patch.object(
                    activity_metrics_module.asyncio,
                    "sleep",
                    side_effect=sleep_side_effect,
                ):
            await manager.start_community_task()
        assert sleep_durations == [10.0, 10.0, 500.0]
        log_mock.assert_any_call(
            "reconcile_skipped",
            reason="max_retries_exceeded",
            retry_attempts=2,
        )


class TestActivityMetricsStopTask:
    @pytest.mark.asyncio
    async def test_stops_uptime_loop(self, tmp_path):
        config = _minimal_config(tmp_path)
        manager = _activity_metrics(config)
        await manager.stop_task()
        assert manager.keep_running is False


class TestActivityMetricsClearActivityBotId:
    def test_clears_metrics_activity_bot_id(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=True)
        config.config[commons_constants.CONFIG_METRICS][
            commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID
        ] = "activity-bot-id"
        activity_metrics_module.ActivityMetrics.clear_activity_bot_id(config)
        assert (
            config.config[commons_constants.CONFIG_METRICS][
                commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID
            ]
            == ""
        )


class TestActivityMetricsLegacyMetricsRemoved:
    def test_removed_legacy_metrics_symbols(self):
        removed_symbols = (
            "register_session",
            "should_register_bot",
            "_get_bot_community",
            "_init_bot_id",
            "_blocking_get_id_and_register",
            "background_get_id_and_register_bot",
        )
        for symbol_name in removed_symbols:
            assert not hasattr(activity_metrics_module.ActivityMetrics, symbol_name), symbol_name
