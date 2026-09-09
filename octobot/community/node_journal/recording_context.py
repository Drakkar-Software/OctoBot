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

import contextlib
import typing

import octobot.community.node_journal.enums as journal_enums
import octobot.community.node_journal.events as journal_events
import octobot.community.node_journal.recording as journal_recording


class scheduler_init_phase(contextlib.AbstractContextManager):
    def __init__(
        self,
        *,
        init_phase: journal_enums.JournalInitPhase,
        backend: journal_enums.JournalSchedulerBackend,
        on_failure: typing.Callable[..., None],
    ) -> None:
        self._init_phase = init_phase
        self._backend = backend
        self._on_failure = on_failure

    def __exit__(self, exc_type, exc, traceback) -> bool:
        del traceback
        if exc is not None and exc_type is not None:
            self._on_failure(
                init_phase=self._init_phase,
                backend=self._backend,
                error=exc,
            )
        return False


class sync_read_operation(contextlib.AbstractContextManager):
    def __init__(
        self,
        *,
        resolve_collection: typing.Callable[[], str],
        resolve_failure_reason: typing.Callable[[BaseException], str],
    ) -> None:
        self._resolve_collection = resolve_collection
        self._resolve_failure_reason = resolve_failure_reason

    def __exit__(self, exc_type, exc, traceback) -> bool:
        del traceback
        if exc is not None and exc_type is not None:
            journal_recording.record_sync_read_failed(
                collection=self._resolve_collection(),
                failure_reason=self._resolve_failure_reason(exc),
                error=exc,
            )
        return False


class sync_storage_error(contextlib.AbstractContextManager):
    def __init__(
        self,
        *,
        event: journal_events.NodeJournalEvent,
        collection: str,
        provider: journal_enums.SyncStorageProvider = journal_enums.SyncStorageProvider.LOCAL,
        recovery_action: journal_enums.SyncStorageRecoveryAction | None = None,
    ) -> None:
        self._event = event
        self._collection = collection
        self._provider = provider
        self._recovery_action = recovery_action

    def __exit__(self, exc_type, exc, traceback) -> bool:
        del traceback
        if exc is not None and exc_type is not None:
            journal_recording.record_sync_storage_event(
                self._event,
                collection=self._collection,
                provider=self._provider,
                error=exc,
                recovery_action=self._recovery_action,
            )
        return False


def raise_wallet_setup_http_error(
    *,
    http_status: int,
    failure_reason: journal_enums.WalletSetupFailureReason,
    setup_method: journal_enums.WalletSetupMethod,
    detail: str,
    error: BaseException | None = None,
    error_message: str | None = None,
) -> typing.NoReturn:
    journal_recording.record_wallet_setup_failed(
        http_status=http_status,
        failure_reason=failure_reason,
        error=error,
        error_message=error_message,
        setup_method=setup_method,
    )
    from fastapi import HTTPException
    raise HTTPException(status_code=http_status, detail=detail) from error


def node_api_startup_failure(
    *,
    error: BaseException,
    startup_phase: journal_enums.JournalStartupPhase,
    force_exit: bool,
    config,
    scheduler_init_failure_was_recorded: typing.Callable[[], bool],
    record_node_startup_failed: typing.Callable[..., None],
) -> None:
    if scheduler_init_failure_was_recorded():
        return
    record_node_startup_failed(
        error,
        startup_phase=startup_phase,
        force_exit=force_exit,
        config=config,
    )