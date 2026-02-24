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

"""
Monitored Process

Base class for async context managers that spawn, monitor, and gracefully terminate
external subprocesses.

Provides:
- Subprocess lifecycle management (start → ready → stop)
- Background stdout/stderr monitoring with error-pattern detection
- Readiness detection via a configurable string match
- Premature-exit detection
- Graceful SIGTERM with forced SIGKILL fallback

Subclasses must implement ``_get_subprocess_args()`` and set ``READINESS_STRING``.
All other hooks have sensible defaults that can be overridden as needed.

Example::

    class MyProcess(MonitoredProcess):
        READINESS_STRING = "server ready"
        ERROR_PATTERNS = ["FATAL"]
        READINESS_TIMEOUT_SECONDS = 30.0

        def __init__(self, port: int):
            super().__init__()
            self._port = port

        def _get_subprocess_args(self) -> list[str]:
            return ["myserver", "--port", str(self._port)]

    async with MyProcess(port=8080) as proc:
        # subprocess is up and the "server ready" line was found in its output
        ...
"""

import asyncio
import logging
import typing


class MonitoredProcessError(Exception):
    """Base error for all monitored-process failures."""


class MonitoredProcessOutputError(MonitoredProcessError):
    """Raised when an error pattern is found in process stdout/stderr."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        message: str,
        stream: str,
        line: str,
        std_out_buffer: list[str],
        std_err_buffer: list[str],
    ):
        self.stream = stream
        self.line = line
        self.std_out_buffer = '\n'.join(std_out_buffer) if std_out_buffer else None
        self.std_err_buffer = '\n'.join(std_err_buffer) if std_err_buffer else None
        super().__init__(
            f"{message} ({stream}): {line}"
            f"{chr(10) + 'stdout:' + chr(10) if self.std_out_buffer else ''}{self.std_out_buffer or ''}"
            f"{chr(10) + 'stderr:' + chr(10) if self.std_err_buffer else ''}{self.std_err_buffer or ''}"
        )


class MonitoredProcessConfigurationError(MonitoredProcessError):
    """Raised when the executable is not found or the process cannot be started."""

    def __init__(self, message: str):
        super().__init__(message)


class MonitoredProcessReadyTimeoutError(MonitoredProcessError):
    """Raised when the readiness string is not detected within the timeout."""

    def __init__(self, readiness_string: str, timeout_seconds: float):
        self.readiness_string = readiness_string
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Did not find '{readiness_string}' in process output within {timeout_seconds}s"
        )


class MonitoredProcessExitedError(MonitoredProcessError):
    """Raised when the process exits prematurely (before the context exits)."""

    def __init__(self, exit_code: typing.Optional[int], stderr: typing.Optional[str] = None):
        self.exit_code = exit_code
        self.stderr = stderr
        msg = f"Process exited prematurely with code {exit_code}"
        if stderr:
            msg += f"; stderr: {stderr}"
        super().__init__(msg)


class MonitoredProcess:  # pylint: disable=too-many-instance-attributes
    """
    Async context manager that spawns and monitors a subprocess.

    Lifecycle
    ---------
    ``__aenter__``:
      1. Calls ``_get_subprocess_args()`` (and optionally ``_get_subprocess_env()`` /
         ``_get_subprocess_cwd()``) to build the subprocess invocation.
      2. Starts background tasks that stream stdout/stderr and watch for process exit.
      3. Blocks until ``READINESS_STRING`` is found in the output (or an error occurs).

    ``__aexit__``:
      1. Cancels the background monitor tasks.
      2. Sends SIGTERM; waits up to ``TERMINATE_TIMEOUT_SECONDS``; sends SIGKILL on timeout.
      3. Re-raises any error captured by the monitors.

    Subclassing
    -----------
    **Must override**:
    - ``_get_subprocess_args() -> list[str]``  — full command ``[program, arg, ...]``
    - ``READINESS_STRING: str``                — substring to watch for in output

    **May override** (all have sensible defaults):
    - ``ERROR_PATTERNS: list[str]``            — substrings that signal a fatal error
    - ``TERMINATE_TIMEOUT_SECONDS: float``     — time before forced kill (default 10 s)
    - ``READINESS_TIMEOUT_SECONDS: float``     — readiness wait limit (default 60 s)
    - ``_get_subprocess_env()``                — environment dict or None (inherit)
    - ``_get_subprocess_cwd()``                — working directory or None (inherit)
    - ``_make_output_error(...)``              — override to raise a subclass-specific type
    - ``_make_exited_error(...)``              — override to raise a subclass-specific type
    - ``_make_ready_timeout_error()``          — override to raise a subclass-specific type
    - ``_make_configuration_error(message)``   — override to raise a subclass-specific type
    """

    TERMINATE_TIMEOUT_SECONDS: float = 10.0
    READINESS_TIMEOUT_SECONDS: float = 60.0

    #: Substring that must appear in stdout/stderr for the process to be considered ready.
    READINESS_STRING: str = ""

    #: Substrings that indicate a fatal error; triggers ``_make_output_error`` when matched.
    ERROR_PATTERNS: list[str] = []

    def __init__(self) -> None:
        self._process: typing.Optional[asyncio.subprocess.Process] = None  # pylint: disable=no-member
        self._monitor_tasks: list[asyncio.Task] = []
        self._monitor_error: typing.Optional[BaseException] = None
        self._ready_event = asyncio.Event()
        self._error_event = asyncio.Event()
        self._shutting_down = False
        self._stderr_buffer: list[str] = []
        self._stdout_buffer: list[str] = []
        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def _get_subprocess_args(self) -> list[str]:
        """Return the full command: ``[program, arg1, arg2, ...]``."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _get_subprocess_args()"
        )

    def _get_subprocess_env(self) -> typing.Optional[dict[str, str]]:
        """Return the environment mapping for the subprocess, or ``None`` to inherit."""
        return None

    def _get_subprocess_cwd(self) -> typing.Optional[str]:
        """Return the working directory for the subprocess, or ``None`` to inherit."""
        return None

    # --- error factories (override to return subclass-specific types) -----

    def _make_output_error(
        self,
        stream: str,
        line: str,
        stdout_buf: list[str],
        stderr_buf: list[str],
    ) -> BaseException:
        return MonitoredProcessOutputError(
            f"{self.__class__.__name__} error", stream, line, stdout_buf, stderr_buf
        )

    def _make_exited_error(
        self,
        exit_code: typing.Optional[int],
        output_err: typing.Optional[str],
    ) -> BaseException:
        return MonitoredProcessExitedError(exit_code, output_err)

    def _make_ready_timeout_error(self) -> BaseException:
        return MonitoredProcessReadyTimeoutError(
            self.READINESS_STRING, self.READINESS_TIMEOUT_SECONDS
        )

    def _make_configuration_error(self, message: str) -> BaseException:
        return MonitoredProcessConfigurationError(message)

    async def __aenter__(self) -> "MonitoredProcess":
        """Spawn the subprocess and block until it signals readiness."""
        args = self._get_subprocess_args()
        self._logger.info("Spawning %s: %s", self.__class__.__name__, ' '.join(args))
        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._get_subprocess_cwd(),
                env=self._get_subprocess_env(),
            )
        except FileNotFoundError as e:
            raise self._make_configuration_error(
                f"Executable '{args[0]}' not found"
            ) from e
        self._logger.debug(
            "Started %s with pid: %s", self.__class__.__name__, self._process.pid
        )
        self._start_output_monitor()
        await self._wait_for_ready()
        self._logger.info("%s is ready", self.__class__.__name__)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Terminate the subprocess and cancel monitors; re-raise any captured error."""
        self._shutting_down = True

        self._logger.debug("Cancelling monitor tasks")
        for task in self._monitor_tasks:
            task.cancel()
        if self._monitor_tasks:
            await asyncio.gather(*self._monitor_tasks, return_exceptions=True)
        self._monitor_tasks.clear()
        self._logger.debug("Monitor tasks cancelled")

        if self._process is None:
            if self._monitor_error is not None:
                raise self._monitor_error
            return

        if self._process.returncode is None:
            self._process.terminate()
            graceful = True
            try:
                self._logger.debug(
                    "Waiting for %s to terminate", self.__class__.__name__
                )
                await asyncio.wait_for(
                    self._process.wait(),
                    timeout=self.TERMINATE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                self._logger.warning(
                    "Terminate timeout, killing %s", self.__class__.__name__
                )
                self._process.kill()
                await self._process.wait()
                graceful = False

            self._logger.info(
                "%s %s terminated",
                self.__class__.__name__,
                'gracefully' if graceful else 'forcibly',
            )
        self._process = None

        self._stderr_buffer.clear()
        self._stdout_buffer.clear()

        if self._monitor_error is not None:
            raise self._monitor_error

    async def _wait_for_ready(self) -> None:
        """Block until ``READINESS_STRING`` is found or a monitor error is detected."""
        self._logger.info("Waiting for %s to be ready", self.__class__.__name__)

        async def wait_ready_or_error() -> None:
            ready_task = asyncio.create_task(self._ready_event.wait())
            error_task = asyncio.create_task(self._error_event.wait())
            done, pending = await asyncio.wait(
                [ready_task, error_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            if error_task in done or self._monitor_error is not None:
                raise self._monitor_error  # type: ignore[misc]

        try:
            await asyncio.wait_for(
                wait_ready_or_error(),
                timeout=self.READINESS_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            if self._monitor_error is not None:
                raise self._monitor_error
            raise self._make_ready_timeout_error()

    def _start_output_monitor(self) -> None:
        """
        Spawn three background tasks:

        - ``read_stream(stdout)`` — logs and scans stdout for the readiness string
          and error patterns.
        - ``read_stream(stderr)`` — same for stderr.
        - ``watch_exit``          — detects premature non-zero exits.

        Captured errors are stored in ``_monitor_error`` and re-raised in ``__aexit__``.
        """
        if self._process is None:
            raise MonitoredProcessError(
                "Process not started; call _start_output_monitor() inside the context"
            )
        if not self._process.stdout or not self._process.stderr:
            raise MonitoredProcessError("stdout/stderr are not PIPE")
        if self._monitor_tasks:
            return  # Already started

        async def read_stream(stream: asyncio.StreamReader, name: str) -> None:
            while True:
                line = await stream.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").rstrip()
                self._logger.debug("[%s] %s", name, line_str)
                if name == "stderr":
                    self._stderr_buffer.append(line_str)
                else:
                    self._stdout_buffer.append(line_str)
                if self.READINESS_STRING and self.READINESS_STRING in line_str:
                    self._ready_event.set()
                for pat in self.ERROR_PATTERNS:
                    if pat in line_str and self._monitor_error is None:
                        self._logger.error(
                            "[%s] [%s] %s", self.__class__.__name__, name, line_str
                        )
                        self._monitor_error = self._make_output_error(
                            name, line_str,
                            self._stdout_buffer, self._stderr_buffer,
                        )
                        self._error_event.set()
                        break

        async def watch_exit() -> None:
            if self._process is None:
                return
            exit_code = await self._process.wait()
            if not self._shutting_down and exit_code != 0 and self._monitor_error is None:
                output_err = "\n".join(self._stderr_buffer) if self._stderr_buffer else (
                    "\n".join(self._stdout_buffer) if self._stdout_buffer else None
                )
                self._monitor_error = self._make_exited_error(exit_code, output_err)
                self._error_event.set()

        self._monitor_tasks = [
            asyncio.create_task(read_stream(self._process.stdout, "stdout")),
            asyncio.create_task(read_stream(self._process.stderr, "stderr")),
            asyncio.create_task(watch_exit()),
        ]

    def log_output(self, last_lines: int) -> None:
        """Log the stdout and stderr buffers."""
        self._logger.info("%s last %s lines from stdout and stderr outputs:\n", self.__class__.__name__, last_lines)
        if self._stdout_buffer:
            self._logger.info("stdout:\n%s", '\n'.join(self._stdout_buffer[-last_lines:]))
        if self._stderr_buffer:
            self._logger.info("stderr:\n%s", '\n'.join(self._stderr_buffer[-last_lines:]))
