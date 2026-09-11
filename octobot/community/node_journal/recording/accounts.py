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
import octobot.community.node_journal.recording.classify as journal_classify


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


def record_account_deleted(
    *,
    account_id: str,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNT_DELETED,
        attributes=journal_models.JournalEventAttributes(
            account_id=account_id,
            user_action_id=user_action_id,
        ),
    )


def record_account_auth_deleted(
    *,
    exchange_name: str | None,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNT_AUTH_DELETED,
        attributes=journal_models.JournalEventAttributes(
            exchange_name=exchange_name,
            user_action_id=user_action_id,
        ),
    )


def record_accounts_refreshed(
    *,
    account_ids: list[str],
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.ACCOUNTS_REFRESHED,
        attributes=journal_models.JournalEventAttributes(
            account_ids=list(account_ids),
            user_action_id=user_action_id,
        ),
    )
