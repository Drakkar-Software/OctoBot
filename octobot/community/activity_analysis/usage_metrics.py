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
import time
import typing

import octobot_commons.configuration as configuration
import octobot_commons.enums as commons_enums

import octobot_protocol.models as protocol_models
import octobot_sync.sync.collection_providers as collection_providers

import octobot.constants as constants
import octobot.community.activity_analysis.metric_definitions as metric_definitions
import octobot.community.activity_analysis.metrics_config as metrics_config
import octobot.community.activity_analysis.metrics_connector as metrics_connector
import octobot.community.activity_analysis.metrics_debug as metrics_debug
import octobot.community.activity_analysis.onboarding_metrics as onboarding_metrics
import octobot.community.authentication as community_authentication


def build_existing_config_snapshot() -> onboarding_metrics.ExistingConfigSnapshot:
    auth = community_authentication.CommunityAuthentication.instance()
    wallet_configured = auth is not None and auth.is_node_wallet_configured()
    wallet_user_ids: list[str] = []
    account_count = 0
    if wallet_configured:
        wallet_user_ids = list(
            collection_providers.AccountProvider.instance().list_collectable_wallet_ids()
        )
        for wallet_id in wallet_user_ids:
            account_count += len(
                collection_providers.AccountProvider.instance().list_accounts(wallet_id)
            )
    reconcile_automations_pending = wallet_configured or account_count > 0
    return onboarding_metrics.ExistingConfigSnapshot(
        wallet_configured=wallet_configured,
        wallet_user_ids=wallet_user_ids,
        account_count=account_count,
        distinct_automation_ids=[],
        reconcile_automations_pending=reconcile_automations_pending,
    )


@metrics_debug.wrapped_exception
def ensure_onboarding_state_for_config(
    config: typing.Optional[configuration.Configuration] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        return
    onboarding_metrics.ensure_onboarding_state_initialized(
        resolved_config,
        build_existing_config_snapshot(),
    )


@metrics_debug.wrapped_exception_async
async def complete_reconcile_automations(
    config: typing.Optional[configuration.Configuration] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        return
    state = onboarding_metrics.get_onboarding_state(resolved_config)
    if not state.reconcile_automations_pending:
        return
    # Lazy import: octobot_node.scheduler pulls octobot_flow → octobot.community (circular at import time).
    import octobot_node.scheduler as scheduler_module
    import octobot_node.scheduler.automations.automation_states_loader as automation_states_loader

    if not scheduler_module.is_initialized():
        metrics_debug.log_activity(
            "reconcile_skipped",
            reason="scheduler_not_initialized",
        )
        return

    automation_ids: set[str] = set()
    for wallet_id in collection_providers.AccountProvider.instance().list_collectable_wallet_ids():
        automation_states = await automation_states_loader.load_protocol_automation_states(
            wallet_id,
            statuses=None,
        )
        automation_ids.update(_distinct_automation_ids_from_states(automation_states))
    onboarding_metrics.apply_reconciled_automations(resolved_config, sorted(automation_ids))


def _distinct_automation_ids_from_states(
    automation_states: list[protocol_models.AutomationState],
) -> list[str]:
    return sorted({
        automation_state.id
        for automation_state in automation_states
        if automation_state.id
    })


@metrics_debug.wrapped_exception
def record_node_process_start(
    distribution: str,
    *,
    was_new_install: bool,
    config: typing.Optional[configuration.Configuration] = None,
    now: typing.Optional[float] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_node_process_start",
            reason="no_enabled_config",
        )
        return
    emit_now = time.time() if now is None else now
    auth = community_authentication.CommunityAuthentication.instance()
    wallet_configured = auth is not None and auth.is_node_wallet_configured()
    ensure_onboarding_state_for_config(resolved_config)
    onboarding_metrics.ensure_onboarding_started_at(resolved_config, emit_now)

    state = onboarding_metrics.get_onboarding_state(resolved_config)
    reconciled_from_existing_config = state.reconciled_from_existing_config
    new_install_attribute = was_new_install and not reconciled_from_existing_config
    process_start_attributes = metric_definitions.NodeProcessStartAttributes(
        wallet_configured=wallet_configured,
        new_install=new_install_attribute,
        onboarding_complete=onboarding_metrics.is_onboarding_complete(resolved_config),
        distribution=distribution,
        version=constants.LONG_VERSION,
        reconciled=True if reconciled_from_existing_config else None,
    )
    metrics_connector.emit_count(resolved_config, process_start_attributes)
    evaluate_user_converted_24h_return(resolved_config, emit_now)
    resolved_config.save()


@metrics_debug.wrapped_exception
def evaluate_user_converted_24h_return(
    config: configuration.Configuration,
    now: float,
) -> None:
    if not onboarding_metrics.is_onboarding_complete(config):
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_user_converted_24h_return",
            reason="onboarding_not_complete",
        )
        return
    if onboarding_metrics.is_milestone_set(
        config,
        commons_enums.MetricEvents.USER_CONVERTED_24H_RETURN,
    ):
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_user_converted_24h_return",
            reason="milestone_already_set",
        )
        return

    state = onboarding_metrics.get_onboarding_state(config)
    if state.reconciled_from_existing_config:
        anchor_timestamp = state.onboarding_started_at
        conversion_path = metric_definitions.ConversionPath.RECONCILED
    else:
        anchor_timestamp = state.first_automation_started_at
        conversion_path = metric_definitions.ConversionPath.POST_ONBOARD
    if anchor_timestamp is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_user_converted_24h_return",
            reason="anchor_timestamp_missing",
        )
        return
    if now - anchor_timestamp < constants.METRICS_CONVERSION_DELAY_SECONDS:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="evaluate_user_converted_24h_return",
            reason="conversion_delay_not_met",
        )
        return

    return_delay_bucket = _return_delay_bucket(now - anchor_timestamp)
    metrics_connector.emit_count(
        config,
        metric_definitions.UserConverted24hReturnAttributes(
            conversion_path=conversion_path,
            return_delay_bucket=return_delay_bucket,
            onboarding_complete=True,
        ),
    )
    onboarding_metrics.set_milestone(
        config,
        commons_enums.MetricEvents.USER_CONVERTED_24H_RETURN,
    )
    config.save()


@metrics_debug.wrapped_exception
def record_account_validated(
    checked_account: protocol_models.Account,
    user_id: str,
    *,
    config: typing.Optional[configuration.Configuration] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_account_validated",
            reason="no_enabled_config",
        )
        return
    if checked_account.state is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_account_validated",
            reason="account_state_missing",
        )
        return
    if checked_account.state.status != protocol_models.AccountStatus.VALID:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_account_validated",
            reason="account_not_valid",
        )
        return
    exchange_name = onboarding_metrics.resolve_account_exchange_name(checked_account, user_id)
    metrics_connector.emit_count(
        resolved_config,
        metric_definitions.AccountValidatedAttributes(
            is_simulated=checked_account.is_simulated,
            exchange_name=exchange_name,
        ),
    )


@metrics_debug.wrapped_exception
def record_new_automation_created(
    automation_id: str,
    strategy: protocol_models.Strategy,
    *,
    config: typing.Optional[configuration.Configuration] = None,
    now: typing.Optional[float] = None,
) -> None:
    resolved_config = metrics_config.resolve_enabled_config(config)
    if resolved_config is None:
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_new_automation_created",
            reason="no_enabled_config",
        )
        return
    state = onboarding_metrics.get_onboarding_state(resolved_config)
    if automation_id in state.get_tracked_automation_ids():
        metrics_debug.log_activity(
            "hook_skipped",
            hook="record_new_automation_created",
            reason="duplicate_automation_id",
            automation_id=automation_id,
        )
        return
    emit_now = time.time() if now is None else now
    distinct_automation_count = state.distinct_automation_count + 1
    state.distinct_automation_count = distinct_automation_count
    state.add_tracked_automation_id(automation_id)

    if distinct_automation_count == 1:
        onboarding_metrics.record_first_automation_started(
            resolved_config,
            strategy,
            now=emit_now,
        )
    else:
        onboarding_metrics.set_distinct_automation_count(resolved_config, distinct_automation_count)

    if distinct_automation_count <= 5 or distinct_automation_count % 5 == 0:
        octobot_kind, flow_subtype = onboarding_metrics.classify_octobot_kind(strategy)
        metrics_connector.emit_count(
            resolved_config,
            metric_definitions.AutomationStartedAttributes(
                automation_count=distinct_automation_count,
                octobot_kind=octobot_kind,
                flow_subtype=flow_subtype,
            ),
        )
    resolved_config.save()


def _return_delay_bucket(delay_seconds: float) -> metric_definitions.ReturnDelayBucket:
    delay_hours = delay_seconds / 3600
    if delay_hours < 48:
        return metric_definitions.ReturnDelayBucket.HOURS_24_TO_48
    if delay_hours < 168:
        return metric_definitions.ReturnDelayBucket.DAYS_2_TO_7
    return metric_definitions.ReturnDelayBucket.DAYS_7_PLUS
