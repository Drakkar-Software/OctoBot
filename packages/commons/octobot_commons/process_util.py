# pylint: disable=C0415,R1732
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
import os
import signal
import subprocess
import sys
import time
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
    forward_terminal_output: bool = False,
) -> subprocess.Popen:
    """
    Launch a child process without a shell (``creationflags``: hide console on Windows when asked).

    When ``forward_terminal_output`` is True, the child inherits the parent stdout/stderr (live terminal
    output). On Windows, ``hide_console_window`` is ignored in that case: ``CREATE_NO_WINDOW`` would
    detach console output and hide logs even when streams are inherited.

    When ``forward_terminal_output`` is False, stdout and stderr are discarded (``subprocess.DEVNULL``).
    """
    resolved_env = dict(environment) if environment is not None else os.environ.copy()
    use_hidden_console = (
        hide_console_window and sys.platform == "win32" and not forward_terminal_output
    )
    # subprocess.CREATE_NO_WINDOW exists only on Windows; tests may patch platform on Linux CI.
    creationflags = (
        getattr(subprocess, "CREATE_NO_WINDOW", 0) if use_hidden_console else 0
    )
    if forward_terminal_output:
        child_stdout: typing.Optional[int] = None
        child_stderr: typing.Optional[int] = None
    else:
        child_stdout = subprocess.DEVNULL
        child_stderr = subprocess.DEVNULL
    proc = subprocess.Popen(
        argv,
        cwd=working_directory,
        env=resolved_env,
        creationflags=creationflags,
        stdout=child_stdout,
        stderr=child_stderr,
    )
    import octobot_commons.managed_child_process_registry as managed_child_process_registry
    managed_child_process_registry.ManagedChildProcessRegistry.instance().register(proc.pid)
    return proc


def pid_is_running(pid: int) -> bool: # pylint: disable=too-many-return-statements
    """Best-effort: whether ``pid`` denotes a running OS process (zombies are treated as not running)."""
    if pid <= 0:
        return False
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return True
    try:
        if proc.status() == psutil.STATUS_ZOMBIE:
            return False
    except psutil.ZombieProcess:
        return False
    except psutil.NoSuchProcess:
        # PID can disappear between Process() creation and status() (e.g. SIGTERM on Windows).
        return False
    try:
        return proc.is_running()
    except psutil.ZombieProcess:
        return False
    except psutil.NoSuchProcess:
        return False


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
        raise commons_errors.ProcessError(
            "Invalid pid for graceful stop via SIGTERM."
        )
    sigterm = getattr(signal, "SIGTERM", None)
    if sigterm is None:
        raise commons_errors.ProcessError(
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
        raise commons_errors.ProcessError(
            f"Failed to send stop signal to pid={pid}: {err}"
        ) from err
    resolved_logger.info("Sent graceful stop signal (sigterm) to pid=%s", pid)
    return {"status": "stopped", "signal": "sigterm"}


def request_force_kill(
    pid: int,
    *,
    logger: typing.Optional[typing.Any] = None,
) -> dict[str, typing.Any]:
    """Force-kill the process identified by ``pid`` (SIGKILL / TerminateProcess)."""
    resolved_logger = logger or commons_logging.get_logger(__name__)
    if pid <= 0:
        raise commons_errors.ProcessError("Invalid pid for force kill.")
    if not pid_is_running(pid):
        resolved_logger.info(
            "Force kill: pid=%s not running, treating as already stopped",
            pid,
        )
        return {"status": "already_stopped", "reason": "not_running"}
    try:
        psutil.Process(pid).kill()
    except psutil.NoSuchProcess:
        resolved_logger.info(
            "Force kill: pid=%s gone before kill",
            pid,
        )
        return {"status": "already_stopped", "reason": "not_running"}
    except Exception as err:
        if not pid_is_running(pid):
            resolved_logger.info(
                "Force kill: pid=%s gone after failed kill: %s",
                pid,
                err,
            )
            return {"status": "already_stopped", "reason": str(err)}
        resolved_logger.warning("Force kill failed for pid=%s: %s", pid, err)
        raise commons_errors.ProcessError(
            f"Failed to force kill pid={pid}: {err}"
        ) from err
    resolved_logger.info("Force killed pid=%s", pid)
    return {"status": "force_killed"}


async def wait_until_pid_stopped_async(
    pid: int,
    *,
    logger: typing.Optional[typing.Any] = None,
    timeout_seconds: float,
    poll_interval: float = 0.2,
) -> None:
    """Poll until ``pid`` is gone or ``timeout_seconds`` elapses."""
    resolved_logger = logger or commons_logging.get_logger(__name__)
    if pid <= 0:
        resolved_logger.info(
            "wait_until_pid_stopped_async: pid=%s treated as already stopped (non-positive)",
            pid,
        )
        return
    resolved_logger.info(
        "wait_until_pid_stopped_async: waiting for pid=%s to exit (timeout=%ss)",
        pid,
        timeout_seconds,
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not pid_is_running(pid):
            resolved_logger.info("wait_until_pid_stopped_async: pid=%s exited", pid)
            return
        await asyncio.sleep(poll_interval)
    raise commons_errors.ProcessError(
        f"Timed out after {timeout_seconds}s waiting for pid={pid} to exit."
    )


def rebind_managed_child_pid(spawn_pid: int, authoritative_pid: int) -> None:
    """Replace spawn pid with authoritative app pid in the managed-child registry."""
    import octobot_commons.managed_child_process_registry as managed_child_process_registry
    managed_child_process_registry.ManagedChildProcessRegistry.instance().rebind_managed_child_pid(
        spawn_pid,
        authoritative_pid,
    )


async def graceful_stop_managed_children(
    *,
    timeout_seconds: float,
    poll_interval: float = 0.2,
) -> dict[int, str]:
    """Gracefully stop all registered managed children (see ManagedChildProcessRegistry)."""
    import octobot_commons.managed_child_process_registry as managed_child_process_registry
    return await managed_child_process_registry.ManagedChildProcessRegistry.instance().graceful_stop_all(
        timeout_seconds=timeout_seconds,
        poll_interval=poll_interval,
    )
