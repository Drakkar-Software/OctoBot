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

import logging

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.models as journal_models
import octobot.community.node_journal.state as journal_state

logger = logging.getLogger(__name__)


def _derive_onboarding_complete(
    event_timestamp: float,
    persisted_state: journal_state.JournalPersistedState,
) -> bool:
    cutoff = persisted_state.first_automation_started_at
    if cutoff is None:
        return False
    return event_timestamp > cutoff


def _log_missing_hydration_field(field_name: str, *, missing_data_warnings: set[str] | None) -> None:
    if missing_data_warnings is not None and field_name in missing_data_warnings:
        return
    logger.warning("Journal event hydration missing %s", field_name)
    if missing_data_warnings is not None:
        missing_data_warnings.add(field_name)


def hydrate_storage_event(
    raw: dict,
    ctx: dict,
    manifest: dict | None,
    persisted_state: journal_state.JournalPersistedState,
    *,
    missing_data_warnings: set[str] | None = None,
) -> journal_models.JournalEventLine:
    event_line_field = journal_enums.JournalEventLineField
    manifest_field = journal_enums.JournalManifestField
    context_field = journal_enums.JournalStorageContextField

    install_id = ""
    if isinstance(manifest, dict) and manifest.get(manifest_field.INSTALL_ID.value):
        install_id = str(manifest[manifest_field.INSTALL_ID.value])
    else:
        _log_missing_hydration_field(manifest_field.INSTALL_ID.value, missing_data_warnings=missing_data_warnings)

    session_id = ""
    if ctx.get(context_field.SESSION_ID.value):
        session_id = str(ctx[context_field.SESSION_ID.value])
    else:
        _log_missing_hydration_field(context_field.SESSION_ID.value, missing_data_warnings=missing_data_warnings)

    app_version = ""
    if ctx.get(context_field.APP_VERSION.value):
        app_version = str(ctx[context_field.APP_VERSION.value])
    else:
        _log_missing_hydration_field(context_field.APP_VERSION.value, missing_data_warnings=missing_data_warnings)

    event_timestamp = float(raw[event_line_field.TIMESTAMP.value])
    expanded_line = {
        event_line_field.EVENT.value: raw[event_line_field.EVENT.value],
        event_line_field.TIMESTAMP.value: event_timestamp,
        event_line_field.SESSION_ID.value: session_id,
        event_line_field.INSTALL_ID.value: install_id,
        event_line_field.APP_VERSION.value: app_version,
        event_line_field.DISTRIBUTION.value: journal_constants.DISTRIBUTION_NODE,
        event_line_field.ONBOARDING_COMPLETE.value: _derive_onboarding_complete(event_timestamp, persisted_state),
        event_line_field.ATTRIBUTES.value: raw.get(event_line_field.ATTRIBUTES.value),
        event_line_field.RECORDED.value: raw.get(event_line_field.RECORDED.value, True),
    }
    return journal_models.JournalEventLine.from_dict(expanded_line)
