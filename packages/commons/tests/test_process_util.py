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
import subprocess
import sys
import time

import mock

import pytest

import octobot_commons.errors as commons_errors
import octobot_commons.process_util as process_util


class TestSpawnManagedSubprocess:
    def test_popen_called_with_argv_cwd_env(self):
        fake_handle = mock.Mock(spec=subprocess.Popen)
        with mock.patch.object(
            process_util.subprocess,
            "Popen",
            return_value=fake_handle,
        ) as popen_mock:
            result = process_util.spawn_managed_subprocess(
                ["x", "y"],
                working_directory="/work",
                environment={"K": "V"},
                hide_console_window=False,
            )
        assert result is fake_handle
        popen_mock.assert_called_once()
        positional_args, keywords = popen_mock.call_args
        assert positional_args[0] == ["x", "y"]
        assert keywords["cwd"] == "/work"
        assert keywords["env"] == {"K": "V"}
        assert keywords.get("creationflags", 0) == 0

    def test_uses_os_environ_copy_when_environment_missing(self):
        with mock.patch.object(process_util.subprocess, "Popen") as popen_mock, mock.patch.dict(
            os.environ,
            {"EXISTING_ENV_KEY": "1"},
            clear=False,
        ):
            process_util.spawn_managed_subprocess([], working_directory="/w")
        _args, keywords = popen_mock.call_args
        assert keywords["env"]["EXISTING_ENV_KEY"] == "1"

    def test_creationflags_hide_console_on_windows(self):
        fake_handle = mock.Mock(spec=subprocess.Popen)
        with mock.patch.object(process_util.sys, "platform", "win32"), mock.patch.object(
            process_util.subprocess,
            "Popen",
            return_value=fake_handle,
        ) as popen_mock:
            process_util.spawn_managed_subprocess([], working_directory="/w", hide_console_window=True)
        _args, keywords = popen_mock.call_args
        assert keywords["creationflags"] == getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0,
        )


class TestPidIsRunning:
    def test_non_positive_pid_is_false(self):
        assert process_util.pid_is_running(0) is False
        assert process_util.pid_is_running(-1) is False

    def test_with_psutil_process_running_true(self):
        fake_process = mock.Mock()
        fake_process.status.return_value = process_util.psutil.STATUS_RUNNING
        fake_process.is_running.return_value = True
        with mock.patch.object(process_util.psutil, "Process", return_value=fake_process):
            assert process_util.pid_is_running(42) is True
        fake_process.is_running.assert_called_once()

    def test_with_psutil_zombie_is_not_running(self):
        """``is_running()`` can stay True for Linux zombies; we treat them as stopped for lifecycle waits."""
        fake_process = mock.Mock()
        fake_process.status.return_value = process_util.psutil.STATUS_ZOMBIE
        fake_process.is_running.return_value = True
        with mock.patch.object(process_util.psutil, "Process", return_value=fake_process):
            assert process_util.pid_is_running(42) is False
        fake_process.is_running.assert_not_called()

    def test_with_psutil_zombie_process_exception_from_status(self):
        fake_process = mock.Mock()
        fake_process.status.side_effect = process_util.psutil.ZombieProcess(42)
        with mock.patch.object(process_util.psutil, "Process", return_value=fake_process):
            assert process_util.pid_is_running(42) is False

    def test_with_psutil_no_such_process(self):
        fake_process_constructor = mock.Mock(
            side_effect=process_util.psutil.NoSuchProcess(42),
        )
        with mock.patch.object(process_util.psutil, "Process", fake_process_constructor):
            assert process_util.pid_is_running(42) is False

    def test_with_psutil_no_such_process_from_status_after_process_ctor(self):
        """Process() succeeds but status() raises (race: exited between ctor and probe, common on Windows)."""
        fake_process = mock.Mock()
        fake_process.status.side_effect = process_util.psutil.NoSuchProcess(42)
        with mock.patch.object(process_util.psutil, "Process", return_value=fake_process):
            assert process_util.pid_is_running(42) is False

    def test_with_psutil_no_such_process_from_is_running(self):
        fake_process = mock.Mock()
        fake_process.status.return_value = process_util.psutil.STATUS_RUNNING
        fake_process.is_running.side_effect = process_util.psutil.NoSuchProcess(42)
        with mock.patch.object(process_util.psutil, "Process", return_value=fake_process):
            assert process_util.pid_is_running(42) is False


class TestRequestGracefulStopViaSigterm:
    def test_invalid_pid_raises(self):
        with pytest.raises(commons_errors.DSLInterpreterError, match="Invalid pid"):
            process_util.request_graceful_stop_via_sigterm(0)

    def test_raises_when_sigterm_unavailable(self):
        sentinel_signal_module = mock.Mock()
        sentinel_signal_module.SIGTERM = None
        with mock.patch.object(process_util, "signal", sentinel_signal_module):
            with pytest.raises(commons_errors.DSLInterpreterError, match="SIGTERM is not available"):
                process_util.request_graceful_stop_via_sigterm(10)

    def test_returns_already_stopped_when_pid_not_running(self):
        with mock.patch.object(process_util, "pid_is_running", return_value=False):
            result = process_util.request_graceful_stop_via_sigterm(55)
        assert result["status"] == "already_stopped"

    def test_os_kill_after_signal_when_process_exits_raises_oserror_returns_already_stopped(self):
        with (
            mock.patch.object(process_util, "pid_is_running", side_effect=[True, False]),
            mock.patch.object(process_util.os, "kill", side_effect=OSError("send failed")),
        ):
            result = process_util.request_graceful_stop_via_sigterm(77)
        assert result["status"] == "already_stopped"

    def test_os_kill_failure_when_still_running_wraps_error(self):
        with (
            mock.patch.object(process_util, "pid_is_running", return_value=True),
            mock.patch.object(process_util.os, "kill", side_effect=OSError("perm denied")),
        ):
            with pytest.raises(
                commons_errors.DSLInterpreterError,
                match=r"Failed to send stop signal to pid=88",
            ):
                process_util.request_graceful_stop_via_sigterm(88)


class TestSpawnManagedSubprocessGracefulStopIntegration:
    def test_spawned_sleeping_child_can_be_stopped_by_request_graceful_stop_via_sigterm(
        self,
        tmp_path,
    ):
        child = process_util.spawn_managed_subprocess(
            [
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            ],
            working_directory=str(tmp_path),
        )
        try:
            assert process_util.pid_is_running(child.pid), "child process should be running"
            result = process_util.request_graceful_stop_via_sigterm(child.pid)
            assert result["status"] == "stopped"
            assert result.get("signal") == "sigterm"
            deadline = time.monotonic() + 25.0
            while child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            assert child.poll() is not None, "child should exit after graceful stop"
            child.wait(timeout=5)
            assert not process_util.pid_is_running(child.pid)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
