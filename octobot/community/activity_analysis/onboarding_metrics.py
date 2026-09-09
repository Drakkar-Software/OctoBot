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
import dataclasses
import time
import typing

import octobot_commons.configuration as configuration
import octobot_commons.enums as commons_enums

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.util.protocol_trading_mapping as protocol_trading_mapping

import octobot.community.activity_analysis.metric_definitions as metric_definitions
import octobot.community.activity_analysis.metrics_config as metrics_config
import octobot.community.activity_analysis.metrics_connector as metrics_connector
import octobot.community.activity_analysis.metrics_debug as metrics_debug
import octobot.community.activity_analysis.onboarding_state as onboarding_state_module
import octobot.constants as constants


@dataclasses.dataclass(frozen=True)
class ExistingConfigSnapshot:
    wallet_configured: bool
    wallet_user_ids: list[str]
    account_count: int
    distinct_automation_ids: list[str]
    reconcile_automations_pending: bool


def get_onboarding_state(config: configuration.Configuration) -> onboarding_state_module.OnboardingState:
    return onboarding_state_module.OnboardingState.from_config(config)


def get_onboarding_started_at(config: configuration.Configuration) -> typing.Optional[float]:
    return get_onboarding_state(config).onboarding_started_at


def ensure_onboarding_started_at(config: configuration.Configuration, now: float) -> None:
    state = get_onboarding_state(config)
    if state.onboarding_started_at is None:
        state.onboarding_started_at = now


def is_onboarding_complete(config: configuration.Configuration) -> bool:
    state = get_onboarding_state(config)
    if state.onboarding_complete:
        return True
    return state.distinct_automation_count >= 1


def _set_onboarding_complete(config: configuration.Configuration) -> None:
    get_onboarding_state(config).onboarding_complete = True


def _milestone_storage_key(
    event: commons_enums.MetricEvents,
    milestone_key: typing.Optional[str] = None,
) -> str:
    if milestone_key is None:
        return event.value
    return milestone_key


def is_milestone_set(
    config: configuration.Configuration,
    event: commons_enums.MetricEvents,
    *,
    milestone_key: typing.Optional[str] = None,
) -> bool:
    milestones = get_onboarding_state(config).milestones_or_none()
    if milestones is None:
        return False
    return bool(milestones.get(_milestone_storage_key(event, milestone_key)))


def set_milestone(
    config: configuration.Configuration,
    event: commons_enums.MetricEvents,
    *,
    milestone_key: typing.Optional[str] = None,
) -> None:
    milestones = get_onboarding_state(config).milestones
    milestones[_milestone_storage_key(event, milestone_key)] = True


def get_tracked_automation_ids(config: configuration.Configuration) -> set[str]:
    return get_onboarding_state(config).get_tracked_automation_ids()


def add_tracked_automation_id(config: configuration.Configuration, automation_id: str) -> None:
    get_onboarding_state(config).add_tracked_automation_id(automation_id)


def set_distinct_automation_count(config: configuration.Configuration, count: int) -> None:
    _set_distinct_automation_count(config, count)


def _set_distinct_automation_count(config: configuration.Configuration, count: int) -> None:
    state = get_onboarding_state(config)
    state.distinct_automation_count = count
    if count >= 1:
        _set_onboarding_complete(config)


def classify_and_reconcile(
    config: configuration.Configuration,
    snapshot: ExistingConfigSnapshot,
) -> bool:
    state = get_onboarding_state(config)
    has_existing_config = (
        snapshot.wallet_configured
        or snapshot.account_count > 0
        or len(snapshot.distinct_automation_ids) > 0
    )
    if not has_existing_config:
        state.reconcile_automations_pending = False
        return False

    state.reconciled_from_existing_config = True
    if snapshot.wallet_configured:
        set_milestone(config, commons_enums.MetricEvents.NODE_WALLET_CONFIGURED)
    if snapshot.account_count > 0 or snapshot.distinct_automation_ids:
        set_milestone(config, commons_enums.MetricEvents.EXTERNAL_INTERFACE_CONNECTED)

    automation_ids = list(snapshot.distinct_automation_ids)
    if automation_ids:
        for automation_id in automation_ids:
            state.add_tracked_automation_id(automation_id)
        _set_distinct_automation_count(config, len(state.get_tracked_automation_ids()))
        set_milestone(config, commons_enums.MetricEvents.FIRST_AUTOMATION_STARTED)

    state.reconcile_automations_pending = snapshot.reconcile_automations_pending
    config.save()
    return True


@metrics_debug.wrapped_exception
def ensure_onboarding_state_initialized(
    config: configuration.Configuration,
    snapshot: ExistingConfigSnapshot,
) -> None:
    state = get_onboarding_state(config)
    if state.reconcile_automations_pending_is_set():
        return
    classify_and_reconcile(config, snapshot)
    metrics_debug.log_activity(
        "onboarding_state_initialized",
        wallet_configured=snapshot.wallet_configured,
        account_count=snapshot.account_count,
        reconcile_automations_pending=state.reconcile_automations_pending,
        reconciled_from_existing_config=state.reconciled_from_existing_config,
    )


@metrics_debug.wrapped_exception
def apply_reconciled_automations(
    config: configuration.Configuration,
    automation_ids: list[str],
) -> None:
    state = get_onboarding_state(config)
    for automation_id in automation_ids:
        state.add_tracked_automation_id(automation_id)
    tracked_count = len(state.get_tracked_automation_ids())
    _set_distinct_automation_count(config, tracked_count)
    if tracked_count >= 1:
        set_milestone(config, commons_enums.MetricEvents.FIRST_AUTOMATION_STARTED)
        set_milestone(config, commons_enums.MetricEvents.EXTERNAL_INTERFACE_CONNECTED)
    state.reconcile_automations_pending = False
    config.save()


def _emit_once(
    config: configuration.Configuration,
    attributes: metric_definitions.MetricAttributes,
    *,
    milestone_key: typing.Optional[str] = None,
    now: typing.Optional[float] = None,
) -> bool:
    if is_onboarding_complete(config):
        metrics_debug.log_activity(
            "emit_once_skipped",
            event=attributes.event.value,
            reason="onboarding_complete",
        )
        return False
    if is_milestone_set(config, attributes.event, milestone_key=milestone_key):
        metrics_debug.log_activity(
            "emit_once_skipped",
            event=attributes.event.value,
            reason="milestone_already_set",
        )
        return False
    metrics_connector.emit_count(config, attributes)
    set_milestone(config, attributes.event, milestone_key=milestone_key)
    onboarding_started_at = get_onboarding_started_at(config)
    if onboarding_started_at is not None and now is not None:
        duration_seconds = now - onboarding_started_at
        metrics_connector.emit_onboarding_duration_gauge(config, duration_seconds, attributes)
    config.save()
    return True


@metrics_debug.wrapped_exception
def record_user_action_entry(
    user_action: protocol_models.UserAction,
    *,
    source: str,
    config: typing.Optional[configuration.Configuration] = None,
    now: typing.Optional[float] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_user_action_entry",
            reason="no_enabled_config",
        )
        return
    emit_now = time.time() if now is None else now
    _emit_once(
        resolved_config,
        metric_definitions.ExternalInterfaceConnectedAttributes(source=source),
        now=emit_now,
    )
    if not _is_account_create_user_action(user_action):
        return
    is_simulated = _get_account_create_is_simulated(user_action)
    _emit_once(
        resolved_config,
        metric_definitions.FirstAccountCreateAttemptAttributes(
            is_simulated=is_simulated,
            source=source,
        ),
        milestone_key=f"{commons_enums.MetricEvents.FIRST_ACCOUNT_CREATE_ATTEMPT.value}:{is_simulated}",
        now=emit_now,
    )


@metrics_debug.wrapped_exception
def record_wallet_configured(
    *,
    config: typing.Optional[configuration.Configuration] = None,
    now: typing.Optional[float] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_wallet_configured",
            reason="no_enabled_config",
        )
        return
    emit_now = time.time() if now is None else now
    state = get_onboarding_state(resolved_config)
    if state.wallet_configured_at is None:
        state.wallet_configured_at = emit_now
    _emit_once(
        resolved_config,
        metric_definitions.NodeWalletConfiguredAttributes(),
        now=emit_now,
    )


def record_first_automation_started(
    config: configuration.Configuration,
    strategy: protocol_models.Strategy,
    *,
    now: typing.Optional[float] = None,
) -> None:
    emit_now = time.time() if now is None else now
    octobot_kind, flow_subtype = classify_octobot_kind(strategy)
    state = get_onboarding_state(config)
    if state.first_automation_started_at is None:
        state.first_automation_started_at = emit_now
    _emit_once(
        config,
        metric_definitions.FirstAutomationStartedAttributes(
            octobot_kind=octobot_kind,
            flow_subtype=flow_subtype,
        ),
        now=emit_now,
    )
    _set_onboarding_complete(config)
    config.save()


def evaluate_stuck_no_external_interface(
    config: configuration.Configuration,
    now: float,
) -> None:
    if is_onboarding_complete(config):
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_stuck_no_external_interface",
            reason="onboarding_complete",
        )
        return
    if is_milestone_set(config, commons_enums.MetricEvents.EXTERNAL_INTERFACE_CONNECTED):
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_stuck_no_external_interface",
            reason="milestone_already_set",
        )
        return
    wallet_configured_at = get_onboarding_state(config).wallet_configured_at
    if wallet_configured_at is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_stuck_no_external_interface",
            reason="wallet_not_configured",
        )
        return
    if now - wallet_configured_at < constants.METRICS_STUCK_NO_EXTERNAL_INTERFACE_DELAY_SECONDS:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_stuck_no_external_interface",
            reason="delay_not_met",
        )
        return
    _emit_once(
        config,
        metric_definitions.StuckNoExternalInterfaceAttributes(),
        now=now,
    )


@metrics_debug.wrapped_exception
def run_stuck_no_external_interface_background_evaluator(
    config: configuration.Configuration,
) -> None:
    evaluate_stuck_no_external_interface(config, time.time())


def classify_octobot_kind(
    strategy: protocol_models.Strategy,
) -> tuple[metric_definitions.OctobotKind, typing.Optional[metric_definitions.FlowSubtypeValue]]:
    configuration_wrapper = strategy.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        return metric_definitions.OctobotKind.MANUAL, None
    inner_configuration = configuration_wrapper.actual_instance
    if isinstance(inner_configuration, protocol_models.GenericProcessConfiguration):
        return metric_definitions.OctobotKind.MANUAL, None
    if isinstance(inner_configuration, protocol_models.MarketMakingConfiguration):
        return metric_definitions.OctobotKind.MARKET_MAKING, None
    if isinstance(inner_configuration, protocol_models.CopyConfiguration):
        return metric_definitions.OctobotKind.FLOW, metric_definitions.FlowSubtype.COPY
    if isinstance(inner_configuration, protocol_models.SignalBotConfiguration):
        return metric_definitions.OctobotKind.FLOW, metric_definitions.FlowSubtype.SIGNAL_BOT
    if isinstance(inner_configuration, protocol_models.GenericWorkflowConfiguration):
        return metric_definitions.OctobotKind.FLOW, metric_definitions.FlowSubtype.AI_AGENTS
    if isinstance(inner_configuration, protocol_models.TradingTentaclesConfiguration):
        tentacle_name = inner_configuration.name or ""
        if not tentacle_name:
            return metric_definitions.OctobotKind.FLOW, metric_definitions.FlowSubtype.OTHER
        return metric_definitions.OctobotKind.FLOW, tentacle_name
    return metric_definitions.OctobotKind.FLOW, metric_definitions.FlowSubtype.OTHER


def resolve_account_exchange_name(
    checked_account: protocol_models.Account,
    user_id: str,
) -> str:
    specifics = checked_account.specifics
    if specifics is None or specifics.actual_instance is None:
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    exchange_account = specifics.actual_instance
    if not isinstance(exchange_account, protocol_models.ExchangeAccount):
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    config_ids = exchange_account.exchange_config_ids or []
    if not config_ids:
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    try:
        exchange_config = collection_providers.AccountProvider.instance().get_exchange_config(
            user_id,
            config_ids[0],
        )
    except collection_errors.CollectionNoDataError:
        return constants.METRICS_GENERIC_EXCHANGE_NAME
    exchange_type = protocol_trading_mapping.TRADING_TYPE_TO_EXCHANGE_TYPE.get(
        protocol_models.TradingType.SPOT
    )
    if exchange_type is None:
        return exchange_config.exchange
    return exchange_config.exchange


def _is_account_create_user_action(user_action: protocol_models.UserAction) -> bool:
    configuration_wrapper = user_action.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        return False
    return isinstance(configuration_wrapper.actual_instance, protocol_models.CreateAccountConfiguration)


def _get_account_create_is_simulated(user_action: protocol_models.UserAction) -> bool:
    configuration_wrapper = user_action.configuration
    if configuration_wrapper is None or configuration_wrapper.actual_instance is None:
        return False
    payload = configuration_wrapper.actual_instance
    if not isinstance(payload, protocol_models.CreateAccountConfiguration):
        return False
    return bool(payload.configuration.is_simulated)
