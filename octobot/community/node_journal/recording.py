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

import enum
import time

import octobot_protocol.models as protocol_models

import octobot.community.node_journal.classify as journal_classify
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.state as journal_state
import octobot.community.node_journal.sync_session as sync_session_module


def _enum_value(value: enum.StrEnum) -> str:
    return value.value if isinstance(value, enum.StrEnum) else str(value)


def record_process_startup_succeeded(
    *,
    wallet_configured: bool,
    new_install: bool,
    reconciled: bool,
) -> None:
    sync_session_module.reset_sync_tracker_after_node_startup()
    journal_module.record(
        journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            wallet_configured=wallet_configured,
            new_install=new_install,
            reconciled=reconciled,
            duration_since_install_start=_duration_since_install_start(),
        ),
    )


def record_process_startup_failed(
    *,
    startup_phase: journal_enums.JournalStartupPhase,
    error: BaseException,
    force_exit: bool,
    wallet_configured: bool | None = None,
    new_install: bool | None = None,
    reconciled: bool | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        startup_phase=_enum_value(startup_phase),
        force_exit=force_exit,
    )
    if wallet_configured is not None:
        attributes.wallet_configured = wallet_configured
    if new_install is not None:
        attributes.new_install = new_install
    if reconciled is not None:
        attributes.reconciled = reconciled
    journal_module.record_failure(
        journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED,
        error=error,
        attributes=attributes,
    )


def record_wallet_setup_attempt(
    *,
    node_type: str,
    setup_method: journal_enums.WalletSetupMethod,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
        attributes=journal_models.JournalEventAttributes(
            node_type=node_type,
            setup_method=_enum_value(setup_method),
        ),
    )


def record_wallet_setup_succeeded() -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(configured=True),
    )


def record_wallet_setup_failed(
    *,
    http_status: int,
    failure_reason: journal_enums.WalletSetupFailureReason,
    error: BaseException | None = None,
    error_message: str | None = None,
    setup_method: journal_enums.WalletSetupMethod | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        http_status=http_status,
        failure_reason=_enum_value(failure_reason),
    )
    if setup_method is not None:
        attributes.setup_method = _enum_value(setup_method)
    journal_module.record_failure(
        journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
        error=error,
        error_message=error_message,
        attributes=attributes,
    )


def record_wallet_operation_failed(
    *,
    operation: journal_enums.WalletOperation,
    error: BaseException,
    http_status: int | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(operation=_enum_value(operation))
    if http_status is not None:
        attributes.http_status = http_status
    journal_module.record_failure(
        journal_events.NodeJournalEvent.WALLET_OPERATION_FAILED,
        error=error,
        attributes=attributes,
    )


def record_sync_read_failed(
    *,
    collection: str,
    failure_reason: journal_enums.SyncReadFailureReason,
    error: BaseException | None = None,
    error_message: str | None = None,
) -> None:
    journal_module.record_failure(
        journal_events.NodeJournalEvent.SYNC_READ_FAILED,
        error=error,
        error_message=error_message,
        attributes=journal_models.JournalEventAttributes(
            collection=collection,
            failure_reason=_enum_value(failure_reason),
        ),
    )


def record_external_action_received(
    user_action: protocol_models.UserAction,
    *,
    source: str,
) -> None:
    action_type = _resolve_user_action_type(user_action)
    journal_module.record(
        journal_events.NodeJournalEvent.EXTERNAL_ACTION_RECEIVED,
        attributes=journal_models.JournalEventAttributes(
            source=source,
            action_type=action_type.value if action_type is not None else "unknown",
            user_action_id=user_action.id,
        ),
    )
    _record_action_attempt(user_action, source=source)


def record_external_action_failed(
    user_action: protocol_models.UserAction,
    *,
    source: str,
    error: BaseException,
) -> None:
    action_type = _resolve_user_action_type(user_action)
    journal_module.record_failure(
        journal_events.NodeJournalEvent.EXTERNAL_ACTION_FAILED,
        error=error,
        attributes=journal_models.JournalEventAttributes(
            source=source,
            action_type=action_type.value if action_type is not None else "unknown",
            user_action_id=user_action.id,
        ),
    )
    _record_typed_action_failure(user_action, error=error)


def record_executor_failure(
    user_action: protocol_models.UserAction,
    *,
    error: BaseException,
) -> None:
    _record_typed_action_failure(user_action, error=error)


def record_account_validated_from_account(
    checked_account: protocol_models.Account,
    user_id: str,
    *,
    user_action_id: str | None = None,
) -> None:
    if checked_account.state is None or checked_account.state.status != protocol_models.AccountStatus.VALID:
        return
    exchange_name = journal_classify.resolve_account_exchange_name(checked_account, user_id)
    record_account_validated(
        account_id=checked_account.id or "",
        is_simulated=checked_account.is_simulated,
        exchange_name=exchange_name or "",
        user_action_id=user_action_id,
    )


def record_new_automation_created_from_strategy(
    automation_id: str,
    strategy: protocol_models.Strategy,
    *,
    user_action_id: str | None = None,
    source: str | None = None,
) -> None:
    persisted_state = journal_state.load_persisted_state()
    if automation_id in persisted_state.tracked_automation_ids:
        return
    octobot_kind, flow_subtype = journal_classify.classify_octobot_kind(strategy)
    is_first_automation = persisted_state.first_automation_started_at is None
    persisted_state.tracked_automation_ids.append(automation_id)
    journal_state.save_persisted_state(persisted_state)
    record_new_automation_created(
        automation_id=automation_id,
        automation_count=len(persisted_state.tracked_automation_ids),
        octobot_kind=octobot_kind.value,
        flow_subtype=flow_subtype,
        user_action_id=user_action_id,
        source=source,
        is_first_automation=is_first_automation,
    )


def record_account_validated(
    *,
    account_id: str = "",
    is_simulated: bool,
    exchange_name: str | None,
    user_action_id: str | None = None,
    account_count: int | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        account_id=account_id or None,
        is_simulated=is_simulated,
        exchange_name=exchange_name,
        user_action_id=user_action_id,
        account_count=account_count,
    )
    journal_module.record(journal_events.NodeJournalEvent.ACCOUNT_VALIDATED, attributes=attributes)


def record_account_validation_failed(
    *,
    is_simulated: bool,
    exchange_name: str | None,
    error: BaseException,
    user_action_id: str | None = None,
) -> None:
    journal_module.record_failure(
        journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED,
        error=error,
        attributes=journal_models.JournalEventAttributes(
            is_simulated=is_simulated,
            exchange_name=exchange_name,
            user_action_id=user_action_id,
        ),
    )


def record_first_automation_started(
    *,
    automation_id: str,
    octobot_kind: journal_enums.OctobotKind,
    flow_subtype: str | None,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED,
        attributes=journal_models.JournalEventAttributes(
            automation_id=automation_id,
            octobot_kind=_enum_value(octobot_kind),
            flow_subtype=flow_subtype,
            user_action_id=user_action_id,
            duration_since_install_start=_duration_since_install_start(),
        ),
    )


def record_automation_started(
    *,
    automation_id: str,
    automation_count: int,
    octobot_kind: journal_enums.OctobotKind,
    flow_subtype: str | None,
    source: str | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        automation_id=automation_id,
        automation_count=automation_count,
        octobot_kind=_enum_value(octobot_kind),
        flow_subtype=flow_subtype,
        source=source,
    )
    journal_module.record(journal_events.NodeJournalEvent.AUTOMATION_STARTED, attributes=attributes)


def record_new_automation_created(
    *,
    automation_id: str,
    automation_count: int,
    octobot_kind: journal_enums.OctobotKind,
    flow_subtype: str | None,
    user_action_id: str | None = None,
    source: str | None = None,
    is_first_automation: bool,
) -> None:
    if is_first_automation:
        record_first_automation_started(
            automation_id=automation_id,
            octobot_kind=octobot_kind,
            flow_subtype=flow_subtype,
            user_action_id=user_action_id,
        )
        return
    record_automation_started(
        automation_id=automation_id,
        automation_count=automation_count,
        octobot_kind=octobot_kind,
        flow_subtype=flow_subtype,
        source=source,
    )


def record_existing_config_detected(
    *,
    wallet_configured: bool,
    account_count: int,
    automation_count: int,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.EXISTING_CONFIG_DETECTED,
        attributes=journal_models.JournalEventAttributes(
            wallet_configured=wallet_configured,
            account_count=account_count,
            automation_count=automation_count,
        ),
    )


def record_reconcile_completed(*, automation_count: int) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.RECONCILE_COMPLETED,
        attributes=journal_models.JournalEventAttributes(automation_count=automation_count),
    )


def record_scheduler_init_failed(
    *,
    init_phase: journal_enums.JournalInitPhase,
    backend: journal_enums.JournalSchedulerBackend,
    error: BaseException,
) -> None:
    journal_module.record_failure(
        journal_events.NodeJournalEvent.SCHEDULER_INIT_FAILED,
        error=error,
        attributes=journal_models.JournalEventAttributes(
            init_phase=_enum_value(init_phase),
            backend=_enum_value(backend),
        ),
    )


def record_sync_storage_event(
    event: journal_events.NodeJournalEvent,
    *,
    collection: str,
    provider: journal_enums.SyncStorageProvider,
    error: BaseException | None = None,
    recovery_action: journal_enums.SyncStorageRecoveryAction | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        collection=collection,
        provider=_enum_value(provider),
        recovery_action=_enum_value(recovery_action) if recovery_action is not None else None,
    )
    if error is None:
        journal_module.record(event, attributes=attributes)
        return
    journal_module.record_failure(event, error=error, attributes=attributes)


def record_automation_run_errored(
    *,
    automation_id: str,
    error_status: str,
    error_origin: str,
    error: BaseException,
    retriable: bool,
) -> None:
    journal_module.record_failure(
        journal_events.NodeJournalEvent.AUTOMATION_RUN_ERRORED,
        error=error,
        attributes=journal_models.JournalEventAttributes(
            automation_id=automation_id,
            error_status=error_status,
            error_origin=error_origin,
            retriable=retriable,
        ),
    )


def _record_action_attempt(user_action: protocol_models.UserAction, *, source: str) -> None:
    action_type = _resolve_user_action_type(user_action)
    if action_type is None:
        return
    common_attributes = journal_models.JournalEventAttributes(
        user_action_id=user_action.id,
        source=source,
    )
    if action_type == protocol_models.UserActionType.ACCOUNT_AUTH_CREATE:
        journal_module.record(
            journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_ATTEMPT,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.ACCOUNT_CREATE:
        journal_module.record(
            journal_events.NodeJournalEvent.ACCOUNT_CREATE_ATTEMPT,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.ACCOUNT_EDIT:
        journal_module.record(
            journal_events.NodeJournalEvent.ACCOUNT_EDIT_ATTEMPT,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.STRATEGY_CREATE:
        journal_module.record(
            journal_events.NodeJournalEvent.STRATEGY_CREATE_ATTEMPT,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.STRATEGY_EDIT:
        journal_module.record(
            journal_events.NodeJournalEvent.STRATEGY_EDIT_ATTEMPT,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.AUTOMATION_CREATE:
        journal_module.record(
            journal_events.NodeJournalEvent.AUTOMATION_CREATE_ATTEMPT,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.AUTOMATION_EDIT:
        journal_module.record(
            journal_events.NodeJournalEvent.AUTOMATION_EDIT_ATTEMPT,
            attributes=common_attributes,
        )


def _record_typed_action_failure(
    user_action: protocol_models.UserAction,
    *,
    error: BaseException,
) -> None:
    action_type = _resolve_user_action_type(user_action)
    if action_type is None:
        return
    common_attributes = journal_models.JournalEventAttributes(user_action_id=user_action.id)
    if action_type == protocol_models.UserActionType.ACCOUNT_AUTH_CREATE:
        journal_module.record_failure(
            journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_FAILED,
            error=error,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.ACCOUNT_CREATE:
        record_account_validation_failed(
            is_simulated=False,
            exchange_name=None,
            error=error,
            user_action_id=user_action.id,
        )
    elif action_type == protocol_models.UserActionType.ACCOUNT_EDIT:
        journal_module.record_failure(
            journal_events.NodeJournalEvent.ACCOUNT_EDIT_FAILED,
            error=error,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.STRATEGY_CREATE:
        journal_module.record_failure(
            journal_events.NodeJournalEvent.STRATEGY_CREATE_FAILED,
            error=error,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.STRATEGY_EDIT:
        journal_module.record_failure(
            journal_events.NodeJournalEvent.STRATEGY_EDIT_FAILED,
            error=error,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.AUTOMATION_CREATE:
        journal_module.record_failure(
            journal_events.NodeJournalEvent.AUTOMATION_CREATE_FAILED,
            error=error,
            attributes=common_attributes,
        )
    elif action_type == protocol_models.UserActionType.AUTOMATION_EDIT:
        journal_module.record_failure(
            journal_events.NodeJournalEvent.AUTOMATION_EDIT_FAILED,
            error=error,
            attributes=common_attributes,
        )


def record_account_auth_create_succeeded(
    *,
    exchange_name: str | None,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            exchange_name=exchange_name,
            user_action_id=user_action_id,
        ),
    )


def record_strategy_create_succeeded(
    *,
    strategy_id: str,
    configuration_type: journal_enums.ConfigurationType,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            strategy_id=strategy_id,
            configuration_type=_enum_value(configuration_type),
            user_action_id=user_action_id,
        ),
    )


def record_strategy_edit_succeeded(
    *,
    strategy_id: str,
    configuration_type: journal_enums.ConfigurationType,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            strategy_id=strategy_id,
            configuration_type=_enum_value(configuration_type),
            user_action_id=user_action_id,
        ),
    )


def record_account_edit_succeeded(
    *,
    account_id: str,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNT_EDIT_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            account_id=account_id,
            user_action_id=user_action_id,
        ),
    )


def record_automation_stopped(
    *,
    automation_id: str,
    cancel_orders: bool,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.AUTOMATION_STOPPED,
        attributes=journal_models.JournalEventAttributes(
            automation_id=automation_id,
            cancel_orders=cancel_orders,
        ),
    )


def record_automation_restarted(
    *,
    automation_id: str,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.AUTOMATION_RESTARTED,
        attributes=journal_models.JournalEventAttributes(automation_id=automation_id),
    )


def record_automation_edit_succeeded(
    *,
    automation_id: str,
    octobot_kind: journal_enums.OctobotKind,
    flow_subtype: str | None,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.AUTOMATION_EDIT_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            automation_id=automation_id,
            octobot_kind=_enum_value(octobot_kind),
            flow_subtype=flow_subtype,
            user_action_id=user_action_id,
        ),
    )


def record_account_deleted(
    *,
    account_id: str,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNT_DELETED,
        attributes=journal_models.JournalEventAttributes(account_id=account_id),
    )


def record_account_auth_deleted(*, exchange_name: str | None) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNT_AUTH_DELETED,
        attributes=journal_models.JournalEventAttributes(exchange_name=exchange_name),
    )


def record_accounts_refreshed(
    *,
    account_ids: list[str],
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNTS_REFRESHED,
        attributes=journal_models.JournalEventAttributes(account_ids=list(account_ids)),
    )


def _duration_since_install_start(now: float | None = None) -> float | None:
    persisted_state = journal_state.load_persisted_state()
    if persisted_state.onboarding_started_at is None:
        return None
    emit_now = time.time() if now is None else now
    return round(max(0.0, emit_now - persisted_state.onboarding_started_at), 3)


def _resolve_user_action_type(
    user_action: protocol_models.UserAction,
) -> protocol_models.UserActionType | None:
    configuration = user_action.configuration
    if configuration is None or configuration.actual_instance is None:
        return None
    return configuration.actual_instance.action_type
