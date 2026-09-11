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


def record_strategy_create_succeeded(
    *,
    strategy_id: str,
    strategy: protocol_models.Strategy | None = None,
    configuration_type: journal_enums.ConfigurationType | str | None = None,
    user_action_id: str | None = None,
) -> None:
    resolved_configuration_type = configuration_type
    if strategy is not None:
        resolved_configuration_type = journal_classify.configuration_type_from_strategy(strategy)
    journal_module.record(
        journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            strategy_id=strategy_id,
            configuration_type=recording_utils.enum_value(resolved_configuration_type),
            user_action_id=user_action_id,
        ),
    )


def record_strategy_edit_succeeded(
    *,
    strategy_id: str,
    strategy: protocol_models.Strategy | None = None,
    configuration_type: journal_enums.ConfigurationType | str | None = None,
    user_action_id: str | None = None,
) -> None:
    resolved_configuration_type = configuration_type
    if strategy is not None:
        resolved_configuration_type = journal_classify.configuration_type_from_strategy(strategy)
    journal_module.record(
        journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED,
        attributes=journal_models.JournalEventAttributes(
            strategy_id=strategy_id,
            configuration_type=recording_utils.enum_value(resolved_configuration_type),
            user_action_id=user_action_id,
        ),
    )
