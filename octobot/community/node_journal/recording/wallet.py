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

import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.recording._utils as recording_utils


def record_wallet_setup_attempt(
    *,
    node_type: str,
    setup_method: journal_enums.WalletSetupMethod,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.WALLET_SETUP_ATTEMPT,
        attributes=journal_models.JournalEventAttributes(
            node_type=node_type,
            setup_method=recording_utils.enum_value(setup_method),
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
        failure_reason=recording_utils.enum_value(failure_reason),
    )
    if setup_method is not None:
        attributes.setup_method = recording_utils.enum_value(setup_method)
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
    attributes = journal_models.JournalEventAttributes(operation=recording_utils.enum_value(operation))
    if http_status is not None:
        attributes.http_status = http_status
    journal_module.record_failure(
        journal_events.NodeJournalEvent.WALLET_OPERATION_FAILED,
        error=error,
        attributes=attributes,
    )
