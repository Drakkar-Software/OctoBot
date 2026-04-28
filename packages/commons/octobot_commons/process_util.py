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

import os
import signal
import subprocess
import sys
import typing

import octobot_commons.errors as commons_errors
import octobot_commons.logging as commons_logging

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore


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
    resolved_env = dict(environment) if environment is not None else os.environ.copy()
    creationflags = subprocess.CREATE_NO_WINDOW if (hide_console_window and sys.platform == "win32") else 0
    return subprocess.Popen(
        argv,
        cwd=working_directory,
        env=resolved_env,
        creationflags=creationflags,
    )


def pid_is_running(pid: int) -> bool:
    """Best-effort: whether ``pid`` denotes a running OS process."""
    if pid <= 0:
        return False
    if psutil is not None:
        try:
            return psutil.Process(pid).is_running()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            return True
    return pid > 0


def request_graceful_stop_via_sigterm(
    pid: int,
    *,
    logger: typing.Optional[typing.Any] = None,
) -> dict[str, typing.Any]:
    """
    Ask the subprocess identified by ``pid`` to terminate (``SIGTERM`` when available).

    Returns a small dict with ``status`` and optional ``reason`` / ``signal`` keys.
    """
    resolved_logger = logger or commons_logging.get_logger(__name__)
    if pid <= 0:
        raise commons_errors.DSLInterpreterError(
            "Invalid pid for graceful stop via SIGTERM."
        )
    sigterm = getattr(signal, "SIGTERM", None)
    if sigterm is None:
        raise commons_errors.DSLInterpreterError(
            "SIGTERM is not available on this platform."
        )
    if not pid_is_running(pid):
        resolved_logger.info(
            "Graceful stop: pid=%s not running, treating as already stopped",
            pid,
        )
        return {"status": "already_stopped", "reason": "not_running"}
    try:
        os.kill(pid, sigterm)
    except OSError as err:
        if not pid_is_running(pid):
            resolved_logger.info(
                "Graceful stop: pid=%s gone after failed signal: %s",
                pid,
                err,
            )
            return {"status": "already_stopped", "reason": str(err)}
        resolved_logger.warning(
            "Graceful stop: failed to signal pid=%s: %s", pid, err
        )
        raise commons_errors.DSLInterpreterError(
            f"Failed to send stop signal to pid={pid}: {err}"
        ) from err
    resolved_logger.info("Sent graceful stop signal (sigterm) to pid=%s", pid)
    return {"status": "stopped", "signal": "sigterm"}
