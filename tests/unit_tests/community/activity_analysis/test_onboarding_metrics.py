#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
import datetime
import json
import os

import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration
import octobot_commons.enums as commons_enums

import octobot_protocol.models as protocol_models

import octobot.community.activity_analysis.metric_definitions as metric_definitions
import octobot.community.activity_analysis.onboarding_metrics as onboarding_metrics_module
import octobot.constants as constants


def _minimal_config(tmp_path, onboarding_state: dict | None = None) -> configuration.Configuration:
    user_root = tmp_path / commons_constants.USER_FOLDER
    user_root.mkdir()
    config_path = user_root / commons_constants.PROFILES_FOLDER
    config_path.mkdir(parents=True, exist_ok=True)
    config_file_path = user_root / commons_constants.CONFIG_FILE
    metrics_section = {commons_constants.CONFIG_ENABLED_OPTION: True}
    if onboarding_state is not None:
        metrics_section[commons_constants.CONFIG_METRICS_ONBOARDING_STATE] = onboarding_state
    config_data = {
        commons_constants.CONFIG_METRICS: metrics_section,
        constants.CONFIG_COMMUNITY: {},
    }
    with open(config_file_path, "w", encoding="utf-8") as config_file:
        json.dump(config_data, config_file)
    config = configuration.Configuration(
        str(config_file_path),
        str(config_path),
        constants.CONFIG_FILE_SCHEMA,
        constants.PROFILE_FILE_SCHEMA,
    )
    config.read(should_raise=False, activate_profile=False)
    return config


class Test_classify_and_reconcile_empty_config:
    def test_fresh_install_leaves_reconcile_pending_false(self, tmp_path):
        config = _minimal_config(tmp_path)
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=False,
            wallet_user_ids=[],
            account_count=0,
            distinct_automation_ids=[],
            reconcile_automations_pending=False,
        )
        with mock.patch.object(config, "save"):
            reconciled = onboarding_metrics_module.classify_and_reconcile(config, snapshot)
        assert reconciled is False


class Test_classify_and_reconcile_wallet_only:
    def test_sets_reconciled_without_onboarding_complete(self, tmp_path):
        config = _minimal_config(tmp_path)
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=0,
            distinct_automation_ids=[],
            reconcile_automations_pending=True,
        )
        with mock.patch.object(config, "save"):
            onboarding_metrics_module.classify_and_reconcile(config, snapshot)
        assert onboarding_metrics_module.is_onboarding_complete(config) is False
        assert onboarding_metrics_module.is_milestone_set(
            config,
            commons_enums.MetricEvents.NODE_WALLET_CONFIGURED,
        )


class Test_classify_and_reconcile_with_automations:
    def test_sets_onboarding_complete_without_sentry(self, tmp_path):
        config = _minimal_config(tmp_path)
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=1,
            distinct_automation_ids=["automation-1"],
            reconcile_automations_pending=False,
        )
        with mock.patch.object(config, "save"), \
                mock.patch.object(
                    onboarding_metrics_module,
                    "_emit_once",
                ) as emit_once_mock:
            onboarding_metrics_module.classify_and_reconcile(config, snapshot)
        emit_once_mock.assert_not_called()
        assert onboarding_metrics_module.is_onboarding_complete(config) is True


class Test_apply_reconciled_automations:
    def test_reconcile_sets_milestones_without_sentry_emit(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"reconcile_automations_pending": True},
        )
        with mock.patch.object(config, "save"), \
                mock.patch.object(
                    onboarding_metrics_module,
                    "_emit_once",
                ) as emit_once_mock:
            onboarding_metrics_module.apply_reconciled_automations(
                config,
                ["automation-1"],
            )
        emit_once_mock.assert_not_called()
        assert onboarding_metrics_module.is_onboarding_complete(config) is True
        assert onboarding_metrics_module.get_onboarding_state(config).reconcile_automations_pending is False


class Test_ensure_onboarding_state_initialized:
    def test_initializes_wallet_only_snapshot(self, tmp_path):
        config = _minimal_config(tmp_path)
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=0,
            distinct_automation_ids=[],
            reconcile_automations_pending=True,
        )
        with mock.patch.object(config, "save"):
            onboarding_metrics_module.ensure_onboarding_state_initialized(config, snapshot)
        state = onboarding_metrics_module.get_onboarding_state(config)
        assert state.reconcile_automations_pending is True
        assert state.reconciled_from_existing_config is True

    def test_second_call_is_no_op(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"reconcile_automations_pending": False},
        )
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=0,
            distinct_automation_ids=[],
            reconcile_automations_pending=True,
        )
        with mock.patch.object(
            onboarding_metrics_module,
            "classify_and_reconcile",
        ) as classify_mock:
            onboarding_metrics_module.ensure_onboarding_state_initialized(config, snapshot)
        classify_mock.assert_not_called()

    def test_logs_on_first_init_when_debug_enabled(self, tmp_path):
        config = _minimal_config(tmp_path)
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=1,
            distinct_automation_ids=[],
            reconcile_automations_pending=True,
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(onboarding_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(config, "save"):
            onboarding_metrics_module.ensure_onboarding_state_initialized(config, snapshot)
        log_mock.assert_called_once()
        assert log_mock.call_args.args[0] == "onboarding_state_initialized"

    def test_does_not_log_when_already_initialized(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"reconcile_automations_pending": True},
        )
        snapshot = onboarding_metrics_module.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=1,
            distinct_automation_ids=[],
            reconcile_automations_pending=True,
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(onboarding_metrics_module.metrics_debug, "log_activity") as log_mock:
            onboarding_metrics_module.ensure_onboarding_state_initialized(config, snapshot)
        log_mock.assert_not_called()


class Test_emit_once:
    def test_includes_duration_gauge(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"onboarding_started_at": 50.0},
        )
        attributes = metric_definitions.NodeWalletConfiguredAttributes()
        with mock.patch.object(
            onboarding_metrics_module.metrics_connector,
            "emit_count",
        ) as emit_count_mock, mock.patch.object(
            onboarding_metrics_module.metrics_connector,
            "emit_onboarding_duration_gauge",
        ) as gauge_mock, mock.patch.object(config, "save"):
            onboarding_metrics_module._emit_once(
                config,
                attributes,
                now=100.0,
            )
        emit_count_mock.assert_called_once_with(config, attributes)
        gauge_mock.assert_called_once_with(config, 50.0, attributes)

    def test_idempotent(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "onboarding_milestones": {
                    commons_enums.MetricEvents.NODE_WALLET_CONFIGURED.value: True,
                },
            },
        )
        with mock.patch.object(
            onboarding_metrics_module.metrics_connector,
            "emit_count",
        ) as emit_count_mock:
            onboarding_metrics_module._emit_once(
                config,
                metric_definitions.NodeWalletConfiguredAttributes(),
                now=100.0,
            )
        emit_count_mock.assert_not_called()

    def test_skipped_when_onboarding_complete(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"onboarding_complete": True, "distinct_automation_count": 1},
        )
        with mock.patch.object(
            onboarding_metrics_module.metrics_connector,
            "emit_count",
        ) as emit_count_mock:
            onboarding_metrics_module._emit_once(
                config,
                metric_definitions.ExternalInterfaceConnectedAttributes(source="sync"),
                now=100.0,
            )
        emit_count_mock.assert_not_called()


class Test_debug_logging_skip_paths:
    def test_emit_once_skipped_when_milestone_already_set(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "onboarding_milestones": {
                    commons_enums.MetricEvents.NODE_WALLET_CONFIGURED.value: True,
                },
            },
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(onboarding_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(
                    onboarding_metrics_module.metrics_connector,
                    "emit_count",
                ) as emit_count_mock:
            onboarding_metrics_module._emit_once(
                config,
                metric_definitions.NodeWalletConfiguredAttributes(),
                now=100.0,
            )
        emit_count_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "emit_once_skipped",
            event=commons_enums.MetricEvents.NODE_WALLET_CONFIGURED.value,
            reason="milestone_already_set",
        )

    def test_emit_once_skipped_when_onboarding_complete(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"onboarding_complete": True, "distinct_automation_count": 1},
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(onboarding_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(
                    onboarding_metrics_module.metrics_connector,
                    "emit_count",
                ) as emit_count_mock:
            onboarding_metrics_module._emit_once(
                config,
                metric_definitions.ExternalInterfaceConnectedAttributes(source="sync"),
                now=100.0,
            )
        emit_count_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "emit_once_skipped",
            event=commons_enums.MetricEvents.EXTERNAL_INTERFACE_CONNECTED.value,
            reason="onboarding_complete",
        )

    def test_record_user_action_entry_skipped_without_enabled_config(self, tmp_path):
        config = _minimal_config(tmp_path, onboarding_state={"onboarding_started_at": 0.0})
        config.config[commons_constants.CONFIG_METRICS][commons_constants.CONFIG_ENABLED_OPTION] = False
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(onboarding_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(onboarding_metrics_module, "_emit_once") as emit_once_mock:
            onboarding_metrics_module.record_user_action_entry(
                mock.Mock(),
                source="sync",
                config=config,
            )
        emit_once_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "hook_skipped",
            hook="record_user_action_entry",
            reason="no_enabled_config",
        )


class Test_stuck_no_external_interface_after_3d:
    def test_emits_after_wallet_configured_delay(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "wallet_configured_at": 0.0,
            },
        )
        with mock.patch.object(
            onboarding_metrics_module,
            "_emit_once",
        ) as emit_once_mock:
            onboarding_metrics_module.evaluate_stuck_no_external_interface(
                config,
                now=3 * 86400 + 1,
            )
        emit_once_mock.assert_called_once()


class Test_classify_octobot_kind:
    def test_generic_process_is_manual(self):
        strategy = protocol_models.Strategy(
            id="strategy-id",
            version="1",
            reference_market="USDT",
            configuration=protocol_models.StrategyConfiguration(
                protocol_models.GenericProcessConfiguration(
                    configuration_type="generic_process",
                )
            ),
        )
        octobot_kind, flow_subtype = onboarding_metrics_module.classify_octobot_kind(strategy)
        assert octobot_kind == metric_definitions.OctobotKind.MANUAL
        assert flow_subtype is None

    def test_trading_tentacles_grid(self):
        strategy = protocol_models.Strategy(
            id="strategy-id",
            version="1",
            reference_market="USDT",
            configuration=protocol_models.StrategyConfiguration(
                protocol_models.TradingTentaclesConfiguration(
                    configuration_type="trading_tentacles",
                    name="GridTradingMode",
                    config={},
                )
            ),
        )
        octobot_kind, flow_subtype = onboarding_metrics_module.classify_octobot_kind(strategy)
        assert octobot_kind == metric_definitions.OctobotKind.FLOW
        assert flow_subtype == "GridTradingMode"

    def test_trading_tentacles_custom_name(self):
        strategy = protocol_models.Strategy(
            id="strategy-id",
            version="1",
            reference_market="USDT",
            configuration=protocol_models.StrategyConfiguration(
                protocol_models.TradingTentaclesConfiguration(
                    configuration_type="trading_tentacles",
                    name="CustomTradingMode",
                    config={},
                )
            ),
        )
        octobot_kind, flow_subtype = onboarding_metrics_module.classify_octobot_kind(strategy)
        assert octobot_kind == metric_definitions.OctobotKind.FLOW
        assert flow_subtype == "CustomTradingMode"

    def test_trading_tentacles_empty_name(self):
        strategy = protocol_models.Strategy(
            id="strategy-id",
            version="1",
            reference_market="USDT",
            configuration=protocol_models.StrategyConfiguration(
                protocol_models.TradingTentaclesConfiguration(
                    configuration_type="trading_tentacles",
                    name="",
                    config={},
                )
            ),
        )
        octobot_kind, flow_subtype = onboarding_metrics_module.classify_octobot_kind(strategy)
        assert octobot_kind == metric_definitions.OctobotKind.FLOW
        assert flow_subtype == metric_definitions.FlowSubtype.OTHER


class Test_record_user_action_entry:
    def test_account_create_attempt_per_is_simulated(self, tmp_path):
        config = _minimal_config(tmp_path)
        account_configuration = protocol_models.CreateAccountConfiguration(
            id="create-account",
            action_type=protocol_models.UserActionType.ACCOUNT_CREATE,
            configuration=protocol_models.Account(
                id="account-id",
                name="account",
                is_simulated=False,
                created_at=datetime.datetime.now(datetime.UTC),
            ),
        )
        user_action = protocol_models.UserAction(
            id="user-action-id",
            configuration=protocol_models.UserActionConfiguration(account_configuration),
        )
        with mock.patch.object(
            onboarding_metrics_module,
            "_emit_once",
            side_effect=[True, True],
        ) as emit_once_mock, mock.patch.object(config, "save"):
            onboarding_metrics_module.record_user_action_entry(
                user_action,
                source="sync",
                config=config,
                now=10.0,
            )
        assert emit_once_mock.call_count == 2
        first_attributes = emit_once_mock.call_args_list[0].args[1]
        assert isinstance(first_attributes, metric_definitions.ExternalInterfaceConnectedAttributes)
        assert first_attributes.source == "sync"

    def test_does_not_propagate_emit_error(self, tmp_path):
        config = _minimal_config(tmp_path)
        logger_mock = mock.Mock()
        with mock.patch.object(
            onboarding_metrics_module.metrics_debug,
            "_LOGGER",
            logger_mock,
        ), mock.patch.object(
            onboarding_metrics_module,
            "_emit_once",
            side_effect=TypeError("cannot pickle '_asyncio.Task' object"),
        ):
            onboarding_metrics_module.record_user_action_entry(
                mock.Mock(),
                source="sync",
                config=config,
            )
        logger_mock.exception.assert_called_once()
        exception_call = logger_mock.exception.call_args
        assert isinstance(exception_call.args[0], TypeError)
        assert exception_call.args[1] is True
        assert exception_call.args[2] == (
            "Activity metrics hook failed hook=record_user_action_entry: "
            "cannot pickle '_asyncio.Task' object"
        )
