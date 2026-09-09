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

import octobot_protocol.models as protocol_models

import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.recording.accounts as accounts_module


ACTION_EVENT_MAP: dict[
    protocol_models.UserActionType,
    tuple[journal_events.NodeJournalEvent, journal_events.NodeJournalEvent | None],
] = {
    protocol_models.UserActionType.ACCOUNT_AUTH_CREATE: (
        journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_ATTEMPT,
        journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_FAILED,
    ),
    protocol_models.UserActionType.ACCOUNT_CREATE: (
        journal_events.NodeJournalEvent.ACCOUNT_CREATE_ATTEMPT,
        None,
    ),
    protocol_models.UserActionType.ACCOUNT_EDIT: (
        journal_events.NodeJournalEvent.ACCOUNT_EDIT_ATTEMPT,
        journal_events.NodeJournalEvent.ACCOUNT_EDIT_FAILED,
    ),
    protocol_models.UserActionType.STRATEGY_CREATE: (
        journal_events.NodeJournalEvent.STRATEGY_CREATE_ATTEMPT,
        journal_events.NodeJournalEvent.STRATEGY_CREATE_FAILED,
    ),
    protocol_models.UserActionType.STRATEGY_EDIT: (
        journal_events.NodeJournalEvent.STRATEGY_EDIT_ATTEMPT,
        journal_events.NodeJournalEvent.STRATEGY_EDIT_FAILED,
    ),
    protocol_models.UserActionType.AUTOMATION_CREATE: (
        journal_events.NodeJournalEvent.AUTOMATION_CREATE_ATTEMPT,
        journal_events.NodeJournalEvent.AUTOMATION_CREATE_FAILED,
    ),
    protocol_models.UserActionType.AUTOMATION_EDIT: (
        journal_events.NodeJournalEvent.AUTOMATION_EDIT_ATTEMPT,
        journal_events.NodeJournalEvent.AUTOMATION_EDIT_FAILED,
    ),
}


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


def _record_action_attempt(user_action: protocol_models.UserAction, *, source: str) -> None:
    action_type = _resolve_user_action_type(user_action)
    if action_type is None:
        return
    attempt_event, _failure_event = ACTION_EVENT_MAP.get(action_type, (None, None))
    if attempt_event is None:
        return
    journal_module.record(
        attempt_event,
        attributes=journal_models.JournalEventAttributes(
            user_action_id=user_action.id,
            source=source,
        ),
    )


def _record_typed_action_failure(
    user_action: protocol_models.UserAction,
    *,
    error: BaseException,
) -> None:
    action_type = _resolve_user_action_type(user_action)
    if action_type is None:
        return
    _attempt_event, failure_event = ACTION_EVENT_MAP.get(action_type, (None, None))
    if action_type == protocol_models.UserActionType.ACCOUNT_CREATE:
        accounts_module.record_account_validation_failed(
            is_simulated=False,
            exchange_name=None,
            error=error,
            user_action_id=user_action.id,
        )
        return
    if failure_event is None:
        return
    journal_module.record_failure(
        failure_event,
        error=error,
        attributes=journal_models.JournalEventAttributes(user_action_id=user_action.id),
    )


def _resolve_user_action_type(
    user_action: protocol_models.UserAction,
) -> protocol_models.UserActionType | None:
    configuration = user_action.configuration
    if configuration is None or configuration.actual_instance is None:
        return None
    return configuration.actual_instance.action_type
