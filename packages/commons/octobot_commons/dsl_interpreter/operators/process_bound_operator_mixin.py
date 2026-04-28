#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import asyncio
import pathlib
import subprocess
import time
import typing

import octobot_commons.dsl_interpreter.operator as dsl_interpreter_operator
import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging
import octobot_commons.process_util as process_util


class ProcessBoundOperatorMixin:
    """
    Identifies operators that are bound to an external process, and provides
    portable helpers for spawning and stopping that process (no app-specific naming).
    """

    def __init__(self) -> None:
        """``pid`` is set when a bound child process identifier becomes available."""
        self.pid: typing.Optional[int] = None

    def is_process_running(self) -> bool:
        """Best-effort: whether ``self.pid`` refers to a running OS process."""
        if self.pid is None:
            return False
        return process_util.pid_is_running(self.pid)

    def request_graceful_stop(
        self,
        *,
        logger: typing.Optional[typing.Any] = None,
    ) -> dict[str, typing.Any]:
        """Ask the bound process (``SIGTERM`` when available) to terminate."""
        if self.pid is None:
            raise commons_errors.DSLInterpreterError(
                "No process id set; cannot request graceful stop."
            )
        return process_util.request_graceful_stop_via_sigterm(self.pid, logger=logger)

    async def wait_until_pid_stopped(
        self,
        pid: int,
        *,
        logger: typing.Optional[typing.Any] = None,
        timeout_seconds: float,
        poll_interval: float = 0.2,
    ) -> None:
        """Poll until ``pid`` is gone or ``timeout_seconds`` elapses (after e.g. SIGTERM)."""
        resolved_logger = logger or commons_logging.get_logger(self.__class__.__name__)
        if pid <= 0:
            resolved_logger.info(
                "wait_until_pid_stopped: pid=%s treated as already stopped (non-positive)",
                pid,
            )
            return
        resolved_logger.info(
            "wait_until_pid_stopped: waiting for pid=%s to exit (timeout=%ss)",
            pid,
            timeout_seconds,
        )
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if not process_util.pid_is_running(pid):
                resolved_logger.info("wait_until_pid_stopped: pid=%s exited", pid)
                return
            await asyncio.sleep(poll_interval)
        raise commons_errors.DSLInterpreterError(
            f"Timed out after {timeout_seconds}s waiting for pid={pid} to exit."
        )

    def spawn_subprocess(
        self,
        argv: list[str],
        *,
        working_directory: str,
        environment: typing.Optional[typing.Mapping[str, str]] = None,
        hide_console_window: bool = False,
    ) -> subprocess.Popen:
        """Launch a child process without a shell (see :func:`process_util.spawn_managed_subprocess`)."""
        proc = process_util.spawn_managed_subprocess(
            argv,
            working_directory=working_directory,
            environment=environment,
            hide_console_window=hide_console_window,
        )
        self.pid = proc.pid
        return proc

    @staticmethod
    def reject_user_path_segment(path_value: str) -> None:
        """Reject obvious path traversal in user-supplied relative paths."""
        if ".." in pathlib.PurePath(path_value).parts:
            raise commons_errors.DSLInterpreterError(
                "Invalid path: parent directory segments are not allowed."
            )

    @staticmethod
    def bind_address_for_env_and_probe_hosts(
        params: dict,
        bind_listen_key: str = "bind_host",
    ) -> tuple[str, str]:
        """
        Effective bind/listen address from ``params``, and the host to use for local
        port checks (``0.0.0.0`` is probed via loopback).
        """
        resolved_bind = params.get(bind_listen_key) or "127.0.0.1"
        probe_bind = "127.0.0.1" if resolved_bind == "0.0.0.0" else resolved_bind
        return resolved_bind, probe_bind

    @staticmethod
    def spawn_managed_subprocess(
        argv: list[str],
        *,
        working_directory: str,
        environment: typing.Optional[typing.Mapping[str, str]] = None,
        hide_console_window: bool = False,
    ) -> subprocess.Popen:
        """
        Launch a child process without a shell (``creationflags``: hide console on Windows when asked).
        """
        return process_util.spawn_managed_subprocess(
            argv,
            working_directory=working_directory,
            environment=environment,
            hide_console_window=hide_console_window,
        )


def is_process_bound(operator: dsl_interpreter_operator.Operator) -> bool:
    """
    Check if the operator is bound to an external process.
    """
    return isinstance(operator, ProcessBoundOperatorMixin)
