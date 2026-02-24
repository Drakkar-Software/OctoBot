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
import unittest.mock as mock

import pytest

import octobot_commons.monitored_process as monitored_process

pytestmark = pytest.mark.asyncio


class _SimpleProcess(monitored_process.MonitoredProcess):
    """Minimal concrete subclass used as system under test."""

    READINESS_STRING = "ready"
    ERROR_PATTERNS = ["FATAL"]
    TERMINATE_TIMEOUT_SECONDS = 0.1
    READINESS_TIMEOUT_SECONDS = 1.0

    def _get_subprocess_args(self) -> list:
        return ["mybin", "--flag"]


def _make_stream(*lines: str) -> asyncio.StreamReader:
    """Create a StreamReader pre-filled with the given lines (each terminated with \\n)."""
    reader = asyncio.StreamReader()
    for line in lines:
        reader.feed_data((line + "\n").encode())
    reader.feed_eof()
    return reader


def _make_mock_process(
    stdout_lines: list = None,
    stderr_lines: list = None,
    returncode: int = None,
    pid: int = 1234,
):
    """
    Build a mock asyncio.subprocess.Process whose stdout/stderr are real
    StreamReaders pre-loaded with the given lines.
    """
    proc = mock.MagicMock()
    proc.pid = pid
    proc.returncode = returncode

    proc.stdout = _make_stream(*(stdout_lines or []))
    proc.stderr = _make_stream(*(stderr_lines or []))

    # proc.wait() returns an awaitable that resolves to returncode.
    async def _wait():
        # Drain the streams first so _start_output_monitor tasks finish.
        while not proc.stdout.at_eof():
            await asyncio.sleep(0)
        while not proc.stderr.at_eof():
            await asyncio.sleep(0)
        return returncode if returncode is not None else 0

    proc.wait = _wait
    proc.terminate = mock.MagicMock()
    proc.kill = mock.MagicMock()
    return proc

async def test_happy_path_readiness_in_stdout():
    proc = _make_mock_process(stdout_lines=["startup log", "ready", "more output"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess() as p:
            assert p._ready_event.is_set()
            assert p._monitor_error is None


async def test_happy_path_readiness_in_stderr():
    proc = _make_mock_process(stderr_lines=["ready"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess() as p:
            assert p._ready_event.is_set()


async def test_subprocess_args_passed_correctly():
    proc = _make_mock_process(stdout_lines=["ready"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        async with _SimpleProcess():
            pass
    mock_exec.assert_called_once()
    call_args = mock_exec.call_args
    assert call_args.args == ("mybin", "--flag")


async def test_env_and_cwd_defaults():
    proc = _make_mock_process(stdout_lines=["ready"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        async with _SimpleProcess():
            pass
    kwargs = mock_exec.call_args.kwargs
    assert kwargs["cwd"] is None
    assert kwargs["env"] is None


async def test_stdout_lines_go_to_stdout_buffer():
    proc = _make_mock_process(stdout_lines=["ready", "line2"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess() as p:
            # Allow monitor tasks to finish draining
            await asyncio.sleep(0.05)
            assert "ready" in p._stdout_buffer
            assert "line2" in p._stdout_buffer
            assert len(p._stderr_buffer) == 0


async def test_stderr_lines_go_to_stderr_buffer():
    proc = _make_mock_process(stdout_lines=["ready"], stderr_lines=["err1", "err2"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess() as p:
            await asyncio.sleep(0.05)
            assert "err1" in p._stderr_buffer
            assert "err2" in p._stderr_buffer


async def test_graceful_shutdown_calls_terminate():
    proc = _make_mock_process(stdout_lines=["ready"])
    # returncode is None while running; set to 0 after terminate
    proc.returncode = None

    terminate_called = asyncio.Event()

    original_terminate = proc.terminate

    def _terminate():
        proc.returncode = 0
        terminate_called.set()
        original_terminate()

    proc.terminate = _terminate

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess():
            pass

    assert terminate_called.is_set()
    proc.kill.assert_not_called()


async def test_forced_kill_when_terminate_times_out():
    proc = _make_mock_process(stdout_lines=["ready"])
    proc.returncode = None

    # wait() never resolves — simulates a hung process.
    hang = asyncio.Event()

    async def _hanging_wait():
        await hang.wait()
        return 0

    proc.wait = _hanging_wait
    proc.terminate = mock.MagicMock()
    proc.kill = mock.MagicMock(side_effect=lambda: hang.set())

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess():
            pass

    proc.terminate.assert_called_once()
    proc.kill.assert_called_once()


async def test_error_pattern_in_stdout_raises_output_error():
    proc = _make_mock_process(stdout_lines=["starting up", "FATAL: something broke"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessOutputError) as exc_info:
            async with _SimpleProcess():
                pass
    assert "FATAL: something broke" in str(exc_info.value)
    assert exc_info.value.stream == "stdout"


async def test_error_pattern_in_stderr_raises_output_error():
    proc = _make_mock_process(
        stdout_lines=["ready"],
        stderr_lines=["FATAL: stderr error"],
    )
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessOutputError) as exc_info:
            async with _SimpleProcess():
                # Keep the context alive long enough for the stderr monitor to fire.
                await asyncio.sleep(0.05)
    assert exc_info.value.stream == "stderr"


async def test_readiness_timeout_raises_ready_timeout_error():
    class _NoReadyProcess(monitored_process.MonitoredProcess):
        READINESS_STRING = "never-appears"
        READINESS_TIMEOUT_SECONDS = 0.05

        def _get_subprocess_args(self) -> list:
            return ["mybin"]

    proc = _make_mock_process(stdout_lines=["line without readiness string"])
    # Make wait() block so the process doesn't exit before the timeout.
    block = asyncio.Event()

    async def _wait():
        await block.wait()
        return 0

    proc.wait = _wait

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessReadyTimeoutError) as exc_info:
            async with _NoReadyProcess():
                pass
    block.set()
    assert exc_info.value.readiness_string == "never-appears"
    assert exc_info.value.timeout_seconds == 0.05


async def test_premature_exit_nonzero_raises_exited_error():
    proc = _make_mock_process(
        stderr_lines=["something went wrong"],
        returncode=1,
    )
    # Ensure returncode is None initially so watch_exit() fires.
    proc.returncode = None

    async def _exit_quickly():
        return 1

    proc.wait = _exit_quickly

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessExitedError) as exc_info:
            async with _SimpleProcess():
                # Give monitor tasks a moment to detect the exit.
                await asyncio.sleep(0.1)
    assert exc_info.value.exit_code == 1


async def test_configuration_error_on_missing_executable():
    with mock.patch(
        "asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError("mybin not found"),
    ):
        with pytest.raises(monitored_process.MonitoredProcessConfigurationError):
            async with _SimpleProcess():
                pass


async def test_monitor_error_reraised_on_aexit():
    """An error captured after __aenter__ is re-raised when the context exits."""
    proc = _make_mock_process(stdout_lines=["ready"])
    proc.returncode = None

    async def _exit_after_ready():
        # Wait a tiny bit so __aenter__ completes first
        await asyncio.sleep(0.02)
        return 2

    proc.wait = _exit_after_ready

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessExitedError):
            async with _SimpleProcess():
                await asyncio.sleep(0.1)


async def test_monitor_error_not_suppressed_after_stdout_buffer_clear():
    """Monitor error is still raised even though __aexit__ clears stdout buffer first."""
    proc = _make_mock_process(stdout_lines=["ready"])
    expected_error = monitored_process.MonitoredProcessExitedError(7)

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessExitedError) as exc_info:
            async with _SimpleProcess() as p:
                p._stdout_buffer.extend(["ready", "extra line"])
                p._monitor_error = expected_error
        assert exc_info.value is expected_error


class _CustomOutputError(monitored_process.MonitoredProcessOutputError):
    pass


class _CustomExitedError(monitored_process.MonitoredProcessExitedError):
    pass


class _CustomTimeoutError(monitored_process.MonitoredProcessReadyTimeoutError):
    pass


class _CustomConfigError(monitored_process.MonitoredProcessConfigurationError):
    pass


class _CustomProcess(_SimpleProcess):
    READINESS_TIMEOUT_SECONDS = 0.05

    def _make_output_error(self, stream, line, stdout_buf, stderr_buf):
        return _CustomOutputError("custom", stream, line, stdout_buf, stderr_buf)

    def _make_exited_error(self, exit_code, output_err):
        return _CustomExitedError(exit_code, output_err)

    def _make_ready_timeout_error(self):
        return _CustomTimeoutError(self.READINESS_STRING, self.READINESS_TIMEOUT_SECONDS)

    def _make_configuration_error(self, message):
        return _CustomConfigError(message)


async def test_custom_output_error_factory():
    proc = _make_mock_process(stdout_lines=["FATAL: boom"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(_CustomOutputError):
            async with _CustomProcess():
                pass


async def test_custom_ready_timeout_error_factory():
    class _NeverReady(_CustomProcess):
        READINESS_STRING = "never-appears"

    proc = _make_mock_process(stdout_lines=["no ready here"])
    block = asyncio.Event()

    async def _wait():
        await block.wait()
        return 0

    proc.wait = _wait

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(_CustomTimeoutError):
            async with _NeverReady():
                pass
    block.set()


async def test_custom_configuration_error_factory():
    with mock.patch(
        "asyncio.create_subprocess_exec",
        side_effect=FileNotFoundError,
    ):
        with pytest.raises(_CustomConfigError):
            async with _CustomProcess():
                pass

async def test_output_error_includes_buffers():
    proc = _make_mock_process(
        stdout_lines=["stdout line 1", "FATAL: crash"],
        stderr_lines=["stderr line 1"],
    )
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessOutputError) as exc_info:
            async with _SimpleProcess():
                await asyncio.sleep(0.05)
    err = exc_info.value
    assert err.std_out_buffer is not None
    assert "stdout line 1" in err.std_out_buffer


async def test_exited_error_includes_stderr():
    proc = _make_mock_process(
        stderr_lines=["crash info"],
        returncode=None,
    )

    async def _exit_quickly():
        return 3

    proc.wait = _exit_quickly

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessExitedError) as exc_info:
            async with _SimpleProcess():
                await asyncio.sleep(0.1)
    assert exc_info.value.exit_code == 3


async def test_log_output_logs_last_lines_from_buffers():
    """log_output logs the last N lines from stdout and stderr buffers."""
    proc = _make_mock_process(
        stdout_lines=["ready", "line2", "line3", "line4"],
        stderr_lines=["err1", "err2", "err3"],
    )
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess() as p:
            await asyncio.sleep(0.05)
            with mock.patch.object(p._logger, "info") as mock_info:
                p.log_output(last_lines=2)
            mock_info.assert_any_call(
                "%s last %s lines from stdout and stderr outputs:\n",
                p.__class__.__name__,
                2,
            )
            mock_info.assert_any_call("stdout:\n%s", "line3\nline4")
            mock_info.assert_any_call("stderr:\n%s", "err2\nerr3")


async def test_log_output_handles_empty_buffers():
    """log_output does not log stdout/stderr sections when buffers are empty."""
    proc = _make_mock_process(stdout_lines=["ready"])
    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        async with _SimpleProcess() as p:
            await asyncio.sleep(0.05)
            p._stderr_buffer.clear()
            with mock.patch.object(p._logger, "info") as mock_info:
                p.log_output(last_lines=5)
            # Header + stdout only (stderr buffer was cleared)
            assert mock_info.call_count == 2
            mock_info.assert_any_call(
                "%s last %s lines from stdout and stderr outputs:\n",
                p.__class__.__name__,
                5,
            )
            mock_info.assert_any_call("stdout:\n%s", "ready")


async def test_empty_readiness_string_never_fires_ready():
    """When READINESS_STRING is empty, the ready event is never set by output."""

    class _NoReadinessProcess(monitored_process.MonitoredProcess):
        READINESS_STRING = ""
        READINESS_TIMEOUT_SECONDS = 0.05

        def _get_subprocess_args(self) -> list:
            return ["mybin"]

    proc = _make_mock_process(stdout_lines=["some output"])
    block = asyncio.Event()

    async def _wait():
        await block.wait()
        return 0

    proc.wait = _wait

    with mock.patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(monitored_process.MonitoredProcessReadyTimeoutError):
            async with _NoReadinessProcess():
                pass
    block.set()
