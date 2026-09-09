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

import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.journal as journal_module
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.recording._utils as recording_utils
import octobot.community.node_journal.recording.classify as journal_classify
import octobot.community.node_journal.state as journal_state


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
        octobot_kind=octobot_kind.value,
        flow_subtype=flow_subtype,
        user_action_id=user_action_id,
        source=source,
        is_first_automation=is_first_automation,
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
            octobot_kind=recording_utils.enum_value(octobot_kind),
            flow_subtype=flow_subtype,
            user_action_id=user_action_id,
            duration_since_install_start=journal_state.duration_since_install_start(),
        ),
    )


def record_automation_started(
    *,
    automation_id: str,
    octobot_kind: journal_enums.OctobotKind,
    flow_subtype: str | None,
    user_action_id: str | None = None,
    source: str | None = None,
) -> None:
    attributes = journal_models.JournalEventAttributes(
        automation_id=automation_id,
        octobot_kind=recording_utils.enum_value(octobot_kind),
        flow_subtype=flow_subtype,
        user_action_id=user_action_id,
        source=source,
    )
    journal_module.record(journal_events.NodeJournalEvent.AUTOMATION_STARTED, attributes=attributes)


def record_new_automation_created(
    *,
    automation_id: str,
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
        octobot_kind=octobot_kind,
        flow_subtype=flow_subtype,
        user_action_id=user_action_id,
        source=source,
    )


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


def record_automation_stopped(
    *,
    automation_id: str,
    cancel_orders: bool,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.AUTOMATION_STOPPED,
        attributes=journal_models.JournalEventAttributes(
            automation_id=automation_id,
            cancel_orders=cancel_orders,
            user_action_id=user_action_id,
        ),
    )


def record_automation_restarted(
    *,
    automation_id: str,
    user_action_id: str | None = None,
) -> None:
    journal_module.record(
        journal_events.NodeJournalEvent.AUTOMATION_RESTARTED,
        attributes=journal_models.JournalEventAttributes(
            automation_id=automation_id,
            user_action_id=user_action_id,
        ),
    )
