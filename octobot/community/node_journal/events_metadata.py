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

import octobot.community.node_journal.events as journal_events

FUNNEL_STEP_ORDER: tuple[journal_events.NodeJournalEvent, ...] = (
    journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_SUCCEEDED,
    journal_events.NodeJournalEvent.NODE_PROCESS_STARTUP_FAILED,
    journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
    journal_events.NodeJournalEvent.WALLET_SETUP_FAILED,
    journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
    journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_SUCCEEDED,
    journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_FAILED,
    journal_events.NodeJournalEvent.ACCOUNT_VALIDATED,
    journal_events.NodeJournalEvent.ACCOUNT_VALIDATION_FAILED,
    journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED,
    journal_events.NodeJournalEvent.STRATEGY_CREATE_FAILED,
    journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED,
    journal_events.NodeJournalEvent.STRATEGY_EDIT_FAILED,
    journal_events.NodeJournalEvent.AUTOMATION_CREATE_ATTEMPT,
    journal_events.NodeJournalEvent.AUTOMATION_CREATE_FAILED,
    journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED,
)

FUNNEL_STEP_RANK = {event: index for index, event in enumerate(FUNNEL_STEP_ORDER)}

JOURNEY_MILESTONE_LABELS: dict[journal_events.NodeJournalEvent, str] = {
    journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED: "wallet_setup",
    journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED: "external_connect",
    journal_events.NodeJournalEvent.ACCOUNT_VALIDATED: "account_validated",
    journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED: "strategy_create",
    journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED: "strategy_edit",
    journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED: "first_automation",
}

JOURNEY_MILESTONE_LABEL_ORDER: tuple[str, ...] = tuple(
    JOURNEY_MILESTONE_LABELS[event]
    for event in FUNNEL_STEP_ORDER
    if event in JOURNEY_MILESTONE_LABELS
)

JOURNEY_SUCCESS_EVENTS = frozenset({
    journal_events.NodeJournalEvent.WALLET_SETUP_SUCCEEDED,
    journal_events.NodeJournalEvent.EXTERNAL_INTERFACE_CONNECTED,
    journal_events.NodeJournalEvent.ACCOUNT_AUTH_CREATE_SUCCEEDED,
    journal_events.NodeJournalEvent.ACCOUNT_VALIDATED,
    journal_events.NodeJournalEvent.STRATEGY_CREATE_SUCCEEDED,
    journal_events.NodeJournalEvent.STRATEGY_EDIT_SUCCEEDED,
    journal_events.NodeJournalEvent.FIRST_AUTOMATION_STARTED,
    journal_events.NodeJournalEvent.AUTOMATION_CREATE_ATTEMPT,
})
