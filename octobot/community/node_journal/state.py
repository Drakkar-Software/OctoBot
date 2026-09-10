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
import uuid

import octobot_commons.configuration as configuration
import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot.community.node_journal.constants as journal_constants


@dataclasses.dataclass
class JournalPersistedState:
    install_id: str
    onboarding_started_at: float | None = None
    first_automation_started_at: float | None = None
    connection_sequence: int = 0
    last_user_data_pull_at: float | None = None
    onboarding_complete: bool = False
    tracked_automation_ids: list[str] = dataclasses.field(default_factory=list)


_session_id: str | None = None
_persisted_state: JournalPersistedState | None = None
_config: configuration.Configuration | None = None


def _get_journal_section(config: configuration.Configuration) -> dict:
    journal_section = config.config.setdefault(journal_constants.CONFIG_JOURNAL_SECTION, {})
    if not isinstance(journal_section, dict):
        raise ValueError(f"{journal_constants.CONFIG_JOURNAL_SECTION} must be a mapping in config")
    return journal_section


def bind_config(config: configuration.Configuration | None) -> None:
    global _config, _persisted_state
    _config = config
    _persisted_state = None


def get_config() -> configuration.Configuration | None:
    return _config


def get_session_id() -> str:
    global _session_id
    if _session_id is None:
        _session_id = str(uuid.uuid4())
    return _session_id


def reset_session_id() -> str:
    global _session_id
    _session_id = str(uuid.uuid4())
    return _session_id


def get_journal_directory() -> str:
    return user_root_folder_provider.get_user_root_folder() + f"/{journal_constants.JOURNAL_DIR_NAME}"


def load_persisted_state(config: configuration.Configuration | None = None) -> JournalPersistedState:
    global _persisted_state
    resolved_config = config if config is not None else _config
    if resolved_config is None:
        if _persisted_state is not None:
            return _persisted_state
        _persisted_state = JournalPersistedState(install_id=str(uuid.uuid4()))
        return _persisted_state
    if _persisted_state is not None and config is None:
        return _persisted_state
    journal_section = _get_journal_section(resolved_config)
    stored_install_id = journal_section.get(journal_constants.CONFIG_INSTALL_ID)
    if not stored_install_id:
        stored_install_id = str(uuid.uuid4())
        journal_section[journal_constants.CONFIG_INSTALL_ID] = stored_install_id
        if journal_section.get(journal_constants.CONFIG_ONBOARDING_STARTED_AT) is None:
            journal_section[journal_constants.CONFIG_ONBOARDING_STARTED_AT] = time.time()
        resolved_config.save()
    _persisted_state = JournalPersistedState(
        install_id=str(stored_install_id),
        onboarding_started_at=_optional_float(journal_section.get(journal_constants.CONFIG_ONBOARDING_STARTED_AT)),
        first_automation_started_at=_optional_float(
            journal_section.get(journal_constants.CONFIG_FIRST_AUTOMATION_STARTED_AT)
        ),
        connection_sequence=int(journal_section.get(journal_constants.CONFIG_CONNECTION_SEQUENCE, 0) or 0),
        last_user_data_pull_at=_optional_float(journal_section.get(journal_constants.CONFIG_LAST_USER_DATA_PULL_AT)),
        onboarding_complete=journal_section.get(journal_constants.CONFIG_FIRST_AUTOMATION_STARTED_AT) is not None,
        tracked_automation_ids=list(journal_section.get(journal_constants.CONFIG_TRACKED_AUTOMATION_IDS, []) or []),
    )
    return _persisted_state


def save_persisted_state(state: JournalPersistedState, config: configuration.Configuration | None = None) -> None:
    global _persisted_state
    resolved_config = config if config is not None else _config
    if resolved_config is None:
        _persisted_state = state
        return
    journal_section = _get_journal_section(resolved_config)
    journal_section[journal_constants.CONFIG_INSTALL_ID] = state.install_id
    if state.onboarding_started_at is not None:
        journal_section[journal_constants.CONFIG_ONBOARDING_STARTED_AT] = state.onboarding_started_at
    if state.first_automation_started_at is not None:
        journal_section[journal_constants.CONFIG_FIRST_AUTOMATION_STARTED_AT] = state.first_automation_started_at
    journal_section[journal_constants.CONFIG_CONNECTION_SEQUENCE] = state.connection_sequence
    if state.last_user_data_pull_at is not None:
        journal_section[journal_constants.CONFIG_LAST_USER_DATA_PULL_AT] = state.last_user_data_pull_at
    journal_section[journal_constants.CONFIG_TRACKED_AUTOMATION_IDS] = list(state.tracked_automation_ids)
    resolved_config.save()
    _persisted_state = state


def mark_first_automation_started(now: float | None = None) -> None:
    state = load_persisted_state()
    if state.first_automation_started_at is not None:
        return
    emit_now = time.time() if now is None else now
    state.first_automation_started_at = emit_now
    state.onboarding_complete = True
    save_persisted_state(state)


def _optional_float(value: typing.Any) -> float | None:
    if value is None:
        return None
    return float(value)
