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
import logging
import os
import time
import typing
import uuid

import octobot_commons.configuration as configuration
import octobot_commons.json_util as json_util
import octobot_commons.user_root_folder_provider as user_root_folder_provider

import octobot.community.node_journal.constants as journal_constants
import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.journal as journal_module

logger = logging.getLogger(__name__)


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
        logger.error(
            "%s must be a mapping in config",
            journal_constants.CONFIG_JOURNAL_SECTION,
        )
        return {}
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
    user_root = user_root_folder_provider.get_user_root_folder()
    return os.path.join(user_root, journal_constants.JOURNAL_DIR_NAME)


def _is_valid_manifest(manifest: typing.Any) -> bool:
    manifest_field = journal_enums.JournalManifestField
    if not isinstance(manifest, dict):
        return False
    if manifest.get(manifest_field.SCHEMA.value) != journal_constants.JOURNAL_SCHEMA_VERSION:
        return False
    install_id = manifest.get(manifest_field.INSTALL_ID.value)
    return isinstance(install_id, str) and bool(install_id)


def ensure_journal_manifest(journal_directory: str | None = None) -> dict:
    journal_dir = journal_directory or get_journal_directory()
    os.makedirs(journal_dir, exist_ok=True)
    manifest_path = os.path.join(journal_dir, journal_constants.MANIFEST_FILE_NAME)
    manifest = None
    if os.path.isfile(manifest_path):
        manifest = json_util.read_file(manifest_path, raise_errors=False, on_error_value={})
    if manifest is not None and _is_valid_manifest(manifest):
        return manifest
    logger.warning("Recreating journal manifest at %s", manifest_path)
    persisted_state = load_persisted_state()
    manifest_field = journal_enums.JournalManifestField
    recreated_manifest = {
        manifest_field.SCHEMA.value: journal_constants.JOURNAL_SCHEMA_VERSION,
        manifest_field.INSTALL_ID.value: persisted_state.install_id,
    }
    json_util.safe_dump(recreated_manifest, manifest_path)
    return recreated_manifest


def load_persisted_state(config: configuration.Configuration | None = None) -> JournalPersistedState:
    return journal_module.run_journal_operation(
        "load_persisted_state",
        lambda: _load_persisted_state(config),
        default=_default_persisted_state(),
    )


def save_persisted_state(state: JournalPersistedState, config: configuration.Configuration | None = None) -> None:
    journal_module.run_journal_operation(
        "save_persisted_state",
        lambda: _save_persisted_state(state, config),
        default=None,
    )


def mark_first_automation_started(now: float | None = None) -> None:
    journal_module.run_journal_operation(
        "mark_first_automation_started",
        lambda: _mark_first_automation_started(now),
        default=None,
    )


def _default_persisted_state() -> JournalPersistedState:
    global _persisted_state
    if _persisted_state is not None:
        return _persisted_state
    _persisted_state = JournalPersistedState(install_id=str(uuid.uuid4()))
    return _persisted_state


def _load_persisted_state(config: configuration.Configuration | None) -> JournalPersistedState:
    global _persisted_state
    resolved_config = config if config is not None else _config
    if resolved_config is None:
        return _default_persisted_state()
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


def _save_persisted_state(
    state: JournalPersistedState,
    config: configuration.Configuration | None = None,
) -> None:
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


def _mark_first_automation_started(now: float | None) -> None:
    state = _load_persisted_state(None)
    if state.first_automation_started_at is not None:
        return
    emit_now = time.time() if now is None else now
    state.first_automation_started_at = emit_now
    state.onboarding_complete = True
    _save_persisted_state(state)


def duration_since_install_start(now: float | None = None) -> float | None:
    persisted_state = load_persisted_state()
    if persisted_state.onboarding_started_at is None:
        return None
    emit_now = time.time() if now is None else now
    return round(max(0.0, emit_now - persisted_state.onboarding_started_at), 3)


def _optional_float(value: typing.Any) -> float | None:
    if value is None:
        return None
    return float(value)
