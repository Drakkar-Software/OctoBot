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

import octobot.community.activity_analysis.usage_metrics as usage_metrics_module
import octobot.constants as constants


def _minimal_config(
    tmp_path,
    onboarding_state: dict | None = None,
    *,
    metrics_enabled: bool = True,
) -> configuration.Configuration:
    user_root = tmp_path / commons_constants.USER_FOLDER
    user_root.mkdir()
    profiles_path = user_root / commons_constants.PROFILES_FOLDER
    profiles_path.mkdir(parents=True, exist_ok=True)
    config_file_path = user_root / commons_constants.CONFIG_FILE
    metrics_section = {commons_constants.CONFIG_ENABLED_OPTION: metrics_enabled}
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
        str(profiles_path),
        constants.CONFIG_FILE_SCHEMA,
        constants.PROFILE_FILE_SCHEMA,
    )
    config.read(should_raise=False, activate_profile=False)
    return config


def _generic_process_strategy() -> protocol_models.Strategy:
    return protocol_models.Strategy(
        id="strategy-id",
        version="1",
        reference_market="USDT",
        configuration=protocol_models.StrategyConfiguration(
            protocol_models.GenericProcessConfiguration(
                configuration_type="generic_process",
            )
        ),
    )


class Test_record_new_automation_created:
    def test_increments_once_and_splits_onboarding_vs_usage_on_first(self, tmp_path):
        config = _minimal_config(tmp_path)
        strategy = _generic_process_strategy()
        with mock.patch.object(
            usage_metrics_module.onboarding_metrics,
            "record_first_automation_started",
        ) as first_automation_mock, \
                mock.patch(
                    "octobot.community.activity_analysis.metrics_connector.emit_count",
                ) as emit_count_mock, \
                mock.patch.object(config, "save"):
            usage_metrics_module.record_new_automation_created(
                "automation-1",
                strategy,
                config=config,
                now=100.0,
            )
        first_automation_mock.assert_called_once()
        emit_count_mock.assert_called_once()
        emitted_attributes = emit_count_mock.call_args.args[1]
        assert isinstance(emitted_attributes, usage_metrics_module.metric_definitions.AutomationStartedAttributes)
        assert emitted_attributes.automation_count == 1

    def test_automation_restart_does_not_emit_automation_started(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "tracked_automation_ids": ["automation-1"],
                "distinct_automation_count": 1,
                "onboarding_complete": True,
            },
        )
        with mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ) as emit_count_mock:
            usage_metrics_module.record_new_automation_created(
                "automation-1",
                _generic_process_strategy(),
                config=config,
            )
        emit_count_mock.assert_not_called()

    def test_does_not_propagate_save_error(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "tracked_automation_ids": ["existing-automation"],
                "distinct_automation_count": 1,
                "onboarding_complete": True,
            },
        )
        logger_mock = mock.Mock()
        with mock.patch.object(
            usage_metrics_module.metrics_debug,
            "_LOGGER",
            logger_mock,
        ), mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ), mock.patch.object(
            config,
            "save",
            side_effect=TypeError("cannot pickle '_asyncio.Task' object"),
        ):
            usage_metrics_module.record_new_automation_created(
                "new-automation",
                _generic_process_strategy(),
                config=config,
            )
        logger_mock.exception.assert_called_once()
        exception_call = logger_mock.exception.call_args
        assert isinstance(exception_call.args[0], TypeError)
        assert exception_call.args[1] is True
        assert exception_call.args[2] == (
            "Activity metrics hook failed hook=record_new_automation_created: "
            "cannot pickle '_asyncio.Task' object"
        )


class Test_automation_started_emits_for_counts_1_through_5_then_every_5th:
    @pytest.mark.parametrize(
        "automation_count,should_emit",
        [
            (2, True),
            (3, True),
            (4, True),
            (5, True),
            (6, False),
            (10, True),
        ],
    )
    def test_throttling(self, tmp_path, automation_count, should_emit):
        tracked_ids = [f"automation-{index}" for index in range(automation_count - 1)]
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "tracked_automation_ids": tracked_ids,
                "distinct_automation_count": automation_count - 1,
                "onboarding_complete": True,
            },
        )
        with mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ) as emit_count_mock, mock.patch.object(config, "save"):
            usage_metrics_module.record_new_automation_created(
                f"automation-{automation_count}",
                _generic_process_strategy(),
                config=config,
            )
        if should_emit:
            emit_count_mock.assert_called_once()
        else:
            emit_count_mock.assert_not_called()


class Test_converted_fresh_path_after_24h_from_first_automation_started_at:
    def test_emits_post_onboard_conversion(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "onboarding_complete": True,
                "first_automation_started_at": 0.0,
                "onboarding_started_at": 0.0,
            },
        )
        with mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ) as emit_count_mock, mock.patch.object(config, "save"):
            usage_metrics_module.evaluate_user_converted_24h_return(config, now=86401.0)
        emit_count_mock.assert_called_once()
        emitted_attributes = emit_count_mock.call_args.args[1]
        assert isinstance(
            emitted_attributes,
            usage_metrics_module.metric_definitions.UserConverted24hReturnAttributes,
        )
        assert emitted_attributes.conversion_path.value == "post_onboard"


class Test_converted_reconciled_path_after_24h_from_onboarding_started_at:
    def test_emits_reconciled_conversion(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "onboarding_complete": True,
                "reconciled_from_existing_config": True,
                "onboarding_started_at": 0.0,
            },
        )
        with mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ) as emit_count_mock, mock.patch.object(config, "save"):
            usage_metrics_module.evaluate_user_converted_24h_return(config, now=86401.0)
        emit_count_mock.assert_called_once()
        emitted_attributes = emit_count_mock.call_args.args[1]
        assert emitted_attributes.conversion_path.value == "reconciled"


class Test_converted_requires_onboarding_complete:
    def test_not_fired_before_onboarding_complete(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "first_automation_started_at": 0.0,
            },
        )
        with mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ) as emit_count_mock:
            usage_metrics_module.evaluate_user_converted_24h_return(config, now=86401.0)
        emit_count_mock.assert_not_called()


class Test_debug_logging_skip_paths:
    def test_record_node_process_start_skipped_without_enabled_config(self, tmp_path):
        config = _minimal_config(tmp_path)
        config.config[commons_constants.CONFIG_METRICS][commons_constants.CONFIG_ENABLED_OPTION] = False
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(usage_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch(
                    "octobot.community.activity_analysis.metrics_connector.emit_count",
                ) as emit_count_mock:
            usage_metrics_module.record_node_process_start(
                "node",
                was_new_install=False,
                config=config,
            )
        emit_count_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "hook_skipped",
            hook="record_node_process_start",
            reason="no_enabled_config",
        )

    def test_record_account_validated_skipped_for_invalid_account(self, tmp_path):
        config = _minimal_config(tmp_path)
        checked_account = protocol_models.Account(
            id="account-id",
            name="account",
            is_simulated=False,
            created_at=datetime.datetime.now(datetime.UTC),
            state=protocol_models.AccountState(status=protocol_models.AccountStatus.INVALID),
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(usage_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch(
                    "octobot.community.activity_analysis.metrics_connector.emit_count",
                ) as emit_count_mock:
            usage_metrics_module.record_account_validated(
                checked_account,
                "wallet-id",
                config=config,
            )
        emit_count_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "hook_skipped",
            hook="record_account_validated",
            reason="account_not_valid",
        )

    def test_record_new_automation_created_skipped_for_duplicate_automation(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "tracked_automation_ids": ["automation-1"],
                "distinct_automation_count": 1,
                "onboarding_complete": True,
            },
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(usage_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch(
                    "octobot.community.activity_analysis.metrics_connector.emit_count",
                ) as emit_count_mock:
            usage_metrics_module.record_new_automation_created(
                "automation-1",
                _generic_process_strategy(),
                config=config,
            )
        emit_count_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "hook_skipped",
            hook="record_new_automation_created",
            reason="duplicate_automation_id",
            automation_id="automation-1",
        )

    def test_evaluate_user_converted_24h_return_skipped_when_delay_not_met(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "onboarding_complete": True,
                "first_automation_started_at": 0.0,
                "onboarding_started_at": 0.0,
            },
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(usage_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch(
                    "octobot.community.activity_analysis.metrics_connector.emit_count",
                ) as emit_count_mock:
            usage_metrics_module.evaluate_user_converted_24h_return(config, now=100.0)
        emit_count_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "hook_skipped",
            hook="evaluate_user_converted_24h_return",
            reason="conversion_delay_not_met",
        )


class Test_record_node_process_start_initializes_state:
    def test_sets_reconcile_pending_from_wallet_snapshot(self, tmp_path):
        config = _minimal_config(tmp_path)
        snapshot = usage_metrics_module.onboarding_metrics.ExistingConfigSnapshot(
            wallet_configured=True,
            wallet_user_ids=["0xabc"],
            account_count=1,
            distinct_automation_ids=[],
            reconcile_automations_pending=True,
        )
        auth_mock = mock.Mock()
        auth_mock.is_node_wallet_configured.return_value = True
        with mock.patch.object(
            usage_metrics_module,
            "build_existing_config_snapshot",
            mock.Mock(return_value=snapshot),
        ), mock.patch.object(
            usage_metrics_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=auth_mock),
        ), mock.patch(
            "octobot.community.activity_analysis.metrics_connector.emit_count",
        ), mock.patch.object(config, "save"):
            usage_metrics_module.record_node_process_start(
                "node",
                was_new_install=False,
                config=config,
            )
        state = usage_metrics_module.onboarding_metrics.get_onboarding_state(config)
        assert state.reconcile_automations_pending is True
        assert state.reconciled_from_existing_config is True


class Test_build_existing_config_snapshot:
    def test_uses_account_provider(self):
        auth_mock = mock.Mock()
        auth_mock.is_node_wallet_configured.return_value = True
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["0xabc"]
        account_provider_mock.list_accounts.return_value = [mock.Mock()]
        with mock.patch.object(
            usage_metrics_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=auth_mock),
        ), mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            mock.Mock(return_value=account_provider_mock),
        ):
            snapshot = usage_metrics_module.build_existing_config_snapshot()
        assert snapshot.wallet_configured is True
        assert snapshot.account_count == 1
        assert snapshot.reconcile_automations_pending is True


class Test_ensure_onboarding_state_for_config:
    def test_initializes_pending_from_wallet_snapshot(self, tmp_path):
        config = _minimal_config(tmp_path)
        auth_mock = mock.Mock()
        auth_mock.is_node_wallet_configured.return_value = True
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["0xabc"]
        account_provider_mock.list_accounts.return_value = [mock.Mock()]
        with mock.patch.object(
            usage_metrics_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=auth_mock),
        ), mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            mock.Mock(return_value=account_provider_mock),
        ), mock.patch.object(config, "save"):
            usage_metrics_module.ensure_onboarding_state_for_config(config)
        state = usage_metrics_module.onboarding_metrics.get_onboarding_state(config)
        assert state.reconcile_automations_pending is True
        assert state.reconciled_from_existing_config is True

    def test_second_call_is_no_op(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"reconcile_automations_pending": False},
        )
        auth_mock = mock.Mock()
        auth_mock.is_node_wallet_configured.return_value = True
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["0xabc"]
        account_provider_mock.list_accounts.return_value = [mock.Mock()]
        with mock.patch.object(
            usage_metrics_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=auth_mock),
        ), mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            mock.Mock(return_value=account_provider_mock),
        ), mock.patch.object(config, "save") as save_mock:
            usage_metrics_module.ensure_onboarding_state_for_config(config)
            usage_metrics_module.ensure_onboarding_state_for_config(config)
        state = usage_metrics_module.onboarding_metrics.get_onboarding_state(config)
        assert state.reconcile_automations_pending is False
        save_mock.assert_not_called()

    def test_no_op_when_config_disabled(self, tmp_path):
        config = _minimal_config(tmp_path, metrics_enabled=False)
        with mock.patch.object(config, "save") as save_mock:
            usage_metrics_module.ensure_onboarding_state_for_config(config)
        assert usage_metrics_module.onboarding_metrics.get_onboarding_state(
            config,
        ).reconcile_automations_pending_is_set() is False
        save_mock.assert_not_called()


class Test_complete_reconcile_automations:
    @pytest.mark.asyncio
    async def test_loads_automation_ids_from_scheduler(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"reconcile_automations_pending": True},
        )
        automation_state = protocol_models.AutomationState(
            id="automation-1",
            status=protocol_models.WorkflowStatus.PENDING,
            metadata=protocol_models.AutomationMetadata(name="automation", description=""),
        )
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["0xwallet"]
        with mock.patch.object(
            usage_metrics_module.onboarding_metrics,
            "apply_reconciled_automations",
        ) as apply_mock, mock.patch(
            "octobot_node.scheduler.is_initialized",
            mock.Mock(return_value=True),
        ), mock.patch(
            "octobot_node.scheduler.automations.automation_states_loader.load_protocol_automation_states",
            mock.AsyncMock(return_value=[automation_state]),
        ), mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            mock.Mock(return_value=account_provider_mock),
        ):
            await usage_metrics_module.complete_reconcile_automations(config)
        apply_mock.assert_called_once_with(config, ["automation-1"])

    @pytest.mark.asyncio
    async def test_reconciles_after_explicit_init(self, tmp_path):
        config = _minimal_config(tmp_path)
        automation_state = protocol_models.AutomationState(
            id="automation-1",
            status=protocol_models.WorkflowStatus.PENDING,
            metadata=protocol_models.AutomationMetadata(name="automation", description=""),
        )
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["0xwallet"]
        auth_mock = mock.Mock()
        auth_mock.is_node_wallet_configured.return_value = True
        account_provider_mock.list_accounts.return_value = [mock.Mock()]
        with mock.patch.object(
            usage_metrics_module.onboarding_metrics,
            "apply_reconciled_automations",
        ) as apply_mock, mock.patch(
            "octobot_node.scheduler.is_initialized",
            mock.Mock(return_value=True),
        ), mock.patch(
            "octobot_node.scheduler.automations.automation_states_loader.load_protocol_automation_states",
            mock.AsyncMock(return_value=[automation_state]),
        ), mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            mock.Mock(return_value=account_provider_mock),
        ), mock.patch.object(
            usage_metrics_module.community_authentication.CommunityAuthentication,
            "instance",
            mock.Mock(return_value=auth_mock),
        ), mock.patch.object(config, "save"):
            usage_metrics_module.ensure_onboarding_state_for_config(config)
            await usage_metrics_module.complete_reconcile_automations(config)
        apply_mock.assert_called_once_with(config, ["automation-1"])

    @pytest.mark.asyncio
    async def test_does_not_initialize_state_on_empty_storage(self, tmp_path):
        config = _minimal_config(tmp_path)
        automation_state = protocol_models.AutomationState(
            id="automation-1",
            status=protocol_models.WorkflowStatus.PENDING,
            metadata=protocol_models.AutomationMetadata(name="automation", description=""),
        )
        account_provider_mock = mock.Mock()
        account_provider_mock.list_collectable_wallet_ids.return_value = ["0xwallet"]
        with mock.patch.object(
            usage_metrics_module.onboarding_metrics,
            "apply_reconciled_automations",
        ) as apply_mock, mock.patch(
            "octobot_node.scheduler.is_initialized",
            mock.Mock(return_value=True),
        ), mock.patch(
            "octobot_node.scheduler.automations.automation_states_loader.load_protocol_automation_states",
            mock.AsyncMock(return_value=[automation_state]),
        ), mock.patch(
            "octobot_sync.sync.collection_providers.AccountProvider.instance",
            mock.Mock(return_value=account_provider_mock),
        ):
            await usage_metrics_module.complete_reconcile_automations(config)
        state = usage_metrics_module.onboarding_metrics.get_onboarding_state(config)
        assert state.reconcile_automations_pending_is_set() is False
        apply_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_scheduler_not_initialized(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={"reconcile_automations_pending": True},
        )
        with mock.patch.object(constants, "ENABLE_ACTIVITY_METRICS_DEBUG_LOGS", True), \
                mock.patch.object(usage_metrics_module.metrics_debug, "log_activity") as log_mock, \
                mock.patch.object(
                    usage_metrics_module.onboarding_metrics,
                    "apply_reconciled_automations",
                ) as apply_mock, mock.patch(
                    "octobot_node.scheduler.is_initialized",
                    mock.Mock(return_value=False),
                ):
            await usage_metrics_module.complete_reconcile_automations(config)
        apply_mock.assert_not_called()
        log_mock.assert_called_once_with(
            "reconcile_skipped",
            reason="scheduler_not_initialized",
        )
        assert usage_metrics_module.onboarding_metrics.get_onboarding_state(
            config,
        ).reconcile_automations_pending is True

    @pytest.mark.asyncio
    async def test_skips_when_reconcile_not_pending_and_onboarding_complete(self, tmp_path):
        config = _minimal_config(
            tmp_path,
            onboarding_state={
                "reconcile_automations_pending": False,
                "onboarding_complete": True,
                "distinct_automation_count": 1,
            },
        )
        with mock.patch.object(
            usage_metrics_module.onboarding_metrics,
            "apply_reconciled_automations",
        ) as apply_mock, mock.patch(
            "octobot_node.scheduler.is_initialized",
            mock.Mock(return_value=True),
        ):
            await usage_metrics_module.complete_reconcile_automations(config)
        apply_mock.assert_not_called()


class Test_metric_events_enum_values_match_sentry_event_strings:
    def test_values(self):
        assert commons_enums.MetricEvents.NODE_PROCESS_START.value == "node_process_start"
        assert commons_enums.MetricEvents.USER_CONVERTED_24H_RETURN.value == "user_converted_24h_return"
